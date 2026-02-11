"""Type aliases for the Enverus Developer API client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

type Record = dict[str, Any]
type RecordIterator = Iterator[Record]
type AsyncRecordIterator = AsyncIterator[Record]
