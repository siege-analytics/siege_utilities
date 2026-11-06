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
    ],
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
