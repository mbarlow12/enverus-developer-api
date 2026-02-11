# enverus-developer-api

[![PyPI version](https://badge.fury.io/py/enverus-developer-api.svg)](https://badge.fury.io/py/enverus-developer-api)

A Python client for the Enverus Developer API. Handles authentication,
pagination, retry/backoff, and streaming via async generators.

Requires Python 3.12+.

## Install

```bash
pip install enverus-developer-api
```

With optional pandas support:

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
        async for record in client.query("wells", pagesize=5, deleteddate="null"):
            print(record)
            break

asyncio.run(main())
```

### Sync

```python
from enverus_developer_api import sync

for record in sync.query("<your-secret-key>", "wells", pagesize=5, deleteddate="null"):
    print(record)
    break
```

Your secret key can be generated at <https://app.enverus.com/provisioning/directaccess>.

## Documentation

See the [documentation](docs/) for examples, the filter DSL reference, and full
API docs.
