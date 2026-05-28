"""Error-path tests for siege_utilities.geo.census_data_selector (SU-4b)."""

import pytest

try:
    from siege_utilities.geo.census_data_selector import (
        CensusDataSelector,
        select_census_datasets,
    )
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or census_data_selector deps missing")


class TestSelectDatasetsErrors:
    """Error paths for CensusDataSelector.select_datasets_for_analysis."""

    def test_invalid_geography_level_returns_error(self):
        """Invalid geography level returns error dict."""
        result = select_census_datasets("demographics", "galaxy_cluster")
        assert "error" in result
        assert "Invalid geography level" in result["error"]

    def test_unknown_analysis_type_returns_error(self):
        """Unknown analysis type returns error dict."""
        result = select_census_datasets("quantum_physics", "county")
        assert "error" in result
        assert "Unknown analysis type" in result["error"]


class TestSelectDatasetsHappyPath:
    """Sanity checks for select_census_datasets."""

    def test_valid_request_returns_recommendations(self):
        """Valid analysis type and geography returns recommendations."""
        result = select_census_datasets("demographics", "county")
        assert "error" not in result
        assert "primary_recommendation" in result
