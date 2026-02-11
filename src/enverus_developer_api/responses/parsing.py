"""Response data parsing utilities."""

from __future__ import annotations

import re

import httpx

from enverus_developer_api._types import Record
from enverus_developer_api.models.metadata import DDLField, DocsField


def parse_records(response: httpx.Response) -> list[Record]:
    """Parse records from a query response.

    Handles both list and single-dict responses.
    """
    data = response.json()
    if isinstance(data, dict):
        return [data]
    return data  # type: ignore[no-any-return]


def parse_ddl(text: str) -> list[DDLField]:
    """Parse a DDL text response into structured DDLField models.

    Expects CREATE TABLE format like::

        CREATE TABLE wells (
        WellID INT NOT NULL,
        WellName VARCHAR(255),
        CONSTRAINT pk PRIMARY KEY (WellID)
        )
    """
    fields: list[DDLField] = []
    primary_keys: set[str] = set()

    # Extract primary key columns
    pk_match = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", text, re.IGNORECASE)
    if pk_match:
        primary_keys = {k.strip() for k in pk_match.group(1).split(",")}

    # Parse field definitions (skip first line CREATE TABLE and CONSTRAINT lines)
    for line in text.split("\n")[1:]:
        line = line.strip().rstrip(",")
        if not line or "CONSTRAINT" in line or line.startswith(")"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            # Type may include size like VARCHAR(255) — take everything up to
            # NOT NULL or comma
            type_str = parts[1].rstrip(",")
            fields.append(
                DDLField(
                    name=name,
                    type=type_str,
                    primary_key=name.upper() in {pk.upper() for pk in primary_keys},
                )
            )

    return fields


def parse_docs(data: list[dict[str, str]]) -> list[DocsField]:
    """Parse docs endpoint response into DocsField models."""
    return [
        DocsField(
            name=item.get("name", ""),
            required=item.get("required", "false").lower() == "true"
            if isinstance(item.get("required"), str)
            else bool(item.get("required", False)),
            default=item.get("default", ""),
            requirements=item.get("requirements", ""),
            description=item.get("description", ""),
            filter_type=item.get("filter_type", ""),
        )
        for item in data
    ]
