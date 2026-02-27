"""
Unit tests for GEOID ↔ slug conversion functions.

Tests round-trip conversion for all geography levels.
"""

import pytest

from siege_utilities.geo.geoid_utils import geoid_to_slug, slug_to_geoid


class TestGeoidToSlug:
    """Tests for geoid_to_slug()."""

    def test_state(self):
        assert geoid_to_slug("06", "state") == "ca"

    def test_county(self):
        assert geoid_to_slug("06037", "county") == "ca-county-037"

    def test_tract(self):
        assert geoid_to_slug("06037101100", "tract") == "ca-037-tract-101100"

    def test_block_group(self):
        assert geoid_to_slug("060371011001", "block_group") == "ca-037-101100-bg-1"

    def test_block(self):
        assert geoid_to_slug("060371011001001", "block") == "ca-037-101100-block-1001"

    def test_place(self):
        assert geoid_to_slug("0644000", "place") == "ca-place-44000"

    def test_zcta(self):
        assert geoid_to_slug("90210", "zcta") == "zcta-90210"

    def test_cd(self):
        assert geoid_to_slug("0614", "cd") == "ca-cd-14"

    def test_sldu(self):
        assert geoid_to_slug("06001", "sldu") == "ca-sldu-001"

    def test_sldl(self):
        assert geoid_to_slug("06001", "sldl") == "ca-sldl-001"

    def test_vtd(self):
        assert geoid_to_slug("06037001", "vtd") == "ca-037-vtd-001"


class TestSlugToGeoid:
    """Tests for slug_to_geoid()."""

    def test_state(self):
        assert slug_to_geoid("ca") == "06"

    def test_county(self):
        assert slug_to_geoid("ca-county-037") == "06037"

    def test_tract(self):
        assert slug_to_geoid("ca-037-tract-101100") == "06037101100"

    def test_block_group(self):
        assert slug_to_geoid("ca-037-101100-bg-1") == "060371011001"

    def test_block(self):
        assert slug_to_geoid("ca-037-101100-block-1001") == "060371011001001"

    def test_place(self):
        assert slug_to_geoid("ca-place-44000") == "0644000"

    def test_zcta(self):
        assert slug_to_geoid("zcta-90210") == "90210"

    def test_cd(self):
        assert slug_to_geoid("ca-cd-14") == "0614"

    def test_sldu(self):
        assert slug_to_geoid("ca-sldu-001") == "06001"

    def test_sldl(self):
        assert slug_to_geoid("ca-sldl-001") == "06001"

    def test_vtd(self):
        assert slug_to_geoid("ca-037-vtd-001") == "06037001"

    def test_unknown_state_raises(self):
        with pytest.raises(ValueError, match="Unknown state"):
            slug_to_geoid("xx-county-037")

    def test_empty_slug_raises(self):
        with pytest.raises(ValueError):
            slug_to_geoid("")


class TestRoundTrip:
    """Test that geoid_to_slug and slug_to_geoid are inverses."""

    CASES = [
        ("06", "state"),
        ("06037", "county"),
        ("06037101100", "tract"),
        ("060371011001", "block_group"),
        ("060371011001001", "block"),
        ("0644000", "place"),
        ("90210", "zcta"),
        ("0614", "cd"),
        ("06001", "sldu"),
        ("06001", "sldl"),
        ("06037001", "vtd"),
    ]

    @pytest.mark.parametrize("geoid,level", CASES, ids=[c[1] for c in CASES])
    def test_roundtrip(self, geoid, level):
        slug = geoid_to_slug(geoid, level)
        recovered = slug_to_geoid(slug)
        assert recovered == geoid, f"Round-trip failed: {geoid} → {slug} → {recovered}"
