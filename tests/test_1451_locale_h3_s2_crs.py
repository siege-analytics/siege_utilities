"""Regression tests for geographic coordinate handling in issue #1451."""

from types import SimpleNamespace
from unittest.mock import Mock

import geopandas as gpd
import pandas as pd
import pytest
from geopandas.testing import assert_geodataframe_equal
from shapely.geometry import Point, box, mapping, shape

from siege_utilities.geo import h3_utils, s2_utils
from siege_utilities.geo.locale import NCESLocaleClassifier


@pytest.fixture
def classifier():
    areas = gpd.GeoDataFrame(
        {"POP20": [500_000]}, geometry=[box(-78, 38, -76, 40)], crs=4269,
    )
    cities = gpd.GeoDataFrame(
        {"GEOID": ["2400100"], "POP20": [300_000]},
        geometry=[box(-77.5, 38.5, -76.5, 39.5)], crs=4269,
    )
    return NCESLocaleClassifier(areas, None, cities, {"2400100": 300_000})


@pytest.mark.parametrize("crs", [3857, 5070])
def test_classify_points_projected_matches_geographic(classifier, crs):
    points = gpd.GeoDataFrame(
        {"name": ["city"]}, geometry=[Point(-77, 39)], crs=4269, index=[7],
    )
    projected = points.to_crs(crs)
    original = projected.copy(deep=True)
    expected = classifier.classify_points(points)
    actual = classifier.classify_points(projected)
    assert expected.locale_code.tolist() == [11]
    assert actual.locale_code.tolist() == expected.locale_code.tolist()
    assert_geodataframe_equal(projected, original)
    assert_geodataframe_equal(actual[original.columns], original)


@pytest.mark.parametrize("method", ["majority", "distribution", "area_weighted"])
def test_classify_polygons_projected_matches_geographic(classifier, method):
    polygons = gpd.GeoDataFrame(
        {"name": ["urban"]}, geometry=[box(-77.2, 38.8, -76.8, 39.2)],
        crs=4269, index=[8],
    )
    projected = polygons.to_crs(3857)
    original = projected.copy(deep=True)
    expected = classifier.classify_polygons(polygons, method=method)
    actual = classifier.classify_polygons(projected, method=method)
    column = "locale_code" if method == "majority" else "locale_distribution"
    assert actual[column].iloc[0] == pytest.approx(expected[column].iloc[0])
    assert_geodataframe_equal(projected, original)
    assert_geodataframe_equal(actual[original.columns], original)


def test_classify_polygon_projected_frame(classifier):
    polygons = gpd.GeoDataFrame(
        geometry=[box(-77.2, 38.8, -76.8, 39.2)], crs=4269,
    )
    expected = classifier.classify_polygon(polygons.geometry.iloc[0])
    assert classifier.classify_polygon(polygons.to_crs(3857)) == pytest.approx(expected)


@pytest.mark.parametrize("method", ["classify_points", "classify_polygons"])
def test_locale_selected_geometry_column_uses_its_crs(classifier, method):
    geometry = Point(-77, 39) if method == "classify_points" else box(-77.2, 38.8, -76.8, 39.2)
    frame = gpd.GeoDataFrame(geometry=[geometry], crs=4269)
    # The selected column has a different CRS from the active geometry.
    frame["projected"] = frame.geometry.to_crs(3857)
    original = frame.copy(deep=True)
    classify = getattr(classifier, method)
    expected = classify(frame)
    actual = classify(frame, geometry_col="projected")
    assert actual.locale_code.tolist() == expected.locale_code.tolist()
    assert_geodataframe_equal(frame, original)


@pytest.mark.parametrize("method", ["classify_points", "classify_polygons", "classify_polygon"])
def test_locale_missing_crs_accepts_geographic_values(classifier, method):
    geometry = Point(-77, 39) if method == "classify_points" else box(-77.2, 38.8, -76.8, 39.2)
    frame = gpd.GeoDataFrame(geometry=[geometry])
    classify = getattr(classifier, method)
    actual = classify(frame)
    expected = classify(frame.set_crs(4269))
    if method == "classify_polygon":
        assert actual == pytest.approx(expected)
    else:
        assert actual.locale_code.tolist() == expected.locale_code.tolist()
        assert actual.crs is None
    assert frame.crs is None


@pytest.mark.parametrize("method", ["classify_points", "classify_polygons", "classify_polygon"])
@pytest.mark.parametrize("axis,value", [("longitude", 500000), ("latitude", -500000)])
def test_locale_missing_crs_rejects_out_of_range(classifier, method, axis, value):
    x, y = (value, 39) if axis == "longitude" else (-77, value)
    geometry = Point(x, y) if method == "classify_points" else box(x, y, x + 1, y + 1)
    frame = gpd.GeoDataFrame(geometry=[geometry])
    with pytest.raises(ValueError, match=rf"{method}.*{axis}.*{value}"):
        getattr(classifier, method)(frame)


def test_classify_polygon_bare_projected_geometry_raises(classifier):
    with pytest.raises(ValueError, match=r"classify_polygon.*longitude.*500000"):
        classifier.classify_polygon(box(500000, 39, 500001, 40))


@pytest.fixture(params=["h3", "s2"])
def grid(request):
    name = request.param
    module = h3_utils if name == "h3" else s2_utils
    return SimpleNamespace(
        name=name, module=module, package="h3" if name == "h3" else "s2sphere",
        resolution=7 if name == "h3" else 12,
        index=getattr(module, f"{name}_index_polygon"),
        join=getattr(module, f"{name}_spatial_join"),
    )


