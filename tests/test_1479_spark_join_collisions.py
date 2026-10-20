"""Spatial joins keep one geometry and multi-layer assignments keep point names."""

import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box

from siege_utilities.engines.dataframe_engine import PandasEngine, SparkEngine


@pytest.fixture(scope="module")
def spark_engine(real_spark_session):
    from pyspark.sql.types import BooleanType, DoubleType, StringType
    from shapely import wkt

    session = real_spark_session.newSession()
    session.udf.register("ST_GeomFromText", lambda value: value, StringType())
    session.udf.register("ST_Contains", lambda a, b: wkt.loads(a).contains(wkt.loads(b)), BooleanType())
    session.udf.register("ST_Intersects", lambda a, b: wkt.loads(a).intersects(wkt.loads(b)), BooleanType())
    session.udf.register("ST_Distance", lambda a, b: wkt.loads(a).distance(wkt.loads(b)), DoubleType())
    return SparkEngine(session)


@pytest.fixture
def pandas_frames():
    points = gpd.GeoDataFrame(
        {"voter_id": [1], "name": ["voter"], "GEOID": ["home"]},
        geometry=[Point(0, 0)], crs="EPSG:3857",
    )
    polygons = gpd.GeoDataFrame(
        {"GEOID": ["01"], "name": ["district"]},
        geometry=[box(-1, -1, 1, 1)], crs=points.crs,
    )
    return points, polygons


@pytest.mark.requires_spark
@pytest.mark.parametrize("method", ["assign_boundaries", "spatial_join", "nearest"])
def test_spark_join_has_one_geometry_and_suffixes(spark_engine, pandas_frames, method):
    points, polygons = [spark_engine.from_geodataframe(frame) for frame in pandas_frames]
    result = getattr(spark_engine, method)(points, polygons)
    assert result.columns.count("geometry") == 1
    assert len(result.columns) == len(set(result.columns))
    assert {"GEOID_left", "GEOID_right", "name_left", "name_right"} <= set(result.columns)
    # Python stand-ins cannot execute Spark's outer-join ON clause. Check the
    # default schema above, then materialize this all-matching fixture as inner.
    if method == "assign_boundaries":
        result = spark_engine.assign_boundaries(points, polygons, how="inner")
    converted = spark_engine.to_geodataframe(result, crs="EPSG:3857")
    assert converted.geometry.iloc[0].equals(Point(0, 0))
    assert converted["name_left"].tolist() == ["voter"]
    assert converted["name_right"].tolist() == ["district"]


@pytest.mark.requires_spark
def test_spark_multi_assign_stays_native(spark_engine, pandas_frames, monkeypatch):
    from pyspark.sql import DataFrame

    points, polygons = [spark_engine.from_geodataframe(frame) for frame in pandas_frames]

    def forbid_collection(*args, **kwargs):
        pytest.fail("multi_assign must not collect to the driver")

    assign = spark_engine.assign_boundaries
    with monkeypatch.context() as patch:
        patch.setattr(spark_engine, "to_pandas", forbid_collection)
        patch.setattr(type(points), "toPandas", forbid_collection)
        patch.setattr(type(points), "collect", forbid_collection)
        result = spark_engine.multi_assign(points, {"cd": polygons, "sldu": polygons})
        assert isinstance(result, DataFrame)
        # Execute the all-matching fixture with Python UDF-compatible joins,
        # while keeping the driver-collection guard active for both layers.
        patch.setattr(spark_engine, "assign_boundaries", lambda *a, **kw: assign(*a, **kw, how="inner"))
        inner = spark_engine.multi_assign(points, {"cd": polygons, "sldu": polygons})
        assert inner.columns == result.columns
    assert set(result.columns) == {
        "voter_id", "name", "GEOID", "geometry", "cd_GEOID", "cd_name", "sldu_GEOID", "sldu_name",
    }
    row = inner.collect()[0]
    assert (row.name, row.cd_name, row.sldu_name) == ("voter", "district", "district")


def test_pandas_multi_assign_preserves_point_columns(pandas_frames):
    points, polygons = pandas_frames
    result = PandasEngine().multi_assign(points, {"cd": polygons, "sldu": polygons})
    assert set(result.columns) == {
        "voter_id", "name", "GEOID", "geometry", "cd_GEOID", "cd_name", "sldu_GEOID", "sldu_name",
    }
    assert result["name"].tolist() == ["voter"]
    assert result["GEOID"].tolist() == ["home"]
    assert result["cd_name"].tolist() == result["sldu_name"].tolist() == ["district"]


@pytest.mark.requires_spark
@pytest.mark.parametrize("method", ["spatial_join", "assign_boundaries"])
def test_spark_suffix_collision_is_rejected(spark_engine, pandas_frames, method):
    points, polygons = [spark_engine.from_geodataframe(frame) for frame in pandas_frames]
    from pyspark.sql import functions as F
    points = points.withColumn("name_left", F.lit("original"))
    with pytest.raises(ValueError, match="duplicate output column.*name_left"):
        getattr(spark_engine, method)(points, polygons)


def test_pandas_multi_assign_keeps_unmatched_points_and_drops_named_index(pandas_frames):
    points, polygons = pandas_frames
    points.loc[1] = [2, "outside", "away", Point(10, 10)]
    polygons.index.name = "polygon_row"
    result = PandasEngine().multi_assign(points, {"cd": polygons, "sldu": polygons})
    assert result["name"].tolist() == ["voter", "outside"]
    assert result.loc[1, ["cd_name", "sldu_name"]].isna().all()
    assert "polygon_row" not in result.columns


@pytest.mark.requires_spark
@pytest.mark.parametrize("method", ["spatial_join", "assign_boundaries"])
def test_collision_rejection_does_not_retain_catalog_views(spark_engine, pandas_frames, method):
    # A suffix collision must be rejected BEFORE any temp view is registered,
    # so repeated rejected calls do not accumulate catalog views.
    from pyspark.sql import functions as F

    points, polygons = [spark_engine.from_geodataframe(frame) for frame in pandas_frames]
    points = points.withColumn("name_left", F.lit("original"))
    session = spark_engine._session

    def temp_view_count():
        return sum(1 for t in session.catalog.listTables() if t.isTemporary)

    before = temp_view_count()
    for _ in range(3):
        with pytest.raises(ValueError, match="duplicate output column.*name_left"):
            getattr(spark_engine, method)(points, polygons)
    assert temp_view_count() == before
