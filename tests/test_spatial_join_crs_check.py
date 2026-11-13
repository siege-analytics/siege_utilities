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


@pytest.mark.filterwarnings("ignore:CRS mismatch between:UserWarning")
def test_multi_assign_keeps_matching_non_default_crs_across_layers(engine, frames):
    points, polygons = frames
    points = points.to_crs(3857)
    layers = {
        "district": polygons.to_crs(3857),
        "county": polygons.rename(columns={"d": "c"}).to_crs(3857),
    }

    result = engine.multi_assign(points, layers)

    assert len(result) == 1
    assert list(result["id"]) == [1]
    assert list(result["district_d"]) == ["x"]
    assert list(result["county_c"]) == ["x"]
    assert result["geometry"].iloc[0].equals(points.geometry.iloc[0])


@pytest.fixture(params=["pandas", "duckdb"])
def layer_checking_engine(request):
    """Engines whose multi_assign keeps the GeoDataFrame, so every layer is checked."""
    if request.param == "pandas":
        return PandasEngine()
    pytest.importorskip("duckdb")
    return DuckDBEngine()


def test_multi_assign_rejects_a_known_mismatch_on_a_later_layer(layer_checking_engine, frames):
    points, polygons = frames
    layers = {
        "district": polygons.to_crs(3857),
        "county": polygons.rename(columns={"d": "c"}),
    }

    with pytest.raises(ValueError) as exc_info:
        layer_checking_engine.multi_assign(points.to_crs(3857), layers)

    assert str(exc_info.value) == (
        "CRS mismatch in spatial_join: left has EPSG:3857, "
        "right has EPSG:4326. Reproject one input to match the other."
    )


@pytest.fixture(params=[
    "duckdb",
    pytest.param("postgis", marks=pytest.mark.postgis),
])
def converting_engine(request):
    """Engines that convert non-GeoDataFrame inputs with to_geodataframe."""
    if request.param == "duckdb":
        pytest.importorskip("duckdb")
        return DuckDBEngine()
    pytest.importorskip("sqlalchemy")
    return PostGISEngine("postgresql://localhost/unused")


@pytest.mark.filterwarnings("ignore:CRS mismatch between:UserWarning")
def test_frame_without_crs_metadata_is_unknown_crs(converting_engine):
    import pandas as pd

    points = pd.DataFrame({"id": [1], "geometry": ["POINT (-10850000 3550000)"]})
    polygons = gpd.GeoDataFrame(
        {"d": ["x"]},
        geometry=[box(-11000000, 3400000, -10700000, 3700000)],
        crs="EPSG:3857",
    )

    result = converting_engine.spatial_join(points, polygons)

    assert len(result) == 1
    assert result[["id", "d"]].to_dict("records") == [{"id": 1, "d": "x"}]
    assert result["geometry"].iloc[0].equals(Point(-10850000, 3550000))


@pytest.mark.filterwarnings("ignore:CRS mismatch between:UserWarning")
def test_multi_assign_keeps_points_without_crs_metadata_unknown(converting_engine):
    import pandas as pd

    points = pd.DataFrame({"id": [1], "geometry": ["POINT (-10850000 3550000)"]})
    polygons = gpd.GeoDataFrame(
        {"d": ["x"]},
        geometry=[box(-11000000, 3400000, -10700000, 3700000)],
        crs="EPSG:3857",
    )
    layers = {
        "district": polygons,
        "county": polygons.rename(columns={"d": "c"}),
    }

    result = converting_engine.multi_assign(points, layers)

    assert len(result) == 1
    assert list(result["id"]) == [1]
    assert list(result["district_d"]) == ["x"]
    assert list(result["county_c"]) == ["x"]
    assert result["geometry"].iloc[0].equals(Point(-10850000, 3550000))


@pytest.mark.requires_spark
def test_spark_spatial_join_rejects_known_mismatched_crs(real_spark_session):
    left = real_spark_session.createDataFrame([("POINT(-97.7 30.3)",)], ["geometry"])
    right = real_spark_session.createDataFrame([("POINT(0 0)",)], ["geometry"])
    left.crs = "EPSG:4326"
    right.crs = "EPSG:3857"

    with pytest.raises(ValueError, match="CRS mismatch in spatial_join"):
        SparkEngine(spark=real_spark_session).spatial_join(left, right)


@pytest.mark.requires_spark
@pytest.mark.parametrize("crs_metadata", ["matching", "case_variant", "unknown", "data_column"])
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
    elif crs_metadata == "case_variant":
        left.crs = "EPSG:4326"
        right.crs = "epsg:4326"
    elif crs_metadata == "data_column":
        from pyspark.sql import functions as F

        left = left.withColumn("crs", F.lit("left data"))
        right = right.withColumn("crs", F.lit("right data"))

    result = SparkEngine(spark=spark).spatial_join(left, right)

    assert [row.asDict() for row in result.select("id", "d").collect()] == [{"id": 1, "d": "x"}]
