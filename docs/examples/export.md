# Exporting Data

The library provides two standalone export helpers that accept any iterable of
record dicts, including the generators returned by `query()` and `sync.query()`.

## Export to CSV

`to_csv()` streams records to a CSV file. Additional keyword arguments are
forwarded to `csv.writer`, giving you control over delimiters and quoting.

```python
import csv
import os
import tempfile

from async_enverus_sdk import sync, to_csv

SECRET_KEY = "..."

csv_path = os.path.join(tempfile.mkdtemp(), "wells.csv")

records = sync.query(SECRET_KEY, "wells", pagesize=1000, deleteddate="null")
rows_written = to_csv(records, csv_path, delimiter=",", quoting=csv.QUOTE_MINIMAL)
print(f"Wrote {rows_written} rows to {csv_path}")
```

Progress is logged every 100,000 rows by default. Pass `log_progress=False` to
silence it.

## Export to DataFrame

`to_dataframe()` converts records to a pandas DataFrame. When you provide DDL
fields, column dtypes are inferred from the database schema instead of relying
on pandas' default inference.

```python
from async_enverus_sdk import sync, to_dataframe

SECRET_KEY = "..."

# 1. Fetch DDL fields for proper column types
ddl_fields = sync.ddl(SECRET_KEY, "wells")

# 2. Stream records and build a typed DataFrame
records = sync.query(SECRET_KEY, "wells", pagesize=1000, deleteddate="null")
df = to_dataframe(records, ddl_fields=ddl_fields)

print(df.dtypes)
print(df.head())
```

You can also pass `converters` to apply custom transformations per column:

```python
df = to_dataframe(
    records,
    ddl_fields=ddl_fields,
    converters={
        "StateProvince": lambda x: x.upper(),
        "ENVOperator": lambda x: x.replace(",", ""),
    },
)
```

!!! note
    The `pandas` optional dependency is required:
    ```bash
    pip install 'async-enverus-sdk[pandas]'
    ```

## Full example

See [`examples/export.py`](https://github.com/enverus-ea/async-enverus-sdk/blob/master/examples/export.py)
for a runnable script.
