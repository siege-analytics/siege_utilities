"""
Unit tests for Census API client.

Tests the CensusAPIClient class and convenience functions with mocked responses.
"""

import pytest
import pandas as pd
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


def _has_pyarrow():
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False

from siege_utilities.geo.census_api_client import (
    CensusAPIClient,
    CensusAPIError,
    CensusAPIKeyError,
    CensusRateLimitError,
    CensusVariableError,
    CensusGeographyError,
    VARIABLE_GROUPS,
    VARIABLE_DESCRIPTIONS,
    get_demographics,
    get_population,
    get_income_data,
    get_education_data,
    get_housing_data,
    get_census_api_client,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def census_client(temp_cache_dir):
    """Create a CensusAPIClient with a temporary cache directory."""
    return CensusAPIClient(cache_dir=temp_cache_dir)


@pytest.fixture
def census_client_with_key(temp_cache_dir):
    """Create a CensusAPIClient with an API key."""
    return CensusAPIClient(api_key='test_api_key_12345', cache_dir=temp_cache_dir)


@pytest.fixture
def mock_census_response():
    """Create a mock Census API response."""
    # Census API returns list of lists, first row is headers
    return [
        ['NAME', 'B01001_001E', 'state', 'county'],
        ['Los Angeles County, California', '10081570', '06', '037'],
        ['San Diego County, California', '3298634', '06', '073'],
        ['Orange County, California', '3186989', '06', '059'],
    ]


@pytest.fixture
def mock_tract_response():
    """Create a mock Census API response for tract-level data."""
    return [
        ['NAME', 'B01001_001E', 'B01001_001M', 'state', 'county', 'tract'],
        ['Census Tract 101, Los Angeles County, California', '4532', '150', '06', '037', '010100'],
        ['Census Tract 102, Los Angeles County, California', '3876', '140', '06', '037', '010200'],
        ['Census Tract 103, Los Angeles County, California', '5210', '180', '06', '037', '010300'],
    ]


@pytest.fixture
def mock_state_response():
    """Create a mock Census API response for state-level data."""
    return [
        ['NAME', 'B01001_001E', 'state'],
        ['California', '39512223', '06'],
        ['Texas', '28995881', '48'],
        ['Florida', '21538187', '12'],
    ]


# =============================================================================
# CLIENT INITIALIZATION TESTS
# =============================================================================

class TestCensusAPIClientInit:
    """Tests for CensusAPIClient initialization."""

    def test_init_without_api_key(self, temp_cache_dir):
        """Test client initialization without an API key."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CENSUS_API_KEY", None)
            client = CensusAPIClient(cache_dir=temp_cache_dir)
            assert client.api_key is None
            assert client.cache_dir == temp_cache_dir

    def test_init_with_explicit_api_key(self, temp_cache_dir):
        """Test client initialization with an explicit API key."""
        client = CensusAPIClient(api_key='my_api_key', cache_dir=temp_cache_dir)
        assert client.api_key == 'my_api_key'

    def test_init_with_env_api_key(self, temp_cache_dir):
        """Test client initialization with environment variable API key."""
        with patch.dict(os.environ, {'CENSUS_API_KEY': 'env_api_key'}):
            client = CensusAPIClient(cache_dir=temp_cache_dir)
            assert client.api_key == 'env_api_key'

    def test_explicit_key_takes_precedence(self, temp_cache_dir):
        """Test that explicit API key takes precedence over environment variable."""
        with patch.dict(os.environ, {'CENSUS_API_KEY': 'env_api_key'}):
            client = CensusAPIClient(api_key='explicit_key', cache_dir=temp_cache_dir)
            assert client.api_key == 'explicit_key'

    def test_init_creates_cache_dir(self):
        """Test that initialization creates the cache directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / 'census_cache'
            assert not cache_path.exists()
            client = CensusAPIClient(cache_dir=cache_path)
            assert cache_path.exists()

    def test_init_with_custom_timeout(self, temp_cache_dir):
        """Test client initialization with custom timeout."""
        client = CensusAPIClient(timeout=60, cache_dir=temp_cache_dir)
        assert client.timeout == 60


# =============================================================================
# VARIABLE RESOLUTION TESTS
# =============================================================================

class TestVariableResolution:
    """Tests for variable resolution and processing."""

    def test_resolve_predefined_group(self, census_client):
        """Test resolving a predefined variable group."""
        variables = census_client._resolve_variables('demographics_basic')
        assert isinstance(variables, list)
        assert 'B01001_001E' in variables  # Total population

    def test_resolve_single_variable(self, census_client):
        """Test resolving a single variable code."""
        variables = census_client._resolve_variables('B19013_001E')
        assert variables == ['B19013_001E']

    def test_resolve_list_of_variables(self, census_client):
        """Test resolving a list of variable codes."""
        input_vars = ['B01001_001E', 'B19013_001E']
        variables = census_client._resolve_variables(input_vars)
        assert variables == input_vars

    def test_add_moe_variables(self, census_client):
        """Test adding margin of error variables."""
        variables = ['B01001_001E', 'B19013_001E']
        result = census_client._add_moe_variables(variables)
        assert 'B01001_001E' in result
        assert 'B01001_001M' in result
        assert 'B19013_001E' in result
        assert 'B19013_001M' in result

    def test_moe_not_added_for_non_estimate_vars(self, census_client):
        """Test that MOE is not added for variables not ending with E."""
        variables = ['P1_001N']  # Decennial census variable
        result = census_client._add_moe_variables(variables)
        assert 'P1_001N' in result
        # Should not have MOE version added
        assert len(result) == 1


# =============================================================================
# GEOGRAPHY VALIDATION TESTS
# =============================================================================

class TestGeographyValidation:
    """Tests for geography parameter validation."""

    def test_valid_county_geography(self, census_client):
        """Test that county geography is valid."""
        # Should not raise
        census_client._validate_geography('county', None, None)
        census_client._validate_geography('county', '06', None)
        census_client._validate_geography('county', '06', '037')

    def test_valid_tract_geography_with_state(self, census_client):
        """Test that tract geography requires state FIPS."""
        # Should not raise with state
        census_client._validate_geography('tract', '06', None)

    def test_tract_requires_state(self, census_client):
        """Test that tract geography without state raises error."""
        with pytest.raises(CensusGeographyError, match="State FIPS code is required"):
            census_client._validate_geography('tract', None, None)

    def test_block_group_requires_state(self, census_client):
        """Test that block group geography without state raises error."""
        with pytest.raises(CensusGeographyError, match="State FIPS code is required"):
            census_client._validate_geography('block_group', None, None)

    def test_invalid_geography_level(self, census_client):
        """Test that invalid geography level raises error."""
        with pytest.raises(CensusGeographyError, match="Invalid geography"):
            census_client._validate_geography('invalid_level', None, None)

    def test_county_fips_requires_state_fips(self, census_client):
        """Test that county FIPS without state FIPS raises error."""
        with pytest.raises(CensusGeographyError, match="County FIPS requires state FIPS"):
            census_client._validate_geography('county', None, '037')


# =============================================================================
# STATE NORMALIZATION TESTS
# =============================================================================

class TestStateNormalization:
    """Tests for state identifier normalization."""

    def test_normalize_fips_code(self, census_client):
        """Test normalizing FIPS code."""
        assert census_client._normalize_state('06') == '06'

    def test_normalize_abbreviation(self, census_client):
        """Test normalizing state abbreviation."""
        assert census_client._normalize_state('CA') == '06'

    def test_normalize_lowercase_abbreviation(self, census_client):
        """Test normalizing lowercase state abbreviation."""
        assert census_client._normalize_state('ca') == '06'

    def test_normalize_state_name(self, census_client):
        """Test normalizing state name."""
        assert census_client._normalize_state('California') == '06'

    def test_normalize_invalid_state(self, census_client):
        """Test that invalid state raises error."""
        with pytest.raises(CensusGeographyError):
            census_client._normalize_state('InvalidState')


# =============================================================================
# URL BUILDING TESTS
# =============================================================================

class TestURLBuilding:
    """Tests for Census API URL building."""

    def test_build_state_url(self, census_client):
        """Test building URL for state-level data."""
        url = census_client._build_url(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='state',
            state_fips=None,
            county_fips=None
        )
        assert 'api.census.gov' in url
        assert '2020/acs/acs5' in url
        assert 'B01001_001E' in url
        assert 'for=state:*' in url

    def test_build_county_url_all_states(self, census_client):
        """Test building URL for county-level data for all states."""
        url = census_client._build_url(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='county',
            state_fips=None,
            county_fips=None
        )
        assert 'for=county:*' in url

    def test_build_county_url_specific_state(self, census_client):
        """Test building URL for county-level data for specific state."""
        url = census_client._build_url(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='county',
            state_fips='06',
            county_fips=None
        )
        assert 'for=county:*' in url
        assert 'in=state:06' in url

    def test_build_tract_url(self, census_client):
        """Test building URL for tract-level data."""
        url = census_client._build_url(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='tract',
            state_fips='06',
            county_fips=None
        )
        assert 'for=tract:*' in url
        assert 'in=state:06' in url

    def test_build_url_with_api_key(self, census_client_with_key):
        """Test that API key is included in URL."""
        url = census_client_with_key._build_url(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='state',
            state_fips=None,
            county_fips=None
        )
        assert 'key=test_api_key_12345' in url

    def test_build_url_acs1_dataset(self, census_client):
        """Test building URL for ACS 1-year dataset."""
        url = census_client._build_url(
            variables=['B01001_001E'],
            year=2021,
            dataset='acs1',
            geography='state',
            state_fips=None,
            county_fips=None
        )
        assert '2021/acs/acs1' in url


# =============================================================================
# GEOID CONSTRUCTION TESTS
# =============================================================================

class TestGEOIDConstruction:
    """Tests for GEOID column construction."""

    def test_construct_state_geoid(self, census_client):
        """Test constructing GEOID for state-level data."""
        df = pd.DataFrame({
            'NAME': ['California'],
            'B01001_001E': ['39512223'],
            'state': ['06']
        })
        result = census_client._construct_geoid(df, 'state')
        assert result['GEOID'].iloc[0] == '06'

    def test_construct_county_geoid(self, census_client):
        """Test constructing GEOID for county-level data."""
        df = pd.DataFrame({
            'NAME': ['Los Angeles County'],
            'B01001_001E': ['10081570'],
            'state': ['06'],
            'county': ['037']
        })
        result = census_client._construct_geoid(df, 'county')
        assert result['GEOID'].iloc[0] == '06037'

    def test_construct_tract_geoid(self, census_client):
        """Test constructing GEOID for tract-level data."""
        df = pd.DataFrame({
            'NAME': ['Census Tract 101'],
            'B01001_001E': ['4532'],
            'state': ['06'],
            'county': ['037'],
            'tract': ['010100']
        })
        result = census_client._construct_geoid(df, 'tract')
        assert result['GEOID'].iloc[0] == '06037010100'

    def test_construct_block_group_geoid(self, census_client):
        """Test constructing GEOID for block group data."""
        df = pd.DataFrame({
            'NAME': ['Block Group 1'],
            'B01001_001E': ['1234'],
            'state': ['06'],
            'county': ['037'],
            'tract': ['010100'],
            'block group': ['1']
        })
        result = census_client._construct_geoid(df, 'block_group')
        assert result['GEOID'].iloc[0] == '060370101001'


# =============================================================================
# DATA FETCHING TESTS (MOCKED)
# =============================================================================

class TestDataFetching:
    """Tests for data fetching with mocked responses."""

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_fetch_county_data(self, mock_get, census_client, mock_census_response):
        """Test fetching county-level data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_census_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        df = census_client.fetch_data(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='county',
            state_fips='06',
            include_moe=False
        )

        assert isinstance(df, pd.DataFrame)
        assert 'GEOID' in df.columns
        assert 'NAME' in df.columns
        assert len(df) == 3  # 3 counties

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_fetch_with_predefined_group(self, mock_get, census_client, mock_census_response):
        """Test fetching data with a predefined variable group."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_census_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        df = census_client.fetch_data(
            variables='total_population',
            year=2020,
            dataset='acs5',
            geography='county',
            state_fips='06',
            include_moe=False
        )

        assert isinstance(df, pd.DataFrame)
        assert 'GEOID' in df.columns

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_fetch_tract_data_with_moe(self, mock_get, census_client, mock_tract_response):
        """Test fetching tract-level data with margin of error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_tract_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        df = census_client.fetch_data(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='tract',
            state_fips='06',
            include_moe=True
        )

        assert isinstance(df, pd.DataFrame)
        assert 'GEOID' in df.columns
        assert len(df['GEOID'].iloc[0]) == 11  # Tract GEOID is 11 digits

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_fetch_handles_empty_response(self, mock_get, census_client):
        """Test handling of empty API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        df = census_client.fetch_data(
            variables=['B01001_001E'],
            year=2020,
            dataset='acs5',
            geography='county',
            state_fips='06',
            include_moe=False
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_fetch_handles_rate_limit(self, mock_get, census_client):
        """Test handling of rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(CensusRateLimitError):
            census_client.fetch_data(
                variables=['B01001_001E'],
                year=2020,
                dataset='acs5',
                geography='county',
                state_fips='06',
                include_moe=False
            )


# =============================================================================
# CACHING TESTS
# =============================================================================

class TestCaching:
    """Tests for response caching."""

    def test_cache_key_generation(self, census_client):
        """Test that cache keys are generated consistently."""
        key1 = census_client._generate_cache_key(
            ['B01001_001E'], 2020, 'acs5', 'county', '06', None
        )
        key2 = census_client._generate_cache_key(
            ['B01001_001E'], 2020, 'acs5', 'county', '06', None
        )
        assert key1 == key2

    def test_different_params_different_keys(self, census_client):
        """Test that different parameters produce different cache keys."""
        key1 = census_client._generate_cache_key(
            ['B01001_001E'], 2020, 'acs5', 'county', '06', None
        )
        key2 = census_client._generate_cache_key(
            ['B01001_001E'], 2021, 'acs5', 'county', '06', None
        )
        assert key1 != key2

    @pytest.mark.skipif(
        not _has_pyarrow(),
        reason="pyarrow not available (required for parquet cache)"
    )
    def test_save_and_retrieve_from_cache(self, census_client):
        """Test saving and retrieving data from cache."""
        df = pd.DataFrame({
            'GEOID': ['06037', '06073'],
            'NAME': ['LA County', 'SD County'],
            'B01001_001E': [10081570, 3298634]
        })

        cache_key = census_client._generate_cache_key(
            ['B01001_001E'], 2020, 'acs5', 'county', '06', None
        )

        # Save to cache
        census_client._save_to_cache(cache_key, df)

        # Retrieve from cache
        cached_df = census_client._get_from_cache(cache_key)

        assert cached_df is not None
        assert len(cached_df) == 2
        assert list(cached_df.columns) == list(df.columns)

    def test_cache_miss_returns_none(self, census_client):
        """Test that cache miss returns None."""
        result = census_client._get_from_cache('nonexistent_key')
        assert result is None

    def test_clear_cache(self, census_client):
        """Test clearing the cache."""
        df = pd.DataFrame({'test': [1, 2, 3]})
        census_client._save_to_cache('test_key', df)

        # Clear cache
        census_client.clear_cache()

        # Should be empty now
        result = census_client._get_from_cache('test_key')
        assert result is None


# =============================================================================
# CONVENIENCE FUNCTIONS TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('siege_utilities.geo.census_api_client.CensusAPIClient.fetch_data')
    def test_get_demographics(self, mock_fetch):
        """Test get_demographics convenience function."""
        mock_df = pd.DataFrame({
            'GEOID': ['06037'],
            'NAME': ['LA County'],
            'B01001_001E': [10081570]
        })
        mock_fetch.return_value = mock_df

        df = get_demographics(state='California', geography='county', year=2020)

        assert mock_fetch.called
        call_kwargs = mock_fetch.call_args.kwargs
        assert call_kwargs['geography'] == 'county'
        assert call_kwargs['state_fips'] == '06'

    @patch('siege_utilities.geo.census_api_client.CensusAPIClient.fetch_data')
    def test_get_population(self, mock_fetch):
        """Test get_population convenience function."""
        mock_df = pd.DataFrame({
            'GEOID': ['06037010100'],
            'NAME': ['Tract 101'],
            'B01001_001E': [4532]
        })
        mock_fetch.return_value = mock_df

        df = get_population(state='CA', geography='tract', year=2020)

        assert mock_fetch.called
        call_kwargs = mock_fetch.call_args.kwargs
        assert call_kwargs['variables'] == 'total_population'

    @patch('siege_utilities.geo.census_api_client.CensusAPIClient.fetch_data')
    def test_get_income_data(self, mock_fetch):
        """Test get_income_data convenience function."""
        mock_df = pd.DataFrame({
            'GEOID': ['06037010100'],
            'NAME': ['Tract 101'],
            'B19013_001E': [75000]
        })
        mock_fetch.return_value = mock_df

        df = get_income_data(state='06', geography='tract', year=2020)

        assert mock_fetch.called
        call_kwargs = mock_fetch.call_args.kwargs
        assert call_kwargs['variables'] == 'income'

    def test_get_census_api_client_singleton(self):
        """Test that get_census_api_client returns a reusable instance."""
        client1 = get_census_api_client()
        client2 = get_census_api_client()
        assert client1 is client2


# =============================================================================
# VARIABLE METADATA TESTS
# =============================================================================

class TestVariableMetadata:
    """Tests for variable metadata functions."""

    def test_variable_groups_not_empty(self):
        """Test that predefined variable groups are defined."""
        assert len(VARIABLE_GROUPS) > 0
        assert 'total_population' in VARIABLE_GROUPS
        assert 'demographics_basic' in VARIABLE_GROUPS
        assert 'income' in VARIABLE_GROUPS
        assert 'education' in VARIABLE_GROUPS
        assert 'housing' in VARIABLE_GROUPS

    def test_variable_descriptions_not_empty(self):
        """Test that variable descriptions are defined."""
        assert len(VARIABLE_DESCRIPTIONS) > 0
        assert 'B01001_001E' in VARIABLE_DESCRIPTIONS
        assert 'B19013_001E' in VARIABLE_DESCRIPTIONS

    def test_get_variable_metadata_local(self, census_client):
        """Test getting variable metadata from local descriptions."""
        metadata = census_client.get_variable_metadata('B01001_001E', 2020)
        assert metadata['code'] == 'B01001_001E'
        assert 'Population' in metadata['label']
        assert metadata['source'] == 'local'

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_list_available_variables(self, mock_get, census_client):
        """Test listing available variables."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'variables': {
                'B01001_001E': {'label': 'Total Population', 'concept': 'SEX BY AGE'},
                'B19013_001E': {'label': 'Median Household Income', 'concept': 'HOUSEHOLD INCOME'},
                'for': {},  # Should be filtered out
                'in': {},   # Should be filtered out
            }
        }
        mock_get.return_value = mock_response

        df = census_client.list_available_variables(2020, 'acs5')

        assert isinstance(df, pd.DataFrame)
        assert 'code' in df.columns
        assert 'label' in df.columns
        # Geography variables should be filtered out
        assert 'for' not in df['code'].values
        assert 'in' not in df['code'].values

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_list_variables_with_search(self, mock_get, census_client):
        """Test listing variables with search filter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'variables': {
                'B01001_001E': {'label': 'Total Population', 'concept': 'SEX BY AGE'},
                'B19013_001E': {'label': 'Median Household Income', 'concept': 'HOUSEHOLD INCOME'},
            }
        }
        mock_get.return_value = mock_response

        df = census_client.list_available_variables(2020, 'acs5', search='income')

        assert isinstance(df, pd.DataFrame)
        # Should only have income variable
        assert 'B19013_001E' in df['code'].values


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_dataset_raises_error(self, census_client):
        """Test that invalid dataset raises error."""
        with pytest.raises(CensusVariableError, match="Unknown dataset"):
            census_client._get_dataset_path(2020, 'invalid_dataset')

    def test_invalid_geography_raises_error(self, census_client):
        """Test that invalid geography raises error."""
        with pytest.raises(CensusGeographyError, match="Invalid geography"):
            census_client._validate_geography('invalid', None, None)

    @patch('siege_utilities.geo.census_api_client.requests.get')
    def test_timeout_handling(self, mock_get, census_client):
        """Test handling of request timeout."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(CensusAPIError, match="timed out"):
            census_client.fetch_data(
                variables=['B01001_001E'],
                year=2020,
                dataset='acs5',
                geography='county',
                state_fips='06',
                include_moe=False
            )


