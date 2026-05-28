"""Error-path tests for siege_utilities.reporting.analytics_reports (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="reporting deps missing")


class TestAnalyticsReportGeneratorErrors:
    """Error paths for AnalyticsReportGenerator methods."""

    def test_invalid_data_source_raises(self):
        gen = AnalyticsReportGenerator()
        with pytest.raises(ValueError, match="[Uu]nsupported"):
            gen.create_custom_analytics_report(
                data_source="nonexistent_source_zz",
                data={"key": "value"},
            )

    def test_empty_data_raises(self):
        gen = AnalyticsReportGenerator()
        with pytest.raises(Exception):
            gen.create_custom_analytics_report(
                data_source="google_analytics",
                data=None,
            )
