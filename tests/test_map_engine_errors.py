"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.map_engine.

create_choropleth_map requires geo_data; passing None raises ValueError before
any rendering.
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


def test_create_choropleth_map_requires_geo_data():
    g = ChartGenerator()
    with pytest.raises(ValueError) as exc_info:
        g.create_choropleth_map(pd.DataFrame({"geoid": ["1"], "v": [1]}), geo_data=None)
    assert "geo_data is required" in str(exc_info.value)
