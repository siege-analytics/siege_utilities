"""Regression tests for equal-area interpolation and output CRS (#1407)."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("shapely")
# Optional imports must follow the dependency skip gates.
from geopandas.testing import assert_geodataframe_equal  # noqa: E402
from shapely.geometry import box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402


@pytest.fixture(params=["shapely", "duckdb", "tobler"])
def area_backend(request, monkeypatch):
    from siege_utilities.geo.interpolation import areal

    if request.param == "tobler":
        pytest.importorskip("tobler")
    monkeypatch.setattr(areal, "_TOBLER_AVAILABLE", request.param == "tobler")
    monkeypatch.setattr(areal, "_DUCKDB_AVAILABLE", request.param == "duckdb")
    if request.param == "duckdb":
        duckdb = pytest.importorskip("duckdb")
        connection = duckdb.connect(config={
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        })
        try:
            connection.execute("LOAD spatial")
        except duckdb.IOException:
            connection.close()
            pytest.skip("DuckDB spatial extension is not installed locally")

        # Exercise real spatial SQL without allowing INSTALL to use the network.
        proxy = Mock(wraps=connection)
        proxy.execute.side_effect = lambda sql: connection.execute(
            "LOAD spatial" if sql == "INSTALL spatial; LOAD spatial;" else sql
        )
        monkeypatch.setattr(areal, "_duckdb", SimpleNamespace(connect=lambda: proxy))
        request.addfinalizer(connection.close)
    return areal


def _rtol(result):
    # Shapely and DuckDB reproduce the reference areas to 1e-8. Tobler's own
    # intersection pipeline differs by ~1e-7 relative; #1407 requires 0.1%.
    return 1e-6 if result.backend == "tobler" else 1e-8


@pytest.fixture
def latitude_split():
    cells = [box(-1, 30, 1, 37.5), box(-1, 37.5, 1, 45)]
    # Retain the shared boundary vertices so coverage is complete after projection.
    source = gpd.GeoDataFrame(
        {"population": [1000.0]}, geometry=[unary_union(cells)],
        crs="EPSG:4326", index=[7],
    )
    target = gpd.GeoDataFrame(
        {"name": ["south", "north"], "population": [-1.0, -1.0]},
        geometry=cells, crs="EPSG:4326", index=[20, 10],
    )
    return source, target


@pytest.mark.parametrize("target_crs", ["EPSG:4326", "EPSG:3857"])
def test_extensive_equal_area_shares(area_backend, latitude_split, target_crs):
    source, geographic_target = latitude_split
    target = geographic_target.to_crs(target_crs)
    original_source, original_target = source.copy(), target.copy()
    source_ea = source.to_crs("ESRI:54009").geometry.iloc[0]
    overlap_areas = geographic_target.to_crs("ESRI:54009").geometry.intersection(source_ea).area
    expected = 1000.0 * overlap_areas.to_numpy() / source_ea.area
    degree_shares = np.array([
        cell.intersection(source.geometry.iloc[0]).area / source.geometry.iloc[0].area
        for cell in geographic_target.geometry
    ])
    np.testing.assert_allclose(degree_shares, [0.5, 0.5])
    # The old 500/500 allocation differs from the equal-area result by about 5%.
    relative_error = np.abs(1000.0 * degree_shares - expected) / expected
    assert np.all((relative_error > 0.045) & (relative_error < 0.055))

    result = area_backend.interpolate_areal(source, target, extensive_variables=["population"])

    np.testing.assert_allclose(result.data["population"], expected, rtol=_rtol(result))
    assert result.data["population"].sum() == pytest.approx(1000.0)
    assert result.data.crs == source.crs
    assert result.data.columns.tolist() == target.columns.tolist()
    assert_geodataframe_equal(result.data.drop(columns="population"),
                              geographic_target.drop(columns="population"),
                              check_less_precise=True)
    assert_geodataframe_equal(source, original_source)
    assert_geodataframe_equal(target, original_target)


@pytest.mark.parametrize("target_crs", ["EPSG:4326", "EPSG:3857"])
def test_intensive_equal_area_average(area_backend, latitude_split, target_crs):
    whole, cells = latitude_split
    source = cells.assign(rate=[100.0, 200.0])
    target = whole.drop(columns="population").to_crs(target_crs)
    target_ea = whole.to_crs("ESRI:54009").geometry.iloc[0]
    overlaps = source.to_crs("ESRI:54009").geometry.intersection(target_ea).area
    expected = np.average(source["rate"], weights=overlaps)
    assert abs(expected - 150.0) > 2.0

    result = area_backend.interpolate_areal(source, target, intensive_variables=["rate"])

    assert result.data["rate"].iloc[0] == pytest.approx(expected, rel=_rtol(result))
    assert result.data.crs == source.crs


@pytest.mark.parametrize("output_crs", [None, "EPSG:32631"])
def test_output_crs_uses_source_or_explicit_override(area_backend, latitude_split, output_crs):
    source, target = latitude_split
    source = source.to_crs("EPSG:3857")

    result = area_backend.interpolate_areal(
        source, target, extensive_variables=["population"], crs=output_crs,
    )

    expected_target = target.to_crs(output_crs or source.crs)
    assert_geodataframe_equal(result.data.drop(columns="population"),
                              expected_target.drop(columns="population"))
    assert result.source_crs == str(source.crs)
    assert result.target_crs == str(target.crs)


def test_tobler_measures_in_area_crs_not_degrees(monkeypatch, latitude_split):
    """#1407: tobler used to measure geographic input in degrees (500/500, with a warning)."""
    import warnings

    pytest.importorskip("tobler")
    from siege_utilities.geo.interpolation import areal

    source, target = latitude_split
    monkeypatch.setattr(areal, "_TOBLER_AVAILABLE", True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = areal.interpolate_areal(source, target, extensive_variables=["population"])

    assert not [w for w in caught if "geographic CRS" in str(w.message)]
    assert result.backend == "tobler"
    np.testing.assert_allclose(result.data["population"], [525.2049, 474.7951], atol=1e-3)
    assert result.data.crs == source.crs
    assert_geodataframe_equal(result.data.drop(columns="population"),
                              target.drop(columns="population"))


def _expected_shares(source, target, area_crs):
    source_area = source.to_crs(area_crs).geometry.iloc[0]
    overlaps = target.to_crs(area_crs).geometry.intersection(source_area).area
    return 1000.0 * overlaps.to_numpy() / source_area.area


def test_default_area_crs_is_recorded(area_backend, latitude_split):
    source, target = latitude_split

    result = area_backend.interpolate_areal(source, target, extensive_variables=["population"])

    assert result.area_crs == "ESRI:54009"


def test_area_crs_is_configurable_and_used(area_backend, latitude_split):
    """The configured CRS must drive the areas, not just the metadata."""
    source, target = latitude_split
    mercator = _expected_shares(source, target, "EPSG:3857")
    mollweide = _expected_shares(source, target, "ESRI:54009")
    assert np.abs(mercator - mollweide).max() > 5.0, "fixture must separate the two CRSs"

    result = area_backend.interpolate_areal(
        source, target, extensive_variables=["population"], area_crs="EPSG:3857",
    )

    assert result.area_crs == "EPSG:3857"
    np.testing.assert_allclose(result.data["population"], mercator, rtol=1e-6)
    assert result.data.crs == source.crs


@pytest.mark.parametrize("bad", ["EPSG:4326", "not-a-crs"])
def test_geographic_or_invalid_area_crs_is_rejected(latitude_split, bad):
    from siege_utilities.geo.interpolation import areal

    source, target = latitude_split
    with pytest.raises(ValueError, match="area_crs"):
        areal.interpolate_areal(source, target, extensive_variables=["population"], area_crs=bad)


def test_interpolate_extensive_passes_area_crs_through(area_backend, latitude_split):
    whole, cells = latitude_split

    extensive = area_backend.interpolate_extensive(
        whole, cells, ["population"], area_crs="EPSG:6933",
    )

    assert extensive.area_crs == "EPSG:6933"
    np.testing.assert_allclose(
        extensive.data["population"], _expected_shares(whole, cells, "EPSG:6933"), rtol=1e-6,
    )


def test_interpolate_intensive_passes_area_crs_through(area_backend, latitude_split):
    whole, cells = latitude_split

    intensive = area_backend.interpolate_intensive(
        cells.assign(rate=[100.0, 200.0]), whole.drop(columns="population"), ["rate"],
        area_crs="EPSG:6933",
    )

    assert intensive.area_crs == "EPSG:6933"
