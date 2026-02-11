"""Retry transports for httpx with 5xx exponential backoff."""

from __future__ import annotations

import asyncio
import time

import httpx


_DEFAULT_STATUS_FORCELIST = frozenset({500, 502, 503, 504})
_DEFAULT_ALLOWED_METHODS = frozenset({"GET", "POST", "HEAD"})


class RetryTransport(httpx.BaseTransport):
    """Wraps an httpx.HTTPTransport with 5xx retry and exponential backoff."""

    def __init__(
        self,
        *,
        transport: httpx.HTTPTransport | None = None,
        retries: int = 5,
        backoff_factor: float = 1.0,
        status_forcelist: frozenset[int] = _DEFAULT_STATUS_FORCELIST,
        allowed_methods: frozenset[str] = _DEFAULT_ALLOWED_METHODS,
    ) -> None:
        self._transport = transport or httpx.HTTPTransport()
        self._retries = retries
        self._backoff_factor = backoff_factor
        self._status_forcelist = status_forcelist
        self._allowed_methods = allowed_methods

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self._retries + 1):
            response = self._transport.handle_request(request)
            if (
                response.status_code not in self._status_forcelist
                or request.method.upper() not in self._allowed_methods
                or attempt == self._retries
            ):
                return response
            last_response = response
            sleep_time = self._backoff_factor * (2**attempt)
            time.sleep(sleep_time)
        # Should not reach here, but satisfy type checker
        assert last_response is not None
        return last_response

    def close(self) -> None:
        self._transport.close()


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
            await asyncio.sleep(sleep_time)
        assert last_response is not None
        return last_response

    async def aclose(self) -> None:
        await self._transport.aclose()
