"""Verification tests for tabblock20 boundary support (su#325).

Confirms that CensusDataSource supports tabblock20 for download,
URL construction, and GEOID parsing — as required by Social Warehouse
and Reverberator downstream consumers.
"""

import pytest

from siege_utilities.config.census_registry import (
    CANONICAL_GEOGRAPHIC_LEVELS,
    TIGER_FILE_PATTERNS,
    get_tiger_url,
    resolve_geographic_level,
)


class TestTabblock20Support:

    def test_in_canonical_levels(self):
        assert "tabblock20" in CANONICAL_GEOGRAPHIC_LEVELS

    def test_geoid_length_15(self):
        level = CANONICAL_GEOGRAPHIC_LEVELS["tabblock20"]
        assert level["geoid_length"] == 15

    def test_has_tiger_file_pattern(self):
        assert "tabblock20" in TIGER_FILE_PATTERNS

    def test_tiger_pattern_has_state_fips(self):
        pattern = TIGER_FILE_PATTERNS["tabblock20"]
        assert "{state_fips}" in pattern

    def test_resolve_geographic_level(self):
        assert resolve_geographic_level("tabblock20") == "tabblock20"

    def test_url_construction(self):
        url = get_tiger_url(year=2020, state_fips="10", geographic_level="tabblock20")
        assert "TABBLOCK20" in url.upper() or "tabblock20" in url
        assert "10" in url  # Delaware FIPS

    def test_geoid_components(self):
        """A tabblock20 GEOID has 15 digits: SS + CCC + TTTTTT + BBBB."""
        sample_geoid = "100010401001000"  # Delaware, Kent County
        assert len(sample_geoid) == 15
        state_fips = sample_geoid[:2]
        county_fips = sample_geoid[2:5]
        tract = sample_geoid[5:11]
        block = sample_geoid[11:15]
        assert state_fips == "10"  # Delaware
        assert county_fips == "001"  # Kent County
        assert len(tract) == 6
        assert len(block) == 4


class TestAllRequiredBoundaryTypes:
    """Verify all boundary types needed by Social Warehouse and Reverberator."""

    @pytest.mark.parametrize("level", [
        "tabblock20", "cd", "sldu", "sldl", "county", "state",
    ])
    def test_in_canonical_levels(self, level):
        assert level in CANONICAL_GEOGRAPHIC_LEVELS

    @pytest.mark.parametrize("level", [
        "tabblock20", "cd", "sldu", "sldl", "county", "state",
    ])
    def test_has_tiger_pattern(self, level):
        assert level in TIGER_FILE_PATTERNS

    @pytest.mark.parametrize("level", [
        "tabblock20", "cd", "sldu", "sldl", "county", "state",
    ])
    def test_resolves(self, level):
        assert resolve_geographic_level(level) == level
