"""Tests for requests/query.py — param building and auto-chunking."""

import pytest

from async_enverus_sdk.requests.query import (
    build_query_params,
    chunks,
    detect_query_chunks,
    format_in,
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


class TestDetectQueryChunks:
    def test_no_chunks_needed(self):
        options = {"field1": "value1", "field2": "in(1,2,3)"}
        assert detect_query_chunks(options) is None

    def test_long_in_filter(self):
        long_values = ",".join(str(i) for i in range(1000))
        options = {"myfield": f"in({long_values})"}
        result = detect_query_chunks(options)
        assert result is not None
        assert result[0] == "myfield"
        assert len(result[1]) > 1
        all_values = []
        for chunk in result[1]:
            all_values.extend(chunk)
        assert len(all_values) == 1000

    def test_short_in_filter_no_chunking(self):
        options = {"field": "in(1,2,3,4,5)"}
        assert detect_query_chunks(options) is None


class TestFormatIn:
    def test_basic(self):
        assert format_in([1, 2, 3]) == "in(1,2,3)"

    def test_strings(self):
        assert format_in(["a", "b", "c"]) == "in(a,b,c)"

    def test_single(self):
        assert format_in([42]) == "in(42)"

    def test_not_list_raises(self):
        with pytest.raises(TypeError, match="not a list"):
            format_in("not a list")  # type: ignore[arg-type]

    def test_not_list_tuple_raises(self):
        with pytest.raises(TypeError, match="not a list"):
            format_in((1, 2, 3))  # type: ignore[arg-type]


class TestBuildQueryParams:
    def test_returns_params_and_none_when_no_chunks(self):
        options = {"deleteddate": "null", "pagesize": 100}
        params, query_chunks = build_query_params(options)
        assert params is options
        assert query_chunks is None

    def test_returns_chunks_for_long_in(self):
        long_values = ",".join(str(i) for i in range(1000))
        options = {"myfield": f"in({long_values})"}
        params, query_chunks = build_query_params(options)
        assert query_chunks is not None
        assert query_chunks[0] == "myfield"
