"""Tests for siege_utilities.geo.capabilities."""


def test_geo_capabilities_returns_dict():
    from siege_utilities.geo.capabilities import geo_capabilities
    caps = geo_capabilities()
    assert isinstance(caps, dict)
    assert "tier" in caps


def test_geo_capabilities_has_expected_keys():
    from siege_utilities.geo.capabilities import geo_capabilities
    caps = geo_capabilities()
    expected = {
        "shapely", "pyproj", "geopy", "censusgeocode",
        "geopandas", "fiona", "rtree", "mapclassify",
        "django_gis", "duckdb", "sedona", "tier",
    }
    assert expected.issubset(caps.keys())


def test_geo_capabilities_tier_is_string():
    from siege_utilities.geo.capabilities import geo_capabilities
    caps = geo_capabilities()
    assert caps["tier"] in ("geodjango", "geo", "geo-lite", "none")


def test_geo_capabilities_values_are_bool():
    from siege_utilities.geo.capabilities import geo_capabilities
    caps = geo_capabilities()
    for key, val in caps.items():
        if key != "tier":
            assert isinstance(val, bool), f"{key} should be bool, got {type(val)}"


def test_geo_capabilities_lazy_import():
    """geo_capabilities is accessible via the geo package lazy imports."""
    from siege_utilities.geo import geo_capabilities
    caps = geo_capabilities()
    assert "tier" in caps
