"""Tests for responses/parsing.py — record, DDL, docs parsing."""

import httpx

from enverus_developer_api.responses.parsing import parse_ddl, parse_docs, parse_records


class TestParseRecords:
    def test_list_response(self):
        response = httpx.Response(200, json=[{"WellID": 1}, {"WellID": 2}])
        records = parse_records(response)
        assert len(records) == 2
        assert records[0]["WellID"] == 1

    def test_single_dict_response(self):
        response = httpx.Response(200, json={"WellID": 1})
        records = parse_records(response)
        assert len(records) == 1
        assert records[0]["WellID"] == 1

    def test_empty_list(self):
        response = httpx.Response(200, json=[])
        records = parse_records(response)
        assert records == []


class TestParseDDL:
    def test_basic_ddl(self):
        ddl_text = (
            "CREATE TABLE wells (\n"
            "WellID INT NOT NULL,\n"
            "WellName VARCHAR(255),\n"
            "Latitude DOUBLE,\n"
            "CONSTRAINT pk PRIMARY KEY (WellID)\n"
            ")"
        )
        fields = parse_ddl(ddl_text)
        assert len(fields) == 3
        assert fields[0].name == "WellID"
        assert fields[0].type == "INT"
        assert fields[0].primary_key is True
        assert fields[1].name == "WellName"
        assert fields[1].type == "VARCHAR(255)"
        assert fields[1].primary_key is False

    def test_composite_primary_key(self):
        ddl_text = (
            "CREATE TABLE completions (\n"
            "CompletionID INT NOT NULL,\n"
            "WellID INT NOT NULL,\n"
            "CONSTRAINT pk PRIMARY KEY (CompletionID,WellID)\n"
            ")"
        )
        fields = parse_ddl(ddl_text)
        assert len(fields) == 2
        assert fields[0].primary_key is True
        assert fields[1].primary_key is True

    def test_no_primary_key(self):
        ddl_text = "CREATE TABLE simple (\nFieldA INT,\nFieldB VARCHAR(100)\n)"
        fields = parse_ddl(ddl_text)
        assert len(fields) == 2
        assert all(not f.primary_key for f in fields)

    def test_empty_ddl(self):
        fields = parse_ddl("CREATE TABLE empty ()")
        assert fields == []


class TestParseDocs:
    def test_basic_docs(self):
        data = [
            {
                "name": "WellID",
                "required": "true",
                "default": "",
                "requirements": "Unique identifier",
                "description": "Well identifier",
                "filter_type": "eq",
            }
        ]
        result = parse_docs(data)
        assert len(result) == 1
        assert result[0].name == "WellID"
        assert result[0].required is True
        assert result[0].filter_type == "eq"

    def test_empty_docs(self):
        result = parse_docs([])
        assert result == []

    def test_missing_fields_default(self):
        data = [{"name": "Field1"}]
        result = parse_docs(data)
        assert len(result) == 1
        assert result[0].name == "Field1"
        assert result[0].required is False
        assert result[0].default == ""
