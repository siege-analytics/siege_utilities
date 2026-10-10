"""Round-7 public regressions, measured against 3e207f39.

Unchanged round-6 tests cover controls that already passed on that baseline.
"""

import gc
from importlib import import_module
from unittest.mock import Mock
import weakref

import pandas as pd
import pytest
from shapely import from_wkb


def engine(**kwargs):
    pytest.importorskip("duckdb")
    return import_module("siege_utilities.engines.dataframe_engine").DuckDBEngine(**kwargs)


@pytest.mark.parametrize("prepared", [False, True], ids=["direct", "prepared"])
@pytest.mark.parametrize("setup,mutation,remaining", [
    ("", "INSERT INTO items VALUES (1)", [1]),
    ("INSERT INTO items VALUES (0);", "UPDATE items SET i = i + 1", [1]),
    ("INSERT INTO items VALUES (1);", "DELETE FROM items", []),
])
def test_dml_returning_geometry_materializes_once(setup, mutation, remaining, prepared):
    eng = engine()
    # The spatial bind retry must not replay setup or the final mutation.
    returning = (
        f"{mutation} "
        "RETURNING i, ST_Point(i,i) AS geometry, 1 AS x, 2 AS x, "
        "ST_Point(3,4) AS geometry, NULL::GEOMETRY AS missing"
    )
    if prepared:
        returning = f'PREPARE "é""round 7" AS {returning}; EXECUTE /* comment */ "é""round 7"'
    result = eng.query(f"CREATE TABLE items(i INT); {setup} {returning}")
    assert isinstance(result, pd.DataFrame)
    assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 1)"
    assert eng.to_geodataframe(result, geometry_col="geometry_1").geometry.iloc[0].wkt == "POINT (3 4)"
    assert result[["i", "x", "x_1"]].iloc[0].tolist() == [1, 1, 2]
    assert pd.isna(result["missing"].iloc[0])
    assert eng.to_pandas(result) is result
    assert from_wkb(bytes(result.geometry.iloc[0])).wkt == "POINT (1 1)"
    assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 1)"
    assert eng.query("SELECT i FROM items ORDER BY i").i.tolist() == remaining
    empty = eng.query("DELETE FROM items WHERE FALSE RETURNING ST_Point(i,i) AS geometry")
    assert empty.empty and empty.columns.tolist() == ["geometry"]
    assert eng.to_geodataframe(empty).geometry.name == "geometry"
    # Prepared DML without RETURNING still reports Count and executes once.
    eng.query("PREPARE counter AS UPDATE items SET i=i+1")
    assert eng.query("EXECUTE counter").to_dict("list") == {"Count": [len(remaining)]}
    assert eng.query("SELECT i FROM items").i.tolist() == [i + 1 for i in remaining]


def test_index_points_keeps_query_geometry_decodable():
    eng = engine()
    indexed = eng.index_points(
        eng.query("SELECT 41 AS lat, -87 AS lon, ST_Point(-87,41) AS geometry"),
        "lat", "lon", grid="s2", level=12,
    )
    restored = eng.to_geodataframe(indexed)
    assert restored.geometry.iloc[0].wkt == "POINT (-87 41)"
    assert restored.s2_index.iloc[0]
    assert from_wkb(bytes(eng.to_pandas(indexed).geometry.iloc[0])).wkt == "POINT (-87 41)"


def test_query_result_survives_engine_collection():
    refs = []

    def get_result():
        eng = engine()
        refs.append(weakref.ref(eng))
        return eng.query("SELECT ST_Point(1,2) AS geometry")

    result = get_result()
    gc.collect()
    assert refs[0]() is None
    assert engine().to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"
    assert isinstance(result, pd.DataFrame)


def test_query_result_is_snapshot_after_source_delete():
    eng = engine()
    eng.query("CREATE TABLE items AS SELECT 7 AS i, ST_Point(1,2) AS geometry")
    saved = eng.query("SELECT * FROM items")
    assert eng.query("DELETE FROM items").to_dict("list") == {"Count": [1]}
    restored = eng.to_geodataframe(saved)
    assert restored.i.tolist() == [7]
    assert restored.geometry.iloc[0].wkt == "POINT (1 2)"
    assert eng.query("SELECT count(*) AS n FROM items").n.iloc[0] == 0


@pytest.mark.parametrize("select,columns", [
    ("ST_Point(1,2) AS geometry, ST_Point(3,4) AS geometry", ["geometry", "geometry_1"]),
    ("ST_Point(1,2) AS geometry, NULL::GEOMETRY AS missing", ["geometry", "missing"]),
    ("NULL::GEOMETRY AS geometry", ["geometry"]),
    ("1 AS x, ST_Point(1,2) AS x WHERE FALSE", ["x", "x_1"]),
])
def test_query_materializes_wkb_with_null_and_empty_schema(select, columns):
    eng = engine()
    result = eng.query(f"SELECT {select}")
    assert isinstance(result, pd.DataFrame)
    assert result.columns.tolist() == columns
    assert eng.to_pandas(result) is result
    if result.empty:
        out = eng.to_geodataframe(result, geometry_col="x_1")
        assert out.empty and out.geometry.name == "x_1"
    else:
        for name in columns:
            decoded = eng.to_geodataframe(result, geometry_col=name)
            if pd.isna(result[name].iloc[0]):
                assert decoded.geometry.iloc[0] is None
            else:
                assert from_wkb(bytes(result[name].iloc[0])).equals(decoded.geometry.iloc[0])


@pytest.mark.parametrize("base", [
    "https://proxy/data/2023/gw",
    "https://proxy/data/2023/cbp",
    "https://proxy/data/2023/acs/acs5",
    "https://proxy/data/2023",
    "https://api.census.gov.proxy/data/2023/gw",
])
def test_census_dataset_rejection_is_host_specific(monkeypatch, base):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    requested = []
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    monkeypatch.setattr(census.requests, "get", lambda url, **kwargs: requested.append(url) or response)
    census.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
    assert requested == [f"{base}/data/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]]
