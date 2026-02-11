"""Query parameter building and auto-chunking for large in_() filters."""

from __future__ import annotations

import re
from collections.abc import Sequence
from math import floor
from typing import Any

from async_enverus_sdk.requests.filters import in_ as in_filter

MAX_QUERY_STRING_LENGTH = 1950


def chunks(iterable: Sequence[Any], n: int) -> list[list[Any]]:
    """Split a sequence into chunks of at most *n* items."""
    length = len(iterable)
    return [list(iterable[i : min(i + n, length)]) for i in range(0, length, n)]


def detect_query_chunks(
    options: dict[str, Any],
) -> tuple[str, list[list[str]]] | None:
    """Detect if any filter value needs to be chunked due to URL length limits.

    Returns ``(field_name, list_of_chunks)`` or ``None``.
    """
    for field, v in options.items():
        v_str = str(v)
        if "in(" in v_str and len(v_str) > MAX_QUERY_STRING_LENGTH:
            values = re.split(r"in\((.*?)\)", v_str)[1].split(",")
            chunksize = int(floor(MAX_QUERY_STRING_LENGTH / len(max(values))))
            return (field, chunks(values, chunksize))
    return None


def build_query_params(
    options: dict[str, Any],
) -> tuple[dict[str, Any], tuple[str, list[list[str]]] | None]:
    """Build query parameters and detect auto-chunking needs.

    Returns ``(params_dict, query_chunks_or_none)``.
    """
    query_chunks = detect_query_chunks(options)
    return options, query_chunks


def format_in(items: list[Any]) -> str:
    """Format a list of values for the API's ``in()`` filter function.

    This is the backwards-compatible version that accepts a list (not varargs).
    """
    if not isinstance(items, list):
        raise TypeError(
            f"Argument provided was not a list. Type provided: {type(items)}"
        )
    return in_filter(*items)
