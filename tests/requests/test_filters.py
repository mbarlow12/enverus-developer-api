"""Tests for requests/filters.py — filter DSL."""

from enverus_developer_api.requests.filters import (
    btw,
    eq,
    ge,
    gt,
    in_,
    le,
    lt,
    ne,
    nil,
    not_,
)


class TestFilterDSL:
    def test_eq(self):
        assert eq("TX") == "eq(TX)"

    def test_ne(self):
        assert ne("TX") == "ne(TX)"

    def test_lt(self):
        assert lt("2024-01-01") == "lt(2024-01-01)"

    def test_le(self):
        assert le(100) == "le(100)"

    def test_gt(self):
        assert gt(0) == "gt(0)"

    def test_ge(self):
        assert ge("2021-05-01") == "ge(2021-05-01)"

    def test_in_multiple(self):
        assert in_("TX", "LA", "WY") == "in(TX,LA,WY)"

    def test_in_single(self):
        assert in_(42) == "in(42)"

    def test_btw(self):
        assert btw(10, 20) == "btw(10,20)"

    def test_nil(self):
        assert nil() == "nil"

    def test_not(self):
        assert not_("eq(TX)") == "not(eq(TX))"

    def test_composition_not_in(self):
        assert not_(in_("A", "B")) == "not(in(A,B))"

    def test_composition_not_nil(self):
        assert not_(nil()) == "not(nil)"

    def test_composition_not_btw(self):
        assert not_(btw(1, 10)) == "not(btw(1,10))"
