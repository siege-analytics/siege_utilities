"""Tests for the configurable default CRS module."""

from __future__ import annotations

from siege_utilities.geo.crs import get_default_crs, set_default_crs


def test_default_crs_is_4326():
    assert get_default_crs() == "EPSG:4326"


def test_set_and_restore_default_crs():
    original = get_default_crs()
    try:
        set_default_crs("EPSG:3857")
        assert get_default_crs() == "EPSG:3857"
    finally:
        set_default_crs(original)
    assert get_default_crs() == original


def test_reproject_if_needed_none_input():
    from siege_utilities.geo.crs import reproject_if_needed
    assert reproject_if_needed(None) is None


def test_reproject_if_needed_uses_default():
    """When crs=None, reproject_if_needed uses get_default_crs()."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        import pytest
        pytest.skip("geopandas not available")

    from siege_utilities.geo.crs import reproject_if_needed

    gdf = gpd.GeoDataFrame(
        {"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326"
    )
    # With default CRS (4326), no reprojection
    result = reproject_if_needed(gdf, None)
    assert result.crs.to_epsg() == 4326

    # Explicit override
    result = reproject_if_needed(gdf, "EPSG:3857")
    assert result.crs.to_epsg() == 3857


def test_reproject_if_needed_with_changed_default():
    """Changing default CRS affects reproject_if_needed(gdf, None)."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        import pytest
        pytest.skip("geopandas not available")

    from siege_utilities.geo.crs import reproject_if_needed

    original = get_default_crs()
    try:
        set_default_crs("EPSG:3857")
        gdf = gpd.GeoDataFrame(
            {"a": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326"
        )
        result = reproject_if_needed(gdf, None)
        assert result.crs.to_epsg() == 3857
    finally:
        set_default_crs(original)
