"""Canonical root-import contracts for reporting mapping/viz wrappers."""

from siege_utilities import create_bivariate_choropleth
from siege_utilities import create_choropleth_map
from siege_utilities import create_flow_map
from siege_utilities import create_heatmap
from siege_utilities import create_marker_map
from siege_utilities import create_scatter_plot

from tests.reporting_chart_support import FakeChartGenerator
from tests.reporting_chart_support import install_fake_chart_generator


def test_create_scatter_plot_delegates(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_scatter_plot(
        data,
        x_column="x",
        y_column="y",
        title="Scatter",
        width=640,
        height=480,
        color="blue",
    ) == {"kind": "scatter"}

    assert FakeChartGenerator.instances[0].calls == [
        ("scatter", (data, "x", "y", "Scatter", 640, 480), {"color": "blue"})
    ]


def test_create_bivariate_choropleth_delegates(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_bivariate_choropleth(
        data,
        x_column="income",
        y_column="education",
        geoid_column="fips",
        title="Bivariate",
        width=12.0,
        height=8.0,
        palette="brand",
    ) == {"kind": "bivariate_choropleth"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "bivariate_choropleth",
            (data, "income", "education", "fips", "Bivariate", 12.0, 8.0),
            {"palette": "brand"},
        )
    ]


def test_create_heatmap_delegates(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_heatmap(
        data,
        x_column="col",
        y_column="row",
        value_column="val",
        title="Heat",
        width=8.0,
        height=6.0,
        cmap="viridis",
    ) == {"kind": "heatmap"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "heatmap",
            (data, "col", "row", "val", "Heat", 8.0, 6.0),
            {"cmap": "viridis"},
        )
    ]


def test_create_choropleth_map_delegates(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_choropleth_map(
        data,
        location_column="state",
        value_column="pop",
        title="Choropleth",
        width=8.0,
        height=6.0,
        map_type="usa",
        projection="albers",
    ) == {"kind": "choropleth"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "choropleth",
            (data, "state", "pop", "Choropleth", 8.0, 6.0, "usa"),
            {"projection": "albers"},
        )
    ]


def test_create_marker_map_delegates(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_marker_map(
        data,
        latitude_column="lat",
        longitude_column="lon",
        value_column="mag",
        label_column="name",
        title="Markers",
        width=10.0,
        height=8.0,
        map_style="carto",
        zoom_level=5,
        opacity=0.7,
    ) == {"kind": "marker"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "marker",
            (
                data,
                "lat",
                "lon",
                "mag",
                "name",
                "Markers",
                10.0,
                8.0,
                "carto",
                5,
            ),
            {"opacity": 0.7},
        )
    ]


def test_create_flow_map_delegates(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_flow_map(
        data,
        origin_lat_column="olat",
        origin_lon_column="olon",
        dest_lat_column="dlat",
        dest_lon_column="dlon",
        flow_value_column="volume",
        title="Flows",
        width=12.0,
        height=10.0,
        curve=0.3,
    ) == {"kind": "flow"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "flow",
            (
                data,
                "olat",
                "olon",
                "dlat",
                "dlon",
                "volume",
                "Flows",
                12.0,
                10.0,
            ),
            {"curve": 0.3},
        )
    ]
