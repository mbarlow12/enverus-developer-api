"""Shared fixtures and helpers for the test suite."""

from __future__ import annotations

import httpx
import pytest
import respx


V3_BASE = "https://api.enverus.com/v3/direct-access/"
V2_BASE = "https://di-api.drillinginfo.com/v2/direct-access/"

TOKEN_RESPONSE_V3 = {"token": "test-token-v3"}
TOKEN_RESPONSE_V2 = {"access_token": "test-token-v2"}


@pytest.fixture()
def mock_v3_api():
    """Set up respx mocks for v3 API token endpoint."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{V3_BASE}tokens").mock(
            return_value=httpx.Response(200, json=TOKEN_RESPONSE_V3)
        )
        yield mock


@pytest.fixture()
def mock_v2_api():
    """Set up respx mocks for v2 API token endpoint."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{V2_BASE}tokens").mock(
            return_value=httpx.Response(200, json=TOKEN_RESPONSE_V2)
        )
        yield mock