# =============================================================================
# INTEGRATION WITH EXISTING CODE TESTS
# =============================================================================

class TestIntegrationWithExisting:
    """Tests for integration with existing siege_utilities code."""

    def test_import_from_geo_module(self):
        """Test that client can be imported from geo module."""
        from siege_utilities.geo import CensusAPIClient, get_demographics
        assert CensusAPIClient is not None
        assert get_demographics is not None

    def test_config_constants_available(self):
        """Test that config constants are available."""
        from siege_utilities.config import (
            CENSUS_API_CACHE_TIMEOUT,
            CENSUS_API_DEFAULT_TIMEOUT,
            CENSUS_API_RATE_LIMIT_RETRY_DELAY,
        )
        assert CENSUS_API_CACHE_TIMEOUT == 86400
        assert CENSUS_API_DEFAULT_TIMEOUT == 30
        assert CENSUS_API_RATE_LIMIT_RETRY_DELAY == 60

    def test_fips_normalization_integration(self):
        """Test that FIPS normalization works with config module."""
        from siege_utilities.config import normalize_state_identifier

        assert normalize_state_identifier('CA') == '06'
        assert normalize_state_identifier('California') == '06'
        assert normalize_state_identifier('06') == '06'


# =============================================================================
# GEOID VALIDATION FROM API MOCK DATA
# =============================================================================

