"""Tests for _export.py — to_csv and to_dataframe."""

from __future__ import annotations

import csv
import os
from shutil import rmtree
from tempfile import mkdtemp

from async_enverus_sdk._export import (
    _ddl_to_dtypes,
    _detect_date_columns,
    _detect_index,
    to_csv,
    to_dataframe,
)
from async_enverus_sdk.models.metadata import DDLField


class TestToCsv:
    def test_basic(self):
        tmpdir = mkdtemp()
        try:
            path = os.path.join(tmpdir, "test.csv")
            records = [{"A": 1, "B": 2}, {"A": 3, "B": 4}]
            count = to_csv(iter(records), path)
            assert count == 2

            with open(path) as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert len(rows) == 3  # header + 2 data
            assert rows[0] == ["A", "B"]
        finally:
            rmtree(tmpdir)

    def test_empty_records(self):
        tmpdir = mkdtemp()
        try:
            path = os.path.join(tmpdir, "empty.csv")
            count = to_csv(iter([]), path)
            assert count == 0
        finally:
            rmtree(tmpdir)

    def test_returns_count(self):
        tmpdir = mkdtemp()
        try:
            path = os.path.join(tmpdir, "test.csv")
            records = [{"x": i} for i in range(50)]
            count = to_csv(iter(records), path)
            assert count == 50
        finally:
            rmtree(tmpdir)


class TestDDLHelpers:
    def test_ddl_to_dtypes(self):
        fields = [
            DDLField(name="WellID", type="INT", primary_key=True),
            DDLField(name="WellName", type="VARCHAR(255)"),
            DDLField(name="Latitude", type="DOUBLE"),
        ]
        dtypes = _ddl_to_dtypes(fields, {"WellID", "WellName", "Latitude"})
        assert dtypes["WellID"] == "Int64"
        assert dtypes["WellName"] == "object"
        assert dtypes["Latitude"] == "float64"

    def test_ddl_to_dtypes_filters(self):
        fields = [
            DDLField(name="WellID", type="INT"),
            DDLField(name="Secret", type="INT"),
        ]
        dtypes = _ddl_to_dtypes(fields, {"WellID"})
        assert "WellID" in dtypes
        assert "Secret" not in dtypes

    def test_detect_index_single(self):
        fields = [DDLField(name="WellID", type="INT", primary_key=True)]
        assert _detect_index(fields) == "WellID"

    def test_detect_index_composite(self):
        fields = [
            DDLField(name="A", type="INT", primary_key=True),
            DDLField(name="B", type="INT", primary_key=True),
        ]
        assert _detect_index(fields) == ["A", "B"]

    def test_detect_index_none(self):
        fields = [DDLField(name="X", type="INT")]
        assert _detect_index(fields) is None

    def test_detect_date_columns(self):
        fields = [
            DDLField(name="UpdatedDate", type="DATETIME"),
            DDLField(name="SpudDate", type="DATE"),
            DDLField(name="WellID", type="INT"),
        ]
        dates = _detect_date_columns(fields, {"UpdatedDate", "SpudDate", "WellID"})
        assert set(dates) == {"UpdatedDate", "SpudDate"}


class TestToDataframe:
    def test_basic(self):
        records = [{"A": 1, "B": "hello"}, {"A": 2, "B": "world"}]
        df = to_dataframe(iter(records))
        assert len(df) == 2
        assert list(df.columns) == ["A", "B"]

    def test_with_ddl(self):
        records = [{"WellID": 1, "WellName": "Test"}]
        ddl_fields = [
            DDLField(name="WellID", type="INT", primary_key=True),
            DDLField(name="WellName", type="VARCHAR(255)"),
        ]
        df = to_dataframe(iter(records), ddl_fields=ddl_fields)
        assert len(df) == 1
        assert df.index.name == "WellID"

    def test_empty_records(self):
        df = to_dataframe(iter([]))
        assert len(df) == 0

    def test_with_ddl_text(self):
        records = [{"WellID": 1, "Lat": 30.5}]
        ddl_text = (
            "CREATE TABLE wells (\n"
            "WellID INT NOT NULL,\n"
            "Lat DOUBLE,\n"
            "CONSTRAINT pk PRIMARY KEY (WellID)\n"
            ")"
        )
        df = to_dataframe(iter(records), ddl_text=ddl_text)
        assert len(df) == 1
