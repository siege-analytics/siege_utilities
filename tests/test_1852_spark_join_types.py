"""SparkEngine spatial joins keep only the left geometry, so they reject right and outer joins (#1852).

These checks run before any Spark call, so stand-in frames are enough: the
projection must reject the join type before a temp view is registered.
"""

from types import SimpleNamespace
import pandas as pd
import pytest

pytest.importorskip("geopandas")
from shapely.geometry import Point

from siege_utilities.engines.dataframe_engine import SparkEngine


class _Frame:
    """Columns plus a record of temp-view registrations."""

    def __init__(self, columns: list[str], registered: list[str]) -> None:
        self.columns = columns
        self._registered = registered

    def createOrReplaceTempView(self, name: str) -> None:  # noqa: N802 - Spark API name
        self._registered.append(name)


def _engine() -> SparkEngine:
    engine = SparkEngine.__new__(SparkEngine)
    # Bypass __init__ so the join-type checks run without a JVM; the stand-in
    # session answers only the calls made before a view would be registered.
    engine._spark = SimpleNamespace(
        conf=SimpleNamespace(get=lambda key, default: "false"),
        catalog=SimpleNamespace(dropTempView=lambda name: None),
        sql=lambda statement: statement,
    )
    engine._enable_sedona = False
    engine._sedona_registered = False
    return engine


@pytest.mark.parametrize("how", ["right", "outer", "full", "RIGHT"])
def test_projection_rejects_joins_that_drop_the_right_geometry(how: str) -> None:
    left = _Frame(["pid", "geometry"], [])
    right = _Frame(["tid", "geometry"], [])

    with pytest.raises(ValueError, match="how='inner' or 'left'"):
        _engine()._spatial_join_projection(left, right, "geometry", "geometry", "l", "r", how)


@pytest.mark.parametrize("how", ["inner", "left", "LEFT"])
def test_projection_still_builds_inner_and_left_joins(how: str) -> None:
    left = _Frame(["pid", "geometry"], [])
    right = _Frame(["tid", "geometry"], [])

    projection = _engine()._spatial_join_projection(left, right, "geometry", "geometry", "l", "r", how)

    assert projection == "l.`pid` AS `pid`, l.`geometry` AS `geometry`, r.`tid` AS `tid`"


@pytest.mark.parametrize("how", ["right", "outer", "full"])
def test_spatial_join_rejects_before_registering_views(how: str) -> None:
    registered: list[str] = []
    left = _Frame(["pid", "geometry"], registered)
    right = _Frame(["tid", "geometry"], registered)

    with pytest.raises(ValueError, match="how='inner' or 'left'"):
        _engine().spatial_join(left, right, how=how)
    assert registered == []


@pytest.mark.parametrize("how", ["right", "outer", "full"])
def test_assign_boundaries_rejects_before_registering_views(how: str) -> None:
    pytest.importorskip("pyspark")
    registered: list[str] = []
    points = _Frame(["pid", "geometry"], registered)
    polygons = _Frame(["tid", "geometry"], registered)

    with pytest.raises(ValueError, match="how='inner' or 'left'"):
        _engine().assign_boundaries(points, polygons, how=how)
    assert registered == []


def test_spark_operation_frame_assigns_the_declared_crs_without_reprojecting() -> None:
    # Spark has no source CRS: crs names the stored coordinates' CRS, so
    # projected metres written with read_spatial(crs="EPSG:3857") stay as-is.
    stored = SimpleNamespace(toPandas=lambda: pd.DataFrame({"geometry": ["POINT (500000 3000000)"]}))

    gdf = _engine()._operation_frame(stored, "geometry", "EPSG:3857")

    assert gdf.crs.to_epsg() == 3857
    assert gdf.geometry.iloc[0].equals(Point(500000, 3000000))
