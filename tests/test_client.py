"""Tests for _client.py — async EnverusClient."""

from __future__ import annotations

import httpx
import pytest
import respx

from async_enverus_sdk import EnverusClient
from async_enverus_sdk._exceptions import (
    DADatasetException,
    DAQueryException,
)
from tests.mock_api import MockEnverusAPI, V3_BASE


@pytest.fixture()
def mock_api():
    with respx.mock(assert_all_called=False) as mock:
        api = MockEnverusAPI(mock)
        yield api


@pytest.mark.asyncio
class TestEnverusClient:
    async def test_query_basic(self, mock_api: MockEnverusAPI):
        mock_api.add_pages("wells", [[{"WellID": 1}, {"WellID": 2}]])
        async with EnverusClient(secret_key="test-key") as client:
            records = [r async for r in client.query("wells", pagesize=10)]
        assert len(records) == 2
        assert records[0]["WellID"] == 1

    async def test_query_empty(self, mock_api: MockEnverusAPI):
        mock_api.add_pages("wells", [[]])
        async with EnverusClient(secret_key="test-key") as client:
            records = [r async for r in client.query("wells")]
        assert records == []

    async def test_query_multi_page(self, mock_api: MockEnverusAPI):
        mock_api.add_pages(
            "wells",
            [
                [{"id": 1}, {"id": 2}],
                [{"id": 3}],
            ],
        )
        async with EnverusClient(secret_key="test-key") as client:
            records = [r async for r in client.query("wells")]
        assert len(records) == 3
        assert [r["id"] for r in records] == [1, 2, 3]

    async def test_query_error(self, mock_api: MockEnverusAPI):
        mock_api.set_error("wells", 400, "Invalid parameter")
        async with EnverusClient(secret_key="test-key") as client:
            with pytest.raises(DAQueryException, match="Invalid parameter"):
                async for _ in client.query("wells"):
                    pass

    async def test_count(self, mock_api: MockEnverusAPI):
        mock_api.set_count("wells", 42)
        async with EnverusClient(secret_key="test-key") as client:
            count = await client.count("wells")
        assert count == 42

    async def test_ddl(self, mock_api: MockEnverusAPI):
        ddl_text = "CREATE TABLE wells (\nWellID INT NOT NULL\n)"
        mock_api.set_ddl("wells", ddl_text)
        async with EnverusClient(secret_key="test-key") as client:
            fields = await client.ddl("wells", database="pg")
        assert len(fields) == 1
        assert fields[0].name == "WellID"

    async def test_docs(self, mock_api: MockEnverusAPI):
        mock_api.set_docs(
            "casings",
            [
                {
                    "name": "CasingID",
                    "required": "true",
                    "default": "",
                    "requirements": "",
                    "description": "Casing ID",
                    "filter_type": "eq",
                }
            ],
        )
        async with EnverusClient(secret_key="test-key") as client:
            docs = await client.docs("casings")
        assert len(docs) == 1
        assert docs[0].name == "CasingID"

    async def test_context_manager(self, mock_api: MockEnverusAPI):
        async with EnverusClient(secret_key="test-key") as client:
            assert isinstance(client, EnverusClient)

    async def test_401_triggers_refresh(self, mock_api: MockEnverusAPI):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "refreshed-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                side_effect=[
                    httpx.Response(401, text="Unauthorized"),
                    httpx.Response(200, json=[{"WellID": 1}]),
                ]
            )
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells", pagesize=1)]
            assert len(records) == 1

    async def test_404_raises_dataset_exception(self, mock_api: MockEnverusAPI):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.head(url__regex=r".*/invalid.*").mock(
                return_value=httpx.Response(404, text="Not found")
            )
            async with EnverusClient(secret_key="test-key") as client:
                with pytest.raises(DADatasetException):
                    await client.count("invalid")

    async def test_in_static_method(self):
        assert EnverusClient.in_([1, 2, 3]) == "in(1,2,3)"

    async def test_single_dict_response(self, mock_api: MockEnverusAPI):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                return_value=httpx.Response(200, json={"WellID": 1})
            )
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells")]
            assert len(records) == 1

    async def test_paging_false(self, mock_api: MockEnverusAPI):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                return_value=httpx.Response(
                    200,
                    json=[{"id": 1}],
                    headers={"Link": '</wells?page=2>; rel="next"'},
                )
            )
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells", paging="false")]
            assert len(records) == 1

    async def test_omit_header_next_links(self, mock_api: MockEnverusAPI):
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

    async def test_to_csv(self, mock_api: MockEnverusAPI):
        """Test to_csv with EnverusClient query results."""
        import csv
        import os
        from shutil import rmtree
        from tempfile import mkdtemp

        from async_enverus_sdk import to_csv

        mock_api.add_pages("wells", [[{"A": 1, "B": 2}, {"A": 3, "B": 4}]])
        tmpdir = mkdtemp()
        try:
            path = os.path.join(tmpdir, "test.csv")
            async with EnverusClient(secret_key="test-key") as client:
                records = [r async for r in client.query("wells")]
            count = to_csv(iter(records), path)
            assert count == 2
            with open(path) as f:
                rows = list(csv.reader(f))
            assert len(rows) == 3  # header + 2 rows
        finally:
            rmtree(tmpdir)
