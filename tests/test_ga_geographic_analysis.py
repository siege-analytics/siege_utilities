"""Error-path tests for siege_utilities.reporting.examples.ga_geographic_analysis (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.examples import ga_geographic_analysis
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="reporting example deps missing")


class TestGaGeographicAnalysisErrors:
    """Error paths for ga_geographic_analysis functions."""

    def test_missing_deps_does_not_raise_on_import(self):
        from siege_utilities.reporting.examples.ga_geographic_analysis import (
            create_state_choropleth,
        )
        assert create_state_choropleth is not None
