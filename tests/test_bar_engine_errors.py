"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.bar_engine.

Chart errors propagate so report generation cannot report success.
"""
import pandas as pd
import pytest

# The reporting engines build ReportLab Image objects (reportlab is the
# `reporting` extra); skip when it is absent (the no-GDAL / no-reporting CI
# job) so the image-conversion path is not exercised without its dependency.
try:
    import reportlab  # noqa: F401
except ImportError:
    pytest.skip("reportlab not available", allow_module_level=True)

from siege_utilities.reporting.chart_generator import ChartGenerator


def test_create_bar_chart_raises_on_invalid_data():
    g = ChartGenerator()
    with pytest.raises(RuntimeError, match="Chart generation failed") as exc:
        g.create_bar_chart(pd.DataFrame({"label": ["x", "y"]}))
    assert isinstance(exc.value.__cause__, ValueError)
