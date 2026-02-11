"""httpx Auth flow for transparent bearer token management."""

from __future__ import annotations

import logging
import time
from collections.abc import Generator
from typing import TYPE_CHECKING

import httpx

from enverus_developer_api._exceptions import (
    DAAuthException,
    DADatasetException,
    DAQueryException,
)

if TYPE_CHECKING:
    from enverus_developer_api._async_client import AsyncBaseClient
    from enverus_developer_api._client import BaseClient

logger = logging.getLogger("directaccess")


class _TokenAuth(httpx.Auth):
    """Bearer token auth with transparent 401 refresh and 403 throttle handling.

    Works for both sync and async httpx clients via httpx's auth_flow protocol.
    """

    requires_response_body = True

    def __init__(self, client: BaseClient | AsyncBaseClient) -> None:
        self._client = client

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if self._client.access_token:
            request.headers["Authorization"] = f"bearer {self._client.access_token}"
        response = yield request

        self._check_error_responses(response)

        if response.status_code == 401:
            logger.warning("Access token expired. Acquiring a new one...")
            self._client.get_access_token()
            request.headers["Authorization"] = f"bearer {self._client.access_token}"
            response = yield request

    @staticmethod
    def _check_error_responses(response: httpx.Response) -> None:
        """Check for error status codes and raise appropriate exceptions."""
        if response.is_success:
            return

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response text: {response.text}")

        if response.status_code == 400:
            if "tokens" in str(response.url):
                raise DAAuthException(
                    f"Error getting token. Code: {response.status_code} Message: {response.text}"
                )
            raise DAQueryException(response.text)

        if response.status_code == 403 and "tokens" in str(response.url):
            logger.warning("Throttled token request. Waiting 60 seconds...")
            time.sleep(60)
            return

        if response.status_code == 404:
            raise DADatasetException("Invalid dataset name provided")
