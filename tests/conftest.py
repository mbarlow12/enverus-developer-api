"""Shared fixtures and helpers for the test suite."""

from __future__ import annotations

import httpx
import pytest
import respx

from tests.mock_api import V3_BASE

TOKEN_RESPONSE_V3 = {"token": "test-token-v3"}


@pytest.fixture()
def mock_v3_api():
    """Set up respx mocks for v3 API token endpoint."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{V3_BASE}tokens").mock(
            return_value=httpx.Response(200, json=TOKEN_RESPONSE_V3)
        )
        yield mock
