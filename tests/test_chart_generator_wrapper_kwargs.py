"""Regression coverage for #1517 at the actual engine method boundary.

Autospecced mixin spies enforce engine signatures without rendering charts or
requiring matplotlib, Folium, or ReportLab. Only initialization is bypassed.
"""

from inspect import signature
from unittest.mock import create_autospec, sentinel

import pandas as pd
import pytest

from siege_utilities.reporting import chart_generator as charts


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "a": [1, 2],
            "b": [3, 4],
            "loc": ["01", "02"],
            "val": [5, 6],
            "date": [1, 2],
            "votes": [7, 8],
        }
    )


@pytest.fixture
def spy_engine(monkeypatch):
    monkeypatch.setattr(charts.BaseChartEngine, "__init__", lambda self: None)

    def install(mixin, method):
        spy = create_autospec(getattr(mixin, method), return_value=sentinel.chart)
        monkeypatch.setattr(mixin, method, spy)
        return spy

    return install


def received_parameters(spy):
    """Bind the recorded call to the real engine signature for useful failures."""
    bound = signature(spy).bind(*spy.call_args.args, **spy.call_args.kwargs)
    bound.apply_defaults()
    return bound.arguments


def test_scatter_title_reaches_engine_as_title(df, spy_engine):
    spy = spy_engine(charts.StatsChartMixin, "create_scatter_plot")
    assert charts.create_scatter_plot(df, "a", "b", "T") is sentinel.chart
    assert received_parameters(spy)["title"] == "T"
    assert spy.call_args.kwargs["title"] == "T"
    assert spy.call_args.kwargs.get("color_column") is None
    assert len(spy.call_args.args) == 1  # only self is positional
    assert spy.call_args.kwargs["width"] == 8.0
    assert spy.call_args.kwargs["height"] == 6.0


def test_choropleth_location_is_not_geometry(df, spy_engine):
    spy = spy_engine(charts.MapChartMixin, "create_choropleth_map")
    assert charts.create_choropleth_map(df, "loc", "val") is sentinel.chart
    assert received_parameters(spy)["geo_data"] != "loc"
    assert spy.call_args.kwargs["location_column"] == "loc"
    assert spy.call_args.kwargs["value_column"] == "val"
    assert spy.call_args.kwargs["geo_data"] is None
    assert len(spy.call_args.args) == 1


@pytest.mark.parametrize(
    "y_column, expected",
    [
        ("votes", ["votes"]),
        (["votes", "val"], ["votes", "val"]),
        (None, None),
    ],
)
def test_line_normalizes_single_column(df, spy_engine, y_column, expected):
    spy = spy_engine(charts.BarChartMixin, "create_line_chart")
    assert charts.create_line_chart(df, "date", y_column) is sentinel.chart
    assert received_parameters(spy)["y_columns"] == expected
    assert spy.call_args.kwargs["y_columns"] == expected
    assert spy.call_args.kwargs["x_column"] == "date"
    assert len(spy.call_args.args) == 1


def test_bivariate_columns_reach_matching_engine_parameters(df, spy_engine):
    spy = spy_engine(charts.MapChartMixin, "create_bivariate_choropleth")
    assert charts.create_bivariate_choropleth(df, "a", "b", "loc", "T") is sentinel.chart
    assert received_parameters(spy)["value_column1"] == "a"
    assert spy.call_args.kwargs["value_column1"] == "a"
    assert spy.call_args.kwargs["value_column2"] == "b"
    assert spy.call_args.kwargs["location_column"] == "loc"
    assert spy.call_args.kwargs["geo_data"] is None
    assert spy.call_args.kwargs["title"] == "T"
    assert len(spy.call_args.args) == 1


@pytest.mark.parametrize(
    "method, columns",
    [
        ("create_choropleth_map", ("loc", "val")),
        ("create_bivariate_choropleth", ("a", "b", "loc")),
    ],
)
def test_map_wrappers_forward_explicit_geometry(df, spy_engine, method, columns):
    spy = spy_engine(charts.MapChartMixin, method)
    getattr(charts, method)(df, *columns, geo_data=sentinel.geometry)
    assert spy.call_args.kwargs["geo_data"] is sentinel.geometry
    assert spy.call_args.kwargs["data"] is df
    assert len(spy.call_args.args) == 1


@pytest.mark.parametrize(
    "method, mixin, columns, extra, expected",
    [
        (
            "create_bar_chart",
            charts.BarChartMixin,
            ("a", "b"),
            {"show_legend": False},
            {"x_column": "a", "y_column": "b"},
        ),
        (
            "create_pie_chart",
            charts.BarChartMixin,
            ("loc", "val"),
            {"show_legend": False},
            {"labels_column": "loc", "values_column": "val"},
        ),
        (
            "create_scatter_plot",
            charts.StatsChartMixin,
            ("a", "b"),
            {"color_column": "loc"},
            {"x_column": "a", "y_column": "b"},
        ),
        (
            "create_heatmap",
            charts.StatsChartMixin,
            ("a", "b", "val"),
            {},
            {"x_column": "a", "y_column": "b", "value_column": "val"},
        ),
        (
            "create_marker_map",
            charts.MapChartMixin,
            ("a", "b"),
            {"zoom_level": 4},
            {"latitude_column": "a", "longitude_column": "b"},
        ),
        (
            "create_flow_map",
            charts.MapChartMixin,
            ("a", "b", "a", "b"),
            {},
            {
                "origin_lat_column": "a",
                "origin_lon_column": "b",
                "dest_lat_column": "a",
                "dest_lon_column": "b",
            },
        ),
    ],
)
def test_wrappers_forward_columns_sizes_and_options(
    df, spy_engine, method, mixin, columns, extra, expected
):
    spy = spy_engine(mixin, method)
    assert (
        getattr(charts, method)(df, *columns, title="T", width=7.5, height=4.25, **extra)
        is sentinel.chart
    )
    assert len(spy.call_args.args) == 1
    kwargs = spy.call_args.kwargs
    assert kwargs["data"] is df
    for key, value in dict(expected, title="T", width=7.5, height=4.25, **extra).items():
        assert kwargs[key] == value


