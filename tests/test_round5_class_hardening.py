"""Round-5 class-level hardening regression tests.

Every test here exercises the PUBLIC API a user would call (``eng.query``,
``eng.to_pandas``, ``eng.to_geodataframe``, ``eng.read_spatial``,
``CrosswalkProcessor.transform``, ``interpolate_areal``,
``CensusCatalogPopulator``), never a private helper. Historical regression checks remain here; round-6
replacements and their measured baseline failures are documented in
docs/testing/round6-verification.txt.
"""

import numpy as np
import pytest


# --- Finding 1: read_spatial selects geometry by TYPE, not by guessed name ---

def test_read_spatial_property_name_clash_keeps_real_geometry(tmp_path):
    # A feature property named "geom" collides with ST_Read's default geometry
    # column name, so DuckDB emits `geom INTEGER` (the property) + `geom_1
    # GEOMETRY` (the real point). Selecting by the name "geom" (pre-fix) grabs
    # the integer and yields active geometry [None]; selecting by introspected
    # GEOMETRY type keeps the real point AND the ordinary property column.
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    gj = tmp_path / "clash.geojson"
    gj.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"properties":{"geom":123},"geometry":{"type":"Point","coordinates":[1,2]}}]}'
    )
    eng = DuckDBEngine()
    gdf = eng.read_spatial(str(gj), crs="EPSG:4326")
    assert gdf.geometry.iloc[0] is not None, "active geometry was discarded"
    assert gdf.geometry.iloc[0].equals(Point(1, 2)), gdf.geometry.iloc[0]
    assert int(gdf["geom"].iloc[0]) == 123, "integer property column lost"


# --- Finding 2: a target with zero valid contributors stays NaN, not 0.0 ---

def test_interpolate_areal_disjoint_source_does_not_zero_nan_target():
    # Source A overlaps target T but carries NaN for `rate`; source B carries a
    # real rate (0.8) but is geographically disjoint from T. T therefore has
    # ZERO valid contributors and its rate is UNDEFINED. Pre-fix the disjoint
    # source leaks a fabricated 0.0 into T.
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    from siege_utilities.geo.interpolation.areal import interpolate_areal

    src = gpd.GeoDataFrame(
        {"rate": [np.nan, 0.8]},
        geometry=[box(0, 0, 1, 1), box(10, 10, 11, 11)],
        crs="EPSG:3857",
    )
    tgt = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:3857")
    res = interpolate_areal(src, tgt, intensive_variables=["rate"])
    assert np.isnan(res.data["rate"].iloc[0]), res.data["rate"].iloc[0]


def test_interpolate_areal_valid_target_keeps_value_when_nan_sibling_present():
    # The flip side of finding 2: a target that DOES overlap a valid source
    # must keep that value even though a NaN-bearing source also exists.
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    from siege_utilities.geo.interpolation.areal import interpolate_areal

    src = gpd.GeoDataFrame(
        {"rate": [np.nan, 0.8]},
        geometry=[box(0, 0, 1, 1), box(10, 10, 11, 11)],
        crs="EPSG:3857",
    )
    tgt = gpd.GeoDataFrame(
        {"id": [1, 2]},
        geometry=[box(0, 0, 1, 1), box(10, 10, 11, 11)],
        crs="EPSG:3857",
    )
    res = interpolate_areal(src, tgt, intensive_variables=["rate"])
    assert np.isnan(res.data["rate"].iloc[0]), res.data["rate"].iloc[0]
    assert abs(res.data["rate"].iloc[1] - 0.8) < 1e-9, res.data["rate"].iloc[1]


# --- Finding 3: DuckDB native GEOMETRY round-trips through the PUBLIC API ---

def test_duckdb_public_query_to_geodataframe_native_geometry():
    # The public query boundary materializes WKB before returning to callers.
    import pandas as pd
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    eng = DuckDBEngine()
    result = eng.query("SELECT 7 AS id, ST_Point(1, 2) AS geometry")
    assert isinstance(result, pd.DataFrame)
    gdf = eng.to_geodataframe(result)
    assert list(gdf["id"]) == [7]
    assert gdf.geometry.iloc[0].equals(Point(1, 2)), gdf.geometry.iloc[0].wkt


def test_duckdb_public_to_pandas_materializes_decodable_wkb():
    # Both external typed relations and query frames expose standard WKB.
    duckdb = pytest.importorskip("duckdb")
    from importlib import import_module
    from shapely import from_wkb
    engine = import_module("siege_utilities.engines.dataframe_engine").DuckDBEngine()
    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        relation = conn.sql("SELECT ST_Point(1, 2) AS geometry")
        actual = engine.to_pandas(relation)
        assert from_wkb(bytes(actual["geometry"].iloc[0])).wkt == "POINT (1 2)"
        result = engine.query("SELECT ST_Point(1, 2) AS geometry")
        assert engine.to_pandas(result) is result
        assert from_wkb(bytes(result["geometry"].iloc[0])).wkt == "POINT (1 2)"
        assert engine.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"


# --- Finding 4: invalid area is recovered (merge) or value-preserved (single) ---

def _two_source_xwalk(overlap, source_area):
    import pandas as pd
    return pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": source_area,
        "overlap_area": overlap,
    })


