"""Async retry transport for httpx with 5xx exponential backoff."""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger("directaccess")

_DEFAULT_STATUS_FORCELIST = frozenset({500, 502, 503, 504})
_DEFAULT_ALLOWED_METHODS = frozenset({"GET", "POST", "HEAD"})


class AsyncRetryTransport(httpx.AsyncBaseTransport):
    """Wraps an httpx.AsyncHTTPTransport with 5xx retry and exponential backoff."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncHTTPTransport | None = None,
        retries: int = 5,
        backoff_factor: float = 1.0,
        status_forcelist: frozenset[int] = _DEFAULT_STATUS_FORCELIST,
        allowed_methods: frozenset[str] = _DEFAULT_ALLOWED_METHODS,
    ) -> None:
        self._transport = transport or httpx.AsyncHTTPTransport()
        self._retries = retries
        self._backoff_factor = backoff_factor
        self._status_forcelist = status_forcelist
        self._allowed_methods = allowed_methods

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self._retries + 1):
            response = await self._transport.handle_async_request(request)
            if (
                response.status_code not in self._status_forcelist
                or request.method.upper() not in self._allowed_methods
                or attempt == self._retries
            ):
                return response
            last_response = response
            sleep_time = self._backoff_factor * (2**attempt)
            logger.debug(
                "Retry %d/%d after %d status (sleeping %.1fs)",
                attempt + 1,
                self._retries,
                response.status_code,
                sleep_time,
            )
            await asyncio.sleep(sleep_time)
        assert last_response is not None
        return last_response

    async def aclose(self) -> None:
        await self._transport.aclose()
