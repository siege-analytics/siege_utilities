"""Spark engine spatial-contract fixes (verified at SQL/source level).

Consensus findings C4/C5/C7 (#1352/#1353/#1355). These run without a JVM:
they assert the generated Spark SQL and the Python control flow, not a live
Sedona computation (noted as a limitation). The SparkEngine is built via
__new__ so no SparkSession is required; self._session and _ensure_sedona are
stubbed.
"""
from unittest.mock import MagicMock

import pytest

from siege_utilities.engines.dataframe_engine import SparkEngine


def _sessionless_engine():
    eng = SparkEngine.__new__(SparkEngine)
    eng._spark = MagicMock()  # _session is a read-only property over _spark
    eng._enable_sedona = False
    eng._sedona_registered = True
    eng._ensure_sedona = lambda: None
    return eng


def _fake_df(columns):
    df = MagicMock()
    df.columns = list(columns)
    return df


def test_buffer_replaces_geometry_column_in_place():
    """C4: buffer must replace `geometry`, not add geometry_buffered."""
    eng = _sessionless_engine()
    captured = {}
    eng._session.sql = lambda sql: captured.setdefault("sql", sql)

    eng.buffer(_fake_df(["id", "geometry"]), distance=0.01, geometry_col="geometry")
    sql = captured["sql"]
    assert "geometry_buffered" not in sql, "buffer still emits a separate column"
    assert "AS `geometry`" in sql, "buffered result is not bound back to geometry"
    assert "SELECT *," not in sql, "original geometry left active via SELECT *"


def test_distance_rejects_dataframe_pairwise():
    """C5: DataFrame-to-DataFrame pairwise is rejected, not a Cartesian product."""
    eng = _sessionless_engine()
    left = _fake_df(["id", "geometry"])
    right = _fake_df(["id", "geometry"])
    with pytest.raises(NotImplementedError, match="positional row"):
        eng.distance(left, right, geometry_col="geometry", other_geom="geometry")


def test_distance_single_geometry_still_works():
    """C5: the single-geometry form is unaffected (returns a result)."""
    eng = _sessionless_engine()
    captured = {}
    eng._session.sql = lambda sql: captured.setdefault("sql", sql)
    eng.distance(_fake_df(["id", "geometry"]), "POINT (0 0)", geometry_col="geometry")
    assert "ST_Distance" in captured["sql"]
    assert "FROM _dist_left_" in captured["sql"]


def test_from_geodataframe_builds_spark_df_with_wkt():
    """C7: SparkEngine.from_geodataframe must not return the GeoDataFrame."""
    gpd = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    from shapely.geometry import Point

    eng = _sessionless_engine()
    captured = {}
    sentinel = object()

    def _create(pdf):
        captured["pdf"] = pdf
        return sentinel

    eng._session.createDataFrame = _create

    gdf = gpd.GeoDataFrame(
        {"id": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326"
    )
    result = eng.from_geodataframe(gdf)
    assert result is sentinel, "did not build a Spark DataFrame (returned gdf?)"
    pdf = captured["pdf"]
    assert list(pdf["geometry"]) == ["POINT (0 0)", "POINT (1 1)"]
    # geometry serialized to WKT strings, not shapely objects
    assert all(isinstance(v, str) for v in pdf["geometry"])


def test_from_geodataframe_rejects_empty():
    """C7 edge: an empty GeoDataFrame has no rows for Spark to infer a schema."""
    gpd = pytest.importorskip("geopandas")
    eng = _sessionless_engine()
    gdf = gpd.GeoDataFrame({"id": []}, geometry=[], crs="EPSG:4326")
    with pytest.raises(ValueError, match="empty GeoDataFrame"):
        eng.from_geodataframe(gdf)


def test_from_geodataframe_types_all_null_geometry_explicitly(monkeypatch):
    """C7 edge: all-null geometry cannot be inferred; type it as a null string
    column instead of letting Spark raise CANNOT_DETERMINE_TYPE. pyspark's lit()
    needs a live SparkContext, so it is stubbed to keep this JVM-free."""
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("pyspark")
    import pyspark.sql.functions as F
    monkeypatch.setattr(F, "lit", lambda *a, **k: MagicMock())

    eng = _sessionless_engine()
    captured = {}
    base = MagicMock()

    def _create(pdf):
        captured["pdf"] = pdf
        return base

    eng._spark.createDataFrame = _create

    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[None, None], crs="EPSG:4326")
    eng.from_geodataframe(gdf)
    # geometry is NOT in the inferred pandas frame (would be all-null); it is
    # attached via an explicitly-typed withColumn instead.
    assert "geometry" not in captured["pdf"].columns
    assert base.withColumn.called
