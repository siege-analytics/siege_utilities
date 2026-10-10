"""Red-on-revert tests for the final-hardening fixes (#1369).

Each test exercises a defect the fresh dual hostile review found on develop and
that the prior mock-heavy tests missed. Grouped by the module fixed.
"""
import types

import pytest


# --- A: Slides figure-upload failure must propagate (not silent text-only slide) ---

def test_slides_report_raises_when_a_figure_upload_fails(monkeypatch):
    from siege_utilities.analytics import google_slides as gs

    monkeypatch.setattr(gs, "create_presentation", lambda client, title, folder_id=None: "pres-1")
    monkeypatch.setattr(gs, "add_blank_slide", lambda *a, **k: "slide-1")
    monkeypatch.setattr(gs, "create_textbox", lambda *a, **k: None)
    monkeypatch.setattr(gs, "insert_image", lambda *a, **k: None)

    def _boom(client, fig, name):
        raise RuntimeError("drive 500")

    # Keep create_argument_slide REAL so the figure-upload catch is exercised.
    monkeypatch.setattr(gs, "upload_figure_to_drive", _boom)

    argument = types.SimpleNamespace(
        layout="full_width", headline="Turnout map", narrative="N",
        base_note=None, source_note=None, map_figure=object(), chart=None, table=None,
    )
    client = type("C", (), {"presentation_url": staticmethod(lambda p: f"http://x/{p}")})()
    with pytest.raises(RuntimeError, match="slides failed"):
        gs.create_report_from_arguments(client, "report", [argument])


# --- B: areal interpolation routes intensive vs extensive variables ---

def test_areal_interpolation_preserves_intensive_and_splits_extensive(monkeypatch):
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("tobler")
    from shapely.geometry import box
    import pandas as pd
    import siege_utilities.geo.timeseries.longitudinal_data as mod

    src = gpd.GeoDataFrame({"GEOID": ["S1"]}, geometry=[box(0, 0, 2, 1)], crs="EPSG:3857")
    tgt = gpd.GeoDataFrame(
        {"GEOID": ["T1", "T2"]}, geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs="EPSG:3857"
    )
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.get_census_boundaries",
        lambda year, geographic_level, state_fips, **k: src.copy() if year == 2010 else tgt.copy(),
    )
    aligner = mod.LongitudinalAligner(target_vintage=2020, geography="tract")
    df = pd.DataFrame({"GEOID": ["S1"], "population": [100], "poverty_rate": [0.2]})
    out = aligner._apply_areal_interpolation(
        df, source_year=2010, target_year=2020, geography_level="tract",
        state_fips="06", geoid_column="GEOID", intensive_columns=["poverty_rate"],
    )
    assert list(out["GEOID"]) == ["T1", "T2"]
    assert abs(out["population"].sum() - 100) < 1e-6          # extensive: conserved
    assert all(abs(r - 0.2) < 1e-9 for r in out["poverty_rate"])  # intensive: unchanged


