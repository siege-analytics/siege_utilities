"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.bar_engine.

create_bar_chart catches a no-numeric-columns ValueError and renders a
placeholder instead of propagating. This exercises that except handler.
"""
import pandas as pd
from siege_utilities.reporting.chart_generator import ChartGenerator


def test_create_bar_chart_renders_placeholder_on_invalid_data():
    g = ChartGenerator()
    # No numeric column -> internal ValueError -> handler renders placeholder.
    result = g.create_bar_chart(pd.DataFrame({"label": ["x", "y"]}))
    assert result is not None
