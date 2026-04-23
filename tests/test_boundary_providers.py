"""Tests for siege_utilities.geo.providers.boundary_providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.providers.boundary_providers import (
    BoundaryProvider,
    CensusTIGERProvider,
    GADMProvider,
    RDHProvider,
    resolve_boundary_provider,
)

# Test-only credential placeholders. Marked noqa to tell scanners these
# are not real secrets; the actual values never leave the test process.
TEST_USERNAME = "test-user"  # noqa: S105 — test fixture placeholder
TEST_PASSWORD = "test-password-placeholder"  # noqa: S105 — test fixture placeholder


@pytest.fixture(autouse=True)
def _isolate_rdh_env(monkeypatch):
    """Strip RDH_USERNAME / RDH_PASSWORD so ambient env doesn't leak in."""
    monkeypatch.delenv("RDH_USERNAME", raising=False)
    monkeypatch.delenv("RDH_PASSWORD", raising=False)


# ---------------------------------------------------------------------------
# ABC contract
# ---------------------------------------------------------------------------


class TestBoundaryProviderABC:
    """BoundaryProvider cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BoundaryProvider()

    def test_subclass_must_implement(self):
        """A subclass that omits required methods cannot be instantiated."""

        class Incomplete(BoundaryProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()


# ---------------------------------------------------------------------------
# CensusTIGERProvider
# ---------------------------------------------------------------------------


class TestCensusTIGERProvider:
    def test_provider_name(self):
        provider = CensusTIGERProvider()
        assert provider.provider_name == 'Census TIGER/Line'

    def test_is_available(self):
        provider = CensusTIGERProvider()
        assert provider.is_available() is True

    def test_list_levels_returns_sorted_canonical_levels(self):
        provider = CensusTIGERProvider()
        levels = provider.list_levels()
        assert isinstance(levels, list)
        assert len(levels) > 0
        assert levels == sorted(levels)
        # Spot-check a few expected entries
        for expected in ('state', 'county', 'tract', 'block_group', 'zcta', 'cd'):
            assert expected in levels

    @patch('siege_utilities.geo.providers.boundary_providers.CensusTIGERProvider.get_boundary')
    def test_get_boundary_delegates(self, mock_get):
        """get_boundary forwards to get_census_boundaries."""
        sentinel = MagicMock(name='gdf')
        mock_get.return_value = sentinel

        provider = CensusTIGERProvider()
        result = provider.get_boundary('county', identifier='06')
        mock_get.assert_called_once_with('county', identifier='06')
        assert result is sentinel

    @patch('siege_utilities.geo.spatial_data.CensusDataSource')
    def test_get_boundary_passes_kwargs(self, MockDS):
        """Extra kwargs (e.g. year) are forwarded to fetch_geographic_boundaries."""
        sentinel_gdf = MagicMock(name='gdf')
        mock_result = MagicMock(success=True, geodataframe=sentinel_gdf)
        MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result

        provider = CensusTIGERProvider()
        result = provider.get_boundary('tract', identifier='36', year=2020)
        MockDS.return_value.fetch_geographic_boundaries.assert_called_once_with(
            geographic_level='tract', state_fips='36', year=2020,
        )
        assert result is sentinel_gdf

    @patch('siege_utilities.geo.spatial_data.CensusDataSource')
    def test_get_boundary_congress_number_forwarded(self, MockDS):
        """congress_number kwarg reaches fetch_geographic_boundaries for CD boundaries."""
        sentinel_gdf = MagicMock(name='cd_gdf')
        mock_result = MagicMock(success=True, geodataframe=sentinel_gdf)
        MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result

        provider = CensusTIGERProvider()
        result = provider.get_boundary('cd', year=2020, congress_number=116)
        MockDS.return_value.fetch_geographic_boundaries.assert_called_once_with(
            geographic_level='cd', year=2020, congress_number=116,
        )
        assert result is sentinel_gdf

    @patch('siege_utilities.geo.spatial_data.CensusDataSource')
    def test_get_boundary_level_authoritative(self, MockDS):
        """geographic_level in kwargs is silently dropped; the level arg wins."""
        mock_result = MagicMock(success=True, geodataframe=MagicMock())
        MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result

        provider = CensusTIGERProvider()
        provider.get_boundary('county', geographic_level='tract')  # kwarg must lose
        call_kwargs = MockDS.return_value.fetch_geographic_boundaries.call_args[1]
        assert call_kwargs['geographic_level'] == 'county'

    @patch('siege_utilities.geo.spatial_data.CensusDataSource')
    def test_get_boundary_failure_returns_none(self, MockDS):
        """result.success=False returns None and logs a warning."""
        mock_result = MagicMock(success=False, error_stage='download', message='404')
        MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result

        provider = CensusTIGERProvider()
        import logging
        with patch.object(logging.getLogger('siege_utilities.geo.providers.boundary_providers'),
                          'warning') as mock_warn:
            result = provider.get_boundary('county')
        assert result is None
        mock_warn.assert_called_once()


# ---------------------------------------------------------------------------
# GADMProvider
# ---------------------------------------------------------------------------


class TestGADMProvider:
    def test_provider_name(self):
        provider = GADMProvider()
        assert provider.provider_name == 'GADM'

    def test_list_levels(self):
        provider = GADMProvider()
        levels = provider.list_levels()
        assert levels == ['country', 'admin1', 'admin2', 'admin3']

    def test_is_available_when_geopandas_present(self):
        provider = GADMProvider()
        # geopandas is installed in this test environment
        assert provider.is_available() is True

    def test_is_available_when_geopandas_missing(self):
        with patch.dict('sys.modules', {'geopandas': None}):
            provider = GADMProvider()
            # Importing geopandas will raise ImportError when module is None
            assert provider.is_available() is False

    @patch('geopandas.read_file')
    def test_get_boundary_builds_correct_url(self, mock_read):
        mock_read.return_value = MagicMock(name='gdf')
        provider = GADMProvider()
        provider.get_boundary('admin1', country_code='DEU')
        url = mock_read.call_args[0][0]
        assert 'DEU' in url
        assert '_1.json' in url

    @patch('geopandas.read_file')
    def test_get_boundary_identifier_as_country_code(self, mock_read):
        """identifier parameter works as country_code."""
        mock_read.return_value = MagicMock(name='gdf')
        provider = GADMProvider()
        provider.get_boundary('country', identifier='FRA')
        url = mock_read.call_args[0][0]
        assert 'FRA' in url
        assert '_0.json' in url

    def test_get_boundary_missing_country_raises(self):
        provider = GADMProvider()
        with pytest.raises(ValueError, match='country_code'):
            provider.get_boundary('admin1')

    def test_get_boundary_invalid_level_raises(self):
        provider = GADMProvider()
        with pytest.raises(ValueError, match='Unknown GADM level'):
            provider.get_boundary('province', country_code='DEU')


# ---------------------------------------------------------------------------
# Factory: resolve_boundary_provider
# ---------------------------------------------------------------------------


class TestResolveBoundaryProvider:
    def test_us_returns_census_tiger(self):
        provider = resolve_boundary_provider('US')
        assert isinstance(provider, CensusTIGERProvider)

    def test_usa_returns_census_tiger(self):
        provider = resolve_boundary_provider('USA')
        assert isinstance(provider, CensusTIGERProvider)

    def test_us_territory_returns_census_tiger(self):
        for code in ('PR', 'GU', 'VI', 'AS', 'MP'):
            provider = resolve_boundary_provider(code)
            assert isinstance(provider, CensusTIGERProvider), f'Failed for {code}'

    def test_case_insensitive(self):
        provider = resolve_boundary_provider('us')
        assert isinstance(provider, CensusTIGERProvider)

    def test_international_returns_gadm(self):
        provider = resolve_boundary_provider('DE')
        assert isinstance(provider, GADMProvider)

    def test_default_is_us(self):
        provider = resolve_boundary_provider()
        assert isinstance(provider, CensusTIGERProvider)

    def test_gadm_kwargs_forwarded(self):
        provider = resolve_boundary_provider('FR', version='3.6')
        assert isinstance(provider, GADMProvider)
        assert provider._version == '3.6'


# ---------------------------------------------------------------------------
# RDHProvider
# ---------------------------------------------------------------------------


class TestRDHProvider:
    def test_provider_name(self):
        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        assert provider.provider_name == 'Redistricting Data Hub'

    def test_list_levels(self):
        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        levels = provider.list_levels()
        assert 'precinct' in levels
        assert 'congress' in levels
        assert 'state_senate' in levels
        assert 'state_house' in levels

    def test_is_available_with_credentials_and_geopandas(self):
        provider = RDHProvider(username="u@example.com", password=TEST_PASSWORD)
        # geopandas is installed in this test environment
        assert provider.is_available() is True

    def test_is_available_without_credentials(self):
        provider = RDHProvider(username='', password=TEST_PASSWORD)
        assert provider.is_available() is False

    def test_is_available_without_password(self):
        """is_available() requires both username AND password."""
        provider = RDHProvider(username=TEST_USERNAME, password='')
        assert provider.is_available() is False

    def test_invalid_level_raises(self):
        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        with pytest.raises(ValueError, match='Unknown RDH level'):
            provider.get_boundary('county', identifier='TX')

    def test_missing_state_raises(self):
        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        with pytest.raises(ValueError, match='state abbreviation'):
            provider.get_boundary('precinct')

    @patch('siege_utilities.geo.providers.boundary_providers.RDHProvider._get_client')
    def test_get_boundary_precinct_delegates(self, mock_get_client):
        """get_boundary('precinct') calls client.get_precinct_data then load_shapefile."""
        sentinel_gdf = MagicMock(name='gdf')
        mock_client = MagicMock()
        mock_client.get_precinct_data.return_value = [MagicMock()]
        mock_client.load_shapefile.return_value = sentinel_gdf
        mock_get_client.return_value = mock_client

        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        result = provider.get_boundary('precinct', identifier='TX')

        mock_client.get_precinct_data.assert_called_once_with('TX', year=None, format='shp')
        assert result is sentinel_gdf

    @patch('siege_utilities.geo.providers.boundary_providers.RDHProvider._get_client')
    def test_get_boundary_congress_delegates(self, mock_get_client):
        """get_boundary('congress') calls client.get_enacted_plans."""
        sentinel_gdf = MagicMock(name='gdf')
        mock_client = MagicMock()
        mock_client.get_enacted_plans.return_value = [MagicMock()]
        mock_client.load_shapefile.return_value = sentinel_gdf
        mock_get_client.return_value = mock_client

        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        result = provider.get_boundary('congress', state='TX', year='2022')

        mock_client.get_enacted_plans.assert_called_once_with('TX', chamber='congress', year='2022', format='shp')
        assert result is sentinel_gdf

    @patch('siege_utilities.geo.providers.boundary_providers.RDHProvider._get_client')
    def test_get_boundary_no_datasets_returns_none(self, mock_get_client):
        """When RDH returns no matching datasets, get_boundary returns None."""
        mock_client = MagicMock()
        mock_client.get_precinct_data.return_value = []
        mock_get_client.return_value = mock_client

        provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
        result = provider.get_boundary('precinct', identifier='TX')
        assert result is None

    def test_credentials_from_env(self, monkeypatch):
        monkeypatch.setenv('RDH_USERNAME', 'env_user')
        monkeypatch.setenv('RDH_PASSWORD', 'env_pass')  # noqa: S105 — test env
        provider = RDHProvider()
        assert provider._username == 'env_user'
        assert provider._password == 'env_pass'

    def test_explicit_empty_username_disables_env_fallback(self, monkeypatch):
        """Passing username='' must NOT fall back to RDH_USERNAME env var."""
        monkeypatch.setenv('RDH_USERNAME', 'should_not_use')
        provider = RDHProvider(username='', password=TEST_PASSWORD)
        assert provider._username == ''