def test_crosswalk_routes_intensive_vs_extensive():
    # The PRIMARY (crosswalk) path, not just the areal fallback, must area-weight
    # intensive columns. A 50/50 split must halve population (extensive) and keep
    # poverty_rate (intensive) at 0.2.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S1"],
        "target_geoid": ["T1", "T2"],
        "area_weight": [0.5, 0.5],
    })
    proc = CrosswalkProcessor(
        crosswalk_df=xwalk, source_year=2010, target_year=2020, geography_level="tract"
    )
    df = pd.DataFrame({"GEOID": ["S1"], "population": [100], "poverty_rate": [0.2]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["population", "poverty_rate"],
        intensive_variables=["poverty_rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "population"] - 50) < 1e-6
    assert abs(out.loc["T2", "population"] - 50) < 1e-6
    assert abs(out.loc["T1", "poverty_rate"] - 0.2) < 1e-9
    assert abs(out.loc["T2", "poverty_rate"] - 0.2) < 1e-9


def test_crosswalk_intensive_merge_is_area_weighted():
    # Finding #1: a MERGE of two sources (areas 1 and 9) with rates .1 and .9
    # must yield the area-weighted mean .82, NOT the unweighted mean .50.
    # area_weight (allocation factor) is 1 for both fully-contained sources and
    # cannot express this; the crosswalk must carry overlap_area/source_area.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],       # allocation factor: useless for the mean
        "source_area": [1.0, 9.0],
        "overlap_area": [1.0, 9.0],      # fully contained -> overlap == source area
    })
    proc = CrosswalkProcessor(
        crosswalk_df=xwalk, source_year=2010, target_year=2020, geography_level="tract"
    )
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"],
        intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.82) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_intensive_merge_matches_real_tobler():
    # The crosswalk merge answer must equal the real tobler areal-interpolation
    # answer for the same geometry (areas 1 and 9 fully merging into one target).
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("tobler")
    import pandas as pd
    from shapely.geometry import box
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    from siege_utilities.geo.interpolation.areal import interpolate_areal

    # Source S1 area 1, S2 area 9, FULLY tiling the target (no gap) so the
    # merge is a clean area-weighted mean. (tobler normalizes intensive values
    # by target area, so parity with Sum(v*overlap)/Sum(overlap) requires the
    # sources to fully cover the target -- which is exactly "fully merging".)
    src = gpd.GeoDataFrame(
        {"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]},
        geometry=[box(0, 0, 1, 1), box(0, 1, 1, 10)],
        crs="EPSG:3857",
    )
    tgt = gpd.GeoDataFrame({"GEOID": ["T1"]}, geometry=[box(0, 0, 1, 10)], crs="EPSG:3857")
    areal = interpolate_areal(
        source_gdf=src, target_gdf=tgt, intensive_variables=["rate"],
    )
    areal_rate = float(areal.data["rate"].iloc[0])

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": [1.0, 9.0],
        "overlap_area": [1.0, 9.0],
    })
    proc = CrosswalkProcessor(
        crosswalk_df=xwalk, source_year=2010, target_year=2020, geography_level="tract"
    )
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    # tobler computes geometric areas in floating point, so match to 1e-6.
    assert abs(out.loc["T1", "rate"] - areal_rate) < 1e-6, (out.loc["T1", "rate"], areal_rate)
    assert abs(areal_rate - 0.82) < 1e-6, areal_rate


def test_crosswalk_intensive_merge_without_area_refuses():
    # Finding #1: when the crosswalk carries only the allocation factor, an
    # intensive MERGE cannot be area-weighted correctly -> raise rather than
    # silently return the wrong (unweighted) number.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
    })
    proc = CrosswalkProcessor(
        crosswalk_df=xwalk, source_year=2010, target_year=2020, geography_level="tract"
    )
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    with pytest.raises(ValueError, match="area-weight intensive"):
        proc.transform(
            df, geoid_column="GEOID", value_columns=["rate"],
            intensive_variables=["rate"],
        )