class TestGEOIDValidationFromAPI:
    """Verify Census API GEOID construction produces valid GEOIDs."""

    def test_state_geoid_length_from_mock(self):
        """State GEOIDs from API mock should be 2 characters."""
        from siege_utilities.geo.geoid_utils import GEOID_LENGTHS, validate_geoid
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = pd.DataFrame([{'state': '06'}, {'state': '36'}])
        result = client._construct_geoid(df, 'state')
        for geoid in result['GEOID']:
            assert len(str(geoid)) == GEOID_LENGTHS['state']
            assert validate_geoid(str(geoid), 'state')

    def test_county_geoid_length_from_mock(self):
        """County GEOIDs from API mock should be 5 characters."""
        from siege_utilities.geo.geoid_utils import GEOID_LENGTHS, validate_geoid
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = pd.DataFrame([
            {'state': '06', 'county': '037'},
            {'state': '36', 'county': '061'},
        ])
        result = client._construct_geoid(df, 'county')
        for geoid in result['GEOID']:
            assert len(str(geoid)) == GEOID_LENGTHS['county']
            assert validate_geoid(str(geoid), 'county')

    def test_tract_geoid_length_from_mock(self):
        """Tract GEOIDs from API mock should be 11 characters."""
        from siege_utilities.geo.geoid_utils import GEOID_LENGTHS, validate_geoid
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = pd.DataFrame([
            {'state': '06', 'county': '037', 'tract': '101100'},
        ])
        result = client._construct_geoid(df, 'tract')
        for geoid in result['GEOID']:
            assert len(str(geoid)) == GEOID_LENGTHS['tract']
            assert validate_geoid(str(geoid), 'tract')

    def test_geoid_column_is_string_type(self):
        """GEOID column must have string dtype after construction."""
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = pd.DataFrame([{'state': '06', 'county': '037'}])
        result = client._construct_geoid(df, 'county')
        assert result['GEOID'].dtype == 'object', (
            f"GEOID column dtype is {result['GEOID'].dtype}, expected 'object' (string)"
        )

    def test_all_mock_geoids_pass_validation(self):
        """All constructed GEOIDs from mock data must pass validate_geoid."""
        from siege_utilities.geo.geoid_utils import validate_geoid
        client = CensusAPIClient.__new__(CensusAPIClient)
        test_cases = [
            ('state', pd.DataFrame([{'state': '06'}])),
            ('county', pd.DataFrame([{'state': '06', 'county': '037'}])),
            ('tract', pd.DataFrame([{'state': '06', 'county': '037', 'tract': '101100'}])),
            ('place', pd.DataFrame([{'state': '06', 'place': '44000'}])),
        ]
        for geography, df in test_cases:
            result = client._construct_geoid(df, geography)
            geoid = result['GEOID'].iloc[0]
            assert validate_geoid(str(geoid), geography), (
                f"{geography} GEOID '{geoid}' fails validate_geoid()"
            )
