"""Exporting query results to CSV and pandas DataFrames.

Demonstrates the standalone ``to_csv()`` and ``to_dataframe()`` helpers.

Requires the ENVERUS_SECRET_KEY environment variable.
The ``to_dataframe()`` example also needs the ``pandas`` optional dependency.
"""

import csv
import os
import tempfile

from async_enverus_sdk import sync, to_csv, to_dataframe

SECRET_KEY = os.environ["ENVERUS_SECRET_KEY"]
DATASET = "wells"
FILTERS = {"pagesize": 1000, "deleteddate": "null"}

# --- Export to CSV ---
csv_path = os.path.join(tempfile.mkdtemp(), "wells.csv")

records = sync.query(SECRET_KEY, DATASET, **FILTERS)
rows_written = to_csv(records, csv_path, delimiter=",", quoting=csv.QUOTE_MINIMAL)
print(f"Wrote {rows_written} rows to {csv_path}")

# --- Export to DataFrame with DDL-based dtype inference ---

# 1. Fetch DDL fields for proper column types
ddl_fields = sync.ddl(SECRET_KEY, DATASET)

# 2. Stream records and build a typed DataFrame
records = sync.query(SECRET_KEY, DATASET, **FILTERS)
df = to_dataframe(records, ddl_fields=ddl_fields)

print(df.dtypes)
print(df.head())
