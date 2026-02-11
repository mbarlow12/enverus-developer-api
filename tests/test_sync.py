"""Tests for _sync.py — sync wrappers backed by background event loop."""

from __future__ import annotations

import httpx
import respx

from async_enverus_sdk._sync import count, ddl, docs, query

V3_BASE = "https://api.enverus.com/v3/direct-access/"


class TestSyncQuery:
    def test_basic_query(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                return_value=httpx.Response(200, json=[{"WellID": 1}, {"WellID": 2}])
            )
            records = list(query("test-key", "wells", pagesize=10))
        assert len(records) == 2
        assert records[0]["WellID"] == 1

    def test_empty_query(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                return_value=httpx.Response(200, json=[])
            )
            records = list(query("test-key", "wells"))
        assert records == []


class TestSyncCount:
    def test_basic_count(self):
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.head(url__regex=r".*/wells.*").mock(
                return_value=httpx.Response(200, headers={"X-Query-Record-Count": "42"})
            )
            result = count("test-key", "wells")
        assert result == 42


class TestSyncDDL:
    def test_basic_ddl(self):
        ddl_text = "CREATE TABLE wells (\nWellID INT NOT NULL\n)"
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/wells.*").mock(
                return_value=httpx.Response(200, text=ddl_text)
            )
            fields = ddl("test-key", "wells", database="pg")
        assert len(fields) == 1
        assert fields[0].name == "WellID"


class TestSyncDocs:
    def test_basic_docs(self):
        docs_data = [
            {
                "name": "CasingID",
                "required": "true",
                "default": "",
                "requirements": "",
                "description": "ID",
                "filter_type": "eq",
            }
        ]
        with respx.mock(assert_all_called=False) as mock:
            mock.post(f"{V3_BASE}tokens").mock(
                return_value=httpx.Response(200, json={"token": "test-token"})
            )
            mock.get(url__regex=r".*/casings.*").mock(
                return_value=httpx.Response(200, json=docs_data)
            )
            result = docs("test-key", "casings")
        assert len(result) == 1
        assert result[0].name == "CasingID"
