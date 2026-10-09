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


# --- C: Spark from_geodataframe normalizes CRS before WKT serialization ---

def test_spark_from_geodataframe_normalizes_crs(monkeypatch):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point
    from shapely import wkt
    from siege_utilities.engines.dataframe_engine import SparkEngine

    eng = SparkEngine.__new__(SparkEngine)
    captured = {}
    eng._spark = types.SimpleNamespace(createDataFrame=lambda pdf: captured.setdefault("pdf", pdf))

    # A projected point (EPSG:3857) ~ (111319.49, 0) is lon 1deg, lat 0.
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(111319.490793, 0)], crs="EPSG:3857")
    eng.from_geodataframe(gdf)
    geom = wkt.loads(captured["pdf"]["geometry"].iloc[0])
    assert abs(geom.x - 1.0) < 1e-3 and abs(geom.y) < 1e-6, (
        f"CRS not normalized before serialize: got {geom.wkt}"
    )


def test_spark_to_geodataframe_reprojects_to_requested_crs():
    gpd = pytest.importorskip("geopandas")
    import pandas as pd
    from siege_utilities.engines.dataframe_engine import SparkEngine

    # Stored WKT is in the default CRS (EPSG:4326). Requesting EPSG:3857 on
    # read-back must REPROJECT (POINT (1 0) deg -> ~111319 m), not relabel the
    # degree coordinates as metres.
    class _DF:
        def toPandas(self):
            return pd.DataFrame({"id": [1], "geometry": ["POINT (1 0)"]})

    eng = SparkEngine.__new__(SparkEngine)
    out = eng.to_geodataframe(_DF(), crs="EPSG:3857")
    assert abs(out.geometry.iloc[0].x - 111319.49) < 1.0, out.geometry.iloc[0].wkt


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
