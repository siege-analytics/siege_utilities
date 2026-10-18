"""Spatial joins reject known CRS mismatches across engines (#1619)."""

import pytest

gpd = pytest.importorskip("geopandas")

from shapely.geometry import Point, box  # noqa: E402

from siege_utilities.engines.dataframe_engine import (  # noqa: E402
    DuckDBEngine,
    PandasEngine,
    PostGISEngine,
    SparkEngine,
)


@pytest.fixture(params=[
    "pandas",
    "duckdb",
    pytest.param("postgis", marks=pytest.mark.postgis),
])
def engine(request):
    if request.param == "pandas":
        return PandasEngine()
    if request.param == "duckdb":
        pytest.importorskip("duckdb")
        return DuckDBEngine()
    pytest.importorskip("sqlalchemy")
    # This join runs on the driver, so no database connection is opened.
    return PostGISEngine("postgresql://localhost/unused")


@pytest.fixture
def frames():
    points = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(-97.7, 30.3)], crs="EPSG:4326",
    )
    polygons = gpd.GeoDataFrame(
        {"d": ["x"]}, geometry=[box(-100, 25, -95, 35)], crs="EPSG:4326",
    )
    return points, polygons


def test_spatial_join_rejects_mismatched_crs(engine, frames):
    points, polygons = frames

    with pytest.raises(ValueError) as exc_info:
        engine.spatial_join(points, polygons.to_crs(3857))

    assert str(exc_info.value) == (
        "CRS mismatch in spatial_join: left has EPSG:4326, "
        "right has EPSG:3857. Reproject one input to match the other."
    )


def test_spatial_join_matching_crs(engine, frames):
    points, polygons = frames

    result = engine.spatial_join(points, polygons)

    assert result[["id", "d"]].to_dict("records") == [{"id": 1, "d": "x"}]
    assert result.crs == points.crs


@pytest.mark.parametrize("unknown_sides", ["left", "right", "both"])
@pytest.mark.filterwarnings("ignore:CRS mismatch between:UserWarning")
def test_spatial_join_allows_unknown_crs(engine, frames, unknown_sides):
    points, polygons = frames
    if unknown_sides in ("left", "both"):
        points.crs = None
    if unknown_sides in ("right", "both"):
        polygons.crs = None

    result = engine.spatial_join(points, polygons)

    assert result[["id", "d"]].to_dict("records") == [{"id": 1, "d": "x"}]


@pytest.mark.parametrize("method", [
    "point_in_polygon", "assign_boundaries", "intersect_boundaries", "multi_assign",
])
def test_spatial_helpers_reject_mismatched_crs(engine, frames, method):
    points, polygons = frames
    right = polygons.to_crs(3857)
    if method == "multi_assign":
        right = {"district": right}
    elif method == "intersect_boundaries":
        points = polygons

    with pytest.raises(ValueError, match="CRS mismatch in spatial_join"):
        getattr(engine, method)(points, right)


@pytest.mark.requires_spark
def test_spark_spatial_join_rejects_known_mismatched_crs(real_spark_session):
    left = real_spark_session.createDataFrame([("POINT(-97.7 30.3)",)], ["geometry"])
    right = real_spark_session.createDataFrame([("POINT(0 0)",)], ["geometry"])
    left.crs = "EPSG:4326"
    right.crs = "EPSG:3857"

    with pytest.raises(ValueError, match="CRS mismatch in spatial_join"):
        SparkEngine(spark=real_spark_session).spatial_join(left, right)


@pytest.mark.requires_spark
@pytest.mark.parametrize("crs_metadata", ["matching", "unknown", "data_column"])
def test_spark_spatial_join_allows_matching_or_unknown_crs(real_spark_session, crs_metadata):
    from shapely import wkt

    spark = real_spark_session.newSession()
    # Exercise the actual Spark SQL join without requiring Sedona JARs.
    spark.udf.register("ST_GeomFromText", lambda value: value, "string")
    spark.udf.register(
        "ST_Intersects", lambda left, right: wkt.loads(left).intersects(wkt.loads(right)), "boolean",
    )
    left = spark.createDataFrame([(1, "POINT(-97.7 30.3)")], ["id", "geometry"])
    right = spark.createDataFrame([("x", "POINT(-97.7 30.3)")], ["d", "geometry"])
    if crs_metadata == "matching":
        left.crs = right.crs = "EPSG:4326"
    elif crs_metadata == "data_column":
        from pyspark.sql import functions as F

        left = left.withColumn("crs", F.lit("left data"))
        right = right.withColumn("crs", F.lit("right data"))

    result = SparkEngine(spark=spark).spatial_join(left, right)

    assert [row.asDict() for row in result.select("id", "d").collect()] == [{"id": 1, "d": "x"}]
