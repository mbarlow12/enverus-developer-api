# async-enverus-sdk

> This is an async-first fork of [`enverus-developer-api`](https://github.com/enverus-ea/enverus-developer-api)
> with Pydantic models, a filter DSL, and modern Python (3.12+).

A Python client for the Enverus Developer API. Handles authentication,
pagination, retry/backoff, and streaming via async generators.

## Install

```bash
pip install async-enverus-sdk
```

With optional pandas support:

```bash
pip install 'async-enverus-sdk[pandas]'
```

## Quick start

### Async (recommended)

```python
import asyncio
from async_enverus_sdk import EnverusClient

async def main():
    async with EnverusClient(secret_key="<your-secret-key>") as client:
        async for record in client.query("wells", pagesize=5, deleteddate="null"):
            print(record)
            break

asyncio.run(main())
```

### Sync

```python
from async_enverus_sdk import sync

for record in sync.query("<your-secret-key>", "wells", pagesize=5, deleteddate="null"):
    print(record)
    break
```

Your secret key can be generated at <https://app.enverus.com/provisioning/directaccess>.

## Documentation

See the [documentation](docs/) for examples, the filter DSL reference, and full
API docs.
