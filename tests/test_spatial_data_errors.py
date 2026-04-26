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

    def test_zcta5_added_from_2012(self):
        assert "ZCTA5" not in _known_tiger_directories_for_year(2011)
        assert "ZCTA5" in _known_tiger_directories_for_year(2012)
        assert "ZCTA5" in _known_tiger_directories_for_year(2024)

    def test_2020_decennial_extras(self):
        dirs = _known_tiger_directories_for_year(2020)
        assert "TABBLOCK20" in dirs
        assert "VTD20" in dirs

    def test_2010_decennial_extras(self):
        dirs = _known_tiger_directories_for_year(2010)
        assert "TABBLOCK10" in dirs
        assert "VTD10" in dirs

    def test_returns_sorted_list(self):
        dirs = _known_tiger_directories_for_year(2022)
        assert dirs == sorted(dirs)


class TestCensusDirectoryDiscovery429Fallback:
    """get_year_directory_contents() must return the static fallback on 429."""

    def _make_429_error(self):
        resp = MagicMock()
        resp.status_code = 429
        err = requests.exceptions.HTTPError(response=resp)
        return err

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
        ):
            first = discovery.get_year_directory_contents(2018)
        # Second call should come from cache, not trigger another request
        second = discovery.get_year_directory_contents(2018)
        assert first == second

    def test_non_429_http_error_still_returns_empty(self):
        discovery = CensusDirectoryDiscovery()
        resp = MagicMock()
        resp.status_code = 503
        err = requests.exceptions.HTTPError(response=resp)
        with patch(
            "siege_utilities.geo.spatial_data.requests.get",
            side_effect=err,
        ):
            result = discovery.get_year_directory_contents(2020, on_error="skip")
        assert result == []
