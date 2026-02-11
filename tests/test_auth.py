"""Tests for _auth.py TokenManager."""

from __future__ import annotations

import httpx
import pytest
import respx

from enverus_developer_api._auth import TokenManager
from enverus_developer_api._exceptions import DAAuthException

V3_BASE = "https://api.enverus.com/v3/direct-access/"
TOKEN_URL = f"{V3_BASE}tokens"


@pytest.mark.asyncio
class TestTokenManager:
    async def test_get_token_acquires_new(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(TOKEN_URL).mock(
                return_value=httpx.Response(200, json={"token": "new-token"})
            )
            async with httpx.AsyncClient() as client:
                mgr = TokenManager("test-key", TOKEN_URL, client)
                token = await mgr.get_token()
                assert token == "new-token"

    async def test_get_token_returns_cached(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(TOKEN_URL).mock(
                return_value=httpx.Response(200, json={"token": "cached-token"})
            )
            async with httpx.AsyncClient() as client:
                mgr = TokenManager("test-key", TOKEN_URL, client)
                token1 = await mgr.get_token()
                token2 = await mgr.get_token()
                assert token1 == token2
                assert len(mock.calls) == 1

    async def test_refresh_token_forces_new(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(TOKEN_URL).mock(
                side_effect=[
                    httpx.Response(200, json={"token": "token-1"}),
                    httpx.Response(200, json={"token": "token-2"}),
                ]
            )
            async with httpx.AsyncClient() as client:
                mgr = TokenManager("test-key", TOKEN_URL, client)
                token1 = await mgr.get_token()
                token2 = await mgr.refresh_token()
                assert token1 == "token-1"
                assert token2 == "token-2"
                assert len(mock.calls) == 2

    async def test_400_raises_auth_exception(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(TOKEN_URL).mock(
                return_value=httpx.Response(400, text="Bad credentials")
            )
            async with httpx.AsyncClient() as client:
                mgr = TokenManager("bad-key", TOKEN_URL, client)
                with pytest.raises(DAAuthException, match="Error getting token"):
                    await mgr.get_token()

    async def test_empty_secret_key_raises(self):
        async with httpx.AsyncClient() as client:
            mgr = TokenManager("", TOKEN_URL, client)
            with pytest.raises(DAAuthException, match="SECRET_KEY"):
                await mgr.get_token()

    async def test_token_property(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(TOKEN_URL).mock(
                return_value=httpx.Response(200, json={"token": "prop-token"})
            )
            async with httpx.AsyncClient() as client:
                mgr = TokenManager("test-key", TOKEN_URL, client)
                assert mgr.token is None
                await mgr.get_token()
                assert mgr.token == "prop-token"

    async def test_token_setter(self):
        async with httpx.AsyncClient() as client:
            mgr = TokenManager("test-key", TOKEN_URL, client)
            mgr.token = "manual-token"
            token = await mgr.get_token()
            assert token == "manual-token"
