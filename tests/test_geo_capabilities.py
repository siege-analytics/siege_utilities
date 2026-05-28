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


# --- Error-path tests (SU-4b) ---

from unittest.mock import patch

from siege_utilities.geo.capabilities import _probe, geo_capabilities


class TestProbeErrors:
    """Error paths for _probe — import failure handling."""

    def test_nonexistent_module_returns_false(self):
        """_probe returns False for a module that cannot be imported."""
        assert _probe("nonexistent_module_xyz_12345") is False

    def test_existing_module_returns_true(self):
        """_probe returns True for a module known to exist."""
        assert _probe("os") is True


class TestGeoCapabilitiesTierFallback:
    """Tier detection when packages are missing."""

    def test_none_tier_when_no_packages(self):
        """When no spatial packages are importable, tier is 'none'."""
        with patch(
            "siege_utilities.geo.capabilities._probe", return_value=False
        ):
            caps = geo_capabilities()
            assert caps["tier"] == "none"
            assert caps["shapely"] is False
            assert caps["geopandas"] is False

    def test_geo_lite_tier_with_shapely_only(self):
        """When only shapely is available, tier is 'geo-lite'."""

        def selective_probe(name):
            return name == "shapely"

        with patch(
            "siege_utilities.geo.capabilities._probe", side_effect=selective_probe
        ):
            caps = geo_capabilities()
            assert caps["tier"] == "geo-lite"
