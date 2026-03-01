"""
Regression tests for su#176-180 review fixes.

Tests scope alignment (county_fips threading), alias normalization,
strict year validation, and GEOID preservation.
"""

import pytest
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box
from unittest.mock import patch, MagicMock

from siege_utilities.geo.census_api_client import (
    CensusAPIClient,
    CensusGeographyError,
)
from siege_utilities.geo.timeseries.longitudinal_data import (
    get_longitudinal_data,
    _add_geometry,
    validate_longitudinal_years,
)


# =============================================================================
# HELPERS
# =============================================================================

def _make_tract_boundaries():
    """State-wide tract boundaries with COUNTYFP column (like TIGER files)."""
    return gpd.GeoDataFrame({
        'GEOID': ['48201000100', '48201000200', '48113000100', '48113000200'],
        'COUNTYFP': ['201', '201', '113', '113'],
        'STATEFP': ['48', '48', '48', '48'],
        'NAME': ['Tract 1 Harris', 'Tract 2 Harris', 'Tract 1 Dallas', 'Tract 2 Dallas'],
        'geometry': [box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1), box(3, 0, 4, 1)],
    }, crs='EPSG:4326')


# =============================================================================
# su#179: Geography alias normalization in CensusAPIClient
# =============================================================================

class TestGeographyAliasNormalization:
    """Verify that _validate_geography returns canonical form and fetch_data uses it."""

    def test_validate_geography_returns_canonical_for_bg(self):
        client = CensusAPIClient()
        result = client._validate_geography('bg', '48', None)
        assert result == 'block_group'

    def test_validate_geography_returns_canonical_for_zip(self):
        client = CensusAPIClient()
        result = client._validate_geography('zip_code', None, None)
        assert result == 'zcta'

    def test_validate_geography_returns_canonical_for_blockgroup(self):
        client = CensusAPIClient()
        result = client._validate_geography('blockgroup', '48', None)
        assert result == 'block_group'

    def test_validate_geography_passthrough_canonical(self):
        client = CensusAPIClient()
        result = client._validate_geography('tract', '48', None)
        assert result == 'tract'

    def test_validate_geography_rejects_invalid(self):
        client = CensusAPIClient()
        with pytest.raises(CensusGeographyError):
            client._validate_geography('nonexistent', None, None)

    def test_validate_geography_rejects_unsupported_api_level(self):
        """cd is a valid geographic level but not supported by Census API."""
        client = CensusAPIClient()
        with pytest.raises(CensusGeographyError, match="does not support"):
            client._validate_geography('cd', None, None)

    def test_validate_geography_rejects_congressional_alias(self):
        """congressional_district resolves to cd, which is not API-supported."""
        client = CensusAPIClient()
        with pytest.raises(CensusGeographyError, match="does not support"):
            client._validate_geography('congressional_district', None, None)

    @patch.object(CensusAPIClient, '_get_from_cache', return_value=None)
    @patch.object(CensusAPIClient, '_make_request_with_retry')
    def test_fetch_data_normalizes_alias(self, mock_request, mock_cache):
        """fetch_data should normalize 'bg' to 'block_group' for URL construction."""
        mock_request.return_value = pd.DataFrame({
            'state': ['48'], 'county': ['201'], 'tract': ['000100'],
            'block group': ['1'], 'NAME': ['BG 1'], 'B01001_001E': ['100'],
        })
        client = CensusAPIClient()
        client.fetch_data(
            variables='B01001_001E',
            year=2020,
            geography='bg',
            state_fips='48',
            include_moe=False,
        )
        # Verify _make_request_with_retry was called with a URL containing
        # the canonical form 'block%20group'
        assert mock_request.called
        url = mock_request.call_args[0][0]
        assert 'block%20group' in url


# =============================================================================
# su#180: county_fips in _add_geometry (timeseries)
# =============================================================================

class TestTimeseriesCountyFipsScope:
    """Verify _add_geometry filters by county_fips when provided."""

    @patch('siege_utilities.geo.spatial_data.get_census_boundaries')
    def test_add_geometry_filters_by_county(self, mock_boundaries):
        mock_boundaries.return_value = _make_tract_boundaries()

        df = pd.DataFrame({
            'GEOID': ['48201000100', '48201000200'],
            'B19013_001E_2020': [50000, 60000],
        })

        result = _add_geometry(
            df=df, geography='tract', state_fips='48',
            year=2020, county_fips='201',
        )

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 2

    @patch('siege_utilities.geo.spatial_data.get_census_boundaries')
    def test_add_geometry_no_county_returns_all(self, mock_boundaries):
        mock_boundaries.return_value = _make_tract_boundaries()

        df = pd.DataFrame({
            'GEOID': ['48201000100', '48201000200', '48113000100', '48113000200'],
            'B19013_001E_2020': [50000, 60000, 70000, 80000],
        })

        result = _add_geometry(
            df=df, geography='tract', state_fips='48', year=2020,
        )

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 4


