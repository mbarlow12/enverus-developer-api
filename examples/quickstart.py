"""Getting started with the Enverus Developer API.

Demonstrates both async (recommended) and sync usage patterns
for querying datasets.

Requires the ENVERUS_SECRET_KEY environment variable.
"""

import asyncio
import os

from enverus_developer_api import EnverusClient, sync

SECRET_KEY = os.environ["ENVERUS_SECRET_KEY"]


# --- Async usage (recommended) ---
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


# --- Sync usage ---
print("\n--- Sync ---")
for record in sync.query(SECRET_KEY, "wells", pagesize=5, deleteddate="null"):
    print(record)
    break
