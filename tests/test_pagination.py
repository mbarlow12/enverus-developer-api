"""Tests for multi-page pagination in EnverusClient."""

from __future__ import annotations

import httpx
import pytest
import respx

from enverus_developer_api import EnverusClient

V3_BASE = "https://api.enverus.com/v3/direct-access/"


@pytest.mark.asyncio
class TestAsyncPagination:
    async def test_follows_link_headers(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            page1 = httpx.Response(
                200,
                json=[{"id": 1}, {"id": 2}],
                headers={"Link": '</wells?page=2>; rel="next"'},
            )
            page2 = httpx.Response(200, json=[{"id": 3}])
            mock.get(url__regex=r".*/wells.*").mock(side_effect=[page1, page2])

            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells")]
            assert len(records) == 3
            assert [r["id"] for r in records] == [1, 2, 3]

    async def test_stops_when_no_links(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(f"{V3_BASE}wells").mock(
                return_value=httpx.Response(200, json=[{"id": 1}])
            )
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells")]
            assert len(records) == 1

    async def test_paging_false_stops_after_first_page(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(f"{V3_BASE}wells").mock(
                return_value=httpx.Response(
                    200,
                    json=[{"id": 1}],
                    headers={"Link": '</wells?page=2>; rel="next"'},
                )
            )
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells", paging="false")]
            assert len(records) == 1

    async def test_omit_header_next_links(self):
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
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                side_effect=[
                    httpx.Response(200, json=page1_data),
                    httpx.Response(200, json=page2_data),
                ]
            )
            async with EnverusClient(secret_key="test-key") as client:
                records = [
                    r
                    async for r in client.query(
                        "wells",
                        pagesize=2,
                        _headers={"X-Omit-Header-Next-Links": "true"},
                    )
                ]
            assert len(records) == 3

    async def test_empty_first_page(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(f"{V3_BASE}wells").mock(return_value=httpx.Response(200, json=[]))
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells")]
            assert records == []