def test_crosswalk_intensive_merge_ignores_nan_values():
    # Finding #4: a NaN value must not dilute the rate. Merging [.2, NaN] with
    # equal areas must yield .2, not .1.
    import numpy as np
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": [1.0, 1.0],
        "overlap_area": [1.0, 1.0],
    })
    proc = CrosswalkProcessor(
        crosswalk_df=xwalk, source_year=2010, target_year=2020, geography_level="tract"
    )
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.2, np.nan]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.2) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_intensive_mean_func_does_not_double_divide():
    # Finding #4: intensive columns must be handled on their own path regardless
    # of aggregation_func, so aggregation_func="mean" cannot double-divide a rate.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1"],
        "target_geoid": ["T1"],
        "area_weight": [1.0],
        "source_area": [1.0],
        "overlap_area": [1.0],
    })
    proc = CrosswalkProcessor(
        crosswalk_df=xwalk, source_year=2010, target_year=2020, geography_level="tract"
    )
    df = pd.DataFrame({"GEOID": ["S1"], "rate": [0.4]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"],
        intensive_variables=["rate"], aggregation_func="mean",
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.4) < 1e-9, out.loc["T1", "rate"]


# --- C: Spark from/to_geodataframe assign the requested CRS (no reproject) ---
#
# Spark/Sedona carries no CRS metadata, so the engine must serialize coordinates
# as-is and ASSIGN (never reproject) on read-back. The caller passes the crs the
# coordinates are actually in. The round-2 normalize-on-write / reproject-on-read
# behavior corrupted projected inputs to POINT(inf inf); these tests lock the
# reverted (develop) semantics in.

def test_spark_from_geodataframe_serializes_coords_as_is(monkeypatch):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point
    from shapely import wkt
    from siege_utilities.engines.dataframe_engine import SparkEngine

    eng = SparkEngine.__new__(SparkEngine)
    captured = {}
    eng._spark = types.SimpleNamespace(createDataFrame=lambda pdf: captured.setdefault("pdf", pdf))

    # A projected point in EPSG:3857 (metres) must be serialized unchanged --
    # NOT reprojected to lon/lat. Reprojecting here is the regression.
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(111319.490793, 0)], crs="EPSG:3857")
    eng.from_geodataframe(gdf)
    geom = wkt.loads(captured["pdf"]["geometry"].iloc[0])
    assert abs(geom.x - 111319.490793) < 1e-3 and abs(geom.y) < 1e-6, (
        f"coordinates must be serialized as-is, got {geom.wkt}"
    )


def test_spark_to_geodataframe_assigns_requested_crs_without_reproject():
    gpd = pytest.importorskip("geopandas")
    import pandas as pd
    from siege_utilities.engines.dataframe_engine import SparkEngine

    # Stored WKT already in EPSG:4326 (degrees). to_geodataframe(crs="EPSG:4326")
    # must preserve the degree coordinates, not reproject them.
    class _DF:
        def toPandas(self):
            return pd.DataFrame({"id": [1], "geometry": ["POINT (1 0)"]})

    eng = SparkEngine.__new__(SparkEngine)
    out = eng.to_geodataframe(_DF(), crs="EPSG:4326")
    assert str(out.crs).upper().endswith("4326")
    assert abs(out.geometry.iloc[0].x - 1.0) < 1e-9, out.geometry.iloc[0].wkt
    assert abs(out.geometry.iloc[0].y) < 1e-9, out.geometry.iloc[0].wkt


def test_spark_projected_wkt_roundtrip_is_preserved_not_corrupted():
    gpd = pytest.importorskip("geopandas")
    import math
    import pandas as pd
    from siege_utilities.engines.dataframe_engine import SparkEngine

    # read_spatial(crs="EPSG:3857") stores PROJECTED WKT (metres). Reading it
    # back with to_geodataframe(crs="EPSG:3857") must yield finite, correct-
    # magnitude coordinates -- the round-2 reproject-on-read produced
    # POINT(inf inf) here (treating metres as degrees).
    class _DF:
        def toPandas(self):
            return pd.DataFrame({"id": [1], "geometry": ["POINT (111319.490793 0)"]})

    eng = SparkEngine.__new__(SparkEngine)
    out = eng.to_geodataframe(_DF(), crs="EPSG:3857")
    pt = out.geometry.iloc[0]
    assert math.isfinite(pt.x) and math.isfinite(pt.y), f"corrupted coords: {pt.wkt}"
    assert abs(pt.x - 111319.490793) < 1e-3 and abs(pt.y) < 1e-6, pt.wkt
    assert str(out.crs).upper().endswith("3857")


# --- D: docstring generator dry-run does not write and honors --path ---

