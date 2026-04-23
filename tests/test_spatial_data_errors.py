"""Tests for the SpatialDataError hierarchy in geo.spatial_data (ELE-2420).

See docs/FAILURE_MODES.md CC1. Previously, every HTTP / parse failure in
GovernmentDataSource and OpenStreetMapDataSource was caught and silently
turned into ``return None`` — producing fake "no data" results
indistinguishable from legitimate empty responses.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.spatial_data import (
    GovernmentDataSource,
    OpenStreetMapDataSource,
    SpatialDataError,
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
