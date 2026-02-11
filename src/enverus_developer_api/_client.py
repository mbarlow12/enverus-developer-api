"""Synchronous clients for the Enverus Developer API."""

from __future__ import annotations

import csv
import json
import logging
import os
import re
from collections import OrderedDict
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any, cast
from uuid import uuid4

import httpx

from enverus_developer_api._auth import _TokenAuth
from enverus_developer_api._exceptions import (
    DAAuthException,
    DAQueryException,
)
from enverus_developer_api._retry import RetryTransport
from enverus_developer_api._types import Record, RecordIterator
from enverus_developer_api._utils import detect_query_chunks, in_, parse_body_links


class BaseClient:
    """Abstract base for Enverus Developer API clients.

    Handles session setup, retries, auth lifecycle, and utility methods.
    """

    url: str

    def __init__(
        self,
        *,
        retries: int = 5,
        backoff_factor: float = 1.0,
        verify: bool = True,
        proxy: str | None = None,
        access_token: str | None = None,
        log_level: int = logging.INFO,
        logger: logging.Logger | None = None,
    ) -> None:
        if logger:
            self.logger = logger.getChild("directaccess")
        else:
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
                datefmt="%a, %d %b %Y %H:%M:%S",
            )
            self.logger = logging.getLogger("directaccess")

        self.retries = retries
        self.backoff_factor = backoff_factor
        self.access_token = access_token

        transport = RetryTransport(
            transport=httpx.HTTPTransport(verify=verify, proxy=proxy),
            retries=retries,
            backoff_factor=backoff_factor,
        )
        self._client = httpx.Client(
            transport=transport,
            headers={"User-Agent": "enverus-developer-api"},
            auth=_TokenAuth(self),
            timeout=httpx.Timeout(30.0),
        )

    def __enter__(self) -> BaseClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_access_token(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def in_(items: list[Any]) -> str:
        """Helper for the API's ``in()`` filter function."""
        return in_(items)

    def ddl(self, dataset: str, *, database: str) -> str:
        """Get DDL statement for dataset.

        Args:
            dataset: A valid dataset name.
            database: One of ``mssql`` or ``pg``.
        """
        ddl_url = f"{self.url}{dataset}"
        self.logger.debug(f"Retrieving DDL for dataset: {dataset}")
        response = self._client.get(ddl_url, params={"ddl": database})
        return response.text

    def docs(self, dataset: str) -> list[Record] | None:
        """Get docs for dataset."""
        docs_url = f"{self.url}{dataset}"
        self.logger.debug(f"Retrieving docs for dataset: {dataset}")
        response = self._client.get(docs_url, params={"docs": "true"})
        if response.status_code == 501:
            self.logger.warning(
                f"docs and example params are not yet supported on dataset {dataset}"
            )
            return None
        return response.json()  # type: ignore[no-any-return]

    def count(self, dataset: str, **options: Any) -> int:
        """Get the count of records for a dataset and query options."""
        head_url = f"{self.url}{dataset}"
        response = self._client.head(head_url, params=options)
        count = response.headers.get("X-Query-Record-Count")
        return int(count)

    def to_csv(
        self,
        query: RecordIterator,
        path: str,
        *,
        log_progress: bool = True,
        **kwargs: Any,
    ) -> str:
        """Write query results to CSV.

        Args:
            query: A query generator from :meth:`query`.
            path: Filesystem path for created CSV.
            log_progress: If True, log a message every 100k rows.
            **kwargs: Passed to :class:`csv.writer`.
        """
        with open(path, mode="w", newline="") as f:
            writer = csv.writer(f, **kwargs)
            count = 0
            for i, row in enumerate(query, start=1):
                row = OrderedDict(sorted(row.items(), key=lambda t: t[0]))
                count = i
                if count == 1:
                    writer.writerow(row.keys())
                writer.writerow(row.values())

                if log_progress and i % 100000 == 0:
                    self.logger.info(f"Wrote {count} records to file {path}")
            self.logger.info(
                f"Completed writing CSV file to {path}. Final count {count}"
            )
        return path

    def to_dataframe(
        self,
        dataset: str,
        *,
        converters: dict[str, Any] | None = None,
        log_progress: bool = True,
        **options: Any,
    ) -> Any:
        """Write query results to a pandas DataFrame with properly set dtypes.

        Args:
            dataset: A valid dataset name.
            converters: Dict of functions for converting column values.
            log_progress: If True, log progress messages.
            **options: Query parameters as keyword arguments.
        """
        try:
            import pandas
        except ImportError:
            raise ImportError(
                "pandas not installed. Install with: pip install 'enverus-developer-api[pandas]'"
            )

        ddl_text = self.ddl(dataset, database="mssql")

        try:
            index_col: list[str] | str | None = re.findall(
                r"PRIMARY KEY \(([a-z0-9_,]*)\)", ddl_text
            )[0].split(",")
        except IndexError:
            index_col = None

        self.logger.debug(f"index_col: {index_col}")
        ddl_map = {
            x.split(" ")[0]: x.split(" ")[1][:-1]
            for x in ddl_text.split("\n")[1:]
            if x and "CONSTRAINT" not in x
        }

        pagesize = options.pop("pagesize", None)
        try:
            filter_ = OrderedDict(
                sorted(
                    next(self.query(dataset, pagesize=1, **options)).items(),
                    key=lambda x: x[0],
                )
            ).keys()
            self.logger.debug(
                f"Fields retrieved from query response: {json.dumps(list(filter_), indent=2, default=str)}"
            )
        except StopIteration:
            raise DAQueryException("No results returned from query")

        if pagesize:
            options["pagesize"] = pagesize

        try:
            assert isinstance(index_col, list)
            index_col = [
                x for x in filter_ if x.upper() in [y.upper() for y in index_col]
            ]
            if index_col and len(index_col) == 1:
                index_col = index_col[0]
        except (IndexError, TypeError, AssertionError) as e:
            self.logger.warning(f"Could not discover index col(s): {e}")
            index_col = None
        self.logger.debug(f"index_col: {index_col}")

        date_cols = [
            k for k, v in ddl_map.items() if v.startswith("DATE") and k in filter_
        ]
        self.logger.debug(f"date columns:\n{json.dumps(date_cols, indent=2)}")

        for k, v in ddl_map.items():
            if k in filter_:
                if v.startswith("VARCHAR"):
                    ddl_map[k] = "VARCHAR"
                elif v.startswith("DOUBL"):
                    ddl_map[k] = "DOUBLE"

        dtypes_mapping = {
            "TEXT": "object",
            "NUMERIC": "float64",
            "REAL": "float64",
            "DOUBLE": "float64",
            "DATETIME": "object",
            "SMALLINT": "Int64",
            "INT": "Int64",
            "INTEGER": "Int64",
            "BIGINT": "Int64",
            "VARCHAR": "object",
            "DATE": "object",
        }
        dtypes = {k: dtypes_mapping[v] for k, v in ddl_map.items() if k in filter_}
        self.logger.debug(f"dtypes:\n{json.dumps(dtypes, indent=2)}")

        t = mkdtemp()
        self.logger.debug(f"Created temporary directory: {t}")

        query = self.query(dataset, **options)

        try:
            pd_chunks = pandas.read_csv(
                filepath_or_buffer=self.to_csv(
                    query,
                    os.path.join(t, f"{uuid4().hex}.csv"),
                    delimiter="|",
                    log_progress=log_progress,
                ),
                sep="|",
                dtype=cast(Any, dtypes),
                index_col=index_col,
                parse_dates=date_cols,
                chunksize=options.get("pagesize", 100000),
                converters=converters,
            )
            df: Any = pandas.concat(pd_chunks)
            return df
        finally:
            rmtree(t)
            self.logger.debug("Removed temporary directory")

    def query(self, dataset: str, **options: Any) -> RecordIterator:
        raise NotImplementedError


class DirectAccessV2(BaseClient):
    """Client for Enverus Developer API Version 2."""

    url = "https://di-api.drillinginfo.com/v2/direct-access/"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        retries: int = 5,
        backoff_factor: float = 1.0,
        access_token: str | None = None,
        verify: bool = True,
        proxy: str | None = None,
        log_level: int = logging.INFO,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            retries=retries,
            backoff_factor=backoff_factor,
            access_token=access_token,
            verify=verify,
            proxy=proxy,
            log_level=log_level,
            logger=logger,
        )
        self.client_id = client_id
        self.client_secret = client_secret

        if self.access_token:
            pass  # Already set by super().__init__
        else:
            self.access_token = self.get_access_token()["access_token"]

    def get_access_token(self) -> dict[str, Any]:
        """Get an access token from /tokens endpoint."""
        if not self.client_id or not self.client_secret:
            raise DAAuthException(
                "CLIENT_ID and CLIENT_SECRET are required to generate an access token"
            )

        import base64

        token_url = f"{self.url}tokens"
        auth_value = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        response = self._client.post(
            token_url,
            params={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {auth_value}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        self.logger.debug(f"Token response: {json.dumps(response.json(), indent=2)}")
        self.access_token = response.json()["access_token"]
        return response.json()  # type: ignore[no-any-return]

    def query(self, dataset: str, **options: Any) -> RecordIterator:
        """Query a Developer API v2 dataset. Returns a generator of dicts."""
        query_url = f"{self.url}{dataset}"

        query_chunks = detect_query_chunks(options)
        chunk_idx = 0

        paging = options.pop("paging", "true")
        links: dict[str, Any] | None = None

        while True:
            if links:
                response = self._client.get(self.url[:-1] + links["next"]["url"])
            else:
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    options[query_chunks[0]] = in_(query_chunks[1][chunk_idx])
                    chunk_idx += 1

                response = self._client.get(query_url, params=options)

            if not response.is_success:
                raise DAQueryException(
                    f"Non-200 response: {response.status_code} {response.text}"
                )

            records = response.json()
            if isinstance(records, dict):
                records = [records]

            if not records:
                links = None
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    continue
                break

            if "next" in response.links:
                links = cast(dict[str, Any], response.links)
            else:
                links = None

            yield from records

            if links is None or paging.lower() == "false":
                break


class DeveloperAPIv3(BaseClient):
    """Client for Enverus Developer API Version 3."""

    url = "https://api.enverus.com/v3/direct-access/"

    def __init__(
        self,
        secret_key: str,
        *,
        retries: int = 5,
        backoff_factor: float = 1.0,
        access_token: str | None = None,
        verify: bool = True,
        proxy: str | None = None,
        log_level: int = logging.INFO,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            retries=retries,
            backoff_factor=backoff_factor,
            access_token=access_token,
            verify=verify,
            proxy=proxy,
            log_level=log_level,
            logger=logger,
        )
        self.secret_key = secret_key

        if self.access_token:
            pass  # Already set by super().__init__
        else:
            self.access_token = self.get_access_token()["token"]

    def get_access_token(self) -> dict[str, Any]:
        """Get an access token from /tokens endpoint."""
        if not self.secret_key:
            raise DAAuthException("SECRET_KEY is required to generate an access token")

        token_url = f"{self.url}tokens"

        response = self._client.post(
            token_url,
            json={"secretKey": self.secret_key},
            headers={"Content-Type": "application/json"},
        )
        self.logger.debug(f"Token response: {json.dumps(response.json(), indent=2)}")
        self.access_token = response.json()["token"]
        return response.json()  # type: ignore[no-any-return]

    def query(self, dataset: str, **options: Any) -> RecordIterator:
        """Query a Developer API v3 dataset. Returns a generator of dicts."""
        request_headers: dict[str, str] | None = None
        omit_header_next_link = False
        if "_headers" in options:
            request_headers = options.pop("_headers")
            if request_headers:
                for k, v in request_headers.items():
                    if k.lower() == "x-omit-header-next-links" and v.lower() == "true":
                        omit_header_next_link = True

        query_url = f"{self.url}{dataset}"

        query_chunks = detect_query_chunks(options)
        chunk_idx = 0

        paging = options.pop("paging", "true")
        links: dict[str, Any] | None = None

        while True:
            if links:
                url = self.url[:-1] + links["next"]["url"]
                response = self._client.get(url, headers=request_headers or {})
            else:
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    options[query_chunks[0]] = in_(query_chunks[1][chunk_idx])
                    chunk_idx += 1

                response = self._client.get(
                    query_url, params=options, headers=request_headers or {}
                )

            if not response.is_success:
                raise DAQueryException(
                    f"Non-200 response: {response.status_code} {response.text}"
                )

            records = response.json()
            if (
                omit_header_next_link
                and isinstance(records, dict)
                and "links" in records
            ):
                body_links = records.get("links")
                if body_links:
                    parsed = parse_body_links(body_links)
                    links = dict(parsed) if parsed else None
                else:
                    links = None
                records = records.get("data", [])
            else:
                if "next" in response.links:
                    links = cast(dict[str, Any], response.links)
                else:
                    links = None

            if isinstance(records, dict):
                records = [records]

            if not records:
                links = None
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    continue
                break

            yield from records

            if links is None or paging.lower() == "false":
                break