def test_generate_docstrings_dry_run_does_not_write(tmp_path, monkeypatch):
    import importlib
    gd = importlib.import_module("siege_utilities.hygiene.generate_docstrings")

    monkeypatch.chdir(tmp_path)
    target = tmp_path / "needs.py"
    original = "def undocumented(x):\n    return x + 1\n"
    target.write_text(original)
    gd.process_python_file(target, dry_run=True)
    assert target.read_text() == original, "dry-run must not modify the file"
    gd.process_python_file(target, dry_run=False)
    assert target.read_text() != original, "non-dry-run must add the docstring"
    assert '"""' in target.read_text()


def test_generate_docstrings_main_honors_base_path(tmp_path, monkeypatch):
    import importlib
    gd = importlib.import_module("siege_utilities.hygiene.generate_docstrings")

    work = tmp_path / "work"; work.mkdir()
    other = tmp_path / "pkg"; other.mkdir()
    (other / "mod.py").write_text("def f(y):\n    return y\n")
    monkeypatch.chdir(work)              # cwd is empty; path points elsewhere
    gd.main(base_path=str(other), dry_run=False)
    assert '"""' in (other / "mod.py").read_text(), "main must process --path, not cwd"


# --- E: DuckDB geometry round-trips its own conversion output ---

def test_duckdb_geometry_roundtrip(tmp_path):
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    eng = DuckDBEngine()
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326")
    back = eng.to_geodataframe(eng.from_geodataframe(gdf))
    assert back.geometry.iloc[0].equals(Point(0, 0))
    assert back.geometry.iloc[1].equals(Point(1, 1))
    # geometry-only (no attribute columns) must not emit "SELECT ,"
    gonly = gpd.GeoDataFrame(geometry=[Point(2, 2)], crs="EPSG:4326")
    back2 = eng.to_geodataframe(eng.from_geodataframe(gonly))
    assert back2.geometry.iloc[0].equals(Point(2, 2))
    # A null geometry round-trips as missing (DuckDB returns pd.NA, not None).
    mixed = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[Point(3, 3), None], crs="EPSG:4326")
    back3 = eng.to_geodataframe(eng.from_geodataframe(mixed))
    assert back3.geometry.iloc[0].equals(Point(3, 3))
    assert back3.geometry.isna().iloc[1]


# --- F: Snowflake write_pandas uses unquoted identifiers to match CREATE ---

def test_snowflake_create_table_quotes_identifiers(monkeypatch):
    # CREATE must quote identifiers to match write_pandas (quoted by default),
    # so the created columns line up with what write_pandas targets. Forcing
    # write_pandas unquoted instead would regress existing case-sensitive tables.
    import siege_utilities.analytics.snowflake_connector as sc
    import pandas as pd

    executed = []
    wp = {}

    def _fake_write_pandas(conn, df, table, **kwargs):
        wp["kwargs"] = kwargs
        return True, 1, len(df), None

    monkeypatch.setattr(sc, "write_pandas", _fake_write_pandas)
    conn = sc.SnowflakeConnector(account="a", user="u")
    conn.connection = object()
    conn.cursor = type("Cur", (), {"execute": lambda self, sql, *a, **k: executed.append(sql)})()
    conn.upload_dataframe(pd.DataFrame({"amount": [1]}), "events", auto_create_table=True)

    create = [s for s in executed if "CREATE TABLE" in s]
    assert create, f"no CREATE TABLE executed: {executed}"
    assert '"amount"' in create[0] and '"events"' in create[0], create[0]
    # write_pandas must not be forced to unquoted identifiers (regression guard).
    assert wp["kwargs"].get("quote_identifiers") is not False


