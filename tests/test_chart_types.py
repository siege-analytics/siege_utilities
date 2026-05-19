"""Tests for siege_utilities.reporting.chart_types module."""

import pytest
pytest.importorskip("matplotlib")
from unittest.mock import MagicMock
from siege_utilities.reporting.chart_types import (
    ChartCreationError,
    ChartParameterError,
    ChartType,
    ChartTypeRegistry,
    UnknownChartTypeError,
    get_chart_registry,
)


class TestChartType:
    """Tests for ChartType dataclass."""

    def test_basic_creation(self):
        ct = ChartType(name="test", category="statistical")
        assert ct.name == "test"
        assert ct.category == "statistical"
        assert ct.required_parameters == []
        assert ct.optional_parameters == {}

    def test_with_parameters(self):
        ct = ChartType(
            name="bar",
            category="statistical",
            required_parameters=["data", "x_column"],
            optional_parameters={"title": "", "color": "blue"},
        )
        assert ct.required_parameters == ["data", "x_column"]
        assert ct.optional_parameters["color"] == "blue"

    def test_supports_flags(self):
        ct = ChartType(
            name="3d_map",
            category="geographic",
            supports_3d=True,
            supports_interactive=True,
        )
        assert ct.supports_3d is True
        assert ct.supports_interactive is True
        assert ct.supports_animation is False

    def test_default_dimensions(self):
        ct = ChartType(name="test", category="statistical")
        assert ct.default_width == 10.0
        assert ct.default_height == 8.0
        assert ct.default_dpi == 300


class TestChartTypeRegistry:
    """Tests for ChartTypeRegistry."""

    def test_default_types_registered(self):
        registry = ChartTypeRegistry()
        types = registry.list_chart_types()
        assert len(types) > 0
        assert "bar_chart" in types
        assert "line_chart" in types
        assert "scatter_plot" in types

    def test_geographic_types(self):
        registry = ChartTypeRegistry()
        geo_types = registry.list_chart_types(category="geographic")
        assert "bivariate_choropleth" in geo_types
        assert "marker_map" in geo_types

    def test_statistical_types(self):
        registry = ChartTypeRegistry()
        stat_types = registry.list_chart_types(category="statistical")
        assert "bar_chart" in stat_types
        assert "line_chart" in stat_types

    def test_temporal_types(self):
        registry = ChartTypeRegistry()
        temporal_types = registry.list_chart_types(category="temporal")
        assert "time_series" in temporal_types

    def test_comparative_types(self):
        registry = ChartTypeRegistry()
        comp_types = registry.list_chart_types(category="comparative")
        assert "comparison_chart" in comp_types

    def test_get_chart_categories(self):
        registry = ChartTypeRegistry()
        categories = registry.get_chart_categories()
        assert "geographic" in categories
        assert "statistical" in categories
        assert "temporal" in categories
        assert "comparative" in categories

    def test_register_custom_type(self):
        registry = ChartTypeRegistry()
        custom = ChartType(name="custom_chart", category="custom")
        registry.register_chart_type(custom)
        assert registry.get_chart_type("custom_chart") is custom

    def test_get_nonexistent_type(self):
        registry = ChartTypeRegistry()
        assert registry.get_chart_type("nonexistent") is None

    def test_list_filtered_by_category(self):
        registry = ChartTypeRegistry()
        all_types = registry.list_chart_types()
        geo_types = registry.list_chart_types(category="geographic")
        assert len(geo_types) < len(all_types)


class TestChartTypeRegistryCreateChart:
    """Tests for create_chart method."""

    def test_create_with_function(self):
        registry = ChartTypeRegistry()
        mock_figure = MagicMock()
        mock_fn = MagicMock(return_value=mock_figure)

        ct = ChartType(
            name="test_create",
            category="test",
            required_parameters=["data"],
            create_function=mock_fn,
        )
        registry.register_chart_type(ct)
        result = registry.create_chart("test_create", data=[1, 2, 3])
        assert result is mock_figure
        mock_fn.assert_called_once()

    def test_create_missing_params(self):
        registry = ChartTypeRegistry()
        ct = ChartType(
            name="needs_params",
            category="test",
            required_parameters=["data", "x_column"],
        )
        registry.register_chart_type(ct)
        with pytest.raises(ChartParameterError):
            registry.create_chart("needs_params", data=[1])

    def test_create_no_function(self):
        registry = ChartTypeRegistry()
        ct = ChartType(name="no_fn", category="test", required_parameters=[])
        registry.register_chart_type(ct)
        with pytest.raises(ChartCreationError):
            registry.create_chart("no_fn")

    def test_create_nonexistent_type(self):
        registry = ChartTypeRegistry()
        with pytest.raises(UnknownChartTypeError):
            registry.create_chart("nonexistent")

    def test_create_function_raises(self):
        registry = ChartTypeRegistry()
        mock_fn = MagicMock(side_effect=RuntimeError("boom"))
        ct = ChartType(
            name="error_chart",
            category="test",
            required_parameters=[],
            create_function=mock_fn,
        )
        registry.register_chart_type(ct)
        with pytest.raises(ChartCreationError) as exc_info:
            registry.create_chart("error_chart")
        assert isinstance(exc_info.value.__cause__, RuntimeError)


class TestChartTypeRegistryValidation:
    """Tests for validate_chart_parameters."""

    def test_valid_params(self):
        registry = ChartTypeRegistry()
        assert registry.validate_chart_parameters(
            "bar_chart", data=[1], x_column="x", y_column="y"
        ) is True

    def test_missing_required(self):
        registry = ChartTypeRegistry()
        assert registry.validate_chart_parameters("bar_chart", data=[1]) is False

    def test_nonexistent_type(self):
        registry = ChartTypeRegistry()
        with pytest.raises(UnknownChartTypeError):
            registry.validate_chart_parameters("nonexistent")

    def test_custom_validation_function(self):
        registry = ChartTypeRegistry()
        mock_validator = MagicMock(return_value=True)
        ct = ChartType(
            name="validated",
            category="test",
            required_parameters=["data"],
            validate_function=mock_validator,
        )
        registry.register_chart_type(ct)
        result = registry.validate_chart_parameters("validated", data=[1])
        assert result is True
        mock_validator.assert_called_once()


class TestChartTypeRegistryHelp:
    """Tests for get_chart_help."""

    def test_help_for_existing(self):
        registry = ChartTypeRegistry()
        help_info = registry.get_chart_help("bar_chart")
        assert help_info["name"] == "bar_chart"
        assert help_info["category"] == "statistical"
        assert "required_parameters" in help_info

    def test_help_for_nonexistent(self):
        registry = ChartTypeRegistry()
        assert registry.get_chart_help("nonexistent") == {}


class TestAddChartCreator:
    """Tests for add_chart_creator."""

    def test_add_creator(self):
        registry = ChartTypeRegistry()
        mock_fn = MagicMock()
        registry.add_chart_creator("bar_chart", mock_fn)
        ct = registry.get_chart_type("bar_chart")
        assert ct.create_function is mock_fn

    def test_add_to_nonexistent(self):
        registry = ChartTypeRegistry()
        mock_fn = MagicMock()
        registry.add_chart_creator("nonexistent", mock_fn)
        # add_chart_creator on a nonexistent type logs a warning but doesn't create it
        assert registry.get_chart_type("nonexistent") is None


class TestGetChartRegistry:
    """Tests for get_chart_registry global function."""

    def test_returns_registry(self):
        registry = get_chart_registry()
        assert isinstance(registry, ChartTypeRegistry)
