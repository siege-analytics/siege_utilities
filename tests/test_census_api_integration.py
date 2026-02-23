"""
Integration tests for Census API client.

These tests make actual calls to the Census Bureau API and require:
1. Network connectivity
2. Optionally, a CENSUS_API_KEY environment variable for better rate limits

Run these tests with:
    pytest tests/test_census_api_integration.py -v

Or run with API key:
    CENSUS_API_KEY=your_key pytest tests/test_census_api_integration.py -v

To skip integration tests when running the full suite:
    pytest --ignore=tests/test_census_api_integration.py
"""

import pytest
import pandas as pd
import os
from datetime import datetime

from siege_utilities.geo.census_api_client import (
    CensusAPIClient,
    CensusAPIError,
    CensusGeographyError,
    VARIABLE_GROUPS,
    get_demographics,
    get_population,
    get_income_data,
    get_education_data,
    get_housing_data,
)


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Skip integration tests if explicitly disabled
SKIP_INTEGRATION = os.environ.get('SKIP_CENSUS_INTEGRATION_TESTS', 'false').lower() == 'true'

# Test year - use a recent year that should have stable data
TEST_YEAR = 2022

# Test state - California (FIPS 06)
TEST_STATE_FIPS = '06'
TEST_STATE_ABBREV = 'CA'
TEST_STATE_NAME = 'California'

# Test county - Los Angeles County (FIPS 037)
TEST_COUNTY_FIPS = '037'


@pytest.fixture(scope='module')
def integration_client():
    """Create a Census API client for integration testing."""
    return CensusAPIClient()