def test_snowflake_get_table_info_quotes_identifier(monkeypatch):
    # Finding #5: get_table_info must quote the table identifier so a
    # quoted-created (case-sensitive) table is addressable. DESCRIBE/SELECT
    # must use "table", not bare table (which Snowflake uppercases).
    import siege_utilities.analytics.snowflake_connector as sc

    executed = []

    class _Cur:
        def execute(self, sql, *a, **k):
            executed.append(sql)
        def fetchall(self):
            return [("amount", "NUMBER", "Y")]
        def fetchone(self):
            # COUNT(*) -> (row_count,); INFORMATION_SCHEMA size -> (bytes, rows).
            return (0, 0)

    conn = sc.SnowflakeConnector(account="a", user="u")
    conn.connection = object()
    conn.cursor = _Cur()
    conn.get_table_info("events")

    describe = [s for s in executed if s.startswith("DESCRIBE TABLE")]
    count = [s for s in executed if s.startswith("SELECT COUNT(*)")]
    assert describe and '"events"' in describe[0], executed
    assert count and '"events"' in count[0], executed


# --- G: census catalog populator does not double the /data path segment ---

def test_census_catalog_url_has_no_double_data(monkeypatch):
    from siege_utilities.geo.census import catalog_populator as cp

    captured = {}

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"variables": {}}

    def _fake_get(url, timeout=None):
        captured["url"] = url
        return _Resp()

    monkeypatch.setattr(cp.requests, "get", _fake_get)
    pop = cp.CensusCatalogPopulator()  # default base_url ends in /data
    pop._fetch_variables("acs/acs5", 2023)
    assert "/data/data/" not in captured["url"], captured["url"]
    assert captured["url"].endswith("/data/2023/acs/acs5/variables.json")


def test_census_catalog_url_adds_data_when_base_lacks_it(monkeypatch):
    # Finding #6: a base_url WITHOUT the /data suffix must still produce a URL
    # containing /data exactly once (both _fetch_variables and _fetch_groups).
    from siege_utilities.geo.census import catalog_populator as cp

    captured = {}

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"variables": {}, "groups": []}

    def _fake_get(url, timeout=None):
        captured.setdefault("urls", []).append(url)
        return _Resp()

    monkeypatch.setattr(cp.requests, "get", _fake_get)
    pop = cp.CensusCatalogPopulator(base_url="https://api.census.gov")  # no /data
    pop._fetch_variables("acs/acs5", 2023)
    pop._fetch_groups("acs/acs5", 2023)
    for url in captured["urls"]:
        assert url.count("/data/") == 1, url
    assert captured["urls"][0].endswith("/data/2023/acs/acs5/variables.json")
    assert captured["urls"][1].endswith("/data/2023/acs/acs5/groups.json")


# --- H: buffer honors a custom geometry_col on the pandas-family engines ---

@pytest.mark.parametrize("engine_name", ["pandas", "duckdb"])
def test_buffer_custom_geometry_col(engine_name):
    pytest.importorskip("geopandas")
    import pandas as pd
    from siege_utilities.engines.dataframe_engine import PandasEngine, DuckDBEngine
    if engine_name == "duckdb":
        pytest.importorskip("duckdb")
    eng = PandasEngine() if engine_name == "pandas" else DuckDBEngine()
    out = eng.buffer(pd.DataFrame({"geom": ["POINT (0 0)"]}), 1.0, geometry_col="geom")
    assert out["geom"].iloc[0].area > 0, "buffer did not produce a polygon on the custom column"


# ===========================================================================
# Round-4 class-level findings (#1369). Each test is red-on-revert against the
# pre-fix code: it fails on the un-fixed implementation and passes on the fix.
# ===========================================================================


# --- Finding #1 (P1): intensive area-weight uses ACTUAL overlap area ---

