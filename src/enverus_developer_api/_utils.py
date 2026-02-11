"""Pure utility functions for the Enverus Developer API client."""

from __future__ import annotations

import re
from collections.abc import Sequence
from math import floor
from typing import Any

from enverus_developer_api._types import PaginationLinks


def chunks(iterable: Sequence[Any], n: int) -> list[list[Any]]:
    """Split a sequence into chunks of at most n items."""
    length = len(iterable)
    return [list(iterable[i : min(i + n, length)]) for i in range(0, length, n)]


def in_(items: list[Any]) -> str:
    """Format a list of values for the API's ``in()`` filter function."""
    if not isinstance(items, list):
        raise TypeError(
            f"Argument provided was not a list. Type provided: {type(items)}"
        )
    return "in({})".format(",".join(str(x) for x in items))


def detect_query_chunks(
    options: dict[str, Any],
) -> tuple[str, list[list[str]]] | None:
    """Detect if any filter value needs to be chunked due to URL length limits.

    Returns a tuple of (field_name, list_of_chunks) or None.
    """
    for field, v in options.items():
        v_str = str(v)
        if "in(" in v_str and len(v_str) > 1950:
            values = re.split(r"in\((.*?)\)", v_str)[1].split(",")
            chunksize = int(floor(1950 / len(max(values))))
            return (field, chunks(values, chunksize))
    return None


def parse_body_links(links_obj: dict[str, str | None]) -> PaginationLinks:
    """Parse link objects from the JSON response body.

    When X-Omit-Header-Next-Links is set, pagination links come in the
    JSON body rather than HTTP headers.
    """
    result: PaginationLinks = {}
    next_link = links_obj.get("next")
    if next_link:
        # Parse Link header format: </path?query>; rel='next'
        for part in next_link.split(","):
            part = part.strip()
            match = re.match(r"<([^>]+)>(?:\s*;\s*rel=['\"]?(\w+)['\"]?)?", part)
            if match:
                url = match.group(1)
                rel = match.group(2) or "next"
                result[rel] = {"url": url, "rel": rel}  # type: ignore[literal-required]
    return result