# =============================================================================
# su#178: GEOID preservation in _add_geometry merge
# =============================================================================

class TestGeoidPreservation:
    """Verify canonical GEOID from demographics is preserved through merge."""

    @patch('siege_utilities.geo.spatial_data.get_census_boundaries')
    def test_canonical_geoid_preserved(self, mock_boundaries):
        mock_boundaries.return_value = _make_tract_boundaries()

        df = pd.DataFrame({
            'GEOID': ['48201000100', '48201000200'],
            'B19013_001E_2020': [50000, 60000],
        })

        result = _add_geometry(
            df=df, geography='tract', state_fips='48', year=2020,
        )

        assert 'GEOID' in result.columns
        assert set(result['GEOID'].tolist()) == {'48201000100', '48201000200'}

    @patch('siege_utilities.geo.spatial_data.get_census_boundaries')
    def test_geoid_length_matches_geography(self, mock_boundaries):
        mock_boundaries.return_value = _make_tract_boundaries()

        df = pd.DataFrame({
            'GEOID': ['48201000100', '48201000200'],
            'B19013_001E_2020': [50000, 60000],
        })

        result = _add_geometry(
            df=df, geography='tract', state_fips='48', year=2020,
        )

        for geoid in result['GEOID'].dropna():
            assert len(str(geoid)) == 11, f"GEOID {geoid} has wrong length"

    @patch('siege_utilities.geo.spatial_data.get_census_boundaries')
    def test_no_geoid_boundary_column_in_output(self, mock_boundaries):
        mock_boundaries.return_value = _make_tract_boundaries()

        df = pd.DataFrame({
            'GEOID': ['48201000100', '48201000200'],
            'B19013_001E_2020': [50000, 60000],
        })

        result = _add_geometry(
            df=df, geography='tract', state_fips='48', year=2020,
        )

        assert 'GEOID_boundary' not in result.columns


# =============================================================================
# su#177: strict_years validation in get_longitudinal_data
# =============================================================================

class TestStrictYearsValidation:

    def test_validate_longitudinal_years_filters_invalid(self):
        valid = validate_longitudinal_years([2015, 2020, 2099], 'acs5')
        assert 2099 not in valid
        assert 2015 in valid
        assert 2020 in valid

    def test_validate_longitudinal_years_raises_on_all_invalid(self):
        with pytest.raises(ValueError, match="No valid years"):
            validate_longitudinal_years([2099, 2100], 'acs5')

    def test_strict_years_raises_on_unavailable(self):
        """strict_years=True should raise for unavailable years."""
        with pytest.raises(ValueError, match="not available"):
            get_longitudinal_data(
                variables='B19013_001E',
                years=[2015, 2099],
                geography='tract',
                state='CA',
                strict_years=True,
            )

    @patch('siege_utilities.geo.census_api_client.CensusAPIClient')
    def test_non_strict_years_skips_unavailable(self, mock_client_cls):
        """strict_years=False should skip unavailable years without error."""
        mock_client = MagicMock()
        mock_client.fetch_data.return_value = pd.DataFrame({
            'GEOID': ['06037010100'],
            'NAME': ['Tract 1'],
            'B19013_001E': [50000],
        })
        mock_client_cls.return_value = mock_client

        result = get_longitudinal_data(
            variables='B19013_001E',
            years=[2020, 2099],
            geography='tract',
            state='CA',
            strict_years=False,
            normalize_boundaries=False,
            include_geometry=False,
        )

        # Should only have fetched for 2020 (2099 filtered out)
        assert mock_client.fetch_data.call_count == 1

    @patch('siege_utilities.geo.census_api_client.CensusAPIClient')
    def test_strict_years_raises_on_fetch_failure(self, mock_client_cls):
        """strict_years=True should raise when a fetch fails."""
        mock_client = MagicMock()
        mock_client.fetch_data.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError, match="Failed to fetch data for year"):
            get_longitudinal_data(
                variables='B19013_001E',
                years=[2020],
                geography='tract',
                state='CA',
                strict_years=True,
                normalize_boundaries=False,
                include_geometry=False,
            )
