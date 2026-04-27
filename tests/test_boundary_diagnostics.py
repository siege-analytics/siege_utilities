"""
Tests for su#197: structured boundary retrieval diagnostics.

Verifies that BoundaryFetchResult and typed exceptions provide
actionable, machine-readable failure information instead of silent None returns.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from siege_utilities.geo.boundary_result import (
    BoundaryFetchResult,
    BoundaryRetrievalError,
    BoundaryInputError,
    BoundaryDiscoveryError,
    BoundaryConfigurationError,
    BoundaryUrlValidationError,
    BoundaryDownloadError,
    BoundaryParseError,
)


# ---------------------------------------------------------------------------
# BoundaryFetchResult tests
# ---------------------------------------------------------------------------

class TestBoundaryFetchResult:
    """Test the result dataclass."""

    def test_ok_result_is_truthy(self):
        mock_gdf = Mock()
        mock_gdf.__len__ = Mock(return_value=42)
        result = BoundaryFetchResult.ok(mock_gdf)
        assert result
        assert result.success is True
        assert result.geodataframe is mock_gdf
        assert result.error_code is None
        assert result.error_stage is None

    def test_fail_result_is_falsy(self):
        result = BoundaryFetchResult.fail(
            error_code="TEST_ERROR",
            error_stage="input_validation",
            message="Test failure",
        )
        assert not result
        assert result.success is False
        assert result.geodataframe is None
        assert result.error_code == "TEST_ERROR"
        assert result.error_stage == "input_validation"
        assert result.message == "Test failure"

    def test_ok_message_includes_feature_count(self):
        mock_gdf = Mock()
        mock_gdf.__len__ = Mock(return_value=100)
        result = BoundaryFetchResult.ok(mock_gdf)
        assert "100" in result.message

    def test_fail_context_preserved(self):
        ctx = {"year": 2020, "state_fips": "48", "url": "https://example.com"}
        result = BoundaryFetchResult.fail(
            error_code="X", error_stage="download", message="failed", context=ctx,
        )
        assert result.context["year"] == 2020
        assert result.context["state_fips"] == "48"

    def test_raise_on_error_success_returns_self(self):
        mock_gdf = Mock()
        mock_gdf.__len__ = Mock(return_value=1)
        result = BoundaryFetchResult.ok(mock_gdf)
        assert result.raise_on_error() is result

    def test_raise_on_error_input_validation(self):
        result = BoundaryFetchResult.fail(
            error_code="BAD_FIPS",
            error_stage="input_validation",
            message="Invalid FIPS",
        )
        with pytest.raises(BoundaryInputError) as exc_info:
            result.raise_on_error()
        assert "Invalid FIPS" in str(exc_info.value)
        assert exc_info.value.stage == "input_validation"

    def test_raise_on_error_discovery(self):
        result = BoundaryFetchResult.fail(
            error_code="NO_TYPE",
            error_stage="discovery",
            message="Not available",
        )
        with pytest.raises(BoundaryDiscoveryError):
            result.raise_on_error()

    def test_raise_on_error_url_validation(self):
        result = BoundaryFetchResult.fail(
            error_code="HTTP_404",
            error_stage="url_validation",
            message="Not found",
        )
        with pytest.raises(BoundaryUrlValidationError):
            result.raise_on_error()

    def test_raise_on_error_download(self):
        result = BoundaryFetchResult.fail(
            error_code="CORRUPT",
            error_stage="download",
            message="Bad zip",
        )
        with pytest.raises(BoundaryDownloadError):
            result.raise_on_error()

    def test_raise_on_error_parse(self):
        result = BoundaryFetchResult.fail(
            error_code="NO_SHP",
            error_stage="parse",
            message="No shapefile",
        )
        with pytest.raises(BoundaryParseError):
            result.raise_on_error()

    def test_raise_on_error_unknown_stage(self):
        result = BoundaryFetchResult.fail(
            error_code="X",
            error_stage="mystery",
            message="Unknown",
        )
        with pytest.raises(BoundaryRetrievalError):
            result.raise_on_error()

    def test_chaining_raise_on_error(self):
        mock_gdf = Mock()
        mock_gdf.__len__ = Mock(return_value=5)
        result = BoundaryFetchResult.ok(mock_gdf)
        gdf = result.raise_on_error().geodataframe
        assert gdf is mock_gdf


# ---------------------------------------------------------------------------
# Typed exception hierarchy tests
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    """Verify that all typed exceptions inherit from the base."""

    def test_all_subclass_base(self):
        for cls in [
            BoundaryInputError,
            BoundaryDiscoveryError,
            BoundaryUrlValidationError,
            BoundaryDownloadError,
            BoundaryParseError,
        ]:
            assert issubclass(cls, BoundaryRetrievalError)
            assert issubclass(cls, Exception)

    def test_exception_carries_stage(self):
        err = BoundaryInputError("bad input", context={"key": "val"})
        assert err.stage == "input_validation"
        assert err.context == {"key": "val"}

    def test_discovery_error_stage(self):
        err = BoundaryDiscoveryError("no types")
        assert err.stage == "discovery"

    def test_url_validation_error_stage(self):
        err = BoundaryUrlValidationError("http 404")
        assert err.stage == "url_validation"

    def test_download_error_stage(self):
        err = BoundaryDownloadError("bad zip")
        assert err.stage == "download"

    def test_parse_error_stage(self):
        err = BoundaryParseError("no shp")
        assert err.stage == "parse"

    def test_base_error_custom_stage(self):
        err = BoundaryRetrievalError("general", stage="custom_stage")
        assert err.stage == "custom_stage"


# ---------------------------------------------------------------------------
# Integration with CensusDataSource.fetch_geographic_boundaries
# ---------------------------------------------------------------------------

class TestFetchGeographicBoundaries:
    """Test the new fetch_geographic_boundaries method returns BoundaryFetchResult."""

    @patch('siege_utilities.geo.spatial_data.CensusDirectoryDiscovery')
    def _make_source(self, MockDiscovery):
        """Helper to create a CensusDataSource with mocked discovery."""
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

    def test_invalid_state_fips_returns_fail_result(self):
        source = self._make_source()
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='county', state_fips='ZZZZ',
        )
        assert not result.success
        assert result.error_stage == "input_validation"
        assert result.error_code == "INVALID_STATE_IDENTIFIER"
        assert "ZZZZ" in result.message

    def test_missing_state_fips_for_tract(self):
        source = self._make_source()
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='tract',
        )
        assert not result.success
        assert result.error_stage == "input_validation"
        assert result.error_code == "INVALID_PARAMETERS"

    def test_url_construction_failure(self):
        source = self._make_source()
        source.discovery.construct_download_url.side_effect = BoundaryDiscoveryError(
            "type not available", context={"year": 2020},
        )
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='county',
        )
        assert not result.success
        assert result.error_stage == "discovery"

    def test_url_validation_failure(self):
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/bad.zip"
        source.discovery.validate_download_url.side_effect = BoundaryUrlValidationError(
            "HTTP 404", context={"http_status": 404},
        )
        result = source.fetch_geographic_boundaries(
            year=2020, geographic_level='county',
        )
        assert not result.success
        assert result.error_stage == "url_validation"
        assert result.error_code == "URL_NOT_ACCESSIBLE"

    def test_download_failure(self):
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/ok.zip"
        source.discovery.validate_download_url.return_value = True

        with patch.object(source, '_download_and_process_tiger') as mock_dl:
            mock_dl.side_effect = BoundaryDownloadError(
                "bad zip", context={"error_code": "INVALID_ZIP"},
            )
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county',
            )
        assert not result.success
        assert result.error_stage == "download"

    def test_parse_failure(self):
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/ok.zip"
        source.discovery.validate_download_url.return_value = True

        with patch.object(source, '_download_and_process_tiger') as mock_dl:
            mock_dl.side_effect = BoundaryParseError(
                "no shapefile", context={"error_code": "NO_SHAPEFILE"},
            )
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county',
            )
        assert not result.success
        assert result.error_stage == "parse"

    def test_success_returns_ok_result(self):
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/ok.zip"
        source.discovery.validate_download_url.return_value = True

        mock_gdf = Mock()
        mock_gdf.__len__ = Mock(return_value=50)

        with patch.object(source, '_download_and_process_tiger', return_value=mock_gdf):
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county',
            )
        assert result.success
        assert result.geodataframe is mock_gdf
        assert "50" in result.message
        assert result.error_code is None

    def test_context_carries_all_parameters(self):
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/ok.zip"
        source.discovery.validate_download_url.return_value = True

        mock_gdf = Mock()
        mock_gdf.__len__ = Mock(return_value=10)

        with patch.object(source, '_download_and_process_tiger', return_value=mock_gdf):
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county', state_fips='48',
            )
        assert result.context["year"] == 2020
        assert result.context["geographic_level"] == "county"
        assert result.context["download_url"] == "https://example.com/ok.zip"

    def test_unexpected_exception_returns_fail(self):
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/ok.zip"
        source.discovery.validate_download_url.return_value = True

        with patch.object(source, '_download_and_process_tiger') as mock_dl:
            mock_dl.side_effect = RuntimeError("disk full")
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county',
            )
        assert not result.success
        assert result.error_code == "UNEXPECTED_ERROR"
        assert "disk full" in result.message


# ---------------------------------------------------------------------------
# Typed exceptions raised by internal methods
# ---------------------------------------------------------------------------

class TestConstructDownloadUrlExceptions:
    """Test that construct_download_url raises typed exceptions."""

    def _make_discovery(self):
        from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery
        disc = CensusDirectoryDiscovery.__new__(CensusDirectoryDiscovery)
        disc.base_url = "https://www2.census.gov/geo/tiger"
        disc.timeout = 30
        disc.cache = {}
        disc.cache_timeout = 3600
        return disc

    def test_invalid_fips_raises_input_error(self):
        disc = self._make_discovery()
        with pytest.raises(BoundaryInputError) as exc_info:
            disc.construct_download_url(2020, 'county', state_fips='ZZ')
        assert exc_info.value.stage == "input_validation"
        assert "ZZ" in str(exc_info.value)

    def test_missing_boundary_type_raises_discovery_error(self):
        disc = self._make_discovery()
        with patch.object(disc, 'get_year_specific_url_patterns', return_value={}):
            with patch.object(disc, 'discover_boundary_types', return_value={'county': 'COUNTY'}):
                with pytest.raises(BoundaryDiscoveryError) as exc_info:
                    disc.construct_download_url(2020, 'unicorn_level')
                assert "unicorn_level" in str(exc_info.value)
                assert exc_info.value.stage == "discovery"


class TestValidateDownloadUrlExceptions:
    """Test that validate_download_url raises typed exceptions."""

    def _make_discovery(self):
        from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery
        disc = CensusDirectoryDiscovery.__new__(CensusDirectoryDiscovery)
        disc.timeout = 5
        return disc

    @patch('siege_utilities.geo.spatial_data.requests.get')
    def test_http_404_raises_url_validation_error(self, mock_get):
        disc = self._make_discovery()
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.close = Mock()
        mock_get.return_value = mock_resp

        with pytest.raises(BoundaryUrlValidationError) as exc_info:
            disc.validate_download_url("https://example.com/missing.zip")
        assert exc_info.value.context["http_status"] == 404

    @patch('siege_utilities.geo.spatial_data.requests.get')
    def test_timeout_raises_url_validation_error(self, mock_get):
        import requests as req
        disc = self._make_discovery()
        mock_get.side_effect = req.exceptions.Timeout("timed out")

        with pytest.raises(BoundaryUrlValidationError) as exc_info:
            disc.validate_download_url("https://example.com/slow.zip")
        assert "timed out" in str(exc_info.value)

    @patch('siege_utilities.geo.spatial_data.requests.get')
    def test_success_returns_true(self, mock_get):
        disc = self._make_discovery()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.close = Mock()
        mock_get.return_value = mock_resp

        assert disc.validate_download_url("https://example.com/ok.zip") is True


# ---------------------------------------------------------------------------
# Legacy backward compatibility
# ---------------------------------------------------------------------------

class TestLegacyBackwardCompatibility:
    """Verify get_geographic_boundaries still returns Optional[GeoDataFrame]."""

    @patch('siege_utilities.geo.spatial_data.CensusDirectoryDiscovery')
    def test_legacy_returns_none_on_failure(self, MockDiscovery):
        mock_disc = MockDiscovery.return_value
        mock_disc.get_available_years.return_value = [2020]
        mock_disc.discover_boundary_types.return_value = {'county': 'COUNTY'}
        mock_disc.get_optimal_year.return_value = 2020
        mock_disc.construct_download_url.side_effect = BoundaryDiscoveryError("boom")

        from siege_utilities.geo.spatial_data import CensusDataSource
        source = CensusDataSource.__new__(CensusDataSource)
        source.name = "Census Bureau"
        source.base_url = "https://www2.census.gov/geo/tiger"
        source.api_key = None
        source.user_config = {}
        source.discovery = mock_disc
        source.available_years = [2020]
        source.state_required_levels = ['tract', 'block_group', 'block', 'tabblock20', 'sldu', 'sldl']
        source.national_levels = ['nation', 'state', 'county', 'place', 'zcta', 'cd']

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = source.get_geographic_boundaries(2020, 'county')
        assert result is None

    @patch('siege_utilities.geo.spatial_data.CensusDirectoryDiscovery')
    def test_legacy_emits_deprecation_warning(self, MockDiscovery):
        mock_disc = MockDiscovery.return_value
        mock_disc.get_available_years.return_value = [2020]
        mock_disc.discover_boundary_types.return_value = {'county': 'COUNTY'}
        mock_disc.get_optimal_year.return_value = 2020
        mock_disc.construct_download_url.side_effect = BoundaryDiscoveryError("boom")

        from siege_utilities.geo.spatial_data import CensusDataSource
        source = CensusDataSource.__new__(CensusDataSource)
        source.name = "Census Bureau"
        source.base_url = "https://www2.census.gov/geo/tiger"
        source.api_key = None
        source.user_config = {}
        source.discovery = mock_disc
        source.available_years = [2020]
        source.state_required_levels = ['tract', 'block_group', 'block', 'tabblock20', 'sldu', 'sldl']
        source.national_levels = ['nation', 'state', 'county', 'place', 'zcta', 'cd']

        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            source.get_geographic_boundaries(2020, 'county')
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1
            assert "fetch_geographic_boundaries" in str(dep_warnings[0].message)


# ---------------------------------------------------------------------------
# BoundaryConfigurationError — silent None → typed exception
# ---------------------------------------------------------------------------

class TestBoundaryConfigurationError:
    """Verify _construct_filename_with_fips_validation raises instead of returning None."""

    def _make_discovery(self):
        from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery
        disc = CensusDirectoryDiscovery.__new__(CensusDirectoryDiscovery)
        disc.base_url = "https://www2.census.gov/geo/tiger"
        disc.timeout = 30
        disc.cache = {}
        disc.cache_timeout = 3600
        return disc

    def test_cd_without_congress_number_raises_for_unknown_year(self):
        """Congressional district without congress_number raises for years not in YEAR_TO_CONGRESS."""
        disc = self._make_discovery()
        patterns = {
            'base_url': 'https://www2.census.gov/geo/tiger/TIGER2000',
            'filename_patterns': {
                'congress': 'tl_{year}_us_cd{congress_num}_shp.zip',
                'congress_state': 'tl_{year}_{state_fips}_cd{congress_num}_shp.zip',
                'state': 'tl_{year}_{state_fips}_{boundary_type}_shp.zip',
                'national': 'tl_{year}_us_{boundary_type}_shp.zip',
            }
        }
        # year=2000 is not in YEAR_TO_CONGRESS, so no auto-lookup is possible
        with pytest.raises(BoundaryConfigurationError) as exc_info:
            disc._construct_filename_with_fips_validation(
                year=2000, boundary_type='cd', state_fips=None,
                congress_number=None, patterns=patterns,
            )
        assert exc_info.value.stage == "configuration"
        assert "congress number" in str(exc_info.value).lower()
        assert exc_info.value.context["boundary_type"] == "cd"

    def test_cd_auto_resolves_congress_for_known_year(self):
        """For years in YEAR_TO_CONGRESS, congress number is auto-resolved without explicit parameter."""
        disc = self._make_discovery()
        patterns = {
            'base_url': 'https://www2.census.gov/geo/tiger/TIGER2020',
            'filename_patterns': {
                'congress': 'tl_{year}_us_cd{congress_num}.zip',
                'congress_state': 'tl_{year}_{state_fips}_cd{congress_num}.zip',
                'state': 'tl_{year}_{state_fips}_{boundary_type}.zip',
                'national': 'tl_{year}_us_{boundary_type}.zip',
            }
        }
        # year=2020 → YEAR_TO_CONGRESS[2020] = 116 (NOT 117; cd117 absent from TIGER)
        filename = disc._construct_filename_with_fips_validation(
            year=2020, boundary_type='cd', state_fips=None,
            congress_number=None, patterns=patterns,
        )
        assert filename == 'tl_2020_us_cd116.zip'

    def test_tract_without_state_fips_raises(self):
        """State-required type without state FIPS raises BoundaryConfigurationError."""
        disc = self._make_discovery()
        patterns = {
            'base_url': 'https://www2.census.gov/geo/tiger/TIGER2020',
            'filename_patterns': {
                'congress': 'tl_{year}_us_cd{congress_num}_shp.zip',
                'state': 'tl_{year}_{state_fips}_{boundary_type}_shp.zip',
                'national': 'tl_{year}_us_{boundary_type}_shp.zip',
            }
        }
        with pytest.raises(BoundaryConfigurationError) as exc_info:
            disc._construct_filename_with_fips_validation(
                year=2020, boundary_type='tract', state_fips=None,
                congress_number=None, patterns=patterns,
            )
        assert exc_info.value.stage == "configuration"
        assert "state fips" in str(exc_info.value).lower()
        assert exc_info.value.context["requires"] == "state_fips"

    def test_block_group_without_state_fips_raises(self):
        """block_group without state FIPS also raises BoundaryConfigurationError."""
        disc = self._make_discovery()
        patterns = {
            'base_url': 'https://www2.census.gov/geo/tiger/TIGER2020',
            'filename_patterns': {
                'congress': 'tl_{year}_us_cd{congress_num}_shp.zip',
                'state': 'tl_{year}_{state_fips}_{boundary_type}_shp.zip',
                'national': 'tl_{year}_us_{boundary_type}_shp.zip',
            }
        }
        with pytest.raises(BoundaryConfigurationError):
            disc._construct_filename_with_fips_validation(
                year=2020, boundary_type='block_group', state_fips=None,
                congress_number=None, patterns=patterns,
            )

    def test_configuration_error_in_hierarchy(self):
        """BoundaryConfigurationError is a subclass of BoundaryRetrievalError."""
        assert issubclass(BoundaryConfigurationError, BoundaryRetrievalError)
        err = BoundaryConfigurationError("test", context={"key": "val"})
        assert err.stage == "configuration"
        assert err.context == {"key": "val"}

    def test_raise_on_error_configuration_stage(self):
        """BoundaryFetchResult.raise_on_error maps 'configuration' stage correctly."""
        result = BoundaryFetchResult.fail(
            error_code="MISSING_CONFIG",
            error_stage="configuration",
            message="Missing congress number",
        )
        with pytest.raises(BoundaryConfigurationError):
            result.raise_on_error()


# ---------------------------------------------------------------------------
# Post-download FIPS filtering
# ---------------------------------------------------------------------------

class TestPostDownloadFiltering:
    """Test that national-only boundary types get filtered by state FIPS after download."""

    @patch('siege_utilities.geo.spatial_data.CensusDirectoryDiscovery')
    def _make_source(self, MockDiscovery):
        mock_disc = MockDiscovery.return_value
        mock_disc.get_available_years.return_value = [2020, 2024]
        mock_disc.discover_boundary_types.return_value = {
            'county': 'COUNTY', 'state': 'STATE', 'cbsa': 'CBSA',
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

    def _make_mock_gdf(self, statefp_col='STATEFP', state_fips_values=None):
        """Create a mock GeoDataFrame with STATEFP column."""
        import pandas as pd
        if state_fips_values is None:
            state_fips_values = ['06', '06', '36', '36', '48']
        data = {
            statefp_col: state_fips_values,
            'NAME': [f'Feature_{i}' for i in range(len(state_fips_values))],
        }
        df = pd.DataFrame(data)
        # Add columns list for the FIPS column detection
        return df

    def test_county_filtered_by_state(self):
        """County (national-only) should filter to requested state only."""
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/county.zip"
        source.discovery.validate_download_url.return_value = True

        mock_gdf = self._make_mock_gdf()

        with patch.object(source, '_download_and_process_tiger', return_value=mock_gdf):
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county', state_fips='06',
            )

        assert result.success
        gdf = result.geodataframe
        assert len(gdf) == 2  # Only CA rows
        assert all(gdf['STATEFP'] == '06')

    def test_national_type_without_state_returns_all(self):
        """County without state_fips should return all records unfiltered."""
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/county.zip"
        source.discovery.validate_download_url.return_value = True

        mock_gdf = self._make_mock_gdf()

        with patch.object(source, '_download_and_process_tiger', return_value=mock_gdf):
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county',
            )

        assert result.success
        assert len(result.geodataframe) == 5  # All rows

    def test_statefp20_column_detected(self):
        """Post-download filtering should detect STATEFP20 variant column."""
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/state.zip"
        source.discovery.validate_download_url.return_value = True

        mock_gdf = self._make_mock_gdf(statefp_col='STATEFP20')

        with patch.object(source, '_download_and_process_tiger', return_value=mock_gdf):
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='state', state_fips='48',
            )

        assert result.success
        assert len(result.geodataframe) == 1  # Only TX

    def test_filtering_context_recorded(self):
        """Filtering metadata (filtered_from, filtered_to) should appear in context."""
        source = self._make_source()
        source.discovery.construct_download_url.return_value = "https://example.com/county.zip"
        source.discovery.validate_download_url.return_value = True

        mock_gdf = self._make_mock_gdf()

        with patch.object(source, '_download_and_process_tiger', return_value=mock_gdf):
            result = source.fetch_geographic_boundaries(
                year=2020, geographic_level='county', state_fips='36',
            )

        assert result.success
        assert result.context.get("filtered_from") == 5
        assert result.context.get("filtered_to") == 2


# ---------------------------------------------------------------------------
# Deprecation of standalone get_census_boundaries
# ---------------------------------------------------------------------------

class TestGetCensusBoundariesDeprecation:
    """Verify standalone get_census_boundaries() emits DeprecationWarning."""

    def test_get_census_boundaries_emits_deprecation(self):
        import warnings
        from siege_utilities.geo.spatial_data import get_census_boundaries

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Call will fail (no network) but we only care about the warning
            try:
                get_census_boundaries(2020, 'county')
            except Exception:
                pass
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1
            assert "get_census_boundaries" in str(dep_warnings[0].message)
            assert "fetch_geographic_boundaries" in str(dep_warnings[0].message)
