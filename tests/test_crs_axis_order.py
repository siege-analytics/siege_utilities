"""Tests for siege_utilities.geo.crs detect_crs + reproject_geom (SU#543)."""

from __future__ import annotations

import pytest

# Skip the whole module if shapely / pyproj aren't installed; reproject_geom
# raises ImportError otherwise but a clean skip avoids noisy collection errors
# in stripped-down environments.
pyproj = pytest.importorskip("pyproj")
shapely_geometry = pytest.importorskip("shapely.geometry")

from siege_utilities.geo.crs import (
    AXIS_ORDER_AUTH_COMPLIANT,
    AXIS_ORDER_TRAD_GIS,
    detect_crs,
    reproject_geom,
)


def test_detect_crs_none_returns_none():
    assert detect_crs(None) is None


def test_detect_crs_bare_geometry_returns_none():
    from shapely.geometry import Point
    assert detect_crs(Point(0, 0)) is None


def test_detect_crs_dict_with_crs_block():
    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [],
    }
    assert detect_crs(geojson) == "EPSG:4326"


def test_detect_crs_dict_without_crs_block():
    geojson = {"type": "FeatureCollection", "features": []}
    assert detect_crs(geojson) is None


def test_detect_crs_object_with_crs_attribute():
    class FakeGDF:
        crs = "EPSG:3857"

    assert detect_crs(FakeGDF()) == "EPSG:3857"


def test_detect_crs_object_with_crs_wkt_attribute():
    class FakeCollection:
        crs = None
        crs_wkt = pyproj.CRS.from_epsg(4326).to_wkt()

    assert detect_crs(FakeCollection()) == "EPSG:4326"


# --- reproject_geom -------------------------------------------------------


def test_reproject_geom_none_returns_none():
    assert reproject_geom(None, "EPSG:4326") is None


def test_reproject_geom_invalid_axis_order():
    from shapely.geometry import Point
    with pytest.raises(ValueError, match="axis_order"):
        reproject_geom(Point(0, 0), "EPSG:4326", axis_order="bogus")


def test_reproject_geom_missing_src_crs():
    from shapely.geometry import Point
    with pytest.raises(ValueError, match="src_crs"):
        reproject_geom(Point(0, 0), None)


def test_reproject_geom_same_crs_noop():
    from shapely.geometry import Point
    p = Point(1.0, 2.0)
    result = reproject_geom(p, "EPSG:4326", dst_epsg=4326)
    # Identity short-circuit returns the same object.
    assert result is p


def test_reproject_geom_4326_to_3857_round_trip():
    from shapely.geometry import Point

    # Origin Point in Austin, TX
    src = Point(-97.7431, 30.2672)
    web_merc = reproject_geom(src, "EPSG:4326", dst_epsg=3857)
    back = reproject_geom(web_merc, "EPSG:3857", dst_epsg=4326)

    assert abs(back.x - src.x) < 1e-6
    assert abs(back.y - src.y) < 1e-6


def test_reproject_geom_trad_gis_lon_first():
    from shapely.geometry import Point

    # Input is (lon, lat). With trad_gis (always_xy=True) reprojecting
    # 4326 -> 3857 should produce easting near the equator origin (-97.7431
    # is roughly -10878000 in EPSG:3857).
    src = Point(-97.7431, 30.2672)
    web_merc = reproject_geom(
        src, "EPSG:4326", dst_epsg=3857, axis_order=AXIS_ORDER_TRAD_GIS
    )
    assert -1.1e7 < web_merc.x < -1.0e7


def test_reproject_geom_axis_order_toggle_differs():
    """trad_gis vs auth_compliant must produce different output for EPSG:4326
    (which the authority defines as lat-first, while consumer files store
    lon-first)."""
    from shapely.geometry import Point

    src = Point(-97.7431, 30.2672)
    trad = reproject_geom(
        src, "EPSG:4326", dst_epsg=3857, axis_order=AXIS_ORDER_TRAD_GIS
    )
    auth = reproject_geom(
        src, "EPSG:4326", dst_epsg=3857, axis_order=AXIS_ORDER_AUTH_COMPLIANT
    )
    # Under auth_compliant, the (x=-97.7431, y=30.2672) tuple is interpreted
    # as (lat=-97.7431, lon=30.2672) which is nonsense and produces a different
    # transformed coordinate. The test asserts the differ-ness, which is the
    # whole point of the toggle existing.
    assert (trad.x, trad.y) != (auth.x, auth.y)
