"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.bar_engine.

create_bar_chart catches a no-numeric-columns ValueError and renders a
placeholder instead of propagating. This exercises that except handler.
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


def test_create_bar_chart_renders_placeholder_on_invalid_data():
    g = ChartGenerator()
    # No numeric column -> internal ValueError -> handler renders placeholder.
    result = g.create_bar_chart(pd.DataFrame({"label": ["x", "y"]}))
    assert result is not None
