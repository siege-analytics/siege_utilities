"""Behavioral regressions for map and heatmap legend accuracy (#1535)."""

import math

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


# Decimals come from the edges as well as the widths. Width alone printed
# 0.004..0.054 as "0.00 - 0.01 ... 0.04 - 0.05", leaving out the maximum.


@pytest.mark.parametrize(
    "minimum, maximum, levels, expected",
    [
        (0.004, 0.054, 5, ["Low: 0.004 - 0.014", "0.014 - 0.024", "0.024 - 0.034",
                           "0.034 - 0.044", "High: 0.044 - 0.054"]),
        (0.004, 0.014, 1, ["Low: 0.004 - 0.014"]),
        (10.125, 10.625, 5, ["Low: 10.125 - 10.225", "10.225 - 10.325", "10.325 - 10.425",
                             "10.425 - 10.525", "High: 10.525 - 10.625"]),
        (0.006, 0.056, 5, ["Low: 0.006 - 0.016", "0.016 - 0.026", "0.026 - 0.036",
                           "0.036 - 0.046", "High: 0.046 - 0.056"]),
        (-0.054, -0.004, 5, ["Low: -0.054 - -0.044", "-0.044 - -0.034", "-0.034 - -0.024",
                             "-0.024 - -0.014", "High: -0.014 - -0.004"]),
    ],
    ids=["offset-max", "single-bin-small-range", "offset-above-ten", "offset-min", "negative-offset"],
)
def test_heatmap_labels_keep_fractional_offsets(heatmap_legend, minimum, maximum, levels, expected):
    labels, swatches = heatmap_legend(minimum, maximum, levels)
    assert labels == expected
    assert len(swatches) == levels
    bounds = _heatmap_bounds(labels)
    assert bounds[0][0] == minimum and bounds[-1][1] == maximum


def test_heatmap_labels_round_outer_bounds_outward_at_the_cap(heatmap_legend):
    """Past six decimals the outer bounds are widened so they still contain min and max."""
    minimum, maximum = 0.0000013, 0.0000113
    labels, _ = heatmap_legend(minimum, maximum, 5)
    assert labels == [
        "Low: 0.000001 - 0.000003", "0.000003 - 0.000005", "0.000005 - 0.000007",
        "0.000007 - 0.000009", "High: 0.000009 - 0.000012",
    ]
    bounds = _heatmap_bounds(labels)
    assert bounds[0][0] < minimum and bounds[-1][1] > maximum


@pytest.mark.parametrize(
    "minimum, maximum, levels, expected",
    [
        (0, 100, 5, ["Low: 0 - 20", "20 - 40", "40 - 60", "60 - 80", "High: 80 - 100"]),
        (0, 1, 5, ["Low: 0.00 - 0.20", "0.20 - 0.40", "0.40 - 0.60", "0.60 - 0.80",
                   "High: 0.80 - 1.00"]),
        (0, 7.5, 5, ["Low: 0.0 - 1.5", "1.5 - 3.0", "3.0 - 4.5", "4.5 - 6.0", "High: 6.0 - 7.5"]),
        (1000, 1e6, 4, ["Low: 1,000 - 250,750", "250,750 - 500,500", "500,500 - 750,250",
                        "High: 750,250 - 1,000,000"]),
        (0.25, 0.25, 3, ["Low: 0.25 - 0.25", "0.25 - 0.25", "High: 0.25 - 0.25"]),
        # In floats the middle edge is 2.8e-17 and the others are off by an ulp.
        (-0.2, 0.1, 3, ["Low: -0.20 - -0.10", "-0.10 - 0.00", "High: 0.00 - 0.10"]),
        (0.3, 0.9, 6, ["Low: 0.30 - 0.40", "0.40 - 0.50", "0.50 - 0.60", "0.60 - 0.70",
                       "0.70 - 0.80", "High: 0.80 - 0.90"]),
    ],
    ids=["integer", "unit", "step-over-one-fractional", "thousands", "zero-width",
         "float-noise-crossing-zero", "float-noise-above-zero"],
)
def test_heatmap_labels_without_offsets_are_unchanged(heatmap_legend, minimum, maximum, levels, expected):
    labels, _ = heatmap_legend(minimum, maximum, levels)
    assert labels == expected


