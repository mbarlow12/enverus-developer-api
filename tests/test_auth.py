"""Tests for _auth.py token management."""

from __future__ import annotations

import httpx
import respx

from enverus_developer_api import DeveloperAPIv3, DirectAccessV2
from enverus_developer_api._exceptions import (
    DAAuthException,
    DADatasetException,
    DAQueryException,
)

import pytest

V3_BASE = "https://api.enverus.com/v3/direct-access/"
V2_BASE = "https://di-api.drillinginfo.com/v2/direct-access/"


class TestTokenAuth:
    def test_v3_sets_bearer_token(self, mock_v3_api: respx.MockRouter):
        v3 = DeveloperAPIv3(secret_key="test-key")
        assert v3.access_token == "test-token-v3"

    def test_v3_pregenerated_token(self, mock_v3_api: respx.MockRouter):
        v3 = DeveloperAPIv3(secret_key="test-key", access_token="my-token")
        assert v3.access_token == "my-token"
        # Token endpoint should NOT be called
        assert not mock_v3_api.calls

    def test_v2_sets_bearer_token(self, mock_v2_api: respx.MockRouter):
        v2 = DirectAccessV2(client_id="id", client_secret="secret")
        assert v2.access_token == "test-token-v2"

    def test_v3_missing_secret_key(self):
        with pytest.raises(DAAuthException):
            DeveloperAPIv3(secret_key="")

    def test_v2_missing_client_id(self):
        with pytest.raises(DAAuthException):
            DirectAccessV2(client_id="", client_secret="secret")

    def test_v2_missing_client_secret(self):
        with pytest.raises(DAAuthException):
            DirectAccessV2(client_id="id", client_secret="")

    def test_401_triggers_token_refresh(self, mock_v3_api: respx.MockRouter):
        """Test that a 401 response triggers a token refresh and retry."""
        # First query call returns 401, second returns success
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            side_effect=[
                httpx.Response(401, text="Unauthorized"),
                httpx.Response(200, json=[{"WellID": 1}]),
            ]
        )
        # Token refresh endpoint (second call)
        mock_v3_api.post(f"{V3_BASE}tokens").mock(
            return_value=httpx.Response(200, json={"token": "refreshed-token"})
        )

        v3 = DeveloperAPIv3(secret_key="test-key", access_token="expired-token")
        records = list(v3.query("wells", pagesize=1))
        assert len(records) == 1
        assert v3.access_token == "refreshed-token"


class TestErrorResponses:
    def test_400_on_tokens_raises_auth_exception(self):
        with respx.mock:
            respx.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(400, text="Bad request")
            )
            with pytest.raises(DAAuthException, match="Error getting token"):
                DeveloperAPIv3(secret_key="bad-key")

    def test_400_on_query_raises_query_exception(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(400, text="Invalid parameter")
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        with pytest.raises(DAQueryException, match="Invalid parameter"):
            list(v3.query("wells", badparam="x"))

    def test_404_raises_dataset_exception(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.head(f"{V3_BASE}invalid").mock(
            return_value=httpx.Response(404, text="Not found")
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        with pytest.raises(DADatasetException, match="Invalid dataset"):
            v3.count("invalid")
