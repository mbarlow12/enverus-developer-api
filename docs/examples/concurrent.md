# Async Patterns

The async client works well with Python's structured concurrency primitives.
This example shows how to run metadata requests in parallel, stream query
results, and convert everything to a typed DataFrame.

## Parallel metadata fetches

Use `asyncio.TaskGroup` to run independent requests concurrently:

```python
import asyncio
from async_enverus_sdk import EnverusClient

SECRET_KEY = "..."

async def main() -> None:
    async with EnverusClient(secret_key=SECRET_KEY) as client:
        async with asyncio.TaskGroup() as tg:
            ddl_task = tg.create_task(client.ddl("wells"))
            count_task = tg.create_task(
                client.count("wells", deleteddate="null")
            )

        ddl_fields = ddl_task.result()
        total = count_task.result()
        print(f"{total} records, {len(ddl_fields)} DDL fields")

asyncio.run(main())
```

Both the DDL and count requests run concurrently over the same connection pool.

## Streaming query to DataFrame

After fetching DDL fields, stream records and convert them to a pandas
DataFrame with proper dtypes:

```python
import asyncio
from async_enverus_sdk import EnverusClient, not_, nil, to_dataframe

SECRET_KEY = "..."

async def main() -> None:
    async with EnverusClient(secret_key=SECRET_KEY) as client:
        # Fetch DDL for dtype inference
        ddl_fields = await client.ddl("wells")

        # Stream records
        records: list[dict] = []
        async for record in client.query(
            "wells", pagesize=100, deleteddate="null", stateprovince=not_(nil())
        ):
            records.append(record)
            if len(records) >= 100:
                break

        # Convert with DDL-based dtypes
        df = to_dataframe(records, ddl_fields=ddl_fields)
        print(df.dtypes)
        print(df.head())

asyncio.run(main())
```

`to_dataframe()` uses the DDL field types to set appropriate pandas dtypes,
avoiding the default object-dtype columns you'd get from `pd.DataFrame(records)`.

## Full example

See [`examples/concurrent.py`](https://github.com/enverus-ea/async-enverus-sdk/blob/master/examples/concurrent.py)
for a runnable script combining all of these patterns.
