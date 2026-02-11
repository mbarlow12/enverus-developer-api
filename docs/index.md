# Enverus Developer API

A Python client for the [Enverus Developer API](https://app.enverus.com/direct/#/api/explorer/v3/gettingStarted).
Handles authentication, pagination, retry/backoff, and streaming via async generators.

Requires **Python 3.12+**.

## Installation

```bash
pip install enverus-developer-api
```

With optional [pandas](https://pandas.pydata.org/) support:

```bash
pip install 'enverus-developer-api[pandas]'
```

## Quick start

### Async (recommended)

```python
import asyncio
from enverus_developer_api import EnverusClient

async def main():
    async with EnverusClient(secret_key="<your-secret-key>") as client:
        # Stream well records
        async for record in client.query("wells", pagesize=5, deleteddate="null"):
            print(record)
            break

        # Get a record count
        count = await client.count("wells", deleteddate="null")
        print(f"{count} wells")

asyncio.run(main())
```

### Sync

The `sync` module provides synchronous wrappers around the async client:

```python
from enverus_developer_api import sync

for record in sync.query("<your-secret-key>", "wells", pagesize=5, deleteddate="null"):
    print(record)
    break
```

Your secret key can be generated and managed at
<https://app.enverus.com/provisioning/directaccess>.

## Features

- **Automatic pagination** -- `query()` returns a generator that follows
  next-page links until all records are consumed.
- **Filter DSL** -- composable functions (`eq`, `gt`, `btw`, `in_`, `not_`, ...)
  that produce API filter strings.
  See the [Filtering](examples/filtering.md) example.
- **Retry with backoff** -- 5xx errors are retried with exponential backoff
  (configurable via `retries` and `backoff_factor`).
- **Pydantic models** -- structured types for DDL fields, docs fields,
  pagination links, and more.
- **Export helpers** -- `to_csv()` and `to_dataframe()` for writing query
  results to CSV files or pandas DataFrames.

## Network configuration

```python
async with EnverusClient(
    secret_key="<your-secret-key>",
    retries=5,           # retry attempts on 5xx (default: 5)
    backoff_factor=1.0,  # exponential backoff multiplier (default: 1.0)
    proxy="http://10.10.1.10:1080",  # HTTP proxy
    verify=False,        # disable SSL verification (not recommended)
) as client:
    ...
```

## Next steps

- [Examples](examples/quickstart.md) -- runnable scripts covering common workflows
- [API Reference](reference/index.md) -- full autodoc for all public classes and functions
