"""Public-API regressions, each measured red against 4ee38349."""

from importlib import import_module
from unittest.mock import Mock

import pandas as pd
import pytest


def engine(**kwargs):
    pytest.importorskip("duckdb")
    return import_module("siege_utilities.engines.dataframe_engine").DuckDBEngine(**kwargs)


def test_ordinary_sql_and_registered_frames_without_external_access():
    for config in [{}, {"enable_external_access": False}]:
        eng = engine(config=config)
        assert eng.query("SELECT 42 AS answer").to_dict("list") == {"answer": [42]}
        frame = pd.DataFrame({"x": [1, 2]})
        assert eng.to_pandas(frame) is frame
        pd.testing.assert_frame_equal(eng.query("SELECT * FROM input", table="input", df=frame), frame)


@pytest.mark.parametrize("sql,count", [
    ("INSERT INTO items VALUES (3), (4)", 2),
    ("UPDATE items SET x = 9 WHERE x = 1", 1),
    ("DELETE FROM items WHERE x > 0", 2),
])
def test_dml_retains_affected_row_count(sql, count):
    eng = engine()
    eng.query("CREATE TABLE items AS SELECT * FROM (VALUES (1), (2)) AS v(x)")
    assert eng.query(sql).to_dict("list") == {"Count": [count]}


def test_ddl_retains_empty_count_schema():
    assert engine().query("CREATE TABLE items(x INT)").to_dict("list") == {"Count": []}


def test_spatial_load_failure_does_not_disable_ordinary_sql():
    duckdb = pytest.importorskip("duckdb")
    eng = engine(config={"enable_external_access": False})
    with pytest.raises(duckdb.PermissionException):
        eng.query("SELECT ST_Point(1, 2) AS geometry")
    assert eng.query("SELECT 42 AS answer").to_dict("list") == {"answer": [42]}
    with pytest.raises(duckdb.CatalogException, match="missing_function"):
        eng.query("SELECT missing_function(42)")


def test_spatial_installs_only_after_missing_local_extension(monkeypatch):
    duckdb = pytest.importorskip("duckdb")
    conn = duckdb.connect()
    actions = []

    class Connection:
        def __getattr__(self, name):
            return getattr(conn, name)

        def execute(self, sql):
            actions.append(sql)
            if actions == ["LOAD spatial"]:
                raise duckdb.IOException("Extension not found locally")
            if sql == "INSTALL spatial":
                return conn  # The test uses the cached real extension; no download.
            return conn.execute(sql)

    monkeypatch.setattr(duckdb, "connect", lambda **kwargs: Connection())
    try:
        eng = engine()
        gdf = eng.to_geodataframe(eng.query("SELECT ST_Point(1, 2) AS geometry"))
        assert gdf.geometry.iloc[0].wkt == "POINT (1 2)"
        assert actions == ["LOAD spatial", "INSTALL spatial", "LOAD spatial"]
    finally:
        conn.close()


def test_batch_spatial_binding_preserves_prior_dml_once():
    eng = engine()
    result = eng.query(
        "CREATE TABLE items(x INT); INSERT INTO items VALUES (7); "
        "SELECT ST_Point(1,2) AS geometry, x AS n, 8 AS n FROM items"
    )
    out = eng.to_geodataframe(result)
    assert out["n"].tolist() == [7]
    assert out["n_1"].tolist() == [8]
    assert eng.query("SELECT count(*) AS n FROM items")["n"].iloc[0] == 1


@pytest.mark.parametrize("select,geometry_col,points,values", [
    ("ST_Point(1,2) AS geometry, 1 AS x, 2 AS x", "geometry", {"geometry": (1, 2)}, {"x": 1, "x_1": 2}),
    ("ST_Point(1,2) AS x, ST_Point(3,4) AS x", "x", {"x": (1, 2), "x_1": (3, 4)}, {}),
    ("ST_Point(1,2) AS x, 7 AS x", "x", {"x": (1, 2)}, {"x_1": 7}),
    ("7 AS x, ST_Point(1,2) AS x", "x_1", {"x_1": (1, 2)}, {"x": 7}),
])
def test_geometry_duplicate_aliases_keep_positions(select, geometry_col, points, values):
    from shapely.geometry import Point

    eng = engine()
    result = eng.query(f"SELECT {select}")
    pdf = eng.to_pandas(result)
    gdf = eng.to_geodataframe(result, geometry_col=geometry_col)
    for name, value in values.items():
        assert pdf[name].iloc[0] == value
        assert gdf[name].iloc[0] == value
    for name, xy in points.items():
        expected = eng.to_pandas(eng.query(f"SELECT ST_Point({xy[0]}, {xy[1]}) AS geometry"))
        assert bytes(pdf[name].iloc[0]) == bytes(expected["geometry"].iloc[0])
        decoded = eng.to_geodataframe(result, geometry_col=name)
        assert decoded.geometry.iloc[0].equals(Point(*xy))


