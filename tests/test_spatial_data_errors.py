"""Tests for the SpatialDataError hierarchy in geo.spatial_data (ELE-2420).

See docs/FAILURE_MODES.md CC1. Previously, every HTTP / parse failure in
GovernmentDataSource and OpenStreetMapDataSource was caught and silently
turned into ``return None`` — producing fake "no data" results
indistinguishable from legitimate empty responses.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import requests

from siege_utilities.geo.spatial_data import (
    CensusDirectoryDiscovery,
    GovernmentDataSource,
    OpenStreetMapDataSource,
    SpatialDataError,
    _known_tiger_directories_for_year,
)


class TestExceptionHierarchy:
    def test_is_runtime_error(self):
        assert issubclass(SpatialDataError, RuntimeError)


class TestGovernmentDataSource:
    def test_metadata_http_failure_raises(self):
        src = GovernmentDataSource(portal_url="https://example.com")
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=ConnectionError("network down"),
        ):
            with pytest.raises(SpatialDataError) as exc_info:
                src._get_dataset_metadata("https://example.com/api/x")
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_metadata_http_error_status_returns_none(self):
        """HTTP 4xx/5xx without exception goes through the response.ok
        branch and returns None — that's a legitimate 'no metadata' path,
        not a silent-swallow of a transport-level failure."""
        src = GovernmentDataSource(portal_url="https://example.com")
        fake_response = MagicMock()
        fake_response.ok = False
        fake_response.status_code = 404
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            return_value=fake_response,
        ):
            result = src._get_dataset_metadata("https://example.com/api/x")
        assert result is None

    def test_format_finder_error_raises(self):
        src = GovernmentDataSource(portal_url="https://example.com")
        # Pass a metadata object where resources.get raises
        broken_metadata = MagicMock()
        broken_metadata.get.side_effect = RuntimeError("broken metadata")
        with pytest.raises(SpatialDataError) as exc_info:
            src._find_best_format(broken_metadata, "geojson")
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_download_dataset_surface_raises(self):
        """download_dataset() wraps helper SpatialDataError cleanly
        (no double-wrap via the outer except Exception)."""
        src = GovernmentDataSource(portal_url="https://example.com")
        with patch.object(
            src,
            "_get_dataset_metadata",
            side_effect=SpatialDataError("helper failed"),
        ):
            with pytest.raises(SpatialDataError, match="helper failed"):
                src.download_dataset("abc")


class TestOpenStreetMapDataSource:
    def test_overpass_network_failure_raises(self):
        src = OpenStreetMapDataSource()
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=ConnectionError("network down"),
        ):
            with pytest.raises(SpatialDataError) as exc_info:
                src.download_osm_data("node[highway]")
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_overpass_http_error_status_returns_none(self):
        """Matches the metadata test — non-2xx responses legitimately
        return None rather than raising."""
        src = OpenStreetMapDataSource()
        fake_response = MagicMock()
        fake_response.ok = False
        fake_response.status_code = 429
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            return_value=fake_response,
        ):
            result = src.download_osm_data("node[highway]")
        assert result is None


class TestKnownTigerDirectories:
    """Unit tests for the static 429-fallback directory list."""

    def test_core_dirs_present_for_all_years(self):
        for year in [2010, 2015, 2018, 2020, 2022, 2024]:
            dirs = _known_tiger_directories_for_year(year)
            for expected in ["BG", "CD", "COUNTY", "SLDL", "SLDU", "STATE", "TRACT"]:
                assert expected in dirs, f"{expected} missing for year {year}"

    def test_zcta_dir_name_changes_at_2020_vintage(self):
        # 2010-2011: ZCTA tied to redistricting release schedule, not in
        # the annual fallback — expect neither.
        assert "ZCTA5" not in _known_tiger_directories_for_year(2011)
        assert "ZCTA520" not in _known_tiger_directories_for_year(2011)
        # 2012-2019: legacy directory + filename suffix (zcta510).
        assert "ZCTA5" in _known_tiger_directories_for_year(2012)
        assert "ZCTA5" in _known_tiger_directories_for_year(2019)
        assert "ZCTA520" not in _known_tiger_directories_for_year(2019)
        # 2020: transition year — both directories are published.
        dirs_2020 = _known_tiger_directories_for_year(2020)
        assert "ZCTA5" in dirs_2020
        assert "ZCTA520" in dirs_2020
        # 2021+: only the 2020-vintage directory.
        assert "ZCTA5" not in _known_tiger_directories_for_year(2024)
        assert "ZCTA520" in _known_tiger_directories_for_year(2024)

    def test_2020_decennial_extras(self):
        dirs = _known_tiger_directories_for_year(2020)
        assert "TABBLOCK20" in dirs
        assert "VTD20" in dirs

    def test_2010_decennial_extras(self):
        dirs = _known_tiger_directories_for_year(2010)
        assert "TABBLOCK10" in dirs
        assert "VTD10" in dirs

    def test_uac_dir_tracks_decennial_vintage(self):
        # 2010-vintage UAC10 published 2011-2019.
        assert "UAC10" in _known_tiger_directories_for_year(2015)
        # 2020-2021 transitional unsuffixed UAC.
        assert "UAC" in _known_tiger_directories_for_year(2020)
        assert "UAC" in _known_tiger_directories_for_year(2021)
        # 2020-vintage UAC20 published 2022 onward.
        assert "UAC20" in _known_tiger_directories_for_year(2022)
        assert "UAC20" in _known_tiger_directories_for_year(2024)
        # No suffix mixing.
        assert "UAC10" not in _known_tiger_directories_for_year(2022)
        assert "UAC20" not in _known_tiger_directories_for_year(2015)

    def test_expanded_layer_coverage(self):
        """The conservative baseline should cover ~30+ layers, not just ~10."""
        dirs = _known_tiger_directories_for_year(2022)
        # Sample of layers a downstream user is plausibly going to ask for
        # via a directory listing fallback.
        for layer in [
            "PUMA", "AIANNH", "ANRC", "CBSA", "CSA", "METDIV", "NECTA",
            "PRIMARYROADS", "PRISECROADS", "ROADS", "RAILS",
            "ELSD", "SCSD", "SDELM", "SDSEC", "SDUNI", "UNSD",
            "EDGES", "FACES", "POINTLM", "LINEARWATER", "AREAWATER",
            "TBG", "TTRACT", "COUNTYSUB",
        ]:
            assert layer in dirs, f"{layer} missing from 2022 fallback list"
        # Sanity floor: at least 30 layers in the modern era.
        assert len(dirs) >= 30, f"only {len(dirs)} layers in 2022 fallback"

    def test_returns_sorted_list(self):
        dirs = _known_tiger_directories_for_year(2022)
        assert dirs == sorted(dirs)


class TestCensusDirectoryDiscovery429Fallback:
    """get_year_directory_contents() must return the static fallback on 429."""

    def _make_429_error(self) -> requests.exceptions.HTTPError:
        resp = MagicMock()
        resp.status_code = 429
        return requests.exceptions.HTTPError(response=resp)

    def test_returns_fallback_on_429(self):
        discovery = CensusDirectoryDiscovery()
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=self._make_429_error(),
        ):
            result = discovery.get_year_directory_contents(2020)
        assert "CD" in result
        assert "BG" in result
        assert "SLDL" in result
        assert "SLDU" in result

    def test_fallback_is_cached(self):
        discovery = CensusDirectoryDiscovery()
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=self._make_429_error(),
        ) as mock_get:
            first = discovery.get_year_directory_contents(2018)
            second = discovery.get_year_directory_contents(2018)
            assert first == second
            assert mock_get.call_count == 1, "second call must hit the cache, not the network"

    def test_429_fallback_only_for_skip_strategy(self):
        """Callers with on_error='raise' must still receive the HTTPError."""
        discovery = CensusDirectoryDiscovery()
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=self._make_429_error(),
        ):
            with pytest.raises(Exception):
                discovery.get_year_directory_contents(2020, on_error="raise")

    def test_non_429_http_error_still_returns_empty(self):
        discovery = CensusDirectoryDiscovery()
        resp = MagicMock()
        resp.status_code = 503
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=requests.exceptions.HTTPError(response=resp),
        ):
            result = discovery.get_year_directory_contents(2020, on_error="skip")
        assert result == []


class TestCensusDirectoryDiscoveryValidateUrl:
    """validate_download_url() must pass through on 429 (rate-limit ≠ file absent)."""

    def test_429_returns_true(self):
        """A 429 response means rate-limited, not missing — validation should pass."""
        discovery = CensusDirectoryDiscovery()
        fake_response = MagicMock()
        fake_response.status_code = 429
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            return_value=fake_response,
        ):
            result = discovery.validate_download_url("https://www2.census.gov/geo/tiger/TIGER2020/CD/tl_2020_us_cd116.zip")
        assert result is True

    def test_404_raises(self):
        """A genuine 404 must still raise BoundaryUrlValidationError."""
        from siege_utilities.geo.spatial_data import BoundaryUrlValidationError
        discovery = CensusDirectoryDiscovery()
        fake_response = MagicMock()
        fake_response.status_code = 404
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            return_value=fake_response,
        ):
            with pytest.raises(BoundaryUrlValidationError):
                discovery.validate_download_url("https://www2.census.gov/geo/tiger/TIGER2020/CD/tl_2020_us_cd116.zip")


class TestCensusUrlConstruction:
    """URL construction edge cases: filename abbreviations and per-state CD 2022+."""

    def _make_discovery(self, available_types: dict) -> CensusDirectoryDiscovery:
        d = CensusDirectoryDiscovery()
        d.discover_boundary_types = MagicMock(return_value=available_types)
        return d

    def test_block_group_uses_bg_abbreviation(self):
        """Census filenames use 'bg' not 'block_group' — URL must reflect that."""
        discovery = self._make_discovery({"block_group": "BG"})
        url = discovery.construct_download_url(2020, "block_group", state_fips="01")
        assert "block_group" not in url
        assert url.endswith("tl_2020_01_bg.zip")

    def test_cd_2022_uses_per_state_url(self):
        """Census dropped the national CD file for 2022+; per-state URL must be used."""
        discovery = self._make_discovery({"cd": "CD"})
        url = discovery.construct_download_url(2022, "cd", state_fips="01", congress_number=118)
        assert "_us_" not in url
        assert url.endswith("tl_2022_01_cd118.zip")

    def test_cd_pre_2022_uses_national_url(self):
        """Before 2022, CD is a single national file."""
        discovery = self._make_discovery({"cd": "CD"})
        url = discovery.construct_download_url(2020, "cd", congress_number=116)
        assert "_us_" in url
        assert url.endswith("tl_2020_us_cd116.zip")
