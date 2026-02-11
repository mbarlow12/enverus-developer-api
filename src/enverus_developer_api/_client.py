"""Async Enverus Developer API v3 client."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, Self

import httpx

from enverus_developer_api._auth import TokenManager
from enverus_developer_api._retry import AsyncRetryTransport
from enverus_developer_api._types import Record
from enverus_developer_api.models.metadata import DDLField, DocsField
from enverus_developer_api.models.pagination import PaginationLinks
from enverus_developer_api.requests.query import detect_query_chunks, format_in
from enverus_developer_api.responses.errors import check_response
from enverus_developer_api.responses.pagination import extract_links
from enverus_developer_api.responses.parsing import parse_ddl, parse_docs

logger = logging.getLogger("directaccess")

DEFAULT_BASE_URL = "https://api.enverus.com/v3/direct-access/"
DEFAULT_PAGESIZE = 10_000
DEFAULT_TIMEOUT_SECONDS = 30.0


class EnverusClient:
    """Async Enverus Developer API v3 client.

    Usage::

        async with EnverusClient(secret_key="...") as client:
            async for row in client.query("wells", deleteddate="null"):
                print(row)
    """

    def __init__(
        self,
        secret_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        verify: bool = True,
        proxy: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._secret_key = secret_key

        transport = AsyncRetryTransport(
            transport=httpx.AsyncHTTPTransport(verify=verify, proxy=proxy),
            retries=retries,
            backoff_factor=backoff_factor,
        )
        self._client = httpx.AsyncClient(
            transport=transport,
            headers={"User-Agent": "enverus-developer-api"},
            timeout=httpx.Timeout(timeout),
        )

        self._token_manager = TokenManager(
            secret_key=secret_key,
            token_url=f"{self._base_url}tokens",
            client=self._client,
        )

    async def __aenter__(self) -> Self:
        await self._ensure_token()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _ensure_token(self) -> None:
        """Ensure we have a valid access token."""
        await self._token_manager.get_token()

    def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers using the current token."""
        token = self._token_manager.token
        if token:
            return {"Authorization": f"bearer {token}"}
        return {}

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an authenticated request with automatic 401 refresh."""
        await self._ensure_token()

        req_headers = self._auth_headers()
        if headers:
            req_headers.update(headers)

        response = await self._client.request(
            method, url, params=params, headers=req_headers
        )

        # Handle 401 — refresh token and retry once
        if response.status_code == 401:
            logger.warning("Access token expired. Acquiring a new one...")
            await self._token_manager.refresh_token()
            req_headers.update(self._auth_headers())
            response = await self._client.request(
                method, url, params=params, headers=req_headers
            )

        # Check for errors (400, 403, 404, etc.)
        check_response(response)

        return response

    async def query(self, dataset: str, **options: Any) -> AsyncIterator[Record]:
        """Query a dataset. Returns an async generator of record dicts.

        Handles pagination automatically — follows next links until exhausted.
        Supports ``X-Omit-Header-Next-Links`` for body-based pagination.
        Auto-chunks large ``in()`` filter values that exceed URL length limits.
        """
        request_headers: dict[str, str] = {}
        omit_header_next_link = False
        if "_headers" in options:
            request_headers = options.pop("_headers") or {}
            for k, v in request_headers.items():
                if k.lower() == "x-omit-header-next-links" and v.lower() == "true":
                    omit_header_next_link = True

        query_url = f"{self._base_url}{dataset}"

        query_chunks = detect_query_chunks(options)
        chunk_idx = 0

        paging = str(options.pop("paging", "true"))
        links: PaginationLinks | None = None

        while True:
            if links and links.next:
                url = self._base_url.rstrip("/") + links.next.url
                response = await self._request("GET", url, headers=request_headers)
            else:
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    options[query_chunks[0]] = format_in(query_chunks[1][chunk_idx])
                    chunk_idx += 1

                response = await self._request(
                    "GET", query_url, params=options, headers=request_headers
                )

            records: list[Record]

            if omit_header_next_link:
                data = response.json()
                if isinstance(data, dict) and "links" in data:
                    body_links = data.get("links")
                    if body_links:
                        from enverus_developer_api.responses.pagination import (
                            _parse_body_links,
                        )

                        links = _parse_body_links(body_links)
                    else:
                        links = None
                    records = data.get("data", [])
                else:
                    links = extract_links(response)
                    records = data if isinstance(data, list) else [data]
            else:
                links = extract_links(response)
                data = response.json()
                if isinstance(data, dict):
                    records = [data]
                else:
                    records = data

            if not records:
                links = None
                if query_chunks and chunk_idx < len(query_chunks[1]):
                    continue
                break

            for record in records:
                yield record

            if links is None or paging.lower() == "false":
                break

    async def count(self, dataset: str, **options: Any) -> int:
        """Get the count of records for a dataset and query options."""
        url = f"{self._base_url}{dataset}"
        response = await self._request("HEAD", url, params=options)
        count_header = response.headers.get("X-Query-Record-Count")
        return int(count_header)

    async def ddl(self, dataset: str, *, database: str = "prism") -> list[DDLField]:
        """Get DDL for a dataset, parsed into structured field models."""
        url = f"{self._base_url}{dataset}"
        logger.debug("Retrieving DDL for dataset: %s", dataset)
        response = await self._request("GET", url, params={"ddl": database})
        return parse_ddl(response.text)

    async def ddl_raw(self, dataset: str, *, database: str = "prism") -> str:
        """Get raw DDL text for a dataset."""
        url = f"{self._base_url}{dataset}"
        response = await self._request("GET", url, params={"ddl": database})
        return response.text

    async def docs(self, dataset: str) -> list[DocsField]:
        """Get docs for a dataset, parsed into structured field models."""
        url = f"{self._base_url}{dataset}"
        logger.debug("Retrieving docs for dataset: %s", dataset)
        response = await self._request("GET", url, params={"docs": "true"})
        if response.status_code == 501:
            return []
        return parse_docs(response.json())

    async def docs_raw(self, dataset: str) -> list[Record] | None:
        """Get raw docs JSON for a dataset."""
        url = f"{self._base_url}{dataset}"
        response = await self._request("GET", url, params={"docs": "true"})
        if response.status_code == 501:
            return None
        return response.json()  # type: ignore[no-any-return]

    @staticmethod
    def in_(items: list[Any]) -> str:
        """Format a list of values for the API's ``in()`` filter function."""
        return format_in(items)
