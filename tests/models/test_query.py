"""Tests for models/query.py."""

import pytest
from pydantic import ValidationError

from async_enverus_sdk.models.query import QueryParams


class TestQueryParams:
    def test_defaults(self):
        qp = QueryParams(dataset="wells")
        assert qp.dataset == "wells"
        assert qp.pagesize == 10_000
        assert qp.paging is True
        assert qp.fields is None

    def test_custom_pagesize(self):
        qp = QueryParams(dataset="wells", pagesize=500)
        assert qp.pagesize == 500

    def test_pagesize_min(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            QueryParams(dataset="wells", pagesize=0)

    def test_pagesize_max(self):
        with pytest.raises(ValidationError, match="less than or equal to 100000"):
            QueryParams(dataset="wells", pagesize=200_000)

    def test_extra_fields_passthrough(self):
        qp = QueryParams(dataset="wells", deleteddate="null", StateProvince="in(TX,LA)")
        dumped = qp.model_dump()
        assert dumped["deleteddate"] == "null"
        assert dumped["StateProvince"] == "in(TX,LA)"

    def test_fields_list(self):
        qp = QueryParams(dataset="wells", fields=["WellID", "WellName"])
        assert qp.fields == ["WellID", "WellName"]
