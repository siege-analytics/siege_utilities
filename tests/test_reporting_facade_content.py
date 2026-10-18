"""Error-path coverage (SU-4b) and wide-DataFrame regression for the reporting
facades (#1461).

`_chart_images` raises `ValueError` on an unsupported facade chart type; the
error-path gate needs a test it can map to `_facade_content.py`. The wide-frame
case checks that a DataFrame with dozens of columns still produces a PDF
instead of a ReportLab "negative availWidth" failure.
"""
import pytest

pytest.importorskip("reportlab")
pd = pytest.importorskip("pandas")

from siege_utilities.reporting._facade_content import _chart_images
from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
from siege_utilities.reporting.report_generator import ReportGenerator


def test_unsupported_chart_type_raises(tmp_path):
    gen = ReportGenerator("Acme", output_dir=tmp_path)
    with pytest.raises(ValueError, match="Unsupported facade chart type"):
        _chart_images({"type": "doughnut", "data": {"labels": ["a"]}}, gen)


def test_custom_report_with_wide_dataframe_still_writes_pdf(tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    df = pd.DataFrame({f"c{i}": range(5) for i in range(40)})
    path = gen.create_custom_analytics_report("dataframe", df, {"title": "Wide"})
    assert path.is_file() and path.stat().st_size > 0
