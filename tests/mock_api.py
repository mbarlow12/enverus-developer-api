"""Configurable mock for Enverus API v3 using respx."""

from __future__ import annotations

from typing import Any, Self

import httpx
import respx

from enverus_developer_api._types import Record

V3_BASE = "https://api.enverus.com/v3/direct-access/"


class MockEnverusAPI:
    """Configurable mock for Enverus API v3 using respx."""

    def __init__(self, mock: respx.MockRouter) -> None:
        self._mock = mock
        self._token = "test-token"
        # Always set up token endpoint
        self._mock.post(f"{V3_BASE}tokens").mock(
            return_value=httpx.Response(200, json={"token": self._token})
        )

    def set_token(self, token: str = "test-token") -> Self:
        """Configure the token returned by the mock."""
        self._token = token
        self._mock.post(f"{V3_BASE}tokens").mock(
            return_value=httpx.Response(200, json={"token": self._token})
        )
        return self

    def add_pages(self, dataset: str, pages: list[list[Record]]) -> Self:
        """Configure multi-page responses for a dataset."""
        responses: list[httpx.Response] = []
        for i, page in enumerate(pages):
            headers: dict[str, str] = {}
            if i < len(pages) - 1:
                # Add Link header for next page
                headers["Link"] = f'</{dataset}?page={i + 2}>; rel="next"'
            responses.append(httpx.Response(200, json=page, headers=headers))

        self._mock.get(url__regex=rf".*/{dataset}.*").mock(side_effect=responses)
        return self

    def set_error(self, dataset: str, status: int, message: str) -> Self:
        """Configure an error response for a dataset."""
        self._mock.get(f"{V3_BASE}{dataset}").mock(
            return_value=httpx.Response(status, text=message)
        )
        return self

    def set_count(self, dataset: str, count: int) -> Self:
        """Configure HEAD response with record count."""
        self._mock.head(url__regex=rf".*/{dataset}.*").mock(
            return_value=httpx.Response(
                200, headers={"X-Query-Record-Count": str(count)}
            )
        )
        return self

    def set_ddl(self, dataset: str, ddl_text: str) -> Self:
        """Configure DDL response for a dataset."""
        self._mock.get(f"{V3_BASE}{dataset}").mock(
            return_value=httpx.Response(200, text=ddl_text)
        )
        return self

    def set_docs(self, dataset: str, docs: list[dict[str, Any]]) -> Self:
        """Configure docs response for a dataset."""
        self._mock.get(f"{V3_BASE}{dataset}").mock(
            return_value=httpx.Response(200, json=docs)
        )
        return self
