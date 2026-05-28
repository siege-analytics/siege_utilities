"""Error-path tests for siege_utilities.reporting.engines.stats_engine (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.engines.stats_engine import StatsChartMixin
    import pandas as pd
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="stats_engine deps missing")


class _StatsEngine(StatsChartMixin):
    pass


class TestStatsChartMixinErrors:
    """Error paths for StatsChartMixin methods."""

    def test_empty_dataframe_heatmap(self):
        engine = _StatsEngine()
        result = engine.create_heatmap(pd.DataFrame())
        assert result is not None

    def test_empty_dataframe_scatter(self):
        engine = _StatsEngine()
        result = engine.create_scatter_plot(
            pd.DataFrame(), x_column="x", y_column="y"
        )
        assert result is not None
