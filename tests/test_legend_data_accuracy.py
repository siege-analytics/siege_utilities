"""Behavioral regressions for map and heatmap legend accuracy (#1535)."""

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba

from siege_utilities.reporting.legend_manager import LegendManager


@pytest.fixture(autouse=True)
def close_figures():
    with plt.style.context("default"):
        yield
        plt.close("all")


@pytest.fixture(params=["elements", "table"])
def heatmap_legend(request):
    """Read the labels and swatches actually handed to each renderer."""
    manager = LegendManager()

    def build(minimum, maximum, levels=5):
        if request.param == "elements":
            patches = manager.create_heatmap_legend_elements(
                minimum, maximum, levels=levels,
            )
            return (
                [patch.get_label() for patch in patches],
                [patch.get_facecolor() for patch in patches],
            )

        pytest.importorskip("reportlab")
        table = manager.create_heatmap_legend_table(
            minimum, maximum, levels=levels,
        )
        labels = [row[2] for row in table._cellvalues[1:]]
        swatches = [
            color.rgba()
            for command, start, end, color in table._bkgrndcmds
            if command == "BACKGROUND" and start[0] == 1
        ]
        return labels, swatches

    return build


def _heatmap_bounds(labels):
    assert all("+" not in label for label in labels)
    return [
        tuple(float(edge.replace(",", "")) for edge in label.split(": ")[-1].split(" - "))
        for label in labels
    ]


def test_heatmap_bins_cover_full_interval(heatmap_legend):
    labels, swatches = heatmap_legend(0, 100)
    assert _heatmap_bounds(labels) == [
        (0, 20), (20, 40), (40, 60), (60, 80), (80, 100),
    ]
    assert labels[-1].endswith("100")
    expected_colors = ["#87ceeb", "#6ca9c8", "#5284a5", "#385f82", "#1e3a5f"]
    np.testing.assert_allclose(swatches, [to_rgba(color) for color in expected_colors])


@pytest.mark.parametrize(
    "maximum, expected_edges",
    [
        (1, [0, 0.2, 0.4, 0.6, 0.8, 1]),
        (0.00001, [0, 0.000002, 0.000004, 0.000006, 0.000008, 0.00001]),
        (7.5, [0, 1.5, 3, 4.5, 6, 7.5]),
    ],
    ids=["unit", "tiny", "step-over-one-fractional"],
)
def test_heatmap_bins_preserve_fractional_edges(heatmap_legend, maximum, expected_edges):
    labels, swatches = heatmap_legend(0, maximum)
    bounds = _heatmap_bounds(labels)
    np.testing.assert_allclose(bounds, list(zip(expected_edges[:-1], expected_edges[1:])))
    assert len(swatches) == len(bounds) == 5
    assert all(lower < upper for lower, upper in bounds)


def test_single_heatmap_bin_covers_full_interval(heatmap_legend):
    labels, swatches = heatmap_legend(0, 1, levels=1)
    assert _heatmap_bounds(labels) == [(0, 1)]
    assert len(swatches) == 1


@pytest.fixture
def map_engine():
    pytest.importorskip("geopandas")
    pytest.importorskip("seaborn")
    from siege_utilities.reporting.engines.map_engine import MapChartMixin

    return MapChartMixin()


@pytest.mark.parametrize("scheme", ["default", "blue_red", "green_orange"])
def test_displayed_bivariate_legend_matches_map_colors(map_engine, scheme):
    import pandas as pd

    matrix = map_engine._create_bivariate_color_matrix(scheme)
    features = pd.DataFrame({"var1": [0, 1, 2] * 3, "var2": np.repeat([0, 1, 2], 3)})
    colored = map_engine._apply_bivariate_colors(features, "var1", "var2", matrix)
    fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
    map_engine._add_bivariate_legend(ax, "var1", "var2", matrix)
    legend_ax = fig.axes[-1]
    fig.canvas.draw()
    pixels = np.asarray(fig.canvas.buffer_rgba()) / 255.0

    # Sample the rendered canvas, so origin and inverted axes both affect the
    # assertion. Start with the visible TOP row: it must be var2 High.
    for row in (2, 1, 0):
        for col in range(3):
            x, y = legend_ax.transAxes.transform(((col + 0.5) / 3, (row + 0.5) / 3))
            displayed = pixels[pixels.shape[0] - 1 - int(y), int(x)]
            expected = to_rgba(matrix[row, col])
            np.testing.assert_allclose(displayed, expected, atol=1 / 255)
            np.testing.assert_allclose(
                displayed, to_rgba(colored.iloc[row * 3 + col]["bivariate_color"]), atol=1 / 255,
            )
    assert [tick.get_text() for tick in legend_ax.get_yticklabels()] == ["Low", "Med", "High"]