def test_crosswalk_intensive_partial_overlap_is_area_weighted():
    # source_area [1, 9] with area_weight (overlap/source) [1, 1/9] means the
    # actual overlaps are [1, 1], so the area-weighted mean of rates [.1, .9]
    # is (.1*1 + .9*1)/2 = .50 -- NOT .82. The pre-fix code fell back to
    # source_area ALONE ([1, 9] -> .82), ignoring the allocation fraction.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0 / 9.0],   # overlap/source fraction
        "source_area": [1.0, 9.0],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.50) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_partial_overlap_matches_real_tobler():
    # The crosswalk answer for a partial overlap must equal the REAL tobler
    # areal-interpolation answer for the same geometry. S1 (area 1) is fully
    # inside the target; S2 (area 9) overlaps the target by exactly 1 (so its
    # allocation fraction is 1/9). Both must yield .50.
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("tobler")
    import pandas as pd
    from shapely.geometry import box
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    from siege_utilities.geo.interpolation.areal import interpolate_areal

    tgt = gpd.GeoDataFrame({"GEOID": ["T1"]}, geometry=[box(0, 0, 1, 2)], crs="EPSG:3857")
    src = gpd.GeoDataFrame(
        {"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]},
        geometry=[box(0, 0, 1, 1), box(0, 1, 1, 10)],  # S1 area1 in T; S2 area9 overlaps by 1
        crs="EPSG:3857",
    )
    areal = interpolate_areal(source_gdf=src, target_gdf=tgt, intensive_variables=["rate"])
    areal_rate = float(areal.data["rate"].iloc[0])
    assert abs(areal_rate - 0.50) < 1e-6, areal_rate

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0 / 9.0],
        "source_area": [1.0, 9.0],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - areal_rate) < 1e-6, (out.loc["T1", "rate"], areal_rate)


# --- Finding #2 (P1): align() areal fallback excludes NaN sources ---

def test_align_areal_fallback_excludes_nan_source(monkeypatch):
    # When the crosswalk refuses (no area columns) and the REAL tobler areal
    # path runs, a NaN source value must not dilute the rate. [.2, NaN] over
    # two equal-area sources fully tiling one target must yield .2, not .1.
    # tobler 0.13 substitutes 0 for the NaN while keeping its area in the
    # denominator; the fix recomputes the variable on its valid-source subset.
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("tobler")
    import numpy as np
    import pandas as pd
    from shapely.geometry import box
    import siege_utilities.geo.timeseries.longitudinal_data as mod

    src = gpd.GeoDataFrame(
        {"GEOID": ["S1", "S2"]},
        geometry=[box(0, 0, 1, 1), box(0, 1, 1, 2)], crs="EPSG:3857",
    )
    tgt = gpd.GeoDataFrame({"GEOID": ["T1"]}, geometry=[box(0, 0, 1, 2)], crs="EPSG:3857")
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.get_census_boundaries",
        lambda year, geographic_level, state_fips, **k: src.copy() if year == 2010 else tgt.copy(),
    )
    aligner = mod.LongitudinalAligner(target_vintage=2020, geography="tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.2, np.nan]})
    out = aligner._apply_areal_interpolation(
        df, source_year=2010, target_year=2020, geography_level="tract",
        state_fips="06", geoid_column="GEOID", intensive_columns=["rate"],
    )
    assert abs(float(out["rate"].iloc[0]) - 0.2) < 1e-9, out["rate"].iloc[0]


def test_interpolate_areal_nan_intensive_excluded_from_denominator():
    # Direct interpolate_areal check on the same defect (independent of align).
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("tobler")
    import numpy as np
    from shapely.geometry import box
    from siege_utilities.geo.interpolation.areal import interpolate_areal

    src = gpd.GeoDataFrame(
        {"GEOID": ["S1", "S2"], "rate": [0.2, np.nan]},
        geometry=[box(0, 0, 1, 1), box(0, 1, 1, 2)], crs="EPSG:3857",
    )
    tgt = gpd.GeoDataFrame({"GEOID": ["T1"]}, geometry=[box(0, 0, 1, 2)], crs="EPSG:3857")
    res = interpolate_areal(source_gdf=src, target_gdf=tgt, intensive_variables=["rate"])
    assert abs(float(res.data["rate"].iloc[0]) - 0.2) < 1e-9, res.data["rate"].iloc[0]


# --- Finding #3: metadata/helper collisions + extensive passthrough ---

def test_crosswalk_input_area_column_collision_no_keyerror():
    # Finding #3a: input data that already carries 'overlap_area'/'source_area'
    # columns must not collide with crosswalk metadata (pre-fix: merge suffix
    # -> KeyError('overlap_area')). The crosswalk's own areas drive the result.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": [1.0, 9.0],
        "overlap_area": [1.0, 9.0],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({
        "GEOID": ["S1", "S2"], "rate": [0.1, 0.9],
        "overlap_area": [111.0, 222.0], "source_area": [333.0, 444.0],  # user columns
    })
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.82) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_extensive_passthrough_survives_helper_name_collision():
    # Finding #3b: extensive input columns named like the internal helpers
    # ('_inum_rate', '_iden_rate') must still be summed into the output, not
    # dropped by a helper-column name collision. Expected totals: 15 and 150.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": [1.0, 1.0],
        "overlap_area": [1.0, 1.0],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({
        "GEOID": ["S1", "S2"], "rate": [0.2, 0.8],
        "_inum_rate": [5.0, 10.0], "_iden_rate": [50.0, 100.0],
    })
    out = proc.transform(
        df, geoid_column="GEOID",
        value_columns=["rate", "_inum_rate", "_iden_rate"],
        intensive_variables=["rate"],
    ).set_index("GEOID")
    assert "_inum_rate" in out.columns and "_iden_rate" in out.columns, list(out.columns)
    assert abs(out.loc["T1", "_inum_rate"] - 15.0) < 1e-9, out.loc["T1", "_inum_rate"]
    assert abs(out.loc["T1", "_iden_rate"] - 150.0) < 1e-9, out.loc["T1", "_iden_rate"]


