"""Tests for the typed exception hierarchy in reporting.chart_types (ELE-2420)."""
from __future__ import annotations

import pytest

from siege_utilities.reporting.chart_types import (
    ChartCreationError,
    ChartParameterError,
    ChartTypeRegistry,
    UnknownChartTypeError,
)


@pytest.fixture
def registry():
    return ChartTypeRegistry()


class TestCreateChart:
    def test_unknown_chart_type_raises(self, registry):
        with pytest.raises(UnknownChartTypeError, match="mystery"):
            registry.create_chart("mystery")

    def test_missing_required_param_raises(self, registry):
        # pick a registered chart type; bar_chart is a safe assumption
        known = next(iter(registry.chart_types)) if hasattr(registry, "_chart_types") else "bar_chart"
        ct = registry.get_chart_type(known)
        if not ct.required_parameters:
            pytest.skip("no required params on this chart type")
        with pytest.raises(ChartParameterError, match="missing required"):
            registry.create_chart(known)  # no kwargs → missing required

    def test_no_create_function_raises(self, registry):
        """A chart type registered without a create_function raises on create_chart."""
        from siege_utilities.reporting.chart_types import ChartType
        bare = ChartType(name="bare", category="test", required_parameters=[])
        registry.chart_types[bare.name] = bare
        with pytest.raises(ChartCreationError, match="no create function"):
            registry.create_chart("bare")

    def test_create_function_raising_becomes_chart_creation_error(self, registry):
        """A create_function that raises is translated to ChartCreationError
        with the original exception as __cause__.
        """
        from siege_utilities.reporting.chart_types import ChartType
        def boom(**kwargs):
            raise ValueError("boom inside create_function")
        ct = ChartType(
            name="boomy",
            category="test",
            required_parameters=[],
            create_function=boom,
        )
        registry.chart_types[ct.name] = ct

        with pytest.raises(ChartCreationError, match="create function") as exc_info:
            registry.create_chart("boomy")
        assert isinstance(exc_info.value.__cause__, ValueError)


class TestValidateChartParameters:
    def test_unknown_chart_type_raises(self, registry):
        with pytest.raises(UnknownChartTypeError):
            registry.validate_chart_parameters("mystery")

    def test_missing_params_returns_false(self, registry):
        """Missing params is a return-value concern, not an exception."""
        from siege_utilities.reporting.chart_types import ChartType
        ct = ChartType(
            name="strict",
            category="test",
            required_parameters=["data"],
        )
        registry.chart_types[ct.name] = ct
        assert registry.validate_chart_parameters("strict") is False

    def test_validate_function_raising_becomes_chart_parameter_error(self, registry):
        from siege_utilities.reporting.chart_types import ChartType
        def validator_raises(**kwargs):
            raise TypeError("validator oops")
        ct = ChartType(
            name="bad-validator",
            category="test",
            required_parameters=[],
            validate_function=validator_raises,
        )
        registry.chart_types[ct.name] = ct
        with pytest.raises(ChartParameterError) as exc_info:
            registry.validate_chart_parameters("bad-validator")
        assert isinstance(exc_info.value.__cause__, TypeError)


class TestExceptionHierarchy:
    def test_unknown_chart_type_is_lookup_error(self):
        assert issubclass(UnknownChartTypeError, LookupError)

    def test_chart_parameter_error_is_value_error(self):
        assert issubclass(ChartParameterError, ValueError)

    def test_chart_creation_error_is_runtime_error(self):
        assert issubclass(ChartCreationError, RuntimeError)
