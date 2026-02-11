"""Tests for _utils.py pure functions."""

from __future__ import annotations

import pytest

from enverus_developer_api._utils import (
    chunks,
    detect_query_chunks,
    in_,
    parse_body_links,
)


class TestChunks:
    def test_even_split(self):
        result = chunks([1, 2, 3, 4], 2)
        assert result == [[1, 2], [3, 4]]

    def test_uneven_split(self):
        result = chunks([1, 2, 3, 4, 5], 2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_single_chunk(self):
        result = chunks([1, 2, 3], 10)
        assert result == [[1, 2, 3]]

    def test_empty(self):
        result = chunks([], 5)
        assert result == []

    def test_chunk_size_one(self):
        result = chunks([1, 2, 3], 1)
        assert result == [[1], [2], [3]]


class TestIn:
    def test_basic(self):
        assert in_([1, 2, 3]) == "in(1,2,3)"

    def test_strings(self):
        assert in_(["a", "b", "c"]) == "in(a,b,c)"

    def test_single(self):
        assert in_([42]) == "in(42)"

    def test_not_list_raises(self):
        with pytest.raises(TypeError, match="not a list"):
            in_("not a list")  # type: ignore[arg-type]

    def test_not_list_tuple_raises(self):
        with pytest.raises(TypeError, match="not a list"):
            in_((1, 2, 3))  # type: ignore[arg-type]


class TestDetectQueryChunks:
    def test_no_chunks_needed(self):
        options = {"field1": "value1", "field2": "in(1,2,3)"}
        assert detect_query_chunks(options) is None

    def test_long_in_filter(self):
        # Need enough values to exceed 1950 chars
        long_values = ",".join(str(i) for i in range(1000))
        options = {"myfield": f"in({long_values})"}
        result = detect_query_chunks(options)
        assert result is not None
        assert result[0] == "myfield"
        assert len(result[1]) > 1
        # All original values should be present
        all_values = []
        for chunk in result[1]:
            all_values.extend(chunk)
        assert len(all_values) == 1000

    def test_short_in_filter_no_chunking(self):
        options = {"field": "in(1,2,3,4,5)"}
        assert detect_query_chunks(options) is None


class TestParseBodyLinks:
    def test_next_link(self):
        links_obj = {
            "next": "</economics?action=next&next_page=WellID+%3C+840600005436298&pagesize=50>; rel='next'"
        }
        result = parse_body_links(links_obj)
        assert "next" in result
        assert (
            result["next"]["url"]
            == "/economics?action=next&next_page=WellID+%3C+840600005436298&pagesize=50"
        )

    def test_no_next_link(self):
        links_obj: dict[str, str | None] = {"next": None}
        result = parse_body_links(links_obj)
        assert result == {}

    def test_empty_dict(self):
        result = parse_body_links({})
        assert result == {}
