"""Projected inputs retain their units and CRS across driver-side engines."""

import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box

from siege_utilities.engines.dataframe_engine import DuckDBEngine, PandasEngine, PostGISEngine


@pytest.fixture(params=["pandas", "duckdb", "postgis"])
def engine(request):
    if request.param == "duckdb":
        pytest.importorskip("duckdb")
        result = DuckDBEngine()
        yield result
        result._connection.close()
    elif request.param == "postgis":
        pytest.importorskip("sqlalchemy")
        # These inherited operations run in GeoPandas; no database is contacted.
        yield PostGISEngine("postgresql://unused")
    else:
        yield PandasEngine()


@pytest.fixture
def projected_points():
    return (
        gpd.GeoDataFrame({"pid": [1]}, geometry=[Point(0, 0)], crs=5070),
        gpd.GeoDataFrame({"tid": [9]}, geometry=[Point(500, 0)], crs=5070),
    )


@pytest.fixture
def projected_areas():
    source = gpd.GeoDataFrame(
        {"pop": [1000]}, geometry=[box(-100, 30, -99, 50)], crs=4326,
    ).to_crs(5070)
    targets = gpd.GeoDataFrame(
        {"half": ["south", "north"]},
        geometry=[box(-100, 30, -99, 40), box(-100, 40, -99, 50)], crs=4326,
    ).to_crs(5070)
    return source, targets


def test_nearest_preserves_metres_and_crs(engine, projected_points):
    points, targets = projected_points
    result = engine.nearest(points, targets, max_distance=1000)
    assert result["distance"].tolist() == pytest.approx([500])
    assert result.crs.to_epsg() == 5070
    unmatched = engine.nearest(points, targets, max_distance=400)
    assert unmatched["tid"].isna().all()
    assert unmatched.crs == points.crs


def test_apportion_uses_projected_area_shares(engine, projected_areas):
    result = engine.apportion(*projected_areas, "pop").set_index("half")
    assert result.loc["south", "apportioned_pop"] == pytest.approx(536.1, rel=0.001)
    assert result.loc["north", "apportioned_pop"] == pytest.approx(463.9, rel=0.001)


def test_dissolve_preserves_input_crs(engine, projected_areas):
    source, _ = projected_areas
    result = engine.dissolve(source.assign(region="one"), by="region")
    assert result.crs == source.crs
    assert result.geometry.iloc[0].equals(source.geometry.iloc[0])


@pytest.mark.parametrize("crs", [5070, None])
def test_geodataframe_conversion_preserves_known_or_unknown_crs(engine, crs):
    source = gpd.GeoDataFrame(geometry=[Point(500, 0)], crs=crs)
    result = engine.to_geodataframe(source)
    assert result.crs == source.crs
    assert result.geometry.iloc[0].equals(source.geometry.iloc[0])


def test_explicit_crs_reprojects_conversion_and_base_operations(engine, projected_points, projected_areas):
    points, targets = projected_points
    converted = engine.to_geodataframe(points, crs=3857)
    assert converted.crs.to_epsg() == 3857
    assert converted.geometry.iloc[0].equals(points.to_crs(3857).geometry.iloc[0])
    nearest = engine.nearest(points, targets, crs=3857)
    expected = points.to_crs(3857).geometry.iloc[0].distance(targets.to_crs(3857).geometry.iloc[0])
    assert nearest["distance"].iloc[0] == pytest.approx(expected)
    assert nearest.crs.to_epsg() == 3857
    source, halves = projected_areas
    dissolved = engine.dissolve(source.assign(region="one"), by="region", crs=3857)
    assert dissolved.crs.to_epsg() == 3857
    from_geographic = engine.apportion(source.to_crs(4326), halves.to_crs(4326), "pop", crs=5070)
    assert from_geographic.set_index("half").loc["south", "apportioned_pop"] == pytest.approx(536.1, rel=0.001)
    assert points.crs.to_epsg() == source.crs.to_epsg() == 5070


def test_geographic_distance_and_area_require_projected_crs(engine, projected_points, projected_areas):
    points, targets = [frame.to_crs(4326) for frame in projected_points]
    with pytest.raises(ValueError, match="projected CRS"):
        engine.nearest(points, targets)
    source, halves = [frame.to_crs(4326) for frame in projected_areas]
    with pytest.raises(ValueError, match="projected CRS"):
        engine.apportion(source, halves, "pop")


def test_mismatched_crs_is_rejected(engine, projected_points, projected_areas):
    points, targets = projected_points
    with pytest.raises(ValueError, match="CRS mismatch"):
        engine.nearest(points, targets.to_crs(3857))
    source, halves = projected_areas
    with pytest.raises(ValueError, match="CRS mismatch"):
        engine.apportion(source, halves.to_crs(3857), "pop")


def test_wkt_text_keeps_default_crs(engine):
    result = engine.to_geodataframe(pd.DataFrame({"geometry": ["POINT (1 2)"]}))
    assert result.crs.to_epsg() == 4326


@pytest.mark.parametrize("source_crs", [5070, None])
def test_explicit_crs_applies_to_empty_geodataframes(engine, source_crs):
    source = gpd.GeoDataFrame(geometry=[], crs=source_crs)
    result = engine.to_geodataframe(source, crs=3857)
    assert result.empty
    assert result.crs.to_epsg() == 3857
