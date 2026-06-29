"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.base_engine.

create_custom_chart validates required config keys; the missing-keys ValueError
is re-raised by the handler as a RuntimeError.
"""
import pytest
from siege_utilities.reporting.chart_generator import ChartGenerator


def test_create_custom_chart_raises_on_missing_required_keys():
    g = ChartGenerator()
    with pytest.raises(RuntimeError) as exc_info:
        g.create_custom_chart({})  # missing 'type' and 'data'
    assert "Custom Chart Error" in str(exc_info.value)