@pytest.fixture
def polygons():
    return gpd.GeoDataFrame(
        {"region": ["city"]}, geometry=[box(-77.1, 38.9, -76.9, 39.1)],
        crs=4326, index=[9],
    )


def test_grid_native_projected_cells_match_geographic(grid, polygons):
    pytest.importorskip(grid.package)
    expected = grid.index(polygons.geometry.iloc[0], grid.resolution)
    projected = polygons.to_crs(3857)
    original = projected.copy(deep=True)
    assert expected
    assert grid.index(projected, grid.resolution) == expected
    assert_geodataframe_equal(projected, original)


def test_grid_native_projected_join_matches_geographic(grid, polygons):
    pytest.importorskip(grid.package)
    points = pd.DataFrame({"lat": [39.0, 0.0], "lon": [-77.0, 0.0]})
    projected = polygons.to_crs(3857)
    original = projected.copy(deep=True)
    expected = grid.join(points, polygons, "lat", "lon", grid.resolution)
    actual = grid.join(points, projected, "lat", "lon", grid.resolution)
    assert expected.region.tolist() == ["city"]
    pd.testing.assert_frame_equal(actual, expected)
    assert_geodataframe_equal(projected, original)


@pytest.fixture
def mocked_cells(grid, monkeypatch):
    """Keep CRS branches runnable without either optional cell library."""
    monkeypatch.setattr(grid.module, f"_require_{grid.name}", lambda: None)
    if grid.name == "h3":
        cell_call = Mock(return_value={"cell"})
        monkeypatch.setattr(grid.module, "_polyfill_single", cell_call)
    else:
        cell_call = Mock(side_effect=lambda lat, lon: (lat, lon))
        coverer = Mock()
        coverer.get_covering.return_value = []
        monkeypatch.setattr(grid.module, "_s2", SimpleNamespace(
            LatLng=SimpleNamespace(from_degrees=cell_call),
            LatLngRect=Mock(), RegionCoverer=Mock(return_value=coverer),
        ))
    return cell_call


def test_grid_passes_geographic_coordinates_to_cell_call(grid, polygons, mocked_cells):
    grid.index(polygons.to_crs(3857), grid.resolution)
    if grid.name == "h3":
        received = shape(mocked_cells.call_args.args[0])
        assert received.equals_exact(polygons.geometry.iloc[0], tolerance=1e-8)
    else:
        assert mocked_cells.call_args_list[0].args == pytest.approx((38.9, -77.1))
        assert mocked_cells.call_args_list[1].args == pytest.approx((39.1, -76.9))


@pytest.mark.parametrize("operation", ["index", "join"])
@pytest.mark.parametrize("axis,value", [("longitude", 500000), ("latitude", -500000)])
def test_grid_missing_crs_raises_before_cell_call(grid, mocked_cells, operation, axis, value):
    x, y = (value, 39) if axis == "longitude" else (-77, value)
    frame = gpd.GeoDataFrame(geometry=[box(x, y, x + 1, y + 1)])
    function = f"{grid.name}_{'index_polygon' if operation == 'index' else 'spatial_join'}"
    with pytest.raises(ValueError, match=rf"{function}.*{axis}.*{value}"):
        if operation == "index":
            grid.index(frame, grid.resolution)
        else:
            grid.join(pd.DataFrame({"lat": [39], "lon": [-77]}), frame, "lat", "lon")
    mocked_cells.assert_not_called()


@pytest.mark.parametrize("as_geojson", [False, True])
def test_grid_bare_projected_polygon_raises(grid, mocked_cells, as_geojson):
    polygon = box(500000, 39, 500001, 40)
    geometry = mapping(polygon) if as_geojson else polygon
    with pytest.raises(ValueError, match=rf"{grid.name}_index_polygon.*longitude.*50000"):
        grid.index(geometry, grid.resolution)
    mocked_cells.assert_not_called()


def test_grid_join_passes_geographic_polygon(grid, polygons, monkeypatch):
    monkeypatch.setattr(grid.module, f"_require_{grid.name}", lambda: None)
    monkeypatch.setattr(grid.module, f"{grid.name}_index_points", Mock(
        return_value=pd.Series(["cell"]),
    ))
    cell_call = Mock(return_value={"cell"})
    monkeypatch.setattr(grid.module, f"{grid.name}_index_polygon", cell_call)
    points = pd.DataFrame({"lat": [39], "lon": [-77]})
    result = grid.join(points, polygons.to_crs(3857), "lat", "lon", grid.resolution)
    received = cell_call.call_args.args[0]
    assert received.equals_exact(polygons.geometry.iloc[0], tolerance=1e-8)
    assert result.region.tolist() == ["city"]


def test_grid_missing_crs_accepts_geographic_values(grid, polygons):
    pytest.importorskip(grid.package)
    unlabelled = gpd.GeoDataFrame({"region": ["city"]}, geometry=list(polygons.geometry))
    assert grid.index(unlabelled, grid.resolution) == grid.index(polygons, grid.resolution)
    points = pd.DataFrame({"lat": [39.0], "lon": [-77.0]})
    pd.testing.assert_frame_equal(
        grid.join(points, unlabelled, "lat", "lon", grid.resolution),
        grid.join(points, polygons, "lat", "lon", grid.resolution),
    )
    assert unlabelled.crs is None


def test_grid_projected_series_with_multiple_polygons(grid, polygons):
    pytest.importorskip(grid.package)
    geometries = gpd.GeoSeries(
        [polygons.geometry.iloc[0], box(-77.4, 38.9, -77.2, 39.1)], crs=4326,
    )
    expected = set().union(*(grid.index(geom, grid.resolution) for geom in geometries))
    assert grid.index(geometries.to_crs(5070), grid.resolution) == expected
