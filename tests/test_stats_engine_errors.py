"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.stats_engine.

create_heatmap requires at least two numeric columns; the shortfall raises a
ValueError that the handler re-raises as RuntimeError.
"""
import pandas as pd
import pytest
from siege_utilities.reporting.chart_generator import ChartGenerator


def test_create_heatmap_raises_with_insufficient_numeric_columns():
    g = ChartGenerator()
    with pytest.raises(RuntimeError) as exc_info:
        g.create_heatmap(pd.DataFrame({"a": [1], "b": ["x"]}))
    assert "Heatmap Error" in str(exc_info.value)
