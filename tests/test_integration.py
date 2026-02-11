"""Live API integration tests. Requires real credentials.

These tests are skipped unless the necessary environment variables are set:
- DIRECTACCESSV3_API_KEY
- DIRECTACCESS_CLIENT_ID
- DIRECTACCESS_CLIENT_SECRET
"""

from __future__ import annotations

import csv
import os
from multiprocessing import Process
from shutil import rmtree
from tempfile import mkdtemp

import pytest

from enverus_developer_api import DeveloperAPIv3, DirectAccessV2
from enverus_developer_api._exceptions import DADatasetException, DAQueryException

HAS_V3_CREDS = bool(os.environ.get("DIRECTACCESSV3_API_KEY"))
HAS_V2_CREDS = bool(
    os.environ.get("DIRECTACCESS_CLIENT_ID")
    and os.environ.get("DIRECTACCESS_CLIENT_SECRET")
)

skip_no_v3 = pytest.mark.skipif(not HAS_V3_CREDS, reason="No v3 API credentials")
skip_no_v2 = pytest.mark.skipif(not HAS_V2_CREDS, reason="No v2 API credentials")


@skip_no_v3
class TestDeveloperAPIv3Integration:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.v3 = DeveloperAPIv3(
            secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
            retries=5,
            backoff_factor=10,
        )
        yield
        self.v3.close()

    def test_query(self):
        query = self.v3.query("casings", pagesize=10, deleteddate="null")
        records = []
        for i, row in enumerate(query, start=1):
            records.append(row)
            if i >= 30:
                break
        assert len(records) > 0

    def test_query_omit_header_next_link(self):
        query = self.v3.query(
            "casings",
            pagesize=10,
            deleteddate="null",
            _headers={"X-Omit-Header-Next-Links": "true"},
        )
        records = []
        for i, row in enumerate(query, start=1):
            records.append(row)
            if i >= 30:
                break
        assert len(records) > 0

    def test_docs(self):
        docs = self.v3.docs("casings")
        assert docs is not None
        assert isinstance(docs, list)

    def test_ddl(self):
        ddl = self.v3.ddl("casings", database="pg")
        assert ddl.startswith("CREATE TABLE casings")

    def test_count(self):
        count = self.v3.count(
            "wells", updateddate="ge(2021-05-01)", StateProvince="in(TX,LA,WY)"
        )
        assert isinstance(count, int)
        assert count > 0

    def test_count_invalid_dataset(self):
        with pytest.raises(DADatasetException):
            self.v3.count("invalid")

    def test_ddl_invalid_db(self):
        with pytest.raises(DAQueryException):
            self.v3.ddl("casings", database="invalid")

    def test_csv(self):
        tempdir = mkdtemp()
        try:
            path = os.path.join(tempdir, "rigs.csv")
            dataset = "rigs"
            options = dict(pagesize=10000, deleteddate="null")

            count = self.v3.count(dataset, **options)
            query = self.v3.query(dataset, **options)
            self.v3.to_csv(
                query, path, log_progress=True, delimiter=",", quoting=csv.QUOTE_MINIMAL
            )

            with open(path) as f:
                reader = csv.reader(f)
                row_count = sum(1 for _ in reader)
            assert row_count == count + 1
        finally:
            rmtree(tempdir)

    def test_context_manager(self):
        with DeveloperAPIv3(
            secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
            access_token=self.v3.access_token,
        ) as api:
            assert isinstance(api, DeveloperAPIv3)

    def test_token_refresh(self):
        v3 = DeveloperAPIv3(
            secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
            access_token="invalid",
            retries=5,
            backoff_factor=10,
        )
        invalid_token = v3.access_token
        count = v3.count("rigs", deleteddate="null")
        query = v3.query("rigs", pagesize=10000, deleteddate="null")
        assert len(list(query)) == count
        assert invalid_token != v3.access_token
        v3.close()

    def test_dataframe(self):
        from pandas.api.types import (
            is_datetime64_ns_dtype,
            is_float_dtype,
            is_int64_dtype,
            is_object_dtype,
        )

        df = self.v3.to_dataframe("rigs", pagesize=1000, deleteddate="null")

        # Check index is set to API endpoint "primary keys"
        assert df.index.names == ["CompletionID", "WellID"]

        # Check object dtypes
        assert is_object_dtype(df.API_UWI)
        assert is_object_dtype(df.ActiveStatus)

        # Check datetime64 dtypes
        assert is_datetime64_ns_dtype(df.DeletedDate)
        assert is_datetime64_ns_dtype(df.SpudDate)
        assert is_datetime64_ns_dtype(df.UpdatedDate)

        # Check Int64 dtypes
        assert is_int64_dtype(df.RatedWaterDepth)
        assert is_int64_dtype(df.RatedHP)

        # Check float dtypes
        assert is_float_dtype(df.RigLatitudeWGS84)
        assert is_float_dtype(df.RigLongitudeWGS84)

    def test_multiple_processes(self):
        def proc_query(dataset: str) -> None:
            v3 = DeveloperAPIv3(
                secret_key=os.environ["DIRECTACCESSV3_API_KEY"],
                retries=5,
                backoff_factor=10,
            )
            resp = v3.query(dataset, deleteddate="null")
            next(resp)
            v3.close()

        procs = [
            Process(target=proc_query, kwargs={"dataset": "rigs"}),
            Process(target=proc_query, kwargs={"dataset": "casings"}),
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        for p in procs:
            assert p.exitcode == 0


@skip_no_v2
class TestDirectAccessV2Integration:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.v2 = DirectAccessV2(
            client_id=os.environ["DIRECTACCESS_CLIENT_ID"],
            client_secret=os.environ["DIRECTACCESS_CLIENT_SECRET"],
            retries=5,
            backoff_factor=10,
        )
        yield
        self.v2.close()

    def test_query(self):
        query = self.v2.query("rigs", pagesize=10, deleteddate="null")
        records = []
        for i, row in enumerate(query, start=1):
            records.append(row)
            if i >= 30:
                break
        assert len(records) > 0
