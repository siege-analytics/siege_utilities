"""DuckDB reads plain frames of Shapely geometry at the default CRS, as Pandas does (#1852).

A plain DataFrame of Shapely objects (for example from load_points) carries no
CRS. Pandas and PostGIS read it at the default CRS, so crs= reprojects it.
DuckDB must do the same; labelling lon/lat degrees as a projected CRS gives
wrong distances and areas with no error.
"""
import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("duckdb")

import pandas as pd  # noqa: E402 - after the optional-dependency skips
from shapely.geometry import box  # noqa: E402

from siege_utilities.engines.dataframe_engine import DuckDBEngine, PandasEngine  # noqa: E402
from siege_utilities.geo.crs import get_default_crs  # noqa: E402


@pytest.fixture
def duck():
    engine = DuckDBEngine()
    yield engine
    engine._connection.close()


def _points():
    return pd.DataFrame({"pid": [1, 2], "lat": [30.27, 30.30], "lon": [-97.74, -97.70]})


def _targets():
    return pd.DataFrame({"tid": [10, 20], "lat": [30.28, 30.31], "lon": [-97.73, -97.69]})


def _sources():
    return pd.DataFrame({"sid": [1], "pop": [100.0], "geometry": [box(-100, 30, -90, 50)]})


def _zones():
    # Split by latitude over a wide band: in lon/lat degrees the two halves are
    # 50/50, while an equal-area projection gives unequal shares.
    return pd.DataFrame({
        "zid": [1, 2],
        "geometry": [box(-100, 30, -90, 40), box(-100, 40, -90, 50)],
    })


def test_load_points_frame_gets_default_crs_like_pandas(duck):
    pandas_engine = PandasEngine()
    expected = pandas_engine.to_geodataframe(pandas_engine.load_points(_points())).crs
    actual = duck.to_geodataframe(duck.load_points(_points())).crs
    assert expected == get_default_crs()
    assert actual == expected


@pytest.mark.parametrize("encode", ["hex", "bytes", "bytearray", "memoryview"])
def test_attrs_less_wkb_stays_unknown_crs(duck, encode):
    from shapely.geometry import Point
    point = Point(1, 2)
    value = {
        "hex": point.wkb_hex,
        "bytes": point.wkb,
        "bytearray": bytearray(point.wkb),
        "memoryview": memoryview(point.wkb),
    }[encode]
    out = duck.to_geodataframe(pd.DataFrame({"geometry": [value]}))
    assert out.crs is None
    assert out.geometry.iloc[0].equals(point)


def test_all_null_plain_frame_gets_default_crs(duck):
    frame = pd.DataFrame({"geometry": [None, None]})
    assert duck.to_geodataframe(frame).crs == get_default_crs()


def test_nearest_projected_crs_matches_pandas(duck):
    pandas_engine = PandasEngine()
    expected = pandas_engine.nearest(
        pandas_engine.load_points(_points()), pandas_engine.load_points(_targets()), crs="EPSG:5070"
    )
    actual = duck.nearest(duck.load_points(_points()), duck.load_points(_targets()), crs="EPSG:5070")
    assert list(actual["tid"]) == list(expected["tid"])
    assert actual["distance"].round(3).tolist() == expected["distance"].round(3).tolist()
    assert expected["distance"].max() > 100  # metres, not degrees


def test_apportion_projected_crs_matches_pandas(duck):
    pandas_engine = PandasEngine()
    expected = pandas_engine.apportion(_sources(), _zones(), "pop", crs="EPSG:5070")
    actual = duck.apportion(_sources(), _zones(), "pop", crs="EPSG:5070")
    expected = expected.sort_values("zid").reset_index(drop=True)
    actual = actual.sort_values("zid").reset_index(drop=True)
    assert actual["apportioned_pop"].round(6).tolist() == expected["apportioned_pop"].round(6).tolist()
    # Degree arithmetic would split the source 50/50; measured area does not.
    assert abs(actual["apportioned_pop"].iloc[0] - 50.0) > 1.0


@pytest.mark.parametrize("target", [None, "EPSG:4326"])
def test_geometry_dtype_column_keeps_its_own_crs(duck, target):
    gdf = gpd.GeoDataFrame({"pid": [1]}, geometry=gpd.points_from_xy([500000.0], [4000000.0]), crs=3857)
    frame = pd.DataFrame(gdf)
    out = duck.to_geodataframe(frame, crs=target)
    if target is None:
        assert out.crs.to_epsg() == 3857
        assert out.geometry.iloc[0].x == 500000.0
    else:
        assert out.crs.to_epsg() == 4326
        assert out.geometry.iloc[0].equals(gdf.to_crs(4326).geometry.iloc[0])


def test_assign_boundaries_from_load_points_keeps_default_crs(duck):
    zones = gpd.GeoDataFrame(_zones(), geometry="geometry", crs=get_default_crs())
    out = duck.assign_boundaries(duck.load_points(_points()), zones)
    assert out.crs == get_default_crs()
