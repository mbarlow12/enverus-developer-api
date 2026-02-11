# Filtering

The Enverus API supports server-side filtering via special expression strings
passed as query parameter values. This library provides a **filter DSL** --
a set of composable functions that produce those strings for you.

## Filter functions

| Function | Example | Output |
|----------|---------|--------|
| `eq(value)` | `eq("TX")` | `eq(TX)` |
| `ne(value)` | `ne("TX")` | `ne(TX)` |
| `gt(value)` | `gt("2024-01-01")` | `gt(2024-01-01)` |
| `ge(value)` | `ge(100)` | `ge(100)` |
| `lt(value)` | `lt(500)` | `lt(500)` |
| `le(value)` | `le(1000)` | `le(1000)` |
| `in_(*values)` | `in_("TX", "NM")` | `in(TX,NM)` |
| `btw(low, high)` | `btw("2024-01-01", "2024-06-01")` | `btw(2024-01-01,2024-06-01)` |
| `nil()` | `nil()` | `nil` |
| `not_(expr)` | `not_(nil())` | `not(nil)` |

All functions are importable from the top-level package:

```python
from async_enverus_sdk import eq, ne, gt, ge, lt, le, in_, btw, nil, not_
```

## Composition

`not_()` wraps any other expression:

```python
not_(in_("TX", "LA"))   # "not(in(TX,LA))"
not_(nil())              # "not(nil)"
```

## Using filters in queries

Pass filter expressions as keyword arguments to `query()` or `count()`:

```python
from async_enverus_sdk import sync, in_, nil

SECRET_KEY = "..."

# Count wells in TX or NM that have a deleted date
count = sync.count(
    SECRET_KEY,
    "wells",
    stateprovince=in_("TX", "NM"),
    deleteddate=nil(),
)
print(f"{count} wells")

# Fetch a few matching records
for record in sync.query(
    SECRET_KEY,
    "wells",
    pagesize=3,
    stateprovince=in_("TX", "NM"),
    deleteddate=nil(),
):
    print(record)
```

You can also pass raw filter strings directly if you prefer:

```python
for record in sync.query(
    SECRET_KEY,
    "wells",
    updateddate="gt(2024-01-01)",
    deleteddate="null",
):
    print(record)
```

## Full example

See [`examples/filtering.py`](https://github.com/enverus-ea/async-enverus-sdk/blob/master/examples/filtering.py)
for a runnable script demonstrating all filter functions.
