"""Synchronous convenience functions backed by a cached background event loop.

Usage::

    from enverus_developer_api import sync

    for row in sync.query("my-secret-key", "wells", deleteddate="null", pagesize=10):
        print(row)

    count = sync.count("my-secret-key", "wells", deleteddate="null")
"""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Coroutine, Iterator
from typing import Any, TypeVar

_T = TypeVar("_T")

from enverus_developer_api._client import EnverusClient
from enverus_developer_api._types import Record
from enverus_developer_api.models.metadata import DDLField, DocsField

_SENTINEL = object()

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_lock = threading.Lock()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create a module-level background event loop."""
    global _loop, _thread
    with _lock:
        if _loop is None or not _loop.is_running():
            _loop = asyncio.new_event_loop()
            _thread = threading.Thread(target=_loop.run_forever, daemon=True)
            _thread.start()
        return _loop


def _run_coro(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run a coroutine on the background event loop and return the result."""
    loop = _get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def query(
    secret_key: str,
    dataset: str,
    *,
    base_url: str = "https://api.enverus.com/v3/direct-access/",
    retries: int = 5,
    backoff_factor: float = 1.0,
    timeout: float = 30.0,
    **filters: Any,
) -> Iterator[Record]:
    """Sync streaming query. Creates client per call, streams via background loop.

    Records flow through a thread-safe queue from the async generator
    to the sync iterator.
    """
    loop = _get_event_loop()
    q: queue.Queue[Any] = queue.Queue(maxsize=1000)

    async def _producer() -> None:
        async with EnverusClient(
            secret_key,
            base_url=base_url,
            retries=retries,
            backoff_factor=backoff_factor,
            timeout=timeout,
        ) as client:
            try:
                async for record in client.query(dataset, **filters):
                    q.put(record)
            except Exception as e:
                q.put(e)
            finally:
                q.put(_SENTINEL)

    asyncio.run_coroutine_threadsafe(_producer(), loop)

    while True:
        item = q.get()
        if item is _SENTINEL:
            break
        if isinstance(item, BaseException):
            raise item
        yield item


def count(
    secret_key: str,
    dataset: str,
    *,
    base_url: str = "https://api.enverus.com/v3/direct-access/",
    retries: int = 5,
    backoff_factor: float = 1.0,
    timeout: float = 30.0,
    **filters: Any,
) -> int:
    """Get the count of records for a dataset."""

    async def _count() -> int:
        async with EnverusClient(
            secret_key,
            base_url=base_url,
            retries=retries,
            backoff_factor=backoff_factor,
            timeout=timeout,
        ) as client:
            return await client.count(dataset, **filters)

    return _run_coro(_count())


def ddl(
    secret_key: str,
    dataset: str,
    *,
    database: str = "prism",
    base_url: str = "https://api.enverus.com/v3/direct-access/",
    retries: int = 5,
    backoff_factor: float = 1.0,
    timeout: float = 30.0,
) -> list[DDLField]:
    """Get DDL for a dataset, parsed into structured field models."""

    async def _ddl() -> list[DDLField]:
        async with EnverusClient(
            secret_key,
            base_url=base_url,
            retries=retries,
            backoff_factor=backoff_factor,
            timeout=timeout,
        ) as client:
            return await client.ddl(dataset, database=database)

    return _run_coro(_ddl())


def docs(
    secret_key: str,
    dataset: str,
    *,
    base_url: str = "https://api.enverus.com/v3/direct-access/",
    retries: int = 5,
    backoff_factor: float = 1.0,
    timeout: float = 30.0,
) -> list[DocsField]:
    """Get docs for a dataset, parsed into structured field models."""

    async def _docs() -> list[DocsField]:
        async with EnverusClient(
            secret_key,
            base_url=base_url,
            retries=retries,
            backoff_factor=backoff_factor,
            timeout=timeout,
        ) as client:
            return await client.docs(dataset)

    return _run_coro(_docs())
