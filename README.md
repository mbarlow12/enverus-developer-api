# enverus-developer-api

[![PyPI version](https://badge.fury.io/py/enverus-developer-api.svg)](https://badge.fury.io/py/enverus-developer-api)

A thin wrapper around Enverus' Developer API. Handles authentication and token management, pagination and
network-related error handling/retries.

Requires Python 3.12+. Supports both sync and async usage via `httpx`.

## Install

```commandline
pip install enverus-developer-api
```

With optional pandas support:

```commandline
pip install 'enverus-developer-api[pandas]'
```

## Clients

### Developer API - Version 3 (Sync)

```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(secret_key='<your-secret-key>')
```

### Developer API - Version 3 (Async)

```python
import asyncio
from enverus_developer_api import AsyncDeveloperAPIv3

async def main():
    async with AsyncDeveloperAPIv3(secret_key='<your-secret-key>') as v3:
        async for row in v3.query('wells', pagesize=5, deleteddate='null'):
            print(row)
            break

asyncio.run(main())
```

Your secret_key can be generated, retrieved and revoked at <https://app.enverus.com/provisioning/directaccess>

The Developer API Version 3 endpoint documentation can be found at <https://app.enverus.com/direct/#/api/explorer/v3/gettingStarted>

### Direct Access - Version 2

```python
from enverus_developer_api import DirectAccessV2

d2 = DirectAccessV2(
    client_id='<your-client-id>',
    client_secret='<your-client-secret>',
)
```

The Direct Access Version 2 endpoint documentation can be found at <https://app.enverus.com/direct/#/api/explorer/v2/gettingStarted>

## Usage

The functionality outlined below exists for **both** DeveloperAPIv3 and DirectAccessV2 clients (and their async variants).

Only 1 instance of the client needs to be created to perform all your queries. It can execute multiple simultaneous requests if needed,
and will automatically refresh the access_token for the Authorization header if expired.
An access_token is valid for 8 hours, and there is rate limit on the number of access_tokens that can be requested per minute
which is why we recommend creating and reusing a single DeveloperAPIv3 client instance for all of your querying.

Provide the query method the dataset and query params. All query parameters must match the valid
Request Parameters found in the Developer API documentation for a given dataset and be passed as keyword arguments.

```python
for row in v3.query('wells', county='REEVES', deleteddate='null'):
    print(row)
```

### Filter functions

Developer API supports filter functions. These can be passed as strings on the keyword arguments.

Some common filters are greater than (`gt()`), less than (`lt()`), null, not null (`not(null)`) and between (`btw()`).
See the Developer API documentation for a list of all available filters.

```python
# Get well records updated after 2018-08-01 and without deleted dates
for row in v3.query('wells', updateddate='gt(2018-08-01)', deleteddate='null'):
    print(row)

# Get permit records with approved dates between 2018-03-01 and 2018-06-01
for row in v3.query('rigs', spuddate='btw(2018-03-01,2018-06-01)'):
    print(row)
```

You can use the `fields` keyword to limit the returned fields in your request.

```python
for row in v3.query('rigs', fields='PermitApprovedDate,LeaseName,RigName_Number,MD_FT'):
    print(row)
```

### Escaping

When making requests containing certain characters like commas, use a backslash to escape them.

```python
# Escaping the comma before LLC
for row in v3.query('rigs', envoperator='PERCUSSION PETROLEUM OPERATING\, LLC'):
    print(row)
```

### Network request handling

This module supports:

- retries and backoff
- network proxies
- ssl verification

#### Retries and backoff

Specify the number of retry attempts in `retries` and the backoff factor in `backoff_factor`. Retries use exponential
backoff on 5xx errors (500, 502, 503, 504).

```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(
    secret_key='<your-secret-key>',
    retries=5,
    backoff_factor=1
)
```

You can specify a network proxy by passing a string URL to `proxy`.

```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(
    secret_key='<your-secret-key>',
    proxy='http://10.10.1.10:1080'
)
```

Finally, if you're in an environment that provides its own SSL certificates that might not be in your trusted store,
you can choose to ignore SSL verification altogether. This is typically not a good idea and you should seek to resolve
certificate errors instead of ignore them.

```python
from enverus_developer_api import DeveloperAPIv3

v3 = DeveloperAPIv3(
    secret_key='<your-secret-key>',
    verify=False
)
```

## Functions

### docs

Returns a sample response for a given dataset

```python
docs = v3.docs("casings")
```

### ddl

Returns a CREATE TABLE DDL statement for a given dataset. Must specify either
"mssql" for MS SQL Server or "pg" for PostgreSQL as the database argument

```python
from tempfile import TemporaryFile

ddl = v3.ddl("casings", database="pg")
with TemporaryFile(mode="w+") as f:
  f.write(ddl)
  f.seek(0)
  for line in f:
    print(line, end='')
```

### count

Returns the count of records for a given dataset and query options in the
X-QUERY-RECORD-COUNT response header value

```python
count = v3.count("rigs", deleteddate="null")
```

### query

Accepts a dataset name, request headers and a variable number of keyword arguments that correspond to the fields specified
in the 'Request Parameters' section for each dataset in the Developer API documentation.

This method only supports the JSON output provided by the API and yields dicts for each record

```python
for row in v3.query("rigs", pagesize=1000, deleteddate="null"):
    print(row)
```

##### X-Omit-Header-Next-Links header

Omit the Next Link in the Response Header section, add the Next Link to the JSON Response Body.

```python
for row in v3.query("rigs", pagesize=1000, deleteddate="null", _headers={'X-Omit-Header-Next-Links': 'true'}):
    print(row)
```

### to_csv

Write query results to CSV. Optional keyword arguments are provided to the csv writer object,
allowing control over delimiters, quoting, etc. The default is comma-separated with csv.QUOTE_MINIMAL

```python
import csv, os
from tempfile import mkdtemp

tempdir = mkdtemp()
path = os.path.join(tempdir, "rigs.csv")

dataset = "rigs"
options = dict(pagesize=10000, deleteddate="null")

query = v3.query(dataset, **options)
v3.to_csv(query, path, log_progress=True, delimiter=",", quoting=csv.QUOTE_MINIMAL)

with open(path, mode="r") as f:
  reader = csv.reader(f)
```

### to_dataframe

Write query results to a pandas Dataframe with properly set dtypes and index columns.

You will need to have pandas installed to use the to_dataframe function

```commandline
pip install 'enverus-developer-api[pandas]'
```

Create a pandas dataframe from a dataset query

```python
df = v3.to_dataframe("rigs", pagesize=10000, deleteddate="null")
```

Create a Texas rigs dataframe, replacing the state abbreviation with the complete name
and removing commas from Operator names

```python
df = v3.to_dataframe(
  dataset="rigs",
  deleteddate="null",
  pagesize=100000,
  stateprovince="TX",
  converters={
    "StateProvince": lambda x: "TEXAS",
    "ENVOperator": lambda x: x.replace(",", "")
  }
)
df.head(10)
```

Reset the index of the DataFrame, and use the default one instead. [reset_index()](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.reset_index.html)

```python
    df = v3.to_dataframe(dataset, pagesize=10000, ENVBasin="SACRAMENTO")
    df.reset_index(inplace=True)
    df.head(10)
```

## Migration from v3.x

v4.0.0 is a major version bump with the following breaking changes:

- **Python 3.12+ required** (dropped Python 2.7 and 3.x < 3.12)
- **`httpx` replaces `requests`** — the `.session` attribute is removed
- **`proxies={}` dict replaced by `proxy=""` string** (httpx convention)
- **`self.links` attribute removed** — pagination state is now generator-local (thread-safe)
- **`unicodecsv` dropped** — `to_csv` uses stdlib `csv`
- **`ddl()` uses keyword-only `database` arg** — `v3.ddl("wells", database="pg")` instead of `v3.ddl("wells", "pg")`

Import paths and class/method names remain the same.
