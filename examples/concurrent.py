"""Async patterns: concurrent metadata fetches and streaming queries.

Uses asyncio.TaskGroup to run DDL and count requests in parallel,
then streams query results and converts them to a DataFrame.

Requires the ENVERUS_SECRET_KEY environment variable and the
``pandas`` optional dependency.
"""

import asyncio
import os

from async_enverus_sdk import EnverusClient, not_, nil, to_dataframe

SECRET_KEY = os.environ["ENVERUS_SECRET_KEY"]
DATASET = "wells"
FILTERS = {"deleteddate": "null", "stateprovince": not_(nil())}


async def main() -> None:
    async with EnverusClient(secret_key=SECRET_KEY) as client:
        # --- Parallel metadata fetches ---
        async with asyncio.TaskGroup() as tg:
            ddl_task = tg.create_task(client.ddl(DATASET))
            count_task = tg.create_task(client.count(DATASET, **FILTERS))

        ddl_fields = ddl_task.result()
        total = count_task.result()
        print(f"{total} records, {len(ddl_fields)} DDL fields")

        # --- Streaming query ---
        records: list[dict] = []
        async for record in client.query(DATASET, pagesize=100, **FILTERS):
            records.append(record)
            if len(records) >= 100:
                break

        print(f"Fetched {len(records)} records")

        # --- Convert to DataFrame with DDL-based dtypes ---
        df = to_dataframe(records, ddl_fields=ddl_fields)
        print(df.dtypes)
        print(df.head())


asyncio.run(main())
