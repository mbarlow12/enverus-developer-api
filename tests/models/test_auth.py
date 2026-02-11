"""Tests for models/auth.py."""

from enverus_developer_api.models.auth import TokenRequest, TokenResponse


class TestTokenRequest:
    def test_serializes_with_alias(self):
        req = TokenRequest(secret_key="my-key")
        assert req.model_dump(by_alias=True) == {"secretKey": "my-key"}

    def test_populate_by_name(self):
        req = TokenRequest(secret_key="my-key")
        assert req.secret_key == "my-key"

    def test_populate_by_alias(self):
        req = TokenRequest.model_validate({"secretKey": "my-key"})
        assert req.secret_key == "my-key"


class TestTokenResponse:
    def test_validates_token(self):
        resp = TokenResponse(token="abc-123")
        assert resp.token == "abc-123"

    def test_from_json(self):
        resp = TokenResponse.model_validate({"token": "xyz"})
        assert resp.token == "xyz"