@pytest.mark.parametrize(
    "classification, values, expected_edges",
    [
        ("quantiles", [100, 300, 600, 1000, 1500, 2100], [100, 300, 600, 1000, 1500, 2100]),
        ("equal_interval", [100, 300, 600, 1000, 1500, 2100], [98, 500, 900, 1300, 1700, 2100]),
        ("quantiles", [100, 100, 100, 100, 900], [100, 260, 900]),
        ("quantiles", [0, 0.002, 0.004, 0.006, 0.008, 0.01], [0, 0.002, 0.004, 0.006, 0.008, 0.01]),
    ],
    ids=["quantiles", "equal-interval", "dropped-duplicate-edges", "small-fractions"],
)
def test_advanced_choropleth_legend_shows_data_ranges(
    map_engine, monkeypatch, tmp_path, classification, values, expected_edges,
):
    import geopandas as gpd
    from shapely.geometry import box

    reportlab = pytest.importorskip("reportlab.platypus")
    from siege_utilities.reporting.chart_generator import ChartGenerator

    geodata = gpd.GeoDataFrame(
        {"geoid": range(len(values)), "value": values},
        geometry=[box(i, 0, i + 0.8, 0.8) for i in range(len(values))],
        crs="EPSG:3857",
    )
    generator = ChartGenerator(output_dir=tmp_path)
    captured = []
    convert = generator._matplotlib_to_reportlab_image

    def capture_figure(fig, width, height):
        captured.append(fig)
        return convert(fig, width, height)

    monkeypatch.setattr(generator, "_matplotlib_to_reportlab_image", capture_figure)
    result = generator.create_advanced_choropleth(
        geodata, geodata, "geoid", "value", classification=classification, bins=5,
    )
    assert isinstance(result, reportlab.Image)
    assert result.imageWidth > 0 and result.imageHeight > 0
    ax = captured[0].axes[0]
    legend = ax.get_legend()
    assert legend is not None, "Expected a discrete legend with data ranges, not a class-index colorbar"
    labels = [text.get_text() for text in legend.get_texts()]
    bounds = [tuple(float(edge.replace(",", "")) for edge in label.split(" – ")) for label in labels]
    np.testing.assert_allclose(bounds, list(zip(expected_edges[:-1], expected_edges[1:])))
    assert legend.get_title().get_text() == "value"

    # Every rendered polygon must use the swatch for its advertised interval,
    # including when qcut drops edges and fewer than five classes remain.
    swatches = [patch.get_facecolor() for patch in legend.get_patches()]
    facecolors = ax.collections[0].get_facecolors()
    for value, facecolor in zip(values, facecolors):
        class_index = next(i for i, upper in enumerate(expected_edges[1:]) if value <= upper)
        np.testing.assert_allclose(facecolor, swatches[class_index])


def _render_advanced_choropleth(monkeypatch, tmp_path, values, classification, bins):
    import geopandas as gpd
    from shapely.geometry import box

    pytest.importorskip("reportlab.platypus")
    from siege_utilities.reporting.chart_generator import ChartGenerator

    geodata = gpd.GeoDataFrame(
        {"geoid": range(len(values)), "value": values},
        geometry=[box(i, 0, i + 0.8, 0.8) for i in range(len(values))],
        crs="EPSG:3857",
    )
    generator = ChartGenerator(output_dir=tmp_path)
    captured = []
    convert = generator._matplotlib_to_reportlab_image

    def capture_figure(fig, width, height):
        captured.append(fig)
        return convert(fig, width, height)

    monkeypatch.setattr(generator, "_matplotlib_to_reportlab_image", capture_figure)
    generator.create_advanced_choropleth(
        geodata, geodata, "geoid", "value", classification=classification, bins=bins,
    )
    return captured[0].axes[0]


