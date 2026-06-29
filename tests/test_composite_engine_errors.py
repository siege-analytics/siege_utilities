"""Error-path coverage (SU-4b) for siege_utilities.reporting.engines.composite_engine.

create_convergence_diagram requires at least one source; an empty list raises a
ValueError that the handler re-raises as RuntimeError.
"""
import pytest
from siege_utilities.reporting.chart_generator import ChartGenerator


def test_create_convergence_diagram_raises_with_no_sources():
    g = ChartGenerator()
    with pytest.raises(RuntimeError) as exc_info:
        g.create_convergence_diagram(sources=[])
    assert "Convergence Diagram Error" in str(exc_info.value)