# =============================================================================
# BASIC CONNECTIVITY TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestBasicConnectivity:
    """Tests for basic API connectivity."""

    def test_api_reachable(self, integration_client):
        """Test that the Census API is reachable."""
        # Fetch a minimal dataset
        df = integration_client.fetch_data(
            variables=['B01001_001E'],
            year=TEST_YEAR,
            dataset='acs5',
            geography='state',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert 'GEOID' in df.columns
        assert 'NAME' in df.columns

    def test_state_data_retrieval(self, integration_client):
        """Test retrieving state-level data."""
        df = integration_client.fetch_data(
            variables=['B01001_001E'],
            year=TEST_YEAR,
            dataset='acs5',
            geography='state',
            include_moe=False
        )

        # Should have multiple states
        assert len(df) > 40  # US has 50 states + territories

    def test_variable_metadata_available(self, integration_client):
        """Test that variable metadata can be retrieved."""
        # List variables with search
        df = integration_client.list_available_variables(
            year=TEST_YEAR,
            dataset='acs5',
            search='population'
        )

        assert isinstance(df, pd.DataFrame)
        # Should find some population-related variables
        assert len(df) > 0


# =============================================================================
# GEOGRAPHY LEVEL TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestGeographyLevels:
    """Tests for different geography levels."""

    def test_state_level_data(self, integration_client):
        """Test fetching state-level data."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='state',
            include_moe=True
        )

        assert not df.empty
        # State GEOID is 2 digits
        assert all(len(str(geoid)) == 2 for geoid in df['GEOID'])

    def test_county_level_data_all_states(self, integration_client):
        """Test fetching county-level data for all states."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            include_moe=False
        )

        assert not df.empty
        # US has ~3000 counties
        assert len(df) > 2500
        # County GEOID is 5 digits
        assert all(len(str(geoid)) == 5 for geoid in df['GEOID'])

    def test_county_level_data_single_state(self, integration_client):
        """Test fetching county-level data for a single state."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )

        assert not df.empty
        # California has 58 counties
        assert len(df) == 58
        # All GEOIDs should start with California's FIPS
        assert all(str(geoid).startswith('06') for geoid in df['GEOID'])

    def test_tract_level_data(self, integration_client):
        """Test fetching tract-level data for a county."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='tract',
            state_fips=TEST_STATE_FIPS,
            county_fips=TEST_COUNTY_FIPS,
            include_moe=True
        )

        assert not df.empty
        # LA County has thousands of tracts
        assert len(df) > 1000
        # Tract GEOID is 11 digits
        assert all(len(str(geoid)) == 11 for geoid in df['GEOID'])
        # All should be in LA County
        assert all(str(geoid).startswith('06037') for geoid in df['GEOID'])

    def test_block_group_level_data(self, integration_client):
        """Test fetching block group-level data for a county."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='block_group',
            state_fips=TEST_STATE_FIPS,
            county_fips=TEST_COUNTY_FIPS,
            include_moe=True
        )

        assert not df.empty
        # LA County has many block groups
        assert len(df) > 3000
        # Block group GEOID is 12 digits
        assert all(len(str(geoid)) == 12 for geoid in df['GEOID'])


# =============================================================================
# VARIABLE GROUP TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestVariableGroups:
    """Tests for predefined variable groups."""

    def test_demographics_basic_group(self, integration_client):
        """Test fetching demographics_basic variable group."""
        df = integration_client.fetch_data(
            variables='demographics_basic',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=True
        )

        assert not df.empty
        # Should have demographic columns
        assert 'B01001_001E' in df.columns  # Total population
        assert 'B01002_001E' in df.columns  # Median age
        # Should have MOE columns
        assert 'B01001_001M' in df.columns

    def test_income_group(self, integration_client):
        """Test fetching income variable group."""
        df = integration_client.fetch_data(
            variables='income',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=True
        )

        assert not df.empty
        # Should have income columns
        assert 'B19013_001E' in df.columns  # Median household income
        assert 'B19301_001E' in df.columns  # Per capita income

    def test_education_group(self, integration_client):
        """Test fetching education variable group."""
        df = integration_client.fetch_data(
            variables='education',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=True
        )

        assert not df.empty
        # Should have education columns
        assert 'B15003_001E' in df.columns  # Population 25+
        assert 'B15003_022E' in df.columns  # Bachelor's degree

    def test_housing_group(self, integration_client):
        """Test fetching housing variable group."""
        df = integration_client.fetch_data(
            variables='housing',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=True
        )

        assert not df.empty
        # Should have housing columns
        assert 'B25001_001E' in df.columns  # Total housing units
        assert 'B25077_001E' in df.columns  # Median home value

    def test_race_ethnicity_group(self, integration_client):
        """Test fetching race_ethnicity variable group."""
        df = integration_client.fetch_data(
            variables='race_ethnicity',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=True
        )

        assert not df.empty
        # Should have race columns
        assert 'B02001_002E' in df.columns  # White alone
        assert 'B03001_003E' in df.columns  # Hispanic or Latino


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestConvenienceFunctions:
    """Tests for convenience functions with real API calls."""

    def test_get_demographics_by_state_name(self):
        """Test get_demographics with state name."""
        df = get_demographics(
            state='California',
            geography='county',
            year=TEST_YEAR,
            variables='demographics_basic'
        )

        assert not df.empty
        assert len(df) == 58  # California counties

    def test_get_demographics_by_abbreviation(self):
        """Test get_demographics with state abbreviation."""
        df = get_demographics(
            state='CA',
            geography='county',
            year=TEST_YEAR,
            variables='demographics_basic'
        )

        assert not df.empty

    def test_get_demographics_by_fips(self):
        """Test get_demographics with FIPS code."""
        df = get_demographics(
            state='06',
            geography='county',
            year=TEST_YEAR,
            variables='demographics_basic'
        )

        assert not df.empty

    def test_get_population(self):
        """Test get_population convenience function."""
        df = get_population(
            state='California',
            geography='tract',
            year=TEST_YEAR
        )

        assert not df.empty
        assert 'B01001_001E' in df.columns
        # California has thousands of tracts
        assert len(df) > 5000

    def test_get_income_data(self):
        """Test get_income_data convenience function."""
        df = get_income_data(
            state='California',
            geography='county',
            year=TEST_YEAR
        )

        assert not df.empty
        assert 'B19013_001E' in df.columns
        assert len(df) == 58

    def test_get_education_data(self):
        """Test get_education_data convenience function."""
        df = get_education_data(
            state='California',
            geography='county',
            year=TEST_YEAR
        )

        assert not df.empty
        assert 'B15003_022E' in df.columns  # Bachelor's degree

    def test_get_housing_data(self):
        """Test get_housing_data convenience function."""
        df = get_housing_data(
            state='California',
            geography='county',
            year=TEST_YEAR
        )

        assert not df.empty
        assert 'B25001_001E' in df.columns  # Total housing units


# =============================================================================
# DATA QUALITY TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestDataQuality:
    """Tests for data quality and consistency."""

    def test_numeric_columns_are_numeric(self, integration_client):
        """Test that numeric columns are properly typed."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=True
        )

        # Population should be numeric
        assert pd.api.types.is_numeric_dtype(df['B01001_001E'])
        # MOE should be numeric
        assert pd.api.types.is_numeric_dtype(df['B01001_001M'])

    def test_geoid_format_consistency(self, integration_client):
        """Test that GEOIDs have consistent format."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )

        # All county GEOIDs should be 5 characters
        assert all(len(str(geoid)) == 5 for geoid in df['GEOID'])
        # All should start with state FIPS
        assert all(str(geoid).startswith(TEST_STATE_FIPS) for geoid in df['GEOID'])

    def test_population_values_reasonable(self, integration_client):
        """Test that population values are reasonable."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )

        # No negative populations
        assert all(df['B01001_001E'] >= 0)
        # California's smallest county is Alpine with ~1,200 people
        # Largest is LA with ~10 million
        assert df['B01001_001E'].min() > 500
        assert df['B01001_001E'].max() > 5000000

    def test_name_column_has_values(self, integration_client):
        """Test that NAME column has meaningful values."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )

        # All names should be non-empty
        assert all(df['NAME'].str.len() > 0)
        # Should contain "County"
        assert all('County' in name for name in df['NAME'])


# =============================================================================
# CACHING TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestCachingIntegration:
    """Tests for caching behavior with real API calls."""

    def test_second_request_uses_cache(self, integration_client):
        """Test that repeated requests use cache."""
        import time

        # First request
        start1 = time.time()
        df1 = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )
        time1 = time.time() - start1

        # Second request (should be cached)
        start2 = time.time()
        df2 = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips=TEST_STATE_FIPS,
            include_moe=False
        )
        time2 = time.time() - start2

        # Both should return same data
        assert len(df1) == len(df2)
        pd.testing.assert_frame_equal(df1, df2)

        # Second request should be much faster (cached)
        # Note: This is a soft assertion - cache should be at least 10x faster
        if time1 > 0.5:  # Only check if first request took significant time
            assert time2 < time1 / 2


# =============================================================================
# MULTIPLE STATES TESTS
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestMultipleStates:
    """Tests for data from multiple states."""

    def test_multiple_states_different_results(self, integration_client):
        """Test that different states return different data."""
        ca_df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips='06',  # California
            include_moe=False
        )

        tx_df = integration_client.fetch_data(
            variables='total_population',
            year=TEST_YEAR,
            dataset='acs5',
            geography='county',
            state_fips='48',  # Texas
            include_moe=False
        )

        # Different number of counties
        assert len(ca_df) == 58  # California
        assert len(tx_df) == 254  # Texas

        # Different GEOID prefixes
        assert all(str(g).startswith('06') for g in ca_df['GEOID'])
        assert all(str(g).startswith('48') for g in tx_df['GEOID'])


# =============================================================================
# INTEGRATION WITH GEOMETRY (Issue #14 prep)
# =============================================================================

@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestGeometryIntegrationPrep:
    """Tests to verify data is suitable for joining with geometries."""

    def test_geoid_format_matches_tiger(self, integration_client):
        """Test that GEOID format matches expected TIGER/Line format."""
        # Get demographic data
        df = integration_client.fetch_data(
            variables='total_population',
            year=2020,  # Use 2020 to match common TIGER vintages
            dataset='acs5',
            geography='county',
            state_fips='06',
            include_moe=False
        )

        # GEOID should be string type
        assert df['GEOID'].dtype == 'object' or df['GEOID'].dtype == 'string'

        # Should be exactly 5 characters for counties
        assert all(len(str(g)) == 5 for g in df['GEOID'])

    def test_tract_geoid_matches_tiger_format(self, integration_client):
        """Test that tract GEOID format matches TIGER/Line."""
        df = integration_client.fetch_data(
            variables='total_population',
            year=2020,
            dataset='acs5',
            geography='tract',
            state_fips='06',
            county_fips='037',  # LA County
            include_moe=False
        )

        # Tract GEOID should be 11 characters
        assert all(len(str(g)) == 11 for g in df['GEOID'])
        # Format: state(2) + county(3) + tract(6)
        sample_geoid = str(df['GEOID'].iloc[0])
        assert sample_geoid[:2] == '06'  # State
        assert sample_geoid[2:5] == '037'  # County
        assert len(sample_geoid[5:]) == 6  # Tract

    def test_data_has_joinable_columns(self, integration_client):
        """Test that data has columns suitable for joining."""
        df = integration_client.fetch_data(
            variables='demographics_basic',
            year=2020,
            dataset='acs5',
            geography='county',
            state_fips='06',
            include_moe=False
        )

        # Must have GEOID for joining
        assert 'GEOID' in df.columns

        # GEOID should be unique (no duplicates)
        assert df['GEOID'].nunique() == len(df)

        # Should have no null GEOIDs
        assert df['GEOID'].isna().sum() == 0