def test_empty_geometry_query_preserves_duplicate_column_types():
    eng = engine()
    result = eng.query("SELECT 1 AS x, ST_Point(1,2) AS x WHERE FALSE")
    frame = eng.to_geodataframe(result, geometry_col="x_1")
    assert frame.empty
    assert list(frame.columns) == ["x", "x_1"]
    assert frame.geometry.name == "x_1"


@pytest.mark.parametrize("api", ["transform", "apply_crosswalk", "align"])
@pytest.mark.parametrize("area", [0.0, None])
def test_zero_allocation_is_not_a_corrupt_merge(monkeypatch, api, area):
    cp = import_module("siege_utilities.geo.crosswalk.crosswalk_processor")
    longitudinal = import_module("siege_utilities.geo.timeseries.longitudinal_data")
    crosswalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"], "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 0.0], "overlap_area": [1.0, area],
    })
    data = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    monkeypatch.setattr(cp, "get_crosswalk", lambda **kwargs: crosswalk.copy())
    if api == "transform":
        out = cp.CrosswalkProcessor(crosswalk, 2010, 2020, "tract").transform(
            data, value_columns=["rate"], intensive_variables=["rate"],
        )
    elif api == "apply_crosswalk":
        out = cp.apply_crosswalk(data, value_columns=["rate"], intensive_variables=["rate"])
    else:
        aligner = longitudinal.LongitudinalAligner(target_vintage=2020)
        fallback = Mock(side_effect=AssertionError("zero overlap must not fall back to areal"))
        monkeypatch.setattr(aligner, "_apply_areal_interpolation", fallback)
        aligned = aligner.align(data, source_vintage=2010, intensive_columns=["rate"])
        fallback.assert_not_called()
        assert aligned.method == "crosswalk"
        assert aligned.warnings == []
        out = aligned.data
    assert out.set_index("GEOID").loc["T1", "rate"] == pytest.approx(0.1)


def test_census_slash_normalization_preserves_proxy_prefixes(monkeypatch):
    cp = import_module("siege_utilities.geo.census.catalog_populator")
    requested = []
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    monkeypatch.setattr(cp.requests, "get", lambda url, **kwargs: requested.append(url) or response)
    for base, root in [
        ("https://api.census.gov//data//data/", "https://api.census.gov/data"),
        ("https://api.census.gov//data/", "https://api.census.gov/data"),
        ("https://api.census.gov", "https://api.census.gov/data"),
        ("https://api.census.gov/data", "https://api.census.gov/data"),
        ("https://api.census.gov/data/", "https://api.census.gov/data"),
        ("https://proxy/data/census", "https://proxy/data/census/data"),
        ("https://proxy/data/2023/census", "https://proxy/data/2023/census/data"),
        ("https://proxy/2023/gw", "https://proxy/2023/gw/data"),
    ]:
        cp.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
        assert requested[-2:] == [f"{root}/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]]


def test_empty_target_has_clear_public_error_with_duckdb(monkeypatch):
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import box

    areal = import_module("siege_utilities.geo.interpolation.areal")
    monkeypatch.setattr(areal, "_TOBLER_AVAILABLE", False)
    source = gpd.GeoDataFrame({"rate": [0.2]}, geometry=[box(0, 0, 1, 1)], crs=3857)
    target = source.iloc[:0].copy()
    with pytest.raises(ValueError, match="target GeoDataFrame is empty"):
        areal.interpolate_areal(source, target, intensive_variables=["rate"])
