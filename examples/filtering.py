"""Using the filter DSL to build query expressions.

The filter functions produce strings that match the Enverus API's
filtering syntax.  They are composable: ``not_(in_("TX", "LA"))``
produces ``"not(in(TX,LA))"``.

Requires the ENVERUS_SECRET_KEY environment variable.
"""

import os

from enverus_developer_api import (
    btw,
    eq,
    ge,
    gt,
    in_,
    le,
    lt,
    ne,
    nil,
    not_,
    sync,
)

SECRET_KEY = os.environ["ENVERUS_SECRET_KEY"]
DATASET = "wells"

# --- Individual filters ---
# Equal / not equal
print("eq:", eq("TX"))        # "eq(TX)"
print("ne:", ne("TX"))        # "ne(TX)"

# Comparison
print("gt:", gt("2024-01-01"))  # "gt(2024-01-01)"
print("ge:", ge(100))           # "ge(100)"
print("lt:", lt(500))           # "lt(500)"
print("le:", le(1000))          # "le(1000)"

# Set membership
print("in_:", in_("TX", "NM", "LA"))  # "in(TX,NM,LA)"

# Range
print("btw:", btw("2024-01-01", "2024-06-01"))  # "btw(2024-01-01,2024-06-01)"

# Null checks
print("nil:", nil())           # "nil"
print("not nil:", not_(nil()))  # "not(nil)"

# --- Composition ---
print("not in:", not_(in_("TX", "LA")))  # "not(in(TX,LA))"

# --- Querying with filters ---

# Preview the count before fetching records
count = sync.count(
    SECRET_KEY,
    DATASET,
    stateprovince=in_("TX", "NM"),
    deleteddate=nil(),
)
print(f"\n{count} wells in TX or NM with a deleted date")

# Fetch a few records with the same filters
for record in sync.query(
    SECRET_KEY,
    DATASET,
    pagesize=3,
    stateprovince=in_("TX", "NM"),
    deleteddate=nil(),
):
    print(record)
