"""Response error checking and exception mapping."""

from __future__ import annotations

import logging

import httpx

from async_enverus_sdk._exceptions import (
    DAAuthException,
    DADatasetException,
    DAQueryException,
)

logger = logging.getLogger("directaccess")


def check_response(response: httpx.Response) -> None:
    """Check for error status codes and raise appropriate exceptions.

    Maps:
    - 400 on ``/tokens`` → DAAuthException
    - 400 on other paths → DAQueryException
    - 403 on ``/tokens`` → DAAuthException (throttled)
    - 404 → DADatasetException
    - Other non-success → DAQueryException
    """
    if response.is_success:
        return

    logger.debug("Response status code: %d", response.status_code)
    logger.debug("Response text: %s", response.text)

    url_str = str(response.url)

    if response.status_code == 400:
        if "tokens" in url_str:
            raise DAAuthException(
                f"Error getting token. Code: {response.status_code} "
                f"Message: {response.text}"
            )
        raise DAQueryException(response.text)

    if response.status_code == 403 and "tokens" in url_str:
        raise DAAuthException(
            f"Throttled token request. Code: {response.status_code} "
            f"Message: {response.text}"
        )

    if response.status_code == 404:
        raise DADatasetException("Invalid dataset name provided")
