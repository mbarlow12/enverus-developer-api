"""Export utilities: to_csv and to_dataframe as standalone functions."""

from __future__ import annotations

import csv
import logging
import os
from collections import OrderedDict
from collections.abc import Iterable
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any
from uuid import uuid4

from enverus_developer_api._types import Record
from enverus_developer_api.models.metadata import DDLField

logger = logging.getLogger("directaccess")

DEFAULT_DATAFRAME_PAGESIZE = 100_000

# DDL SQL type → pandas dtype mapping
_DTYPES_MAPPING: dict[str, str] = {
    "TEXT": "object",
    "NUMERIC": "float64",
    "REAL": "float64",
    "DOUBLE": "float64",
    "DATETIME": "object",
    "SMALLINT": "Int64",
    "INT": "Int64",
    "INTEGER": "Int64",
    "BIGINT": "Int64",
    "VARCHAR": "object",
    "DATE": "object",
}


def to_csv(
    records: Iterable[Record],
    path: str | Path,
    *,
    log_progress: bool = True,
    **csv_kwargs: Any,
) -> int:
    """Write records to a CSV file.

    Args:
        records: Iterable of record dicts.
        path: Filesystem path for the CSV file.
        log_progress: If True, log a message every 100k rows.
        **csv_kwargs: Passed to :class:`csv.writer`.

    Returns:
        Number of rows written.
    """
    path = str(path)
    count = 0
    with open(path, mode="w", newline="") as f:
        writer = csv.writer(f, **csv_kwargs)
        for i, row in enumerate(records, start=1):
            row = OrderedDict(sorted(row.items(), key=lambda t: t[0]))
            count = i
            if count == 1:
                writer.writerow(row.keys())
            writer.writerow(row.values())

            if log_progress and i % 100_000 == 0:
                logger.info("Wrote %d records to file %s", count, path)

        logger.info("Completed writing CSV file to %s. Final count %d", path, count)

    return count


def _ddl_to_dtypes(
    ddl_fields: list[DDLField], filter_fields: set[str]
) -> dict[str, str]:
    """Map DDL field types to pandas dtypes for fields present in filter_fields."""
    dtypes: dict[str, str] = {}
    for field in ddl_fields:
        if field.name not in filter_fields:
            continue
        # Normalize the type: strip size suffixes like VARCHAR(255)
        type_upper = field.type.upper()
        if type_upper.startswith("VARCHAR"):
            type_upper = "VARCHAR"
        elif type_upper.startswith("DOUBL"):
            type_upper = "DOUBLE"

        mapped = _DTYPES_MAPPING.get(type_upper)
        if mapped:
            dtypes[field.name] = mapped
    return dtypes


def _detect_index(ddl_fields: list[DDLField]) -> list[str] | str | None:
    """Detect primary key column(s) from DDL fields."""
    pk_cols = [f.name for f in ddl_fields if f.primary_key]
    if not pk_cols:
        return None
    if len(pk_cols) == 1:
        return pk_cols[0]
    return pk_cols


def _detect_date_columns(
    ddl_fields: list[DDLField], filter_fields: set[str]
) -> list[str]:
    """Detect date columns from DDL fields."""
    return [
        f.name
        for f in ddl_fields
        if f.type.upper().startswith("DATE") and f.name in filter_fields
    ]


def to_dataframe(
    records: Iterable[Record],
    *,
    ddl_fields: list[DDLField] | None = None,
    ddl_text: str | None = None,
    pagesize: int = DEFAULT_DATAFRAME_PAGESIZE,
    converters: dict[str, Any] | None = None,
    log_progress: bool = True,
) -> Any:
    """Convert records to a pandas DataFrame with optional DDL-based dtype inference.

    Args:
        records: Iterable of record dicts.
        ddl_fields: Pre-parsed DDL fields for dtype inference.
        ddl_text: Raw DDL text (alternative to ddl_fields — will be parsed).
        pagesize: Chunk size for reading the staged CSV.
        converters: Dict of functions for converting column values.
        log_progress: If True, log progress messages.

    Returns:
        A pandas DataFrame.
    """
    try:
        import pandas
    except ImportError:
        raise ImportError(
            "pandas not installed. Install with: "
            "pip install 'enverus-developer-api[pandas]'"
        )

    from enverus_developer_api.responses.parsing import parse_ddl

    # Parse DDL if provided as text
    if ddl_fields is None and ddl_text is not None:
        ddl_fields = parse_ddl(ddl_text)

    # Stage records to a temp CSV
    tmpdir = mkdtemp()
    try:
        csv_path = os.path.join(tmpdir, f"{uuid4().hex}.csv")
        row_count = to_csv(records, csv_path, delimiter="|", log_progress=log_progress)

        if row_count == 0:
            return pandas.DataFrame()

        # Determine column names from first data row for dtype filtering
        with open(csv_path) as f:
            reader = csv.reader(f, delimiter="|")
            header = next(reader, None)
        filter_fields = set(header) if header else set()

        # Build dtype inference from DDL
        dtypes: dict[str, str] | None = None
        index_col: list[str] | str | None = None
        date_cols: list[str] = []

        if ddl_fields:
            dtypes = _ddl_to_dtypes(ddl_fields, filter_fields)
            raw_index = _detect_index(ddl_fields)
            # Filter index to only columns present in the data
            if isinstance(raw_index, list):
                index_col = [c for c in raw_index if c in filter_fields] or None
                if index_col and len(index_col) == 1:
                    index_col = index_col[0]
            elif isinstance(raw_index, str) and raw_index in filter_fields:
                index_col = raw_index
            date_cols = _detect_date_columns(ddl_fields, filter_fields)

        pd_chunks = pandas.read_csv(
            filepath_or_buffer=csv_path,
            sep="|",
            dtype=dtypes,  # type: ignore[arg-type]
            index_col=index_col,
            parse_dates=date_cols if date_cols else False,
            chunksize=pagesize,
            converters=converters,
        )
        df: Any = pandas.concat(pd_chunks)
        return df
    finally:
        rmtree(tmpdir)
        logger.debug("Removed temporary directory")
