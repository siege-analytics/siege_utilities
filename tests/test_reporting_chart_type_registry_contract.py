"""Canonical root-import contract for the reporting chart type registry."""

import pytest

from siege_utilities import ChartTypeRegistry
from siege_utilities.reporting.chart_types import ChartCreationError
from siege_utilities.reporting.chart_types import ChartParameterError
from siege_utilities.reporting.chart_types import ChartType
from siege_utilities.reporting.chart_types import UnknownChartTypeError


def test_chart_type_registry_registers_lists_and_describes_custom_type():
    registry = ChartTypeRegistry()
    chart_type = ChartType(
        name="custom_metric",
        category="custom",
        description="Custom metric chart",
        required_parameters=["data", "value"],
        optional_parameters={"title": "Default title"},
        custom_options={"palette": "brand"},
        supports_interactive=True,
    )

    registry.register_chart_type(chart_type)

    assert registry.get_chart_type("custom_metric") is chart_type
    assert "custom_metric" in registry.list_chart_types()
    assert registry.list_chart_types("custom") == ["custom_metric"]
    assert "custom" in registry.get_chart_categories()
    assert registry.get_chart_help("custom_metric") == {
        "name": "custom_metric",
        "category": "custom",
        "description": "Custom metric chart",
        "required_parameters": ["data", "value"],
        "optional_parameters": {"title": "Default title"},
        "custom_options": {"palette": "brand"},
        "supports_interactive": True,
        "supports_3d": False,
        "supports_animation": False,
    }


def test_chart_type_registry_create_chart_applies_defaults_and_wraps_errors():
    registry = ChartTypeRegistry()
    calls = []
    chart_type = ChartType(
        name="custom_metric",
        category="custom",
        required_parameters=["data", "value"],
        optional_parameters={"title": "Default title"},
        create_function=lambda **kwargs: calls.append(kwargs) or "figure",
    )
    registry.register_chart_type(chart_type)

    assert (
        registry.create_chart("custom_metric", data=[1], value="sales")
        == "figure"
    )
    assert calls == [
        {"data": [1], "value": "sales", "title": "Default title"}
    ]

    assert registry.validate_chart_parameters(
        "custom_metric",
        data=[1],
        value="sales",
    ) is True
    assert (
        registry.validate_chart_parameters("custom_metric", data=[1])
        is False
    )
    with pytest.raises(UnknownChartTypeError, match="missing"):
        registry.create_chart("missing", data=[])
    with pytest.raises(ChartParameterError, match="validate_function"):
        broken = ChartType(
            name="broken_validator",
            category="custom",
            required_parameters=[],
            validate_function=lambda **kwargs: (_ for _ in ()).throw(
                ValueError("bad validator")
            ),
        )
        registry.register_chart_type(broken)
        registry.validate_chart_parameters("broken_validator")
    with pytest.raises(ChartCreationError, match="create function"):
        broken_create = ChartType(
            name="broken_create",
            category="custom",
            required_parameters=[],
            create_function=lambda **kwargs: (_ for _ in ()).throw(
                ValueError("bad create")
            ),
        )
        registry.register_chart_type(broken_create)
        registry.create_chart("broken_create")
