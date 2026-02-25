"""Tests for BOUNDARY_TYPE_CATALOG and TIGER_FILE_PATTERNS consistency."""

import pytest

from siege_utilities.geo.spatial_data import BOUNDARY_TYPE_CATALOG
from siege_utilities.config.census_constants import TIGER_FILE_PATTERNS


# Valid geometry types in TIGER shapefiles
VALID_GEOMETRY_TYPES = {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}


class TestBoundaryTypeCatalog:
    """Tests for the BOUNDARY_TYPE_CATALOG dictionary."""

    def test_every_entry_has_geometry_type(self):
        """All catalog entries must have a geometry_type field."""
        for key, entry in BOUNDARY_TYPE_CATALOG.items():
            assert "geometry_type" in entry, f"Missing geometry_type for '{key}'"

    def test_geometry_types_are_valid(self):
        """All geometry_type values must be recognized shapefile geometry types."""
        for key, entry in BOUNDARY_TYPE_CATALOG.items():
            gt = entry["geometry_type"]
            assert gt in VALID_GEOMETRY_TYPES, (
                f"Invalid geometry_type '{gt}' for '{key}'. "
                f"Must be one of {VALID_GEOMETRY_TYPES}"
            )

    def test_every_entry_has_required_fields(self):
        """All entries must have category, abbrev, name, geometry_type."""
        required = {"category", "abbrev", "name", "geometry_type"}
        for key, entry in BOUNDARY_TYPE_CATALOG.items():
            missing = required - set(entry.keys())
            assert not missing, f"Entry '{key}' missing fields: {missing}"

    def test_categories_valid(self):
        """Category must be 'redistricting' or 'general'."""
        for key, entry in BOUNDARY_TYPE_CATALOG.items():
            assert entry["category"] in ("redistricting", "general"), (
                f"Invalid category '{entry['category']}' for '{key}'"
            )

    def test_line_features_are_multilinestring(self):
        """Roads, rails, linear_water, edges, address_features should be MultiLineString."""
        line_types = ["roads", "rails", "linear_water", "edges", "address_features"]
        for key in line_types:
            assert key in BOUNDARY_TYPE_CATALOG, f"Missing catalog entry: '{key}'"
            assert BOUNDARY_TYPE_CATALOG[key]["geometry_type"] == "MultiLineString", (
                f"Expected MultiLineString for '{key}', got "
                f"'{BOUNDARY_TYPE_CATALOG[key]['geometry_type']}'"
            )

    def test_pointlm_is_point(self):
        """Point landmarks should have Point geometry type."""
        assert "pointlm" in BOUNDARY_TYPE_CATALOG
        assert BOUNDARY_TYPE_CATALOG["pointlm"]["geometry_type"] == "Point"

    def test_arealm_is_multipolygon(self):
        """Area landmarks should have MultiPolygon geometry type."""
        assert "arealm" in BOUNDARY_TYPE_CATALOG
        assert BOUNDARY_TYPE_CATALOG["arealm"]["geometry_type"] == "MultiPolygon"

    def test_puma_present(self):
        """PUMA should be in the catalog."""
        assert "puma" in BOUNDARY_TYPE_CATALOG
        assert BOUNDARY_TYPE_CATALOG["puma"]["geometry_type"] == "MultiPolygon"

    def test_uac_entries(self):
        """Urban areas (uac, uac20) should be present and MultiPolygon."""
        for key in ("uac", "uac20"):
            assert key in BOUNDARY_TYPE_CATALOG
            assert BOUNDARY_TYPE_CATALOG[key]["geometry_type"] == "MultiPolygon"

    def test_minimum_entry_count(self):
        """Catalog should have at least 47 entries (original + new)."""
        assert len(BOUNDARY_TYPE_CATALOG) >= 47


class TestTigerFilePatterns:
    """Tests for TIGER_FILE_PATTERNS consistency with the catalog."""

    def test_all_patterns_reference_valid_levels(self):
        """All pattern keys should be recognized geographic levels."""
        for level in TIGER_FILE_PATTERNS:
            assert isinstance(TIGER_FILE_PATTERNS[level], str), (
                f"Pattern for '{level}' is not a string"
            )

    def test_new_patterns_present(self):
        """All newly added patterns should be present."""
        new_patterns = [
            "uac", "uac20", "rails", "aiannh",
            "roads", "linear_water", "area_water", "edges",
            "address_features", "pointlm", "arealm",
            "elsd", "scsd", "unsd",
        ]
        for pat in new_patterns:
            assert pat in TIGER_FILE_PATTERNS, f"Missing TIGER pattern: '{pat}'"

    def test_state_patterns_have_state_fips(self):
        """State-scope patterns must include {state_fips} placeholder."""
        state_levels = [
            "cousub", "tract", "block_group", "block", "tabblock20", "tabblock10",
            "place", "sldu", "sldl", "vtd", "vtd20", "puma",
            "roads", "linear_water", "area_water", "edges",
            "address_features", "pointlm", "arealm", "elsd", "scsd", "unsd",
        ]
        for level in state_levels:
            if level in TIGER_FILE_PATTERNS:
                assert "{state_fips}" in TIGER_FILE_PATTERNS[level], (
                    f"State-scope pattern '{level}' missing {{state_fips}} placeholder"
                )

    def test_national_patterns_no_state_fips(self):
        """National-scope patterns should NOT include {state_fips}."""
        national_levels = ["nation", "state", "county", "cbsa", "zcta", "uac", "uac20", "rails", "aiannh"]
        for level in national_levels:
            if level in TIGER_FILE_PATTERNS:
                assert "{state_fips}" not in TIGER_FILE_PATTERNS[level], (
                    f"National pattern '{level}' should not have {{state_fips}}"
                )

    def test_all_patterns_have_year(self):
        """All patterns must include {year} placeholder."""
        for level, pattern in TIGER_FILE_PATTERNS.items():
            assert "{year}" in pattern, (
                f"Pattern '{level}' missing {{year}} placeholder"
            )

    def test_pattern_count(self):
        """Should have at least 32 patterns."""
        assert len(TIGER_FILE_PATTERNS) >= 32
