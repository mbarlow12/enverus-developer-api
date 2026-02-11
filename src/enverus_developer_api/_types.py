"""Type aliases and TypedDicts for the Enverus Developer API client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, TypedDict


type Record = dict[str, Any]
type RecordIterator = Iterator[Record]
type AsyncRecordIterator = AsyncIterator[Record]


class LinkInfo(TypedDict):
    url: str
    rel: str


class PaginationLinks(TypedDict, total=False):
    next: LinkInfo
    prev: LinkInfo
