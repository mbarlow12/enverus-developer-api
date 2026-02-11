# Quick Start

The library provides two usage patterns:

- **Async** (recommended) -- `EnverusClient` is an async context manager with
  async generator–based pagination.
- **Sync** -- the `sync` module wraps the async client behind a background event
  loop so you can use plain `for` loops.

## Async usage

```python
import asyncio
from enverus_developer_api import EnverusClient

SECRET_KEY = "..."

async def main() -> None:
    async with EnverusClient(secret_key=SECRET_KEY) as client:
        # Stream well records
        async for record in client.query("wells", pagesize=5, deleteddate="null"):
            print(record)
            break

        # Get a record count
        count = await client.count("wells", deleteddate="null")
        print(f"{count} active wells")

        # Fetch DDL (field definitions)
        fields = await client.ddl("wells")
        for field in fields[:5]:
            print(f"  {field.name}: {field.type}")

asyncio.run(main())
```

`EnverusClient` should be used as an async context manager so the underlying
HTTP connection pool is properly closed. All methods that hit the network are
`async`.

`query()` returns an `AsyncIterator[Record]` that transparently follows
next-page links, so you can consume an arbitrarily large result set with a
simple `async for` loop.

## Sync usage

If you don't need async, the `sync` module exposes the same operations as
top-level functions. Each call creates a short-lived client behind the scenes.

```python
from enverus_developer_api import sync

SECRET_KEY = "..."

for record in sync.query(SECRET_KEY, "wells", pagesize=5, deleteddate="null"):
    print(record)
    break
```

Available sync functions: `query`, `count`, `ddl`, `docs`.

## Full example

See [`examples/quickstart.py`](https://github.com/enverus-ea/enverus-developer-api/blob/master/examples/quickstart.py)
for a runnable script.
