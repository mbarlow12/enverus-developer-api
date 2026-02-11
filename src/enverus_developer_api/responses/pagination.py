"""Pagination link extraction from response headers or body."""

from __future__ import annotations

import re

import httpx

from enverus_developer_api.models.pagination import LinkInfo, PaginationLinks


def extract_links(
    response: httpx.Response, *, from_body: bool = False
) -> PaginationLinks | None:
    """Extract pagination links from response headers or body.

    Args:
        response: The httpx response.
        from_body: If True, parse links from the JSON body ``links`` field
            (used with ``X-Omit-Header-Next-Links: true``).

    Returns:
        Parsed PaginationLinks or None if no links found.
    """
    if from_body:
        data = response.json()
        if not isinstance(data, dict) or "links" not in data:
            return None
        return _parse_body_links(data["links"])

    # Parse from HTTP Link headers
    if "next" not in response.links:
        return None

    links_dict = response.links
    next_info = links_dict.get("next")
    if next_info and "url" in next_info:
        return PaginationLinks(next=LinkInfo(url=next_info["url"], rel="next"))
    return None


def _parse_body_links(links_obj: dict[str, str | None]) -> PaginationLinks | None:
    """Parse link objects from the JSON response body.

    When X-Omit-Header-Next-Links is set, pagination links come in the
    JSON body rather than HTTP headers.
    """
    next_link = links_obj.get("next")
    if not next_link:
        return None

    # Parse Link header format: </path?query>; rel='next'
    for part in next_link.split(","):
        part = part.strip()
        match = re.match(r"<([^>]+)>(?:\s*;\s*rel=['\"]?(\w+)['\"]?)?", part)
        if match:
            url = match.group(1)
            rel = match.group(2) or "next"
            return PaginationLinks(next=LinkInfo(url=url, rel=rel))

    return None
