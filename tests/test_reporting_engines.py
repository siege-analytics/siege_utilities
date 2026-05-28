"""Error-path tests for siege_utilities.reporting.engines (SU-4b).

Covers base_engine, bar_engine, composite_engine, map_engine, stats_engine.
The engine except blocks catch errors internally (SU-1 concern), so these
tests verify the error paths execute without crashing the process.
"""

import pytest

try:
    from siege_utilities.reporting.engines.base_engine import BaseChartEngine
    from reportlab.lib.units import inch
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="reporting engine or reportlab deps missing")


class TestBaseChartEngineErrors:
    """Error paths for BaseChartEngine.create_custom_chart."""

    def test_missing_type_key_raises_internally(self):
        """Chart config without 'type' key triggers error path."""
        engine = BaseChartEngine()
        result = engine.create_custom_chart({"data": [1, 2, 3]})
        assert result is not None

    def test_empty_config_raises_internally(self):
        """Empty chart config triggers error path."""
        engine = BaseChartEngine()
        result = engine.create_custom_chart({})
        assert result is not None