def _run_two_source(overlap, source_area, rates=(0.1, 0.9)):
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    proc = CrosswalkProcessor(_two_source_xwalk(overlap, source_area), 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": list(rates)})
    return proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")


def test_crosswalk_negative_overlap_reconstructs_from_source_area():
    # overlap [1, -1] (invalid) must reconstruct from source_area*area_weight
    # ([1,9]*[1,1]=[1,9]) -> .82. Pre-fix: -1 is treated as present -> rejected.
    out = _run_two_source([1.0, -1.0], [1.0, 9.0])
    assert abs(out.loc["T1", "rate"] - 0.82) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_inf_overlap_reconstructs_from_source_area():
    # overlap [1, +inf] (invalid) must reconstruct -> .82. Pre-fix: inf passes
    # the isna/<0 check, giving inf/inf -> silent NaN.
    out = _run_two_source([1.0, float("inf")], [1.0, 9.0])
    assert abs(out.loc["T1", "rate"] - 0.82) < 1e-9, out.loc["T1", "rate"]


def _run_single_source(overlap, source_area=5.0, rate=0.42):
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    xwalk = pd.DataFrame({
        "source_geoid": ["S1"], "target_geoid": ["T1"], "area_weight": [1.0],
        "source_area": [source_area], "overlap_area": [overlap],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1"], "rate": [rate]})
    return proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")


def test_crosswalk_single_source_zero_overlap_preserves_value():
    # A lone source feeding a target preserves its intensive value regardless
    # of area. overlap 0 -> unit weight -> .42. Pre-fix: 0/0 -> NaN.
    out = _run_single_source(0.0)
    assert abs(out.loc["T1", "rate"] - 0.42) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_single_source_inf_overlap_preserves_value():
    # overlap +inf for a lone source -> value preserved (.42). Pre-fix: NaN.
    out = _run_single_source(float("inf"))
    assert abs(out.loc["T1", "rate"] - 0.42) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_rejects_invalid_contributors_but_ignores_zero_allocations():
    import pandas as pd
    from importlib import import_module
    processor = import_module("siege_utilities.geo.crosswalk.crosswalk_processor").CrosswalkProcessor
    data = pd.DataFrame({"GEOID": ["S1", "S2", "S3"], "rate": [0.1, 0.9, 0.7]})
    for bad in [-1.0, np.inf, np.nan]:
        crosswalk = pd.DataFrame({
            "source_geoid": ["S1", "S2", "S3"], "target_geoid": ["T1"] * 3,
            "area_weight": [1.0, 1.0, 0.0], "overlap_area": [1.0, 9.0, bad],
        })
        def run():
            return processor(crosswalk, 2010, 2020, "tract").transform(
                data, value_columns=["rate"], intensive_variables=["rate"],
            ).set_index("GEOID")
        assert run().loc["T1", "rate"] == pytest.approx(0.82)
        crosswalk.loc[2, "area_weight"] = 1.0
        with pytest.raises(ValueError, match="area-weight intensive"):
            run()


# --- Finding 5: reserved-prefix INPUT columns are rejected, never dropped ---

def test_crosswalk_reserved_prefix_input_column_rejected():
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    xwalk = pd.DataFrame({"source_geoid": ["S1"], "target_geoid": ["T1"], "area_weight": [1.0]})
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1"], "rate": [0.2], "__xwalk__total_weight": [9]})
    with pytest.raises(ValueError, match="reserved"):
        proc.transform(df, geoid_column="GEOID", value_columns=["rate"])


def test_crosswalk_reserved_prefix_source_geoid_input_rejected():
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    xwalk = pd.DataFrame({"source_geoid": ["S1"], "target_geoid": ["T1"], "area_weight": [1.0]})
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1"], "rate": [0.2], "__xwalk__source_geoid": ["X"]})
    with pytest.raises(ValueError, match="reserved"):
        proc.transform(df, geoid_column="GEOID", value_columns=["rate"])


# --- Finding 6: legitimate proxy prefixes containing data/year are accepted ---

def test_census_proxy_data_prefix_accepted():
    from siege_utilities.geo.census import catalog_populator as cp
    assert (
        cp.CensusCatalogPopulator(base_url="https://proxy/data/census").base_url
        == "https://proxy/data/census/data"
    )


def test_census_proxy_data_year_prefix_accepted():
    from siege_utilities.geo.census import catalog_populator as cp
    assert (
        cp.CensusCatalogPopulator(base_url="https://proxy/data/2023/census").base_url
        == "https://proxy/data/2023/census/data"
    )


def test_census_dataset_endpoint_rejected_regardless_of_arity():
    from importlib import import_module
    cp = import_module("siege_utilities.geo.census.catalog_populator")
    for path in ["data/2023/cbp", "data/2023/acs/acs5", "data/2023/custom/a/b", "data/2023"]:
        with pytest.raises(ValueError, match="full dataset path"):
            cp.CensusCatalogPopulator(base_url=f"https://api.census.gov/{path}")


# --- Finding 7: identifiers with embedded double quotes are escaped ---

def test_duckdb_embedded_quote_identifier_through_public_api():
    # An attribute column named `a"b` alongside a geometry must not break the
    # ST_AsWKB projection. Pre-fix the identifier is emitted un-escaped
    # (`"a"b"`) -> ParserException (and query() also fails to load spatial).
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    eng = DuckDBEngine()
    gdf = eng.to_geodataframe(
        eng.query('SELECT ST_Point(1, 2) AS geometry, 5 AS "a""b"')
    )
    assert 'a"b' in gdf.columns, list(gdf.columns)
    assert int(gdf['a"b'].iloc[0]) == 5
    assert gdf.geometry.iloc[0].equals(Point(1, 2))
