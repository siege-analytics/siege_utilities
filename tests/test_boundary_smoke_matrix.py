"""
Boundary smoke matrix: parametrized integration tests for Census boundary retrieval.

Tests year × geographic_level × state combinations to validate that the full
fetch_geographic_boundaries pipeline works end-to-end. These require network
access and are marked @pytest.mark.integration.

Run with: pytest -m integration tests/test_boundary_smoke_matrix.py -v
"""

import pytest
from unittest.mock import patch

from siege_utilities.geo.boundary_result import (
    BoundaryConfigurationError,
)


# ---------------------------------------------------------------------------
# Integration matrix (requires network)
# ---------------------------------------------------------------------------

YEARS = [2020, 2023]
GEO_LEVELS = ["state", "county", "tract"]
STATES = ["06", "36", "48"]  # CA, NY, TX


@pytest.mark.integration
class TestBoundarySmokeMatrix:
    """End-to-end boundary retrieval for key year×geo×state combos."""

    @pytest.mark.parametrize("year", YEARS)
    @pytest.mark.parametrize("geo_level", ["state", "county"])
    @pytest.mark.parametrize("state_fips", ["06", "36"])
    def test_national_boundary_retrieval(self, year, geo_level, state_fips):
        """National-only types (state, county) should succeed and filter to state."""
        from siege_utilities.geo.spatial_data import CensusDataSource
        source = CensusDataSource()
        result = source.fetch_geographic_boundaries(
            year=year, geographic_level=geo_level, state_fips=state_fips,
        )
        assert result.success, f"Failed: {result.error_stage}: {result.message}"
        assert result.geodataframe is not None
        assert len(result.geodataframe) > 0
        # Verify expected columns
        gdf = result.geodataframe
        assert "geometry" in gdf.columns or gdf.geometry is not None

    @pytest.mark.parametrize("year", YEARS)
    @pytest.mark.parametrize("state_fips", ["06", "36"])
    def test_tract_retrieval(self, year, state_fips):
        """Tracts (state-required) should succeed for given state."""
        from siege_utilities.geo.spatial_data import CensusDataSource
        source = CensusDataSource()
        result = source.fetch_geographic_boundaries(
            year=year, geographic_level="tract", state_fips=state_fips,
        )
        assert result.success, f"Failed: {result.error_stage}: {result.message}"
        assert len(result.geodataframe) > 0

    @pytest.mark.parametrize("state_fips", STATES)
    def test_state_fips_filtering(self, state_fips):
        """State FIPS filtering returns only the requested state's records."""
        from siege_utilities.geo.spatial_data import CensusDataSource
        source = CensusDataSource()
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level="county", state_fips=state_fips,
        )
        assert result.success
        gdf = result.geodataframe
        # Find the STATEFP column
        fips_col = None
        for col in ["STATEFP", "statefp", "STATEFP20", "statefp20"]:
            if col in gdf.columns:
                fips_col = col
                break
        assert fips_col is not None, f"No STATEFP column in {gdf.columns.tolist()}"
        assert all(gdf[fips_col] == state_fips), (
            f"Expected all STATEFP == '{state_fips}', got: {gdf[fips_col].unique()}"
        )


# ---------------------------------------------------------------------------
# Error path tests (no network needed)
# ---------------------------------------------------------------------------

class TestBoundaryErrorPaths:
    """Validate error reporting for invalid inputs."""

    @patch('siege_utilities.geo.spatial_data.CensusDirectoryDiscovery')
    def _make_source(self, MockDiscovery):
        mock_disc = MockDiscovery.return_value
        mock_disc.get_available_years.return_value = [2020, 2024]
        mock_disc.discover_boundary_types.return_value = {
            'county': 'COUNTY', 'tract': 'TRACT', 'state': 'STATE',
        }
        mock_disc.get_optimal_year.return_value = 2020

        from siege_utilities.geo.spatial_data import CensusDataSource
        source = CensusDataSource.__new__(CensusDataSource)
        source.name = "Census Bureau"
        source.base_url = "https://www2.census.gov/geo/tiger"
        source.api_key = None
        source.user_config = {}
        source.discovery = mock_disc
        source.available_years = [2020, 2024]
        source.state_required_levels = ['tract', 'block_group', 'block', 'tabblock20', 'sldu', 'sldl']
        source.national_levels = ['nation', 'state', 'county', 'place', 'zcta', 'cd']
        return source

    def test_invalid_state_fips(self):
        """Invalid FIPS code returns fail result at input_validation stage."""
        source = self._make_source()
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='county', state_fips='ZZ',
        )
        assert not result.success
        assert result.error_stage == "input_validation"
        assert result.error_code == "INVALID_STATE_IDENTIFIER"

    def test_invalid_geographic_level(self):
        """Non-existent geographic level returns fail result at input_validation."""
        source = self._make_source()
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='unicorn',
        )
        assert not result.success
        assert result.error_stage == "input_validation"

    def test_configuration_error_propagated(self):
        """BoundaryConfigurationError from URL construction propagates correctly."""
        source = self._make_source()
        # Patch _validate_census_parameters to let cd through to URL construction
        with patch.object(source, '_validate_census_parameters'):
            source.discovery.construct_download_url.side_effect = BoundaryConfigurationError(
                "Missing congress number",
                context={"boundary_type": "cd", "year": 2020},
            )
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='cd',
            )
        assert not result.success
        assert result.error_stage == "configuration"

    def test_numeric_state_fips(self):
        """Numeric string '99' that's not a real state fails gracefully."""
        source = self._make_source()
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='county', state_fips='99',
        )
        assert not result.success
        assert result.error_stage == "input_validation"
