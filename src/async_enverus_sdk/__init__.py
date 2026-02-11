"""Enverus Developer API Python Client."""

# Primary client
from async_enverus_sdk._client import EnverusClient

# Sync convenience module
from async_enverus_sdk import _sync as sync

# Models
from async_enverus_sdk.models.auth import TokenRequest, TokenResponse
from async_enverus_sdk.models.errors import ErrorResponse
from async_enverus_sdk.models.metadata import DDLField, DocsField
from async_enverus_sdk.models.pagination import LinkInfo, PaginationLinks
from async_enverus_sdk.models.query import QueryParams

# Filter DSL
from async_enverus_sdk.requests.filters import (
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
)

# Exceptions
from async_enverus_sdk._exceptions import (
    DAAuthException,
    DADatasetException,
    DAError,
    DAQueryException,
)

# Export utilities
from async_enverus_sdk._export import to_csv, to_dataframe

# Types
from async_enverus_sdk._types import Record

__all__ = [
    # Client
    "EnverusClient",
    "sync",
    # Models
    "DDLField",
    "DocsField",
    "ErrorResponse",
    "LinkInfo",
    "PaginationLinks",
    "QueryParams",
    "TokenRequest",
    "TokenResponse",
    # Filters
    "btw",
    "eq",
    "ge",
    "gt",
    "in_",
    "le",
    "lt",
    "ne",
    "nil",
    "not_",
    # Exceptions
    "DAAuthException",
    "DADatasetException",
    "DAError",
    "DAQueryException",
    # Export
    "to_csv",
    "to_dataframe",
    # Types
    "Record",
]
