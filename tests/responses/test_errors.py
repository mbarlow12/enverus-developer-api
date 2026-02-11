"""Tests for responses/errors.py — error checking."""

import httpx
import pytest

from async_enverus_sdk._exceptions import (
    DAAuthException,
    DADatasetException,
    DAQueryException,
)
from async_enverus_sdk.responses.errors import check_response


class TestCheckResponse:
    def test_success_does_nothing(self):
        response = httpx.Response(200)
        check_response(response)  # Should not raise

    def test_400_on_tokens_raises_auth(self):
        response = httpx.Response(
            400,
            text="Bad request",
            request=httpx.Request(
                "POST", "https://api.enverus.com/v3/direct-access/tokens"
            ),
        )
        with pytest.raises(DAAuthException, match="Error getting token"):
            check_response(response)

    def test_400_on_query_raises_query(self):
        response = httpx.Response(
            400,
            text="Invalid parameter",
            request=httpx.Request(
                "GET", "https://api.enverus.com/v3/direct-access/wells"
            ),
        )
        with pytest.raises(DAQueryException, match="Invalid parameter"):
            check_response(response)

    def test_403_on_tokens_raises_auth(self):
        response = httpx.Response(
            403,
            text="Throttled",
            request=httpx.Request(
                "POST", "https://api.enverus.com/v3/direct-access/tokens"
            ),
        )
        with pytest.raises(DAAuthException, match="Throttled"):
            check_response(response)

    def test_404_raises_dataset(self):
        response = httpx.Response(
            404,
            text="Not found",
            request=httpx.Request(
                "HEAD", "https://api.enverus.com/v3/direct-access/invalid"
            ),
        )
        with pytest.raises(DADatasetException, match="Invalid dataset"):
            check_response(response)

    def test_200_no_exception(self):
        response = httpx.Response(200)
        check_response(response)
