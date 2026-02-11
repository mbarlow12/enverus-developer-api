"""Async-native token lifecycle management."""

from __future__ import annotations

import asyncio
import logging

import httpx

from async_enverus_sdk._exceptions import DAAuthException

logger = logging.getLogger("directaccess")

THROTTLE_WAIT_SECONDS = 60


class TokenManager:
    """Manages async token lifecycle: acquisition, caching, 401 refresh, 403 throttle."""

    def __init__(
        self,
        secret_key: str,
        token_url: str,
        client: httpx.AsyncClient,
    ) -> None:
        self._secret_key = secret_key
        self._token_url = token_url
        self._client = client
        self._token: str | None = None
        self._lock = asyncio.Lock()

    @property
    def token(self) -> str | None:
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        self._token = value

    async def get_token(self) -> str:
        """Return cached token or acquire a new one."""
        if self._token:
            return self._token
        return await self.refresh_token()

    async def refresh_token(self) -> str:
        """Force-acquire a new token from the API."""
        async with self._lock:
            if not self._secret_key:
                raise DAAuthException(
                    "SECRET_KEY is required to generate an access token"
                )

            logger.debug("Acquiring new access token from %s", self._token_url)
            response = await self._client.post(
                self._token_url,
                json={"secretKey": self._secret_key},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 400:
                raise DAAuthException(
                    f"Error getting token. Code: {response.status_code} "
                    f"Message: {response.text}"
                )

            if response.status_code == 403:
                logger.warning(
                    "Throttled token request. Waiting %d seconds...",
                    THROTTLE_WAIT_SECONDS,
                )
                await asyncio.sleep(THROTTLE_WAIT_SECONDS)
                # Retry once after throttle
                response = await self._client.post(
                    self._token_url,
                    json={"secretKey": self._secret_key},
                    headers={"Content-Type": "application/json"},
                )
                if not response.is_success:
                    raise DAAuthException(
                        f"Token request failed after throttle wait. "
                        f"Code: {response.status_code} Message: {response.text}"
                    )

            if not response.is_success:
                raise DAAuthException(
                    f"Token request failed. Code: {response.status_code} "
                    f"Message: {response.text}"
                )

            data = response.json()
            self._token = data["token"]
            logger.debug("Token acquired successfully")
            return self._token

    async def handle_throttle(self) -> None:
        """Wait out a 403 throttle response."""
        logger.warning(
            "Throttled token request. Waiting %d seconds...",
            THROTTLE_WAIT_SECONDS,
        )
        await asyncio.sleep(THROTTLE_WAIT_SECONDS)
