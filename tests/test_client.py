"""Tests for _client.py sync clients."""

from __future__ import annotations

import csv
import os
from tempfile import mkdtemp
from shutil import rmtree

import httpx
import pytest
import respx

from enverus_developer_api import DeveloperAPIv3, DirectAccessV2
from enverus_developer_api._exceptions import DAQueryException

V3_BASE = "https://api.enverus.com/v3/direct-access/"
V2_BASE = "https://di-api.drillinginfo.com/v2/direct-access/"


class TestDeveloperAPIv3:
    def test_query_basic(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[{"WellID": 1}, {"WellID": 2}])
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(v3.query("wells", pagesize=10))
        assert len(records) == 2
        assert records[0]["WellID"] == 1

    def test_query_non_200_raises(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(400, text="Bad request")
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        with pytest.raises(DAQueryException, match="Bad request"):
            list(v3.query("wells"))

    def test_query_empty_response(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[])
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(v3.query("wells"))
        assert records == []

    def test_query_single_dict_response(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json={"WellID": 1})
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        records = list(v3.query("wells"))
        assert len(records) == 1

    def test_count(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.head(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, headers={"X-Query-Record-Count": "42"})
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        assert v3.count("wells") == 42

    def test_docs(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}casings").mock(
            return_value=httpx.Response(200, json=[{"field": "CasingID"}])
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        docs = v3.docs("casings")
        assert docs is not None
        assert len(docs) == 1

    def test_docs_501(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}casings").mock(
            return_value=httpx.Response(501, text="Not implemented")
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        assert v3.docs("casings") is None

    def test_ddl(self, mock_v3_api: respx.MockRouter):
        ddl_text = "CREATE TABLE wells (\nWellID INT NOT NULL\n)"
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, text=ddl_text)
        )
        v3 = DeveloperAPIv3(secret_key="test-key")
        assert v3.ddl("wells", database="pg") == ddl_text

    def test_context_manager(self, mock_v3_api: respx.MockRouter):
        with DeveloperAPIv3(secret_key="test-key") as v3:
            assert isinstance(v3, DeveloperAPIv3)

    def test_to_csv(self, mock_v3_api: respx.MockRouter):
        v3 = DeveloperAPIv3(secret_key="test-key")

        def mock_query():
            yield {"A": 1, "B": 2}
            yield {"A": 3, "B": 4}

        tempdir = mkdtemp()
        try:
            path = os.path.join(tempdir, "test.csv")
            result = v3.to_csv(mock_query(), path)
            assert result == path

            with open(path) as f:
                reader = csv.reader(f)
                rows = list(reader)
            # Header + 2 data rows
            assert len(rows) == 3
            assert rows[0] == ["A", "B"]
        finally:
            rmtree(tempdir)

    def test_in_static_method(self):
        assert DeveloperAPIv3.in_([1, 2, 3]) == "in(1,2,3)"


class TestDirectAccessV2:
    def test_query_basic(self, mock_v2_api: respx.MockRouter):
        mock_v2_api.get(f"{V2_BASE}rigs").mock(
            return_value=httpx.Response(200, json=[{"RigID": 1}])
        )
        v2 = DirectAccessV2(client_id="id", client_secret="secret")
        records = list(v2.query("rigs", pagesize=10))
        assert len(records) == 1

    def test_context_manager(self, mock_v2_api: respx.MockRouter):
        with DirectAccessV2(client_id="id", client_secret="secret") as v2:
            assert isinstance(v2, DirectAccessV2)