def test_natural_breaks_uses_fisher_jenks_not_quantiles(map_engine, monkeypatch, tmp_path):
    """#1535: natural_breaks was silently computed as quantiles."""
    import pandas as pd
    from siege_utilities.geo.classification import classify_series

    values = [1, 2, 3, 4, 5, 6, 7, 8, 100, 200]
    jenks = classify_series(values, "natural_breaks", k=3)
    _, quantile_edges = pd.qcut(values, 3, labels=False, retbins=True)
    assert not np.allclose(jenks.breaks, quantile_edges), "fixture must separate the two schemes"

    ax = _render_advanced_choropleth(monkeypatch, tmp_path, values, "natural_breaks", bins=3)

    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    bounds = [tuple(float(edge.replace(",", "")) for edge in label.split(" – ")) for label in labels]
    np.testing.assert_allclose(bounds, list(zip(jenks.breaks[:-1], jenks.breaks[1:])))

    # Polygons and legend come from the same classification.
    swatches = [patch.get_facecolor() for patch in ax.get_legend().get_patches()]
    facecolors = ax.collections[0].get_facecolors()
    for class_index, facecolor in zip(jenks.bins, facecolors):
        np.testing.assert_allclose(facecolor, swatches[class_index])


@pytest.mark.parametrize("backend", ["mapclassify", "numpy"])
def test_natural_breaks_value_on_interior_break_uses_lower_range(
    map_engine, monkeypatch, tmp_path, backend,
):
    """A value equal to an interior break belongs to the range it closes, on both backends."""
    from siege_utilities.geo import classification

    if backend == "mapclassify":
        pytest.importorskip("mapclassify")
    else:
        monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)

    # Both backends split these values into {0,1,2}, {30,31,32}, {60,61,62}; they
    # report the interior breaks differently (2/32 vs 30/60).
    values = [0, 1, 2, 30, 31, 32, 60, 61, 62]
    ax = _render_advanced_choropleth(monkeypatch, tmp_path, values, "natural_breaks", bins=3)

    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    bounds = [tuple(float(edge.replace(",", "")) for edge in label.split(" – ")) for label in labels]
    assert bounds == [(0.0, 2.0), (2.0, 32.0), (32.0, 62.0)]
    # Independent expectation: 2 closes the first range and 32 the second.
    expected_classes = [0, 0, 0, 1, 1, 1, 2, 2, 2]
    swatches = [patch.get_facecolor() for patch in ax.get_legend().get_patches()]
    facecolors = ax.collections[0].get_facecolors()
    for class_index, facecolor in zip(expected_classes, facecolors):
        np.testing.assert_allclose(facecolor, swatches[class_index])


def test_natural_breaks_constant_fractional_column(map_engine, monkeypatch, tmp_path):
    """Zero-width classes must not break legend precision."""
    ax = _render_advanced_choropleth(monkeypatch, tmp_path, [0.25] * 4, "natural_breaks", bins=3)

    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    assert labels
    assert all("0.25" in label for label in labels)


def test_natural_breaks_leaves_missing_values_unclassified(map_engine, monkeypatch, tmp_path):
    values = [1, 2, 3, float("nan"), 50, 51, 52, 100, 101, 102]

    ax = _render_advanced_choropleth(monkeypatch, tmp_path, values, "natural_breaks", bins=3)

    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    assert len(labels) == 3
    assert not any("nan" in label.lower() for label in labels)


@pytest.mark.parametrize("columns", ["pivot", "correlation"])
def test_heatmap_does_not_center_sequential_colormap(monkeypatch, tmp_path, columns):
    """#1535: center=0 with YlOrRd compressed all-positive data into half the ramp."""
    import pandas as pd

    pytest.importorskip("seaborn")
    pytest.importorskip("reportlab.platypus")
    from siege_utilities.reporting.chart_generator import ChartGenerator
    from siege_utilities.reporting.engines import stats_engine

    calls = []
    real_heatmap = stats_engine.sns.heatmap

    def spy(data, **kwargs):
        calls.append(kwargs)
        return real_heatmap(data, **kwargs)

    monkeypatch.setattr(stats_engine.sns, "heatmap", spy)
    data = pd.DataFrame({
        "x": ["a", "a", "b", "b"], "y": ["p", "q", "p", "q"],
        "count": [5, 12, 40, 75], "share": [0.1, 0.2, 0.6, 0.9],
    })
    generator = ChartGenerator(output_dir=tmp_path)
    if columns == "pivot":
        generator.create_heatmap(data, x_column="x", y_column="y", value_column="count")
    else:
        generator.create_heatmap(data[["count", "share"]])

    assert len(calls) == 1
    assert calls[0]["cmap"] == "YlOrRd"
    assert "center" not in calls[0]