def test_range_edges_round_outward_only_on_the_outer_bounds():
    from siege_utilities.reporting._range_labels import format_range_edges

    # Ordinary rounding would print 1/3 as 0.333333, below the true upper bound.
    assert format_range_edges([-2 / 3, 0.1, 1 / 3], 2) == ["-0.666667", "0.100000", "0.333334"]
    # Exact edges, including floating-point noise such as 0.1 + 0.2, are not widened.
    assert format_range_edges([0.1, 0.1 + 0.2, 0.5], 1) == ["0.1", "0.3", "0.5"]


def _advanced_labels(monkeypatch, tmp_path, values, classification, bins):
    ax = _render_advanced_choropleth(monkeypatch, tmp_path, values, classification, bins)
    return [text.get_text() for text in ax.get_legend().get_texts()]


@pytest.mark.parametrize(
    "classification, values, bins, expected",
    [
        ("quantiles", [0.0625, 5.0625, 10.0625, 15.0625], 3,
         ["0.0625 – 5.0625", "5.0625 – 10.0625", "10.0625 – 15.0625"]),
        ("equal_interval", [10.125, 12.125, 18.125, 20.125], 2,
         ["10.115 – 15.125", "15.125 – 20.125"]),
        ("natural_breaks", [0.0625, 1.0625, 10.0625, 11.0625, 20.0625, 21.0625], 3,
         ["0.0625 – 1.0625", "1.0625 – 11.0625", "11.0625 – 21.0625"]),
    ],
    ids=["quantiles", "equal-interval", "natural-breaks"],
)
@pytest.mark.parametrize("backend", ["mapclassify", "numpy"])
def test_advanced_labels_keep_fractional_offsets(
    map_engine, monkeypatch, tmp_path, classification, values, bins, expected, backend,
):
    from siege_utilities.geo import classification as classifiers

    if backend == "mapclassify":
        pytest.importorskip("mapclassify")
    else:
        monkeypatch.setattr(classifiers, "_MAPCLASSIFY_AVAILABLE", False)
    assert _advanced_labels(monkeypatch, tmp_path, values, classification, bins) == expected


def test_advanced_labels_round_outer_bounds_outward_at_the_cap(map_engine, monkeypatch, tmp_path):
    values = [1 / 3, 1, 2, 3, 4, 5, 6, 50 / 7]
    labels = _advanced_labels(monkeypatch, tmp_path, values, "quantiles", 3)
    assert labels == ["0.333333 – 2.333333", "2.333333 – 4.666667", "4.666667 – 7.142858"]
    assert float(labels[0].split(" – ")[0]) < min(values)
    assert float(labels[-1].split(" – ")[1]) > max(values)


@pytest.mark.parametrize(
    "classification, values, bins, expected",
    [
        ("quantiles", [100, 300, 600, 1000, 1500, 2100], 5,
         ["100.0 – 300.0", "300.0 – 600.0", "600.0 – 1,000.0", "1,000.0 – 1,500.0",
          "1,500.0 – 2,100.0"]),
        ("equal_interval", [100, 300, 600, 1000, 1500, 2100], 5,
         ["98.0 – 500.0", "500.0 – 900.0", "900.0 – 1,300.0", "1,300.0 – 1,700.0",
          "1,700.0 – 2,100.0"]),
        ("quantiles", [100, 100, 100, 100, 900], 5, ["100.0 – 260.0", "260.0 – 900.0"]),
        ("quantiles", [0, 0.002, 0.004, 0.006, 0.008, 0.01], 5,
         ["0.000 – 0.002", "0.002 – 0.004", "0.004 – 0.006", "0.006 – 0.008", "0.008 – 0.010"]),
        ("natural_breaks", [0, 1, 2, 30, 31, 32, 60, 61, 62], 3,
         ["0.0 – 2.0", "2.0 – 32.0", "32.0 – 62.0"]),
        ("natural_breaks", [0.25] * 4, 3, ["0.25 – 0.25"]),
    ],
    ids=["quantiles", "equal-interval", "dropped-duplicate-edges", "small-fractions",
         "natural-breaks", "zero-width"],
)
def test_advanced_labels_without_offsets_are_unchanged(
    map_engine, monkeypatch, tmp_path, classification, values, bins, expected,
):
    assert _advanced_labels(monkeypatch, tmp_path, values, classification, bins) == expected


