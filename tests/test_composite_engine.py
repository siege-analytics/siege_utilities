"""Error-path tests for siege_utilities.reporting.engines.composite_engine (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.engines.composite_engine import CompositeChartMixin
    import pandas as pd
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="composite_engine deps missing")


class _CompositeEngine(CompositeChartMixin):
    pass


class TestCompositeChartMixinErrors:
    """Error paths for CompositeChartMixin methods."""

    def test_empty_sources_convergence(self):
        engine = _CompositeEngine()
        result = engine.create_convergence_diagram(sources=[])
        assert result is not None

    def test_empty_dataframe_summary(self):
        engine = _CompositeEngine()
        result = engine.create_dataframe_summary_charts(pd.DataFrame())
        assert result is not None