# --- Finding #4: missing/invalid area is recovered or rejected, never zeroed ---

def test_crosswalk_recovers_overlap_area_from_source_area_when_nan():
    # overlap_area [1, NaN] must be recovered from source_area * area_weight
    # ([1, 9] * [1, 1] = [1, 9]) -> .82, NOT silently zeroed (pre-fix -> .1).
    import numpy as np
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": [1.0, 9.0],
        "overlap_area": [1.0, np.nan],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.82) < 1e-9, out.loc["T1", "rate"]


def test_crosswalk_unrecoverable_invalid_area_rejects():
    # overlap_area [1, NaN] with NO source_area fallback on a 2-distinct-source
    # merge cannot be area-weighted -> must raise, not silently drop the source.
    import numpy as np
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "overlap_area": [1.0, np.nan],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    with pytest.raises(ValueError, match="area-weight intensive"):
        proc.transform(
            df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
        )


# --- Finding #5: refusal counts DISTINCT sources, not rows ---

def test_crosswalk_duplicate_source_rows_do_not_refuse():
    # One distinct source geography (S1) with two duplicate input rows mapping
    # to T1 is unambiguous: the result is .2. The pre-fix code counted ROWS and
    # raised a bogus "merge" ValueError.
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1"],
        "target_geoid": ["T1"],
        "area_weight": [1.0],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S1"], "rate": [0.2, 0.2]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"], intensive_variables=["rate"],
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.2) < 1e-9, out.loc["T1", "rate"]


# --- Finding #7: full dataset-path base_url is rejected (no doubled /data) ---

def test_census_catalog_full_dataset_path_base_url_rejected():
    from siege_utilities.geo.census import catalog_populator as cp
    # A base_url that already contains the dataset path would otherwise produce
    # '.../data/2023/acs/acs5/data/2023/acs/acs5/variables.json'.
    with pytest.raises(ValueError, match="full dataset path"):
        cp.CensusCatalogPopulator(base_url="https://api.census.gov/data/2023/acs/acs5")


