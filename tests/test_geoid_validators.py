"""Tests for GEOID validators (su#130)."""

import pytest

from siege_utilities.geo.validators import (
    is_valid_state_fips,
    is_valid_county_fips,
    is_valid_tract_geoid,
    is_valid_block_group_geoid,
)


# =============================================================================
# STATE FIPS VALIDATION
# =============================================================================

class TestIsValidStateFips:
    @pytest.mark.parametrize("fips", ["01", "06", "11", "36", "48", "72", "78", "60", "66", "69", "74"])
    def test_valid_state_fips(self, fips):
        assert is_valid_state_fips(fips) is True

    @pytest.mark.parametrize("fips", ["00", "03", "07", "99", "77", "80"])
    def test_invalid_state_fips(self, fips):
        assert is_valid_state_fips(fips) is False

    def test_empty_string(self):
        assert is_valid_state_fips("") is False

    def test_single_digit(self):
        assert is_valid_state_fips("6") is False

    def test_three_digits(self):
        assert is_valid_state_fips("006") is False

    def test_letters(self):
        assert is_valid_state_fips("CA") is False

    def test_none(self):
        assert is_valid_state_fips(None) is False

    def test_integer(self):
        assert is_valid_state_fips(6) is False


# =============================================================================
# COUNTY FIPS VALIDATION
# =============================================================================

class TestIsValidCountyFips:
    @pytest.mark.parametrize("fips", ["06037", "36061", "48201", "11001", "01001"])
    def test_valid_county_fips(self, fips):
        assert is_valid_county_fips(fips) is True

    def test_invalid_state_prefix(self):
        assert is_valid_county_fips("99001") is False

    def test_too_short(self):
        assert is_valid_county_fips("0603") is False

    def test_too_long(self):
        assert is_valid_county_fips("060370") is False

    def test_letters(self):
        assert is_valid_county_fips("CA037") is False

    def test_empty(self):
        assert is_valid_county_fips("") is False

    def test_none(self):
        assert is_valid_county_fips(None) is False

    def test_integer(self):
        assert is_valid_county_fips(6037) is False


# =============================================================================
# TRACT GEOID VALIDATION
# =============================================================================

class TestIsValidTractGeoid:
    @pytest.mark.parametrize("geoid", ["06037101100", "36061000100", "48201310100"])
    def test_valid_tract_geoid(self, geoid):
        assert is_valid_tract_geoid(geoid) is True

    def test_invalid_state_prefix(self):
        assert is_valid_tract_geoid("99037101100") is False

    def test_too_short(self):
        assert is_valid_tract_geoid("0603710110") is False

    def test_too_long(self):
        assert is_valid_tract_geoid("060371011001") is False

    def test_letters(self):
        assert is_valid_tract_geoid("0603710110A") is False

    def test_empty(self):
        assert is_valid_tract_geoid("") is False

    def test_none(self):
        assert is_valid_tract_geoid(None) is False


# =============================================================================
# BLOCK GROUP GEOID VALIDATION
# =============================================================================

class TestIsValidBlockGroupGeoid:
    @pytest.mark.parametrize("geoid", ["060371011001", "360610001001", "482013101002"])
    def test_valid_block_group_geoid(self, geoid):
        assert is_valid_block_group_geoid(geoid) is True

    def test_invalid_state_prefix(self):
        assert is_valid_block_group_geoid("990371011001") is False

    def test_too_short(self):
        assert is_valid_block_group_geoid("06037101100") is False

    def test_too_long(self):
        assert is_valid_block_group_geoid("0603710110012") is False

    def test_letters(self):
        assert is_valid_block_group_geoid("06037101100A") is False

    def test_empty(self):
        assert is_valid_block_group_geoid("") is False

    def test_none(self):
        assert is_valid_block_group_geoid(None) is False


# =============================================================================
# DJANGO VALIDATORS (only run if Django is installed)
# =============================================================================

try:
    from django.core.exceptions import ValidationError
    from siege_utilities.geo.validators import (
        StateFIPSValidator,
        CountyFIPSValidator,
        TractGEOIDValidator,
        BlockGroupGEOIDValidator,
    )
    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False


@pytest.mark.skipif(not HAS_DJANGO, reason="Django not installed")
class TestDjangoValidators:
    def test_state_fips_valid(self):
        # Django validators return None on success, raise ValidationError on failure
        assert StateFIPSValidator()("06") is None

    def test_state_fips_invalid(self):
        with pytest.raises(ValidationError):
            StateFIPSValidator()("99")

    def test_county_fips_valid(self):
        assert CountyFIPSValidator()("06037") is None

    def test_county_fips_invalid(self):
        with pytest.raises(ValidationError):
            CountyFIPSValidator()("99001")

    def test_tract_geoid_valid(self):
        assert TractGEOIDValidator()("06037101100") is None

    def test_tract_geoid_invalid(self):
        with pytest.raises(ValidationError):
            TractGEOIDValidator()("invalid")

    def test_block_group_geoid_valid(self):
        assert BlockGroupGEOIDValidator()("060371011001") is None

    def test_block_group_geoid_invalid(self):
        with pytest.raises(ValidationError):
            BlockGroupGEOIDValidator()("invalid")
