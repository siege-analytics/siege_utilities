"""Error-path tests for siege_utilities.reporting.engines.bar_engine (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.engines.bar_engine import BarChartMixin
    import pandas as pd
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="bar_engine deps missing")


class _BarEngine(BarChartMixin):
    pass


class TestBarChartMixinErrors:
    """Error paths for BarChartMixin methods."""

    def test_empty_dataframe_bar_chart(self):
        engine = _BarEngine()
        result = engine.create_bar_chart(pd.DataFrame())
        assert result is not None

    def test_empty_dataframe_line_chart(self):
        engine = _BarEngine()
        result = engine.create_line_chart(pd.DataFrame())
        assert result is not None

    def test_empty_dataframe_pie_chart(self):
        engine = _BarEngine()
        result = engine.create_pie_chart(pd.DataFrame())
        assert result is not None
