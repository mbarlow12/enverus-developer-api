"""Tests for _retry.py async transport wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from async_enverus_sdk._retry import AsyncRetryTransport


@pytest.mark.asyncio
class TestAsyncRetryTransport:
    async def test_success_no_retry(self):
        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.handle_async_request = mock_handle
        transport = AsyncRetryTransport(transport=inner, retries=3)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200

    @patch("async_enverus_sdk._retry.asyncio.sleep")
    async def test_retries_on_500(self, mock_sleep: MagicMock):
        call_count = 0

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return httpx.Response(500)
            return httpx.Response(200)

        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.handle_async_request = mock_handle
        transport = AsyncRetryTransport(transport=inner, retries=5, backoff_factor=1.0)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert call_count == 3

    @patch("async_enverus_sdk._retry.asyncio.sleep")
    async def test_exhausts_retries(self, mock_sleep: MagicMock):
        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.handle_async_request = mock_handle
        transport = AsyncRetryTransport(transport=inner, retries=2, backoff_factor=0.1)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 503

    async def test_no_retry_for_non_retriable_status(self):
        call_count = 0

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(400)

        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.handle_async_request = mock_handle
        transport = AsyncRetryTransport(transport=inner, retries=3)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 400
        assert call_count == 1

    @patch("async_enverus_sdk._retry.asyncio.sleep")
    async def test_backoff_factor(self, mock_sleep: MagicMock):
        call_count = 0

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return httpx.Response(500)
            return httpx.Response(200)

        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.handle_async_request = mock_handle
        transport = AsyncRetryTransport(transport=inner, retries=5, backoff_factor=2.0)

        request = httpx.Request("GET", "https://example.com")
        await transport.handle_async_request(request)

        # First sleep: 2.0 * 2^0 = 2.0
        # Second sleep: 2.0 * 2^1 = 4.0
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

    async def test_aclose(self):
        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.aclose = MagicMock(return_value=None)

        async def mock_aclose() -> None:
            pass

        inner.aclose = mock_aclose
        transport = AsyncRetryTransport(transport=inner)
        await transport.aclose()
