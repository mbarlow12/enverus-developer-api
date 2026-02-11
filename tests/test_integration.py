"""Live API integration tests. Requires real credentials.

These tests are skipped unless the DIRECTACCESSV3_API_KEY environment variable is set.
"""

from __future__ import annotations

import csv
import os
from shutil import rmtree
from tempfile import mkdtemp

import pytest

from enverus_developer_api import EnverusClient, sync, to_csv
from enverus_developer_api._exceptions import DADatasetException, DAQueryException

HAS_V3_CREDS = bool(os.environ.get("DIRECTACCESSV3_API_KEY"))
skip_no_v3 = pytest.mark.skipif(not HAS_V3_CREDS, reason="No v3 API credentials")


@skip_no_v3
@pytest.mark.asyncio
class TestEnverusClientIntegration:
    @pytest.fixture(autouse=True)
    async def setup_client(self):
        self.client = EnverusClient(
            secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
            retries=5,
            backoff_factor=10,
        )
        await self.client._ensure_token()
        yield
        await self.client.close()

    async def test_query(self):
        records = []
        async for row in self.client.query("casings", pagesize=10, deleteddate="null"):
            records.append(row)
            if len(records) >= 30:
                break
        assert len(records) > 0

    async def test_query_omit_header_next_link(self):
        records = []
        async for row in self.client.query(
            "casings",
            pagesize=10,
            deleteddate="null",
            _headers={"X-Omit-Header-Next-Links": "true"},
        ):
            records.append(row)
            if len(records) >= 30:
                break
        assert len(records) > 0

    async def test_docs(self):
        docs = await self.client.docs("casings")
        assert isinstance(docs, list)
        assert len(docs) > 0

    async def test_ddl(self):
        fields = await self.client.ddl("casings", database="pg")
        assert len(fields) > 0

    async def test_ddl_raw(self):
        text = await self.client.ddl_raw("casings", database="pg")
        assert text.startswith("CREATE TABLE casings")

    async def test_count(self):
        count = await self.client.count(
            "wells", updateddate="ge(2021-05-01)", StateProvince="in(TX,LA,WY)"
        )
        assert isinstance(count, int)
        assert count > 0

    async def test_count_invalid_dataset(self):
        with pytest.raises(DADatasetException):
            await self.client.count("invalid")

    async def test_ddl_invalid_db(self):
        with pytest.raises(DAQueryException):
            await self.client.ddl("casings", database="invalid")

    async def test_csv(self):
        tmpdir = mkdtemp()
        try:
            path = os.path.join(tmpdir, "rigs.csv")
            options = {"pagesize": 10000, "deleteddate": "null"}

            count = await self.client.count("rigs", **options)
            records = [r async for r in self.client.query("rigs", **options)]
            to_csv(iter(records), path, delimiter=",")

            with open(path) as f:
                reader = csv.reader(f)
                row_count = sum(1 for _ in reader)
            assert row_count == count + 1
        finally:
            rmtree(tmpdir)

    async def test_context_manager(self):
        async with EnverusClient(
            secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
        ) as api:
            assert isinstance(api, EnverusClient)

    async def test_token_refresh(self):
        client = EnverusClient(
            secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
            retries=5,
            backoff_factor=10,
        )
        # Set an invalid token to trigger refresh
        client._token_manager.token = "invalid"
        count = await client.count("rigs", deleteddate="null")
        assert count > 0
        await client.close()


@skip_no_v3
class TestSyncIntegration:
    def test_sync_query(self):
        records = []
        for row in sync.query(
            os.environ["DIRECTACCESSV3_API_KEY"],
            "casings",
            pagesize=10,
            deleteddate="null",
        ):
            records.append(row)
            if len(records) >= 10:
                break
        assert len(records) > 0

    def test_sync_count(self):
        count = sync.count(
            os.environ["DIRECTACCESSV3_API_KEY"],
            "wells",
            updateddate="ge(2021-05-01)",
        )
        assert count > 0