# Exactness is judged per edge. A single tolerance for all edges, scaled by the
# largest one, let an outlier at 1e12 make 1.0044 look exact at 1.004.
CROSS_SCALE_EDGES = {
    "small-positive-maximum": ([-1e12, 1.0044, 1.0064],
                               ["-1,000,000,000,000.0000", "1.0044", "1.0064"]),
    "small-negative-minimum": ([-1.0064, -1.0044, 1e12],
                               ["-1.0064", "-1.0044", "1,000,000,000,000.0000"]),
    "small-class-upper": ([1.0044, 1.0064, 1e12],
                          ["1.0044", "1.0064", "1,000,000,000,000.0000"]),
}


@pytest.mark.parametrize("case", list(CROSS_SCALE_EDGES))
def test_range_edges_keep_small_edge_digits_beside_a_distant_edge(case):
    from siege_utilities.reporting._range_labels import format_range_edges

    edges, expected = CROSS_SCALE_EDGES[case]
    assert format_range_edges(edges, 3) == expected


@pytest.mark.parametrize(
    "edges, expected",
    [
        ([1.0044, 5e11, 1e12], ["1.0044", "500,000,000,000.0000", "1,000,000,000,000.0000"]),
        ([-1e12, 1.0044, 1e12], ["-1,000,000,000,000.0000", "1.0044", "1,000,000,000,000.0000"]),
        ([1.0044, 1e12], ["1.0044", "1,000,000,000,000.0000"]),
    ],
    ids=["only-neighbour-distant", "both-neighbours-distant", "two-edges"],
)
def test_range_edges_keep_digits_when_every_neighbour_is_distant(edges, expected):
    from siege_utilities.reporting._range_labels import format_range_edges

    assert format_range_edges(edges, 3) == expected


def test_heatmap_single_level_keeps_small_minimum_beside_large_maximum(heatmap_legend):
    labels, _ = heatmap_legend(1.0044, 1e12, 1)
    assert labels == ["Low: 1.0044 - 1,000,000,000,000.0000"]


def test_heatmap_wide_span_keeps_exact_small_minimum(heatmap_legend):
    """A huge span must not make an exact minimum (0.875) print as 1; e6e43b1d printed these."""
    labels, _ = heatmap_legend(0.875, 1e18, 5)
    assert labels == [
        "Low: 0.875 - 200,000,000,000,000,000.000",
        "200,000,000,000,000,000.000 - 400,000,000,000,000,000.000",
        "400,000,000,000,000,000.000 - 600,000,000,000,000,000.000",
        "600,000,000,000,000,000.000 - 800,000,000,000,000,000.000",
        "High: 800,000,000,000,000,000.000 - 1,000,000,000,000,000,000.000",
    ]


def test_range_edges_never_show_a_signed_zero():
    from siege_utilities.reporting._range_labels import format_range_edges

    noise = 0.1 + 0.2 - 0.3  # 5.6e-17: never written exactly within six places
    labels = format_range_edges([-0.1, -noise, 0.1], 1)
    # Its value at the cap is -0.000000, which "0.0" also reads as.
    assert labels[1] == "0.0"
    assert [float(label) for label in labels] == [-0.1, 0.0, 0.1]


@pytest.mark.parametrize(
    "values, expected",
    [
        ([-1e12, 1.0044, 1.0064],
         ["-1,000,000,000,000.0000 – 1.0044", "1.0044 – 1.0064"]),
        ([-1.0064, -1.0044, 1e12],
         ["-1.0064 – -1.0044", "-1.0044 – 1,000,000,000,000.0000"]),
        ([1.0044, 1.0064, 1e12],
         ["1.0044 – 1.0064", "1.0064 – 1,000,000,000,000.0000"]),
    ],
    ids=list(CROSS_SCALE_EDGES),
)
def test_advanced_labels_contain_their_values_beside_a_distant_value(
    map_engine, monkeypatch, tmp_path, values, expected,
):
    import pandas as pd

    labels = _advanced_labels(monkeypatch, tmp_path, values, "quantiles", 2)
    assert labels == expected
    classes = pd.qcut(pd.Series(values), 2, labels=False, duplicates="drop")
    bounds = [tuple(float(edge.replace(",", "")) for edge in label.split(" – ")) for label in labels]
    for value, class_index in zip(values, classes):
        lower, upper = bounds[int(class_index)]
        assert lower <= value <= upper


