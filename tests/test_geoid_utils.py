"""
Unit tests for GEOID utilities.

Tests the geoid_utils module for GEOID construction, normalization, parsing, and validation.
"""

import pytest
import pandas as pd

from siege_utilities.geo.geoid_utils import (
    GEOID_LENGTHS,
    GEOID_COMPONENT_LENGTHS,
    normalize_geoid,
    normalize_geoid_column,
    construct_geoid,
    construct_geoid_from_row,
    parse_geoid,
    extract_parent_geoid,
    validate_geoid,
    can_normalize_geoid,
    validate_geoid_column,
    prepare_geoid_for_join,
    find_geoid_column,
)


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestGEOIDConstants:
    """Tests for GEOID length constants."""

    def test_state_geoid_length(self):
        """Test state GEOID length is 2."""
        assert GEOID_LENGTHS['state'] == 2

    def test_county_geoid_length(self):
        """Test county GEOID length is 5."""
        assert GEOID_LENGTHS['county'] == 5

    def test_tract_geoid_length(self):
        """Test tract GEOID length is 11."""
        assert GEOID_LENGTHS['tract'] == 11

    def test_block_group_geoid_length(self):
        """Test block group GEOID length is 12."""
        assert GEOID_LENGTHS['block_group'] == 12


# =============================================================================
# NORMALIZATION TESTS
# =============================================================================

class TestNormalizeGEOID:
    """Tests for GEOID normalization."""

    def test_normalize_short_state_fips(self):
        """Test normalizing short state FIPS code."""
        assert normalize_geoid("6", "state") == "06"

    def test_normalize_correct_state_fips(self):
        """Test that correct state FIPS is unchanged."""
        assert normalize_geoid("06", "state") == "06"

    def test_normalize_short_county_fips(self):
        """Test normalizing short county FIPS code."""
        assert normalize_geoid("6037", "county") == "06037"

    def test_normalize_correct_county_fips(self):
        """Test that correct county FIPS is unchanged."""
        assert normalize_geoid("06037", "county") == "06037"

    def test_normalize_short_tract(self):
        """Test normalizing short tract code."""
        assert normalize_geoid("6037101100", "tract") == "06037101100"

    def test_normalize_integer_input(self):
        """Test normalizing integer input."""
        assert normalize_geoid(6, "state") == "06"
        assert normalize_geoid(6037, "county") == "06037"

    def test_normalize_invalid_geography(self):
        """Test that invalid geography raises error."""
        with pytest.raises(ValueError, match="Unrecognized geographic level"):
            normalize_geoid("06", "invalid_level")


class TestNormalizeGEOIDColumn:
    """Tests for column-wise GEOID normalization."""

    def test_normalize_column(self):
        """Test normalizing a DataFrame column."""
        df = pd.DataFrame({'geoid': ['6', '12', '48']})
        result = normalize_geoid_column(df, 'geoid', 'state')
        assert list(result['geoid']) == ['06', '12', '48']

    def test_normalize_column_inplace(self):
        """Test in-place column normalization."""
        df = pd.DataFrame({'geoid': ['6037', '6073']})
        normalize_geoid_column(df, 'geoid', 'county', inplace=True)
        assert list(df['geoid']) == ['06037', '06073']


# =============================================================================
# CONSTRUCTION TESTS
# =============================================================================

class TestConstructGEOID:
    """Tests for GEOID construction."""

    def test_construct_state_geoid(self):
        """Test constructing state GEOID."""
        assert construct_geoid("state", state="06") == "06"
        assert construct_geoid("state", state="6") == "06"

    def test_construct_county_geoid(self):
        """Test constructing county GEOID."""
        assert construct_geoid("county", state="06", county="037") == "06037"
        assert construct_geoid("county", state="6", county="37") == "06037"

    def test_construct_tract_geoid(self):
        """Test constructing tract GEOID."""
        result = construct_geoid("tract", state="06", county="037", tract="101100")
        assert result == "06037101100"

    def test_construct_block_group_geoid(self):
        """Test constructing block group GEOID."""
        result = construct_geoid(
            "block_group", state="06", county="037", tract="101100", block_group="1"
        )
        assert result == "060371011001"

    def test_construct_missing_component(self):
        """Test that missing required component raises error."""
        with pytest.raises(ValueError, match="Missing required component"):
            construct_geoid("county", state="06")  # Missing county


