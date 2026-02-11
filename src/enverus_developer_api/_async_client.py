"""Asynchronous clients for the Enverus Developer API."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import httpx

from enverus_developer_api._auth import _TokenAuth
from enverus_developer_api._exceptions import (
    DAAuthException,
    DAQueryException,
)
from enverus_developer_api._retry import AsyncRetryTransport
from enverus_developer_api._types import AsyncRecordIterator, Record
from enverus_developer_api._utils import detect_query_chunks, in_, parse_body_links


class AsyncBaseClient:
    """Abstract base for async Enverus Developer API clients."""

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

        transport = AsyncRetryTransport(
            transport=httpx.AsyncHTTPTransport(verify=verify, proxy=proxy),
            retries=retries,
            backoff_factor=backoff_factor,
        )
        self._client = httpx.AsyncClient(
            transport=transport,
            headers={"User-Agent": "enverus-developer-api"},
            auth=_TokenAuth(self),
            timeout=httpx.Timeout(30.0),
        )

    async def __aenter__(self) -> AsyncBaseClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    def get_access_token(self) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def in_(items: list[Any]) -> str:
        """Helper for the API's ``in()`` filter function."""
        return in_(items)

    async def ddl(self, dataset: str, *, database: str) -> str:
        """Get DDL statement for dataset."""
        ddl_url = f"{self.url}{dataset}"
        self.logger.debug(f"Retrieving DDL for dataset: {dataset}")
        response = await self._client.get(ddl_url, params={"ddl": database})
        return response.text

    async def docs(self, dataset: str) -> list[Record] | None:
        """Get docs for dataset."""
        docs_url = f"{self.url}{dataset}"
        self.logger.debug(f"Retrieving docs for dataset: {dataset}")
        response = await self._client.get(docs_url, params={"docs": "true"})
        if response.status_code == 501:
            self.logger.warning(
                f"docs and example params are not yet supported on dataset {dataset}"
            )
            return None
        return response.json()  # type: ignore[no-any-return]

    async def count(self, dataset: str, **options: Any) -> int:
        """Get the count of records for a dataset."""
        head_url = f"{self.url}{dataset}"
        response = await self._client.head(head_url, params=options)
        count = response.headers.get("X-Query-Record-Count")
        return int(count)

    def query(self, dataset: str, **options: Any) -> AsyncRecordIterator:
        raise NotImplementedError


class AsyncDirectAccessV2(AsyncBaseClient):
    """Async client for Enverus Developer API Version 2."""

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

        if not self.access_token:
            self.access_token = self.get_access_token()["access_token"]

    def get_access_token(self) -> dict[str, Any]:
        """Get an access token from /tokens endpoint (sync call used by auth flow)."""
        if not self.client_id or not self.client_secret:
            raise DAAuthException(
                "CLIENT_ID and CLIENT_SECRET are required to generate an access token"
            )

        import base64

        token_url = f"{self.url}tokens"
        auth_value = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        # Use a sync httpx client for token acquisition (auth flow is sync in httpx)
        response = httpx.post(
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

    async def query(self, dataset: str, **options: Any) -> AsyncRecordIterator:
        """Query a Developer API v2 dataset. Returns an async generator of dicts."""
        query_url = f"{self.url}{dataset}"

        query_chunks = detect_query_chunks(options)
        chunk_idx = 0

        paging = options.pop("paging", "true")
        links: dict[str, Any] | None = None

        while True:
            if links:
                response = await self._client.get(self.url[:-1] + links["next"]["url"])
            else:
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    options[query_chunks[0]] = in_(query_chunks[1][chunk_idx])
                    chunk_idx += 1

                response = await self._client.get(query_url, params=options)

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

            for record in records:
                yield record

            if links is None or paging.lower() == "false":
                break


class AsyncDeveloperAPIv3(AsyncBaseClient):
    """Async client for Enverus Developer API Version 3."""

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

        if not self.access_token:
            self.access_token = self.get_access_token()["token"]

    def get_access_token(self) -> dict[str, Any]:
        """Get an access token from /tokens endpoint (sync call used by auth flow)."""
        if not self.secret_key:
            raise DAAuthException("SECRET_KEY is required to generate an access token")

        token_url = f"{self.url}tokens"

        # Use a sync httpx client for token acquisition (auth flow is sync in httpx)
        response = httpx.post(
            token_url,
            json={"secretKey": self.secret_key},
            headers={"Content-Type": "application/json"},
        )
        self.logger.debug(f"Token response: {json.dumps(response.json(), indent=2)}")
        self.access_token = response.json()["token"]
        return response.json()  # type: ignore[no-any-return]

    async def query(self, dataset: str, **options: Any) -> AsyncRecordIterator:
        """Query a Developer API v3 dataset. Returns an async generator of dicts."""
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
                response = await self._client.get(url, headers=request_headers or {})
            else:
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    options[query_chunks[0]] = in_(query_chunks[1][chunk_idx])
                    chunk_idx += 1

                response = await self._client.get(
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

            for record in records:
                yield record

            if links is None or paging.lower() == "false":
                break