# --- Finding #8: DuckDB native GEOMETRY round-trips (ST_AsWKB on read-back) ---

def test_duckdb_native_geometry_query_roundtrips():
    # A relation from a native-geometry query (ST_Point) carries DuckDB's
    # internal GEOMETRY blob, NOT valid WKB. to_geodataframe() must convert it
    # via ST_AsWKB; pre-fix it reached the WKB decoder and raised
    # "GEOSException: Unknown WKB type 0".
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    eng = DuckDBEngine()
    # Exercise the PUBLIC path: eng.query() must itself load spatial and
    # ST_AsWKB the GEOMETRY column before fetch (the private
    # eng._connection.query() path masked the defect by handing to_geodataframe
    # a live relation it could still convert).
    gdf = eng.to_geodataframe(eng.query("SELECT 7 AS id, ST_Point(1, 2) AS geometry"))
    assert list(gdf["id"]) == [7]
    assert gdf.geometry.iloc[0].equals(Point(1, 2)), gdf.geometry.iloc[0].wkt


def test_duckdb_read_spatial_native_geometry_roundtrips(tmp_path):
    # read_spatial fetches ST_Read's native GEOMETRY; it must ST_AsWKB it so the
    # decoder gets valid WKB (pre-fix returned corrupt/opaque bytes).
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    geojson = tmp_path / "pt.geojson"
    geojson.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"properties":{"id":1},"geometry":{"type":"Point","coordinates":[1,2]}}]}'
    )
    eng = DuckDBEngine()
    gdf = eng.read_spatial(str(geojson), crs="EPSG:4326")
    geom = gdf.geometry.iloc[0]
    assert geom.equals(Point(1, 2)), geom.wkt


# --- Finding #9a: nontrivial two-source mean merge is not double-divided ---

def test_crosswalk_two_source_mean_merge_not_double_divided():
    # A MERGE of two sources (areas 1 and 9, rates .1 and .9) under
    # aggregation_func="mean" must yield the area-weighted mean .82. Intensive
    # columns are computed on their own numerator/denominator path, so the
    # aggregation_func cannot double-divide (the round-2 defect produced .25).
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor

    xwalk = pd.DataFrame({
        "source_geoid": ["S1", "S2"],
        "target_geoid": ["T1", "T1"],
        "area_weight": [1.0, 1.0],
        "source_area": [1.0, 9.0],
        "overlap_area": [1.0, 9.0],
    })
    proc = CrosswalkProcessor(xwalk, 2010, 2020, "tract")
    df = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    out = proc.transform(
        df, geoid_column="GEOID", value_columns=["rate"],
        intensive_variables=["rate"], aggregation_func="mean",
    ).set_index("GEOID")
    assert abs(out.loc["T1", "rate"] - 0.82) < 1e-9, out.loc["T1", "rate"]


# --- Finding #9b: no-CRS serialization exercises the module logger path ---

def test_spark_from_geodataframe_no_crs_uses_module_logger():
    # A GeoDataFrame with no CRS takes the warning branch in
    # SparkEngine.from_geodataframe. That branch calls the module-level `log`;
    # if the module logger is undefined the serialization raises NameError.
    # This test exercises that path (red-on-revert: remove `log = getLogger`).
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point
    from siege_utilities.engines.dataframe_engine import SparkEngine

    eng = SparkEngine.__new__(SparkEngine)
    captured = {}
    eng._spark = types.SimpleNamespace(
        createDataFrame=lambda pdf: captured.setdefault("pdf", pdf)
    )
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(5, 6)], crs=None)
    assert gdf.crs is None
    eng.from_geodataframe(gdf)  # must not raise NameError on the no-CRS log path
    assert captured["pdf"]["geometry"].iloc[0] == "POINT (5 6)", captured["pdf"]["geometry"].iloc[0]