class TestConstructGEOIDFromRow:
    """Tests for constructing GEOID from DataFrame row."""

    def test_construct_county_from_row(self):
        """Test constructing county GEOID from row."""
        row = pd.Series({'state': '06', 'county': '037'})
        assert construct_geoid_from_row(row, 'county') == '06037'

    def test_construct_tract_from_row(self):
        """Test constructing tract GEOID from row."""
        row = pd.Series({'state': '06', 'county': '037', 'tract': '101100'})
        assert construct_geoid_from_row(row, 'tract') == '06037101100'

    def test_construct_with_space_column_name(self):
        """Test handling Census API column names with spaces."""
        row = pd.Series({'state': '06', 'county': '037', 'tract': '101100', 'block group': '1'})
        assert construct_geoid_from_row(row, 'block_group') == '060371011001'


# =============================================================================
# PARSING TESTS
# =============================================================================

class TestParseGEOID:
    """Tests for GEOID parsing."""

    def test_parse_state_geoid(self):
        """Test parsing state GEOID."""
        result = parse_geoid("06", "state")
        assert result == {'state': '06'}

    def test_parse_county_geoid(self):
        """Test parsing county GEOID."""
        result = parse_geoid("06037", "county")
        assert result == {'state': '06', 'county': '037'}

    def test_parse_tract_geoid(self):
        """Test parsing tract GEOID."""
        result = parse_geoid("06037101100", "tract")
        assert result == {'state': '06', 'county': '037', 'tract': '101100'}

    def test_parse_block_group_geoid(self):
        """Test parsing block group GEOID."""
        result = parse_geoid("060371011001", "block_group")
        assert result == {
            'state': '06',
            'county': '037',
            'tract': '101100',
            'block_group': '1'
        }


class TestExtractParentGEOID:
    """Tests for extracting parent GEOID."""

    def test_extract_state_from_county(self):
        """Test extracting state from county GEOID."""
        assert extract_parent_geoid("06037", "county", "state") == "06"

    def test_extract_county_from_tract(self):
        """Test extracting county from tract GEOID."""
        assert extract_parent_geoid("06037101100", "tract", "county") == "06037"

    def test_extract_state_from_tract(self):
        """Test extracting state from tract GEOID."""
        assert extract_parent_geoid("06037101100", "tract", "state") == "06"

    def test_extract_tract_from_block_group(self):
        """Test extracting tract from block group GEOID."""
        assert extract_parent_geoid("060371011001", "block_group", "tract") == "06037101100"


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidateGEOID:
    """Tests for GEOID validation."""

    def test_valid_state_geoid(self):
        """Test validating correct state GEOID."""
        assert validate_geoid("06", "state") is True

    def test_valid_county_geoid(self):
        """Test validating correct county GEOID."""
        assert validate_geoid("06037", "county") is True

    def test_valid_tract_geoid(self):
        """Test validating correct tract GEOID."""
        assert validate_geoid("06037101100", "tract") is True

    def test_invalid_short_geoid_default(self):
        """Test that short GEOID missing leading zeros is invalid by default."""
        assert validate_geoid("6037", "county") is False

    def test_valid_short_geoid_non_strict(self):
        """Test that short GEOID is valid in non-strict mode (normalizable)."""
        assert validate_geoid("6037", "county", strict=False) is True

    def test_invalid_short_geoid_strict(self):
        """Test that short GEOID is invalid in strict mode."""
        assert validate_geoid("6037", "county", strict=True) is False

    def test_invalid_non_numeric(self):
        """Test that non-numeric GEOID is invalid."""
        assert validate_geoid("CA037", "county") is False

    def test_invalid_empty(self):
        """Test that empty GEOID is invalid."""
        assert validate_geoid("", "county") is False

    def test_invalid_none(self):
        """Test that None GEOID is invalid."""
        assert validate_geoid(None, "county") is False


