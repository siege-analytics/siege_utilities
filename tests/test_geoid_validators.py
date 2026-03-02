"""
Unit tests for GEOID format validators.

Tests the level-specific validation functions in geoid_utils and the
Django validator classes in validators.py.
"""

import pytest

from siege_utilities.geo.geoid_utils import (
    GEOID_PATTERNS,
    validate_state_fips,
    validate_county_fips,
    validate_tract_geoid,
    validate_block_group_geoid,
)

# Configure Django so the validator classes can raise ValidationError
try:
    import django
    from django.conf import settings as django_settings

    if not django_settings.configured:
        django_settings.configure(
            DATABASES={
                "default": {
                    "ENGINE": "django.contrib.gis.db.backends.postgis",
                    "NAME": "test_siege_geo",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.gis",
            ],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        )
        django.setup()
    _DJANGO_AVAILABLE = True
except Exception:
    _DJANGO_AVAILABLE = False


# =============================================================================
# GEOID_PATTERNS constant tests
# =============================================================================

class TestGEOIDPatterns:
    """Tests for the GEOID_PATTERNS regex dictionary."""

    def test_patterns_exist_for_core_levels(self):
        """GEOID_PATTERNS should have entries for all core Census levels."""
        for level in ("state", "county", "tract", "block_group", "block",
                      "place", "zcta", "cd", "sldu", "sldl", "vtd"):
            assert level in GEOID_PATTERNS, f"Missing GEOID_PATTERNS['{level}']"

    def test_state_pattern_matches_two_digits(self):
        assert GEOID_PATTERNS["state"].match("06")
        assert not GEOID_PATTERNS["state"].match("6")
        assert not GEOID_PATTERNS["state"].match("123")

    def test_county_pattern_matches_five_digits(self):
        assert GEOID_PATTERNS["county"].match("06037")
        assert not GEOID_PATTERNS["county"].match("6037")

    def test_tract_pattern_matches_eleven_digits(self):
        assert GEOID_PATTERNS["tract"].match("06037101100")
        assert not GEOID_PATTERNS["tract"].match("0603710110")

    def test_block_group_pattern_matches_twelve_digits(self):
        assert GEOID_PATTERNS["block_group"].match("060371011001")
        assert not GEOID_PATTERNS["block_group"].match("06037101100")


# =============================================================================
# validate_state_fips tests
# =============================================================================

class TestValidateStateFIPS:
    """Tests for validate_state_fips()."""

    def test_valid_california(self):
        assert validate_state_fips("06") is True

    def test_valid_texas(self):
        assert validate_state_fips("48") is True

    def test_valid_leading_zero(self):
        assert validate_state_fips("01") is True

    def test_invalid_single_digit(self):
        """Single digit without leading zero is not a valid FIPS code."""
        assert validate_state_fips("6") is False

    def test_invalid_three_digits(self):
        assert validate_state_fips("123") is False

    def test_invalid_letters(self):
        assert validate_state_fips("CA") is False

    def test_invalid_mixed(self):
        assert validate_state_fips("0A") is False

    def test_invalid_empty(self):
        assert validate_state_fips("") is False

    def test_invalid_none(self):
        assert validate_state_fips(None) is False

    def test_invalid_whitespace_only(self):
        assert validate_state_fips("  ") is False

    def test_invalid_integer_type(self):
        """Integer input should return False (must be string)."""
        assert validate_state_fips(6) is False


# =============================================================================
# validate_county_fips tests
# =============================================================================

class TestValidateCountyFIPS:
    """Tests for validate_county_fips()."""

    def test_valid_la_county(self):
        assert validate_county_fips("06037") is True

    def test_valid_cook_county(self):
        assert validate_county_fips("17031") is True

    def test_invalid_four_digits(self):
        """Missing leading zero makes it 4 digits, not valid."""
        assert validate_county_fips("6037") is False

    def test_invalid_six_digits(self):
        assert validate_county_fips("060370") is False

    def test_invalid_letters(self):
        assert validate_county_fips("CA037") is False

    def test_invalid_empty(self):
        assert validate_county_fips("") is False

    def test_invalid_none(self):
        assert validate_county_fips(None) is False


# =============================================================================
# validate_tract_geoid tests
# =============================================================================

class TestValidateTractGEOID:
    """Tests for validate_tract_geoid()."""

    def test_valid_tract(self):
        assert validate_tract_geoid("06037101100") is True

    def test_valid_tract_with_zeros(self):
        assert validate_tract_geoid("01001020100") is True

    def test_invalid_ten_digits(self):
        """10 digits is too short for a tract GEOID."""
        assert validate_tract_geoid("0603710110") is False

    def test_invalid_twelve_digits(self):
        """12 digits is a block group, not a tract."""
        assert validate_tract_geoid("060371011001") is False

    def test_invalid_five_digits(self):
        """County FIPS is not a tract GEOID."""
        assert validate_tract_geoid("06037") is False

    def test_invalid_letters(self):
        assert validate_tract_geoid("0603710110A") is False

    def test_invalid_empty(self):
        assert validate_tract_geoid("") is False

    def test_invalid_none(self):
        assert validate_tract_geoid(None) is False


# =============================================================================
# validate_block_group_geoid tests
# =============================================================================

class TestValidateBlockGroupGEOID:
    """Tests for validate_block_group_geoid()."""

    def test_valid_block_group(self):
        assert validate_block_group_geoid("060371011001") is True

    def test_valid_block_group_with_zeros(self):
        assert validate_block_group_geoid("010010201001") is True

    def test_invalid_eleven_digits(self):
        """11 digits is a tract, not a block group."""
        assert validate_block_group_geoid("06037101100") is False

    def test_invalid_thirteen_digits(self):
        assert validate_block_group_geoid("0603710110012") is False

    def test_invalid_fifteen_digits(self):
        """15 digits is a block, not a block group."""
        assert validate_block_group_geoid("060371011001001") is False

    def test_invalid_letters(self):
        assert validate_block_group_geoid("06037101100A") is False

    def test_invalid_empty(self):
        assert validate_block_group_geoid("") is False

    def test_invalid_none(self):
        assert validate_block_group_geoid(None) is False


# =============================================================================
# Django validator class tests
# =============================================================================

@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="Django not available",
)
class TestStateFIPSValidator:
    """Tests for StateFIPSValidator Django validator."""

    def test_valid_fips_passes(self):
        from siege_utilities.geo.validators import StateFIPSValidator
        v = StateFIPSValidator()
        v("06")  # should not raise

    def test_invalid_fips_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import StateFIPSValidator
        v = StateFIPSValidator()
        with pytest.raises(ValidationError, match="2 digits"):
            v("6")

    def test_non_digit_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import StateFIPSValidator
        v = StateFIPSValidator()
        with pytest.raises(ValidationError, match="2 digits"):
            v("CA")

    def test_empty_string_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import StateFIPSValidator
        v = StateFIPSValidator()
        with pytest.raises(ValidationError, match="non-empty string"):
            v("")

    def test_none_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import StateFIPSValidator
        v = StateFIPSValidator()
        with pytest.raises(ValidationError, match="non-empty string"):
            v(None)

    def test_equality(self):
        from siege_utilities.geo.validators import StateFIPSValidator
        assert StateFIPSValidator() == StateFIPSValidator()

    def test_repr(self):
        from siege_utilities.geo.validators import StateFIPSValidator
        assert repr(StateFIPSValidator()) == "StateFIPSValidator()"

    def test_deconstruct(self):
        from siege_utilities.geo.validators import StateFIPSValidator
        path, args, kwargs = StateFIPSValidator().deconstruct()
        assert "StateFIPSValidator" in path
        assert args == ()
        assert kwargs == {}


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="Django not available",
)
class TestCountyFIPSValidator:
    """Tests for CountyFIPSValidator Django validator."""

    def test_valid_county_passes(self):
        from siege_utilities.geo.validators import CountyFIPSValidator
        v = CountyFIPSValidator()
        v("06037")

    def test_invalid_county_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import CountyFIPSValidator
        v = CountyFIPSValidator()
        with pytest.raises(ValidationError, match="5 digits"):
            v("6037")

    def test_equality(self):
        from siege_utilities.geo.validators import CountyFIPSValidator
        assert CountyFIPSValidator() == CountyFIPSValidator()


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="Django not available",
)
class TestTractGEOIDValidator:
    """Tests for TractGEOIDValidator Django validator."""

    def test_valid_tract_passes(self):
        from siege_utilities.geo.validators import TractGEOIDValidator
        v = TractGEOIDValidator()
        v("06037101100")

    def test_invalid_tract_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import TractGEOIDValidator
        v = TractGEOIDValidator()
        with pytest.raises(ValidationError, match="11 digits"):
            v("06037")

    def test_equality(self):
        from siege_utilities.geo.validators import TractGEOIDValidator
        assert TractGEOIDValidator() == TractGEOIDValidator()


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="Django not available",
)
class TestBlockGroupGEOIDValidator:
    """Tests for BlockGroupGEOIDValidator Django validator."""

    def test_valid_block_group_passes(self):
        from siege_utilities.geo.validators import BlockGroupGEOIDValidator
        v = BlockGroupGEOIDValidator()
        v("060371011001")

    def test_invalid_block_group_raises(self):
        from django.core.exceptions import ValidationError
        from siege_utilities.geo.validators import BlockGroupGEOIDValidator
        v = BlockGroupGEOIDValidator()
        with pytest.raises(ValidationError, match="12 digits"):
            v("06037101100")

    def test_equality(self):
        from siege_utilities.geo.validators import BlockGroupGEOIDValidator
        assert BlockGroupGEOIDValidator() == BlockGroupGEOIDValidator()

    def test_inequality_across_types(self):
        """Different validator types should not be equal."""
        from siege_utilities.geo.validators import (
            BlockGroupGEOIDValidator, TractGEOIDValidator,
        )
        assert BlockGroupGEOIDValidator() != TractGEOIDValidator()


# =============================================================================
# Lazy import tests (via siege_utilities.geo namespace)
# =============================================================================

class TestLazyImports:
    """Verify new symbols are accessible from the geo package."""

    def test_geoid_patterns_importable(self):
        from siege_utilities.geo import GEOID_PATTERNS as gp
        assert "state" in gp

    def test_validate_county_fips_importable(self):
        from siege_utilities.geo import validate_county_fips as vcf
        assert vcf("06037") is True

    def test_validate_tract_geoid_importable(self):
        from siege_utilities.geo import validate_tract_geoid as vtg
        assert vtg("06037101100") is True

    def test_validate_block_group_geoid_importable(self):
        from siege_utilities.geo import validate_block_group_geoid as vbg
        assert vbg("060371011001") is True

    @pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="Django not available")
    def test_django_validators_importable(self):
        from siege_utilities.geo import (
            StateFIPSValidator, CountyFIPSValidator,
            TractGEOIDValidator, BlockGroupGEOIDValidator,
        )
        assert StateFIPSValidator is not None
        assert CountyFIPSValidator is not None
        assert TractGEOIDValidator is not None
        assert BlockGroupGEOIDValidator is not None
