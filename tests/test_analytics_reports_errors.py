"""Error-path coverage (SU-4b) for reporting.analytics_reports."""
import pytest
from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator


def test_create_custom_analytics_report_rejects_unknown_data_source(tmp_path):
    gen = AnalyticsReportGenerator(client_name="test", output_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        gen.create_custom_analytics_report("bogus_source", {}, {})
    assert "Unsupported data source" in str(exc_info.value)