# "Shown exactly" means the label reads back as the identical float. At 1e12 a
# unit in the last place (ulp) is 1.2e-4, so a class 16 ulps wide has real
# digits in its fourth decimal; a tolerance of a few ulps hid them.
_BIG = 1e12
_ULP = math.ulp(_BIG)
LARGE_ULP_EDGES = {
    "large-final-class": (
        [0.0, _BIG + 36 * _ULP, _BIG + 52 * _ULP],
        ["0.0000", "1,000,000,000,000.0044", "1,000,000,000,000.0063"],
    ),
    "large-negative-minimum": (
        [-_BIG - 52 * _ULP, -_BIG - 36 * _ULP, 0.0],
        ["-1,000,000,000,000.0063", "-1,000,000,000,000.0044", "0.0000"],
    ),
    "large-inner-class": (
        [_BIG + 36 * _ULP, _BIG + 52 * _ULP, 2 * _BIG],
        ["1,000,000,000,000.0044", "1,000,000,000,000.0063", "2,000,000,000,000.0000"],
    ),
}


@pytest.mark.parametrize("case", list(LARGE_ULP_EDGES))
def test_range_edges_round_trip_large_magnitude_digits(case):
    from siege_utilities.reporting._range_labels import format_range_edges

    edges, expected = LARGE_ULP_EDGES[case]
    labels = format_range_edges(edges, 3)
    assert labels == expected
    assert [float(label.replace(",", "")) for label in labels] == edges


@pytest.mark.parametrize("case", list(LARGE_ULP_EDGES))
def test_advanced_labels_contain_values_in_classes_a_few_ulps_wide(
    map_engine, monkeypatch, tmp_path, case,
):
    import pandas as pd

    values, _ = LARGE_ULP_EDGES[case]
    labels = _advanced_labels(monkeypatch, tmp_path, values, "quantiles", 2)
    classes = pd.qcut(pd.Series(values), 2, labels=False, duplicates="drop")
    bounds = [tuple(float(edge.replace(",", "")) for edge in label.split(" – ")) for label in labels]
    for value, class_index in zip(values, classes):
        lower, upper = bounds[int(class_index)]
        assert lower <= value <= upper


def test_heatmap_large_offset_keeps_exact_binary_fraction(heatmap_legend):
    """1e15 + 0.875 reads back from "...000.9"; rounding it to "...001" excluded it."""
    low = 1e15 + 0.875
    assert low - 1e15 == 0.875
    labels, _ = heatmap_legend(low, low + 10, 5)
    assert labels == [
        "Low: 1,000,000,000,000,000.9 - 1,000,000,000,000,002.9",
        "1,000,000,000,000,002.9 - 1,000,000,000,000,004.9",
        "1,000,000,000,000,004.9 - 1,000,000,000,000,006.9",
        "1,000,000,000,000,006.9 - 1,000,000,000,000,008.9",
        "High: 1,000,000,000,000,008.9 - 1,000,000,000,000,010.9",
    ]
    bounds = _heatmap_bounds(labels)
    assert bounds[0][0] == low and bounds[-1][1] == low + 10


def test_range_edges_interior_float_noise_is_not_an_outer_bound():
    """A pandas quantile edge 1000.0000000000002 cannot be written exactly within
    six places, so it shows as its value at the cap. Inside the legend that is
    1,000.0; as an outer bound it is rounded outward, and a last edge keeps the
    cap rather than being widened to 1,000.1."""
    from siege_utilities.reporting._range_labels import format_range_edges

    noisy = 1000.0000000000002
    assert format_range_edges([100.0, noisy, 2100.0], 1) == ["100.0", "1,000.0", "2,100.0"]
    first = format_range_edges([noisy, 2100.0], 1)
    assert first == ["1,000.0", "2,100.0"]
    assert float(first[0].replace(",", "")) <= noisy
    last = format_range_edges([100.0, noisy], 1)
    assert last == ["100.000000", "1,000.000001"]
    assert float(last[1].replace(",", "")) >= noisy


# An edge that can be written exactly within six places is written exactly,
# however wide its classes are. A tolerance relative to class width let
# 1000000000.100001 print as ...000.1 and put 20 of 21 class members outside
# their own range.
_X9 = 1e9 + 0.100001
_X12 = 1e12 + 0.1001
REPRESENTABLE_EDGES = {
    "1e9-six-places": (
        [0.0, _X9, 2e9],
        ["0.000000", "1,000,000,000.100001", "2,000,000,000.000000"],
    ),
    "1e12-four-places": (
        [0.0, _X12, 2e12],
        ["0.0000", "1,000,000,000,000.1001", "2,000,000,000,000.0000"],
    ),
    "1e9-negative": (
        [-2e9, -_X9, 0.0],
        ["-2,000,000,000.000000", "-1,000,000,000.100001", "0.000000"],
    ),
}