@pytest.mark.parametrize(
    "chart_type, mixin, method, expected",
    [
        ("bar", charts.BarChartMixin, "create_bar_chart", {"x_column": "loc", "y_column": "a"}),
        (
            "line",
            charts.BarChartMixin,
            "create_line_chart",
            {"x_column": "loc", "y_columns": ["a", "b"]},
        ),
        (
            "pie",
            charts.BarChartMixin,
            "create_pie_chart",
            {"labels_column": "loc", "values_column": "a"},
        ),
        (
            "scatter",
            charts.StatsChartMixin,
            "create_scatter_plot",
            {"x_column": "loc", "y_column": "a"},
        ),
        ("heatmap", charts.StatsChartMixin, "create_heatmap", {}),
        (
            "choropleth",
            charts.MapChartMixin,
            "create_choropleth_map",
            {"location_column": "loc", "value_column": "a", "geo_data": sentinel.geometry},
        ),
        (
            "bivariate_choropleth",
            charts.MapChartMixin,
            "create_bivariate_choropleth",
            {
                "location_column": "loc",
                "value_column1": "a",
                "value_column2": "b",
                "geo_data": sentinel.geometry,
            },
        ),
        ("unknown", charts.BarChartMixin, "create_bar_chart", {"x_column": "loc", "y_column": "a"}),
    ],
)
def test_dataframe_dispatcher(df, spy_engine, chart_type, mixin, method, expected):
    spy = spy_engine(mixin, method)
    options = {"geo_data": sentinel.geometry} if "geo_data" in expected else {}
    assert (
        charts.generate_chart_from_dataframe(
            df,
            chart_type,
            "loc",
            ["a", "b"],
            "T",
            7.5,
            4.25,
            **options,
        )
        is sentinel.chart
    )
    assert len(spy.call_args.args) == 1
    assert spy.call_args.kwargs["data"] is df
    for key, value in dict(expected, title="T", width=7.5, height=4.25).items():
        assert spy.call_args.kwargs[key] == value


@pytest.mark.parametrize(
    "chart_type, mixin, method, options",
    [
        ("bar", charts.BarChartMixin, "create_bar_chart", {"x_column": "a", "y_column": "b"}),
        (
            "line",
            charts.BarChartMixin,
            "create_line_chart",
            {"x_column": "a", "y_columns": ["b", "val"]},
        ),
        (
            "pie",
            charts.BarChartMixin,
            "create_pie_chart",
            {"labels_column": "loc", "values_column": "val"},
        ),
        (
            "scatter",
            charts.StatsChartMixin,
            "create_scatter_plot",
            {"x_column": "a", "y_column": "b", "color_column": "loc"},
        ),
        (
            "heatmap",
            charts.StatsChartMixin,
            "create_heatmap",
            {"x_column": "a", "y_column": "b", "value_column": "val"},
        ),
        (
            "choropleth",
            charts.MapChartMixin,
            "create_choropleth_map",
            {"location_column": "loc", "value_column": "val", "geo_data": sentinel.geometry},
        ),
        (
            "bivariate_choropleth",
            charts.MapChartMixin,
            "create_bivariate_choropleth",
            {"location_column": "loc", "value_columns": ["a", "b"], "geo_data": sentinel.geometry},
        ),
        ("unknown", charts.BarChartMixin, "create_bar_chart", {"x_column": "a", "y_column": "b"}),
    ],
)
def test_custom_dispatcher(df, spy_engine, chart_type, mixin, method, options):
    spy = spy_engine(mixin, method)
    config = dict(options, type=chart_type, data=df, title="T")
    assert (
        charts.ChartGenerator().create_custom_chart(config, width=7.5, height=4.25)
        is sentinel.chart
    )
    assert len(spy.call_args.args) == 1
    assert spy.call_args.kwargs["data"] is df
    expected = dict(options, title="T", width=7.5, height=4.25)
    if "value_columns" in expected:
        expected["value_column1"], expected["value_column2"] = expected.pop("value_columns")
    for key, value in expected.items():
        assert spy.call_args.kwargs[key] == value


@pytest.mark.parametrize("method", ["create_bar_chart", "create_line_chart", "create_pie_chart"])
def test_basic_wrapper_defaults_are_inches(df, spy_engine, method):
    spy = spy_engine(charts.BarChartMixin, method)
    getattr(charts, method)(df)
    assert spy.call_args.kwargs["width"] == 8.0
    assert spy.call_args.kwargs["height"] == 6.0


def test_engine_exceptions_propagate(df, spy_engine):
    spy = spy_engine(charts.StatsChartMixin, "create_scatter_plot")
    spy.side_effect = RuntimeError("render failed")
    with pytest.raises(RuntimeError, match="render failed"):
        charts.create_scatter_plot(df, "a", "b", "T")
