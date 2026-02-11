"""Enverus Developer API Python Client."""

# Primary client
from enverus_developer_api._client import EnverusClient

# Sync convenience module
from enverus_developer_api import _sync as sync

# Models
from enverus_developer_api.models.auth import TokenRequest, TokenResponse
from enverus_developer_api.models.errors import ErrorResponse
from enverus_developer_api.models.metadata import DDLField, DocsField
from enverus_developer_api.models.pagination import LinkInfo, PaginationLinks
from enverus_developer_api.models.query import QueryParams

# Filter DSL
from enverus_developer_api.requests.filters import (
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
from enverus_developer_api._exceptions import (
    DAAuthException,
    DADatasetException,
    DAError,
    DAQueryException,
)

# Export utilities
from enverus_developer_api._export import to_csv, to_dataframe

# Types
from enverus_developer_api._types import Record

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
