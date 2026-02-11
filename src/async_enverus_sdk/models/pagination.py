"""Pagination link models."""

from pydantic import BaseModel


class LinkInfo(BaseModel):
    """A single pagination link with URL and relation type."""

    url: str
    rel: str


class PaginationLinks(BaseModel):
    """Parsed pagination links from response headers or body."""

    next: LinkInfo | None = None
    prev: LinkInfo | None = None
