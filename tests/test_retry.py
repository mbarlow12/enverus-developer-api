"""Tests for _retry.py transport wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from enverus_developer_api._retry import AsyncRetryTransport, RetryTransport


class TestRetryTransport:
    def test_success_no_retry(self):
        inner = MagicMock(spec=httpx.HTTPTransport)
        inner.handle_request.return_value = httpx.Response(200)
        transport = RetryTransport(transport=inner, retries=3)

        request = httpx.Request("GET", "https://example.com")
        response = transport.handle_request(request)

        assert response.status_code == 200
        assert inner.handle_request.call_count == 1

    @patch("enverus_developer_api._retry.time.sleep")
    def test_retries_on_500(self, mock_sleep: MagicMock):
        inner = MagicMock(spec=httpx.HTTPTransport)
        inner.handle_request.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200),
        ]
        transport = RetryTransport(transport=inner, retries=5, backoff_factor=1.0)

        request = httpx.Request("GET", "https://example.com")
        response = transport.handle_request(request)

        assert response.status_code == 200
        assert inner.handle_request.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("enverus_developer_api._retry.time.sleep")
    def test_exhausts_retries(self, mock_sleep: MagicMock):
        inner = MagicMock(spec=httpx.HTTPTransport)
        inner.handle_request.return_value = httpx.Response(503)
        transport = RetryTransport(transport=inner, retries=2, backoff_factor=0.1)

        request = httpx.Request("GET", "https://example.com")
        response = transport.handle_request(request)

        assert response.status_code == 503
        # 1 initial + 2 retries = 3 calls
        assert inner.handle_request.call_count == 3

    def test_no_retry_for_non_retriable_status(self):
        inner = MagicMock(spec=httpx.HTTPTransport)
        inner.handle_request.return_value = httpx.Response(400)
        transport = RetryTransport(transport=inner, retries=3)

        request = httpx.Request("GET", "https://example.com")
        response = transport.handle_request(request)

        assert response.status_code == 400
        assert inner.handle_request.call_count == 1

    @patch("enverus_developer_api._retry.time.sleep")
    def test_backoff_factor(self, mock_sleep: MagicMock):
        inner = MagicMock(spec=httpx.HTTPTransport)
        inner.handle_request.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200),
        ]
        transport = RetryTransport(transport=inner, retries=5, backoff_factor=2.0)

        request = httpx.Request("GET", "https://example.com")
        transport.handle_request(request)

        # First sleep: 2.0 * 2^0 = 2.0
        # Second sleep: 2.0 * 2^1 = 4.0
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

    def test_close(self):
        inner = MagicMock(spec=httpx.HTTPTransport)
        transport = RetryTransport(transport=inner)
        transport.close()
        inner.close.assert_called_once()


@pytest.mark.asyncio
class TestAsyncRetryTransport:
    async def test_success_no_retry(self):
        inner = MagicMock(spec=httpx.AsyncHTTPTransport)
        inner.handle_async_request = MagicMock(return_value=httpx.Response(200))
        # Make it an awaitable

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        inner.handle_async_request = mock_handle
        transport = AsyncRetryTransport(transport=inner, retries=3)

        request = httpx.Request("GET", "https://example.com")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200

    @patch("enverus_developer_api._retry.asyncio.sleep")
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
