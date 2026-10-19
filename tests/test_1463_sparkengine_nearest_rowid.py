"""Nearest joins preserve point rows and the GeoPandas output contract (#1463).

Run real Spark SQL with Shapely stand-ins for the two Sedona functions.
"""

import math

import pytest


pytestmark = pytest.mark.requires_spark

POINTS = [(1, "POINT (0 0)"), (2, "POINT (0 0)"), (3, "POINT (100 100)")]
TARGETS = [(10, "POINT (1 0)"), (11, "POINT (2 0)")]


@pytest.fixture(scope="module")
def nearest_engine(real_spark_session):
    pytest.importorskip("shapely")
    from pyspark.sql.types import DoubleType, StringType
    from shapely import wkt

    from siege_utilities.engines.dataframe_engine import SparkEngine

    def distance(left, right):
        if left is None or right is None:
            return None
        return wkt.loads(left).distance(wkt.loads(right))

    # Isolate the stand-ins from other tests sharing the Spark context.
    session = real_spark_session.newSession()
    session.udf.register("ST_GeomFromText", lambda value: value, StringType())
    session.udf.register("ST_Distance", distance, DoubleType())
    return SparkEngine(session)


@pytest.fixture
def frames(nearest_engine):
    session = nearest_engine._session
    return (
        session.createDataFrame(POINTS, "point_id long, geometry string"),
        session.createDataFrame(TARGETS, "target_id long, geometry string"),
    )


def test_colocated_points_each_receive_a_nearest_target(nearest_engine, frames):
    result = nearest_engine.nearest(*frames, k=1)
    rows = result.collect()
    assert sorted(row.point_id for row in rows) == [1, 2, 3]
    assert {row.point_id: row.target_id for row in rows} == {1: 10, 2: 10, 3: 11}
    assert {row.point_id: row.distance for row in rows} == pytest.approx(
        {1: 1.0, 2: 1.0, 3: math.hypot(98, 100)}
    )


def test_max_distance_keeps_unmatched_points(nearest_engine, frames):
    result = nearest_engine.nearest(*frames, k=1, max_distance=5)
    rows = {row.point_id: row for row in result.collect()}
    assert set(rows) == {1, 2, 3}
    assert rows[1].target_id == rows[2].target_id == 10
    assert rows[3].geometry == "POINT (100 100)"
    assert rows[3].target_id is None
    assert rows[3].index_right is None
    assert rows[3].distance is None


def test_output_columns_match_base_contract(nearest_engine, frames):
    gpd = pytest.importorskip("geopandas")
    from shapely import wkt

    from siege_utilities.engines.dataframe_engine import PandasEngine

    points = gpd.GeoDataFrame(
        {"point_id": [row[0] for row in POINTS]},
        geometry=[wkt.loads(row[1]) for row in POINTS], crs="EPSG:3857",
    )
    targets = gpd.GeoDataFrame(
        {"target_id": [row[0] for row in TARGETS]},
        geometry=[wkt.loads(row[1]) for row in TARGETS], crs="EPSG:3857",
    )
    expected = PandasEngine().nearest(points, targets)
    result = nearest_engine.nearest(*frames)
    assert result.columns == list(expected.columns)
    assert result.columns == ["point_id", "geometry", "index_right", "target_id", "distance"]
    assert len(result.columns) == len(set(result.columns))
    assert not {"d", "rn"}.intersection(result.columns)
    rows = {row.point_id: row for row in result.collect()}
    assert rows[1].index_right == rows[2].index_right
    assert rows[1].index_right != rows[3].index_right


@pytest.mark.parametrize("max_distance, expected_count", [(None, 6), (1.0, 3), (5.0, 5)])
def test_k_nearest_is_per_point(nearest_engine, frames, max_distance, expected_count):
    rows = nearest_engine.nearest(*frames, k=2, max_distance=max_distance).collect()
    assert len(rows) == expected_count
    assert {row.point_id for row in rows} == {1, 2, 3}
    for point_id in (1, 2):
        expected_targets = [10] if max_distance == 1.0 else [10, 11]
        assert sorted(row.target_id for row in rows if row.point_id == point_id) == expected_targets


@pytest.mark.parametrize("empty_side", ["points", "targets"])
def test_empty_inputs(nearest_engine, frames, empty_side):
    points, targets = frames
    if empty_side == "points":
        points = points.limit(0)
    else:
        targets = targets.limit(0)
    result = nearest_engine.nearest(points, targets)
    assert result.columns == ["point_id", "geometry", "index_right", "target_id", "distance"]
    rows = result.collect()
    if empty_side == "points":
        assert rows == []
    else:
        assert sorted(row.point_id for row in rows) == [1, 2, 3]
        assert all(row.target_id is None and row.index_right is None and row.distance is None for row in rows)


def test_identical_rows_keep_their_multiplicity_after_shuffle(nearest_engine):
    session = nearest_engine._session
    points = session.createDataFrame(
        [("POINT (0 0)",)] * 4, "geometry string",
    ).repartition(3)
    targets = session.createDataFrame(TARGETS, "target_id long, geometry string").repartition(2)
    result = nearest_engine.nearest(points, targets, k=2)
    first = result.collect()
    second = result.collect()
    assert len(first) == len(second) == 8
    assert sorted(first) == sorted(second)
    for target_id in (10, 11):
        matches = [row for row in first if row.target_id == target_id]
        assert len(matches) == 4
        assert len({row.index_right for row in matches}) == 1
    assert len({row.index_right for row in first}) == 2


def test_custom_geometry_and_shared_attributes(nearest_engine):
    session = nearest_engine._session
    points = session.createDataFrame(
        [(1, "POINT (0 0)", "point")], "id long, location string, `site name` string",
    )
    targets = session.createDataFrame(
        [(10, "POINT (1 0)", "target", "description")],
        "id long, shape string, `site name` string, location string",
    )
    result = nearest_engine.nearest(points, targets, point_geom="location", target_geom="shape")
    assert result.columns == [
        "id_left", "location", "site name_left", "index_right", "id_right",
        "site name_right", "location_right", "distance",
    ]
    row = result.collect()[0]
    assert row.id_left == 1
    assert row.id_right == 10
    assert row.location == "POINT (0 0)"
    assert row.location_right == "description"
    assert row["site name_left"] == "point"
    assert row["site name_right"] == "target"
    assert row.distance == pytest.approx(1.0)


def test_null_geometries_do_not_displace_valid_candidates(nearest_engine):
    session = nearest_engine._session
    points = session.createDataFrame(
        [(1, None), (2, "POINT (0 0)")], "point_id long, geometry string",
    )
    targets = session.createDataFrame(
        [(10, None), (11, "POINT (1 0)")], "target_id long, geometry string",
    )
    rows = {row.point_id: row for row in nearest_engine.nearest(points, targets).collect()}
    assert set(rows) == {1, 2}
    assert rows[1].target_id is rows[1].index_right is rows[1].distance is None
    assert rows[2].target_id == 11
    assert rows[2].distance == pytest.approx(1.0)