@pytest.mark.parametrize("case", list(REPRESENTABLE_EDGES))
def test_range_edges_write_representable_interior_edges_exactly(case):
    from siege_utilities.reporting._range_labels import format_range_edges

    edges, expected = REPRESENTABLE_EDGES[case]
    labels = format_range_edges(edges, 1)
    assert labels == expected
    assert [float(label.replace(",", "")) for label in labels] == edges


def test_heatmap_outward_rounded_zero_is_unsigned(heatmap_legend):
    """-1e-17 rounded up (outward) is Decimal("-0.00"); the label shows 0.00."""
    labels, _ = heatmap_legend(-0.1, -1e-17, 1)
    assert labels == ["Low: -0.10 - 0.00"]
    assert _heatmap_bounds(labels)[0][1] >= -1e-17


def test_advanced_near_zero_noise_edge_shows_its_value_at_the_cap(map_engine, monkeypatch, tmp_path):
    """A declared approximation: the interior edge -4.16e-17 cannot be written
    within six places; its value there is zero, so it shows as 0.00 (two
    decimals is the width-based minimum, the class being 0.09999999999999996
    wide). The member -n/2 lies 2.78e-17 below the second range's printed
    lower bound."""
    n = 0.1 + 0.2 - 0.3
    labels = _advanced_labels(monkeypatch, tmp_path, [-0.1, -n, -n / 2, 0.1], "quantiles", 2)
    assert labels == ["-0.10 – 0.00", "0.00 – 0.10"]


@pytest.mark.parametrize(
    "values",
    [
        [0.0] + [_X9] * 20 + [2e9],
        [0.0] + [_X12] * 20 + [2e12],
        # The edge is -_X9; the upper class holds 9 values 4 ulps above it, which
        # a lower bound printed as -...000.1 left below their own range.
        [-2e9] * 10 + [-_X9] + [-_X9 + 4 * math.ulp(_X9)] * 9 + [0.0],
    ],
    ids=["1e9-six-places", "1e12-four-places", "1e9-negative-upper-class"],
)
def test_advanced_labels_contain_every_member_when_edges_are_representable(
    map_engine, monkeypatch, tmp_path, values,
):
    import pandas as pd

    labels = _advanced_labels(monkeypatch, tmp_path, values, "quantiles", 2)
    classes = pd.qcut(pd.Series(values), 2, labels=False, duplicates="drop")
    bounds = [tuple(float(edge.replace(",", "")) for edge in label.split(" – ")) for label in labels]
    outside = [
        value for value, class_index in zip(values, classes)
        if not bounds[int(class_index)][0] <= value <= bounds[int(class_index)][1]
    ]
    assert outside == []


# Nullable columns with a missing value. pandas 2.0 refuses to convert a masked
# array holding NA to float unless na_value is given; later 2.x releases map NA
# to NaN. CI does not run the declared pandas floor (#1958), so the end-to-end
# tests below pass on newer pandas with or without the fix; the classifier
# contract test and the labelled pandas 2.0 emulation are the ones that fail
# without it.
_PRESENT = [1, 2, 3, 50, 51, 52, 100, 101, 102]
_MISSING_AT = 3


def _with_missing(missing, dtype=None):
    import pandas as pd

    values = _PRESENT[:_MISSING_AT] + [missing] + _PRESENT[_MISSING_AT:]
    return values if dtype is None else pd.array(values, dtype=dtype)


def _use_backend(monkeypatch, backend):
    from siege_utilities.geo import classification

    if backend == "mapclassify":
        pytest.importorskip("mapclassify")
    else:
        monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)


@pytest.mark.parametrize("dtype", ["Int64", "Float64"])
def test_natural_breaks_classifier_receives_float_array_with_nan_for_missing(
    map_engine, monkeypatch, tmp_path, dtype,
):
    """The classifier gets float64 NaN for a missing value, never the nullable column."""
    from siege_utilities.geo import classification

    real = classification.classify_series
    received = []

    def spy(values, *args, **kwargs):
        received.append(values)
        return real(values, *args, **kwargs)

    monkeypatch.setattr(classification, "classify_series", spy)
    _render_advanced_choropleth(
        monkeypatch, tmp_path, _with_missing(None, dtype), "natural_breaks", bins=3,
    )

    assert len(received) == 1
    passed = received[0]
    assert type(passed) is np.ndarray, f"classifier received {type(passed).__name__}"
    assert passed.dtype == np.float64
    expected_missing = [index == _MISSING_AT for index in range(len(_PRESENT) + 1)]
    np.testing.assert_array_equal(np.isnan(passed), expected_missing)
    np.testing.assert_array_equal(passed[~np.isnan(passed)], _PRESENT)


