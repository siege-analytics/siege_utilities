"""Round-8 public regressions; every case fails against 715f623f."""

from importlib import import_module
from unittest.mock import Mock

import pandas as pd
import pytest


def engine():
    pytest.importorskip("duckdb")
    return import_module("siege_utilities.engines.dataframe_engine").DuckDBEngine()


@pytest.mark.parametrize("mutation,remaining", [
    ("INSERT INTO items VALUES (2)", [1, 2]),
    ("UPDATE items SET i=i+1", [2]),
    ("DELETE FROM items", []),
])
@pytest.mark.parametrize("geometry", [False, True], ids=["scalar", "geometry"])
def test_prepare_returning_reports_status_without_executing(mutation, remaining, geometry):
    eng = engine()
    eng.query("CREATE TABLE items AS SELECT 1 AS i")
    projection = "i, ST_Point(i,i) AS geometry" if geometry else "i"
    status = eng.query(f"PREPARE p AS {mutation} RETURNING {projection}")
    assert isinstance(status, pd.DataFrame)
    assert status.to_dict("list") == {"Success": []}
    assert eng.query("SELECT i FROM items").i.tolist() == [1]
    result = eng.query("EXECUTE p")
    assert isinstance(result, pd.DataFrame)
    assert result.i.tolist() == ([1] if mutation.startswith("DELETE") else [2])
    if geometry:
        assert eng.to_geodataframe(result).geometry.iloc[0].wkt == f"POINT ({result.i.iloc[0]} {result.i.iloc[0]})"
    assert eng.query("SELECT i FROM items ORDER BY i").i.tolist() == remaining


@pytest.mark.parametrize("count_name,row_name", [("é", "É"), ("É", "é")])
def test_unicode_prepared_names_keep_distinct_counts_and_geometry(count_name, row_name):
    eng = engine()
    eng.query("CREATE TABLE items(i INT)")
    eng.query(f'PREPARE "{count_name}" AS INSERT INTO items VALUES (7)')
    eng.query(f'PREPARE "{row_name}" AS SELECT ST_Point(1,2) AS geometry')
    for _ in range(2):
        count = eng.query(f'EXECUTE "{count_name}"')
        assert isinstance(count, pd.DataFrame)
        assert count.to_dict("list") == {"Count": [1]}
        result = eng.query(f'EXECUTE "{row_name}"')
        assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"
    assert eng.query("SELECT i FROM items").i.tolist() == [7, 7]
    # ASCII aliases still resolve, without merging the accented names.
    eng.query('PREPARE "éP" AS SELECT ST_Point(3,4) AS geometry')
    eng.query('PREPARE "ÉP" AS INSERT INTO items VALUES (8)')
    assert eng.to_geodataframe(eng.query('EXECUTE "ép"')).geometry.iloc[0].wkt == "POINT (3 4)"
    assert eng.query('EXECUTE "Ép"').to_dict("list") == {"Count": [1]}


@pytest.mark.parametrize("execute", [
    "EXECUTE p--comment",
    "  EXECUTE /* before */ p--comment\n  ",
    "EXECUTE p--comment\n/* after */ ;",
    "EXECUTE /* outer /* nested */ comment */ p--comment",
])
def test_execute_line_comments_keep_returning_geometry(execute):
    eng = engine()
    eng.query("CREATE TABLE items(i INT)")
    eng.query("PREPARE p AS INSERT INTO items VALUES (1) RETURNING ST_Point(i,i) AS geometry")
    result = eng.query(execute)
    assert isinstance(result, pd.DataFrame)
    assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 1)"
    assert eng.query("SELECT i FROM items").i.tolist() == [1]
    # Block comments, quoted comment markers and parameters must also survive.
    for name, invocation in [
        ("p", "EXECUTE p/* trailing */"),
        ('é"--/*p', 'EXECUTE /* leading */ "é""--/*p"/* trailing */'),
        ("args", "EXECUTE args/* trailing */(2)-- end"),
    ]:
        if name != "p":
            quoted = '"' + name.replace('"', '""') + '"'
            expr = "$1" if name == "args" else "1"
            eng.query(f"PREPARE {quoted} AS SELECT ST_Point({expr},{expr}) AS geometry")
        point = "POINT (2 2)" if name == "args" else "POINT (1 1)"
        assert eng.to_geodataframe(eng.query(invocation)).geometry.iloc[0].wkt == point
    # Missing names must still raise the database's error, never a success frame.
    import duckdb
    with pytest.raises(duckdb.BinderException, match="does not exist"):
        eng.query("EXECUTE missing--comment")


@pytest.mark.parametrize("base", [
    "https://%61pi.census.gov/data/2023/cbp",
    "https://api.census.gov./data/2023/cbp",
    "HTTP://user:pw@%41PI.CENSUS.GOV.:443/data/2023/cbp?x=1#fragment",
])
def test_equivalent_census_hosts_reject_dataset_paths_before_http(monkeypatch, base):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)
    with pytest.raises(ValueError, match="full dataset path"):
        census.CensusCatalogPopulator(base_url=base)
    request.assert_not_called()
