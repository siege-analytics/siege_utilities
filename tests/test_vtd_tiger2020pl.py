"""Tests for TIGER2020PL VTD URL routing in CensusDirectoryDiscovery."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from siege_utilities.geo.spatial_data import (
    CensusDirectoryDiscovery,
    _VTD_PL_STATE_NAMES,
    TIGER_PL_BASE_URL,
)
from siege_utilities.geo.boundary_result import (
    BoundaryInputError,
    BoundaryDiscoveryError,
)


# ---------------------------------------------------------------------------
# _is_vtd_pl_boundary
# ---------------------------------------------------------------------------


class TestIsVtdPlBoundary:
    def test_vtd_2020(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd', 2020) is True

    def test_vtd20_2020(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd20', 2020) is True

    def test_vtd_2010(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd', 2010) is True

    def test_vtd10_2010(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd10', 2010) is True

    def test_vtd_non_decennial_is_false(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd', 2019) is False

    def test_non_vtd_decennial_is_false(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('county', 2020) is False

    def test_tract_is_false(self):
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('tract', 2020) is False

    def test_vtd10_with_2020_is_false(self):
        """Cross-vintage pair: 2010 suffix with 2020 year must not match."""
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd10', 2020) is False

    def test_vtd20_with_2010_is_false(self):
        """Cross-vintage pair: 2020 suffix with 2010 year must not match."""
        assert CensusDirectoryDiscovery._is_vtd_pl_boundary('vtd20', 2010) is False


# ---------------------------------------------------------------------------
# _construct_vtd_pl_url
# ---------------------------------------------------------------------------


class TestConstructVtdPlUrl:
    def test_texas_2020(self):
        url = CensusDirectoryDiscovery._construct_vtd_pl_url(2020, '48')
        assert url == (
            f'{TIGER_PL_BASE_URL}/TIGER2020PL/STATE/48_TEXAS/48/tl_2020_48_vtd20.zip'
        )

    def test_california_2020(self):
        url = CensusDirectoryDiscovery._construct_vtd_pl_url(2020, '06')
        assert 'TIGER2020PL' in url
        assert '06_CALIFORNIA' in url
        assert 'vtd20' in url

    def test_dc_2020(self):
        url = CensusDirectoryDiscovery._construct_vtd_pl_url(2020, '11')
        assert 'DISTRICT_OF_COLUMBIA' in url

    def test_new_hampshire_underscore(self):
        url = CensusDirectoryDiscovery._construct_vtd_pl_url(2020, '33')
        assert '33_NEW_HAMPSHIRE' in url

    def test_2010_raises_because_state_level_url_does_not_exist(self):
        """2010 VTDs are published county-level under TIGER2010/VTD/2010/;
        the state-level TIGER2010PL path does not exist on Census and would
        404. We fail fast rather than returning a broken URL."""
        with pytest.raises(BoundaryDiscoveryError, match="per-county"):
            CensusDirectoryDiscovery._construct_vtd_pl_url(2010, '48')

    def test_puerto_rico(self):
        url = CensusDirectoryDiscovery._construct_vtd_pl_url(2020, '72')
        assert '72_PUERTO_RICO' in url

    def test_unsupported_territory_raises(self):
        """Guam (66) has no VTD data in TIGER2020PL."""
        with pytest.raises(BoundaryInputError, match='does not publish VTD'):
            CensusDirectoryDiscovery._construct_vtd_pl_url(2020, '66')

    def test_non_decennial_year_raises(self):
        with pytest.raises(BoundaryDiscoveryError, match='decennial year'):
            CensusDirectoryDiscovery._construct_vtd_pl_url(2019, '48')

    def test_all_mapped_states_produce_valid_url(self):
        """Smoke test: every entry in _VTD_PL_STATE_NAMES builds without error."""
        for fips in _VTD_PL_STATE_NAMES:
            url = CensusDirectoryDiscovery._construct_vtd_pl_url(2020, fips)
            assert url.startswith('https://')
            assert fips in url
            assert 'vtd20.zip' in url


# ---------------------------------------------------------------------------
# construct_download_url routes VTD to TIGER PL
# ---------------------------------------------------------------------------


class TestConstructDownloadUrlVtdRouting:
    def _discovery(self) -> CensusDirectoryDiscovery:
        return CensusDirectoryDiscovery()

    def test_vtd_2020_bypasses_discovery(self):
        """construct_download_url must not call discover_boundary_types for VTD 2020."""
        d = self._discovery()
        with patch.object(d, 'discover_boundary_types') as mock_discover:
            url = d.construct_download_url(2020, 'vtd', state_fips='48')
        mock_discover.assert_not_called()
        assert 'TIGER2020PL' in url
        assert '48_TEXAS' in url

    def test_vtd20_2020_bypasses_discovery(self):
        d = self._discovery()
        with patch.object(d, 'discover_boundary_types') as mock_discover:
            url = d.construct_download_url(2020, 'vtd20', state_fips='06')
        mock_discover.assert_not_called()
        assert 'TIGER2020PL' in url

    def test_vtd_without_state_fips_raises(self):
        d = self._discovery()
        with pytest.raises(BoundaryInputError, match='state_fips'):
            d.construct_download_url(2020, 'vtd')

    def test_non_decennial_vtd_goes_through_normal_path(self):
        """vtd for non-decennial year falls through to normal discovery."""
        d = self._discovery()
        mock_types = {'vtd': 'VTD'}
        with (
            patch.object(d, 'discover_boundary_types', return_value=mock_types),
            patch.object(d, 'get_year_specific_url_patterns',
                         return_value={'base_url': 'https://x', 'filename_patterns': {
                             'state': 'tl_{year}_{state_fips}_{boundary_type}.zip',
                             'national': 'tl_{year}_us_{boundary_type}.zip',
                             'congress': 'tl_{year}_us_cd{congress_num}.zip',
                         }, 'directory_mappings': {}}),
            patch.object(d, '_construct_filename_with_fips_validation',
                         return_value='tl_2015_48_vtd.zip'),
        ):
            url = d.construct_download_url(2015, 'vtd', state_fips='48')
        assert 'TIGER2020PL' not in url