def _legend_and_colours(ax):
    legend = ax.get_legend()
    return (
        [text.get_text() for text in legend.get_texts()],
        [patch.get_facecolor() for patch in legend.get_patches()],
        ax.collections[0].get_facecolors(),
    )


@pytest.mark.parametrize("backend", ["mapclassify", "numpy"])
@pytest.mark.parametrize("dtype", ["Int64", "Float64"])
def test_natural_breaks_nullable_column_with_missing_value(
    map_engine, monkeypatch, tmp_path, dtype, backend,
):
    """A nullable column with NA renders like float64 with NaN: same legend and colours."""
    _use_backend(monkeypatch, backend)

    labels, swatches, facecolors = _legend_and_colours(_render_advanced_choropleth(
        monkeypatch, tmp_path, _with_missing(None, dtype), "natural_breaks", bins=3,
    ))
    reference = _legend_and_colours(_render_advanced_choropleth(
        monkeypatch, tmp_path, _with_missing(float("nan")), "natural_breaks", bins=3,
    ))

    assert len(labels) == 3
    assert not any("nan" in label.lower() for label in labels)
    assert labels == reference[0]
    np.testing.assert_allclose(swatches, reference[1])
    # The missing polygon is left unclassified and is not drawn; every other
    # polygon takes the swatch of its range.
    assert len(facecolors) == len(_PRESENT)
    np.testing.assert_allclose(facecolors, reference[2])
    for class_index, facecolor in zip([0, 0, 0, 1, 1, 1, 2, 2, 2], facecolors):
        np.testing.assert_allclose(facecolor, swatches[class_index])


def _emulate_pandas_20_masked_float_conversion(monkeypatch):
    """Emulation, not pandas 2.0 itself: refuse a float conversion of NA without na_value.

    pandas 2.0's BaseMaskedArray.to_numpy defaulted na_value to pd.NA and raised
    this ValueError, and its __array__ called to_numpy(dtype=dtype). Only that
    float refusal is emulated here.
    """
    import pandas as pd

    no_default = pd.api.extensions.no_default
    for array_type in (pd.arrays.IntegerArray, pd.arrays.FloatingArray):
        original = array_type.to_numpy

        def to_numpy(self, dtype=None, copy=False, na_value=no_default, _original=original):
            if (
                na_value is no_default
                and dtype is not None
                and pd.api.types.is_float_dtype(dtype)
                and self.isna().any()
            ):
                raise ValueError(
                    f"cannot convert to '{np.dtype(dtype)}'-dtype NumPy array with missing "
                    "values. Specify an appropriate 'na_value' for this dtype."
                )
            return _original(self, dtype=dtype, copy=copy, na_value=na_value)

        monkeypatch.setattr(array_type, "to_numpy", to_numpy)


def test_pandas_20_emulation_refuses_float_conversion_with_missing_values(monkeypatch):
    import pandas as pd

    _emulate_pandas_20_masked_float_conversion(monkeypatch)
    column = pd.Series(_with_missing(None, "Int64"))
    with pytest.raises(ValueError, match="Specify an appropriate 'na_value'"):
        np.asarray(column, dtype=np.float64)
    assert np.isnan(column.to_numpy(dtype=float, na_value=np.nan)[_MISSING_AT])


@pytest.mark.parametrize("backend", ["mapclassify", "numpy"])
@pytest.mark.parametrize("dtype", ["Int64", "Float64"])
def test_natural_breaks_nullable_missing_value_under_pandas_20_emulation(
    map_engine, monkeypatch, tmp_path, dtype, backend,
):
    """Emulated pandas 2.0 conversion: natural breaks still renders a nullable column with NA."""
    _use_backend(monkeypatch, backend)
    _emulate_pandas_20_masked_float_conversion(monkeypatch)

    labels, swatches, facecolors = _legend_and_colours(_render_advanced_choropleth(
        monkeypatch, tmp_path, _with_missing(None, dtype), "natural_breaks", bins=3,
    ))

    assert len(labels) == 3
    assert len(facecolors) == len(_PRESENT)
    for class_index, facecolor in zip([0, 0, 0, 1, 1, 1, 2, 2, 2], facecolors):
        np.testing.assert_allclose(facecolor, swatches[class_index])
