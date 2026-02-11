"""Tests for _async_client.py async clients."""

from __future__ import annotations

import httpx
import pytest
import respx

from enverus_developer_api import AsyncDeveloperAPIv3, AsyncDirectAccessV2
from enverus_developer_api._exceptions import DAQueryException

V3_BASE = "https://api.enverus.com/v3/direct-access/"
V2_BASE = "https://di-api.drillinginfo.com/v2/direct-access/"


@pytest.mark.asyncio
class TestAsyncDeveloperAPIv3:
    async def test_query_basic(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[{"WellID": 1}, {"WellID": 2}])
        )
        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        records = [record async for record in v3.query("wells", pagesize=10)]
        await v3.close()
        assert len(records) == 2

    async def test_query_empty(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, json=[])
        )
        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        records = [record async for record in v3.query("wells")]
        await v3.close()
        assert records == []

    async def test_query_error(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(400, text="Bad request")
        )
        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        with pytest.raises(DAQueryException):
            async for _ in v3.query("wells"):
                pass
        await v3.close()

    async def test_context_manager(self, mock_v3_api: respx.MockRouter):
        async with AsyncDeveloperAPIv3(secret_key="test-key") as v3:
            assert isinstance(v3, AsyncDeveloperAPIv3)

    async def test_count(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.head(f"{V3_BASE}wells").mock(
            return_value=httpx.Response(200, headers={"X-Query-Record-Count": "10"})
        )
        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        count = await v3.count("wells")
        await v3.close()
        assert count == 10

    async def test_docs(self, mock_v3_api: respx.MockRouter):
        mock_v3_api.get(f"{V3_BASE}casings").mock(
            return_value=httpx.Response(200, json=[{"field": "CasingID"}])
        )
        v3 = AsyncDeveloperAPIv3(secret_key="test-key")
        docs = await v3.docs("casings")
        await v3.close()
        assert docs is not None


@pytest.mark.asyncio
class TestAsyncDirectAccessV2:
    async def test_query_basic(self, mock_v2_api: respx.MockRouter):
        mock_v2_api.get(f"{V2_BASE}rigs").mock(
            return_value=httpx.Response(200, json=[{"RigID": 1}])
        )
        v2 = AsyncDirectAccessV2(client_id="id", client_secret="secret")
        records = [record async for record in v2.query("rigs")]
        await v2.close()
        assert len(records) == 1

    async def test_context_manager(self, mock_v2_api: respx.MockRouter):
        async with AsyncDirectAccessV2(client_id="id", client_secret="secret") as v2:
            assert isinstance(v2, AsyncDirectAccessV2)
