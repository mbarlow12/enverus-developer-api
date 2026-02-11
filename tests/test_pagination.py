"""Tests for multi-page pagination in sync and async clients."""

from __future__ import annotations

import httpx
import pytest
import respx

from enverus_developer_api import DeveloperAPIv3, AsyncDeveloperAPIv3

V3_BASE = "https://api.enverus.com/v3/direct-access/"


class TestSyncPagination:
    def test_follows_link_headers(self, mock_v3_api: respx.MockRouter):
        """Test that query follows pagination via Link headers."""
        page1 = httpx.Response(
            200,
            json=[{"id": 1}, {"id": 2}],
            headers={"Link": f'<{V3_BASE[:-1]}/wells?page=2>; rel="next"'},
        )
        page2 = httpx.Response(
            200,
            json=[{"id": 3}],
        )
        # Use side_effect for sequential responses on any GET to wells
        mock_v3_api.get(url__regex=r".*/wells.*").mock(side_effect=[page1, page2])

        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(v3.query("wells"))
        assert len(records) == 3
        assert [r["id"] for r in records] == [1, 2, 3]

    def test_stops_when_no_links(self, mock_v3_api: respx.MockRouter):
        """Test that query stops when no Link header is present."""
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(v3.query("wells"))
        assert len(records) == 1

    def test_paging_false_stops_after_first_page(self, mock_v3_api: respx.MockRouter):
        """Test that paging=false stops after first page."""
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"Link": f'<{V3_BASE[:-1]}/wells?page=2>; rel="next"'},
            )
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(v3.query("wells", paging="false"))
        assert len(records) == 1

    def test_omit_header_next_links(self, mock_v3_api: respx.MockRouter):
        """Test X-Omit-Header-Next-Links body pagination."""
        page1_data = {
            "data": [{"id": 1}, {"id": 2}],
            "links": {
                "next": "</wells?action=next&next_page=2&pagesize=2>; rel='next'"
            },
        }
        page2_data = {
            "data": [{"id": 3}],
            "links": {"next": None},
        }
        # Use side_effect so both pages come from the same route sequentially
        mock_v3_api.get(url__regex=r".*/wells.*").mock(
            side_effect=[
                httpx.Response(200, json=page1_data),
                httpx.Response(200, json=page2_data),
            ]
        )

        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(
            v3.query(
                "wells",
                pagesize=2,
                _headers={"X-Omit-Header-Next-Links": "true"},
            )
        )
        assert len(records) == 3

    def test_thread_safe_no_shared_links(self, mock_v3_api: respx.MockRouter):
        """Verify that query uses local links state, not self.links."""
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        assert not hasattr(v3, "links")
        list(v3.query("wells"))
        # After query completes, there should be no self.links attribute
        assert not hasattr(v3, "links")


@pytest.mark.asyncio
class TestAsyncPagination:
    async def test_follows_link_headers(self, mock_v3_api: respx.MockRouter):
        page1 = httpx.Response(
            200,
            json=[{"id": 1}, {"id": 2}],
            headers={"Link": f'<{V3_BASE[:-1]}/wells?page=2>; rel="next"'},
        )
        page2 = httpx.Response(200, json=[{"id": 3}])
        mock_v3_api.get(url__regex=r".*/wells.*").mock(side_effect=[page1, page2])

        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        records = [r async for r in v3.query("wells")]
        await v3.close()
        assert len(records) == 3

    async def test_stops_when_no_links(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        records = [r async for r in v3.query("wells")]
        await v3.close()
        assert len(records) == 1