class TestCanNormalizeGEOID:
    """Tests for GEOID normalizability check."""

    def test_already_valid_geoid(self):
        """Test that a properly formatted GEOID is normalizable."""
        assert can_normalize_geoid("06037", "county") is True

    def test_short_geoid_normalizable(self):
        """Test that a short all-digits value can be zero-padded."""
        assert can_normalize_geoid("6037", "county") is True

    def test_integer_normalizable(self):
        """Test that integer values are normalizable."""
        assert can_normalize_geoid(6037, "county") is True
        assert can_normalize_geoid(6, "state") is True

    def test_too_long_not_normalizable(self):
        """Test that values too long for geography are not normalizable."""
        assert can_normalize_geoid("123456", "county") is False

    def test_non_numeric_not_normalizable(self):
        """Test that non-numeric values are not normalizable."""
        assert can_normalize_geoid("CA037", "county") is False

    def test_empty_not_normalizable(self):
        """Test that empty string is not normalizable."""
        assert can_normalize_geoid("", "county") is False

    def test_unknown_geography(self):
        """Test that unknown geography level returns False."""
        assert can_normalize_geoid("06037", "invalid_level") is False


class TestValidateGEOIDColumn:
    """Tests for column-wise GEOID validation."""

    def test_validate_column(self):
        """Test validating a DataFrame column."""
        df = pd.DataFrame({'geoid': ['06037', '06073', 'invalid']})
        result = validate_geoid_column(df, 'geoid', 'county')
        assert list(result) == [True, True, False]


# =============================================================================
# JOINING HELPERS TESTS
# =============================================================================

class TestFindGEOIDColumn:
    """Tests for GEOID column detection."""

    def test_find_geoid_column(self):
        """Test finding GEOID column."""
        df = pd.DataFrame({'GEOID': ['06037'], 'name': ['LA County']})
        assert find_geoid_column(df) == 'GEOID'

    def test_find_geoid_column_lowercase(self):
        """Test finding lowercase geoid column."""
        df = pd.DataFrame({'geoid': ['06037'], 'name': ['LA County']})
        assert find_geoid_column(df) == 'geoid'

    def test_find_geoid20_column(self):
        """Test finding GEOID20 column."""
        df = pd.DataFrame({'GEOID20': ['06037'], 'name': ['LA County']})
        assert find_geoid_column(df) == 'GEOID20'

    def test_find_fips_column(self):
        """Test finding FIPS column."""
        df = pd.DataFrame({'FIPS': ['06037'], 'name': ['LA County']})
        assert find_geoid_column(df) == 'FIPS'

    def test_not_found(self):
        """Test when no GEOID column exists."""
        df = pd.DataFrame({'code': ['06037'], 'name': ['LA County']})
        assert find_geoid_column(df) is None


class TestPrepareGEOIDForJoin:
    """Tests for join preparation."""

    def test_prepare_for_join(self):
        """Test preparing GEOID column for joining."""
        df = pd.DataFrame({'geoid': ['6037', '6073']})
        result = prepare_geoid_for_join(df, 'geoid', 'county')
        assert list(result['geoid']) == ['06037', '06073']

    def test_prepare_with_output_column(self):
        """Test preparing with different output column."""
        df = pd.DataFrame({'fips': ['6037']})
        result = prepare_geoid_for_join(df, 'fips', 'county', output_column='GEOID')
        assert 'GEOID' in result.columns
        assert result['GEOID'].iloc[0] == '06037'
