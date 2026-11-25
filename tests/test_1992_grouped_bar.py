"""Regression tests for issue #1992 (``group_by`` in ``create_bar_chart``).

``ChartGenerator.create_bar_chart(group_by=...)`` documented a ``group_by``
parameter but never used it: a long-form frame with a grouping column was
drawn as one unlabelled series with overlapping bars and an empty-legend
warning. These tests were contributed with PR #2001 and are tightened here:
every bar is checked against its own category and series (unsorted), the
horizontal layout is covered, the value labels are asserted, an unknown
``group_by`` column must be refused by name, tick labels rotate by category
count rather than row count, and the default single-series chart keeps its
legend-free look.
"""

import warnings

import pytest

pytest.importorskip("matplotlib")
import pandas as pd

from siege_utilities import ChartGenerator
from siege_utilities.reporting.chart_types import ChartParameterError

EXPECTED = {
    ("Total Sales", "Today"): 1685.95,
    ("Total Sales", "Benchmark"): 4067.69,
    ("Inside Sales", "Today"): 1615.32,
    ("Inside Sales", "Benchmark"): 3942.53,
}


def _draw(data, **kwargs):
    """Call create_bar_chart and return its axes plus any warnings raised."""
    cg = ChartGenerator()
    captured = {}

    def fake(fig, width, height):
        captured["fig"] = fig
        return "IMG"

    cg._matplotlib_to_reportlab_image = fake
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = cg.create_bar_chart(data, **kwargs)
    assert out == "IMG"
    return captured["fig"].axes[0], [str(w.message) for w in caught]


def _frame():
    return pd.DataFrame(
        {
            "metric": ["Total Sales", "Total Sales", "Inside Sales", "Inside Sales"],
            "value": [1685.95, 4067.69, 1615.32, 3942.53],
            "series": ["Today", "Benchmark", "Today", "Benchmark"],
        }
    )


def _drawn_by_category_and_series(ax, horizontal=False):
    """Map (tick label, series label) -> drawn bar length, using bar centres."""
    if horizontal:
        ticks = dict(zip(ax.get_yticks(), [t.get_text() for t in ax.get_yticklabels()]))
    else:
        ticks = dict(zip(ax.get_xticks(), [t.get_text() for t in ax.get_xticklabels()]))
    drawn = {}
    centres_by_tick = {}
    for container in ax.containers:
        for patch in container:
            if horizontal:
                centre = patch.get_y() + patch.get_height() / 2
                length = patch.get_width()
            else:
                centre = patch.get_x() + patch.get_width() / 2
                length = patch.get_height()
            nearest = min(ticks, key=lambda tick: abs(tick - centre))
            # Every bar of a group lies inside its category's 0.8-wide slot.
            assert abs(nearest - centre) < 0.4
            centres_by_tick.setdefault(nearest, []).append(centre)
            key = (ticks[nearest], container.get_label())
            assert key not in drawn, f"two bars for {key}"
            drawn[key] = round(length, 2)
    # Each category's group of bars is centred on its tick.
    for tick, centres in centres_by_tick.items():
        assert sum(centres) / len(centres) == pytest.approx(tick, abs=1e-9)
    return drawn


def test_group_by_draws_one_bar_per_category_and_series():
    ax, caught = _draw(_frame(), x_column="metric", y_column="value",
                       title="Today vs benchmark", group_by="series")

    # Each series draws its own values in category order (no sorting, so a
    # swapped series or a value on the wrong category is caught).
    by_series = {c.get_label(): [round(p.get_height(), 2) for p in c] for c in ax.containers}
    assert by_series == {"Today": [1685.95, 1615.32], "Benchmark": [4067.69, 3942.53]}

    # Each bar sits on its own category tick.
    assert _drawn_by_category_and_series(ax) == EXPECTED

    # Bars are clustered, not stacked on the same x position.
    assert len({round(p.get_x(), 4) for p in ax.patches}) == 4

    # A real legend with both series, and no empty-legend warning.
    legend = ax.get_legend()
    assert legend is not None
    assert [t.get_text() for t in legend.get_texts()] == ["Today", "Benchmark"]
    assert not [m for m in caught if "put in legend" in m]


def test_group_by_value_labels_match_each_bar():
    ax, _ = _draw(_frame(), x_column="metric", y_column="value", group_by="series")
    labels = {(round(t.get_position()[0], 4), round(t.get_position()[1], 2)): t.get_text()
              for t in ax.texts}
    for patch in ax.patches:
        key = (round(patch.get_x() + patch.get_width() / 2, 4), round(patch.get_height(), 2))
        assert key in labels, f"no value label at the top of bar {key}"
        assert float(labels[key].replace(",", "")) == pytest.approx(patch.get_height())


def test_group_by_preserves_category_and_series_order():
    ax, _ = _draw(_frame(), x_column="metric", y_column="value", group_by="series")
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Total Sales", "Inside Sales"]
    assert [c.get_label() for c in ax.containers] == ["Today", "Benchmark"]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["Today", "Benchmark"]


def test_horizontal_group_by_draws_widths_per_category_and_series():
    ax, _ = _draw(_frame(), x_column="metric", y_column="value", group_by="series",
                  chart_type="horizontal")
    assert [t.get_text() for t in ax.get_yticklabels()] == ["Total Sales", "Inside Sales"]
    by_series = {c.get_label(): [round(p.get_width(), 2) for p in c] for c in ax.containers}
    assert by_series == {"Today": [1685.95, 1615.32], "Benchmark": [4067.69, 3942.53]}
    assert _drawn_by_category_and_series(ax, horizontal=True) == EXPECTED
    # Value labels sit at the end of each bar and show its value.
    assert len(ax.texts) == len(ax.patches) == 4
    for patch, text in zip(ax.patches, ax.texts):
        assert text.get_position() == pytest.approx(
            (patch.get_width(), patch.get_y() + patch.get_height() / 2))
        assert float(text.get_text().replace(",", "")) == pytest.approx(patch.get_width())


def test_unknown_group_by_column_is_refused_by_name():
    """The engine's RuntimeError contract is kept; the cause names the
    argument, the missing column and the available columns."""
    with pytest.raises(RuntimeError, match="Chart generation failed") as exc:
        _draw(_frame(), x_column="metric", y_column="value", group_by="serie")
    cause = exc.value.__cause__
    assert isinstance(cause, ChartParameterError)
    assert "group_by" in str(cause)
    assert "'serie'" in str(cause)
    assert "series" in str(cause)  # the available columns are listed


def test_two_categories_of_three_series_keep_level_tick_labels():
    frame = pd.DataFrame({"name": ["A", "A", "A", "B", "B", "B"], "group": list("xyzxyz"),
                          "value": [1, 2, 3, 4, 5, 6]})
    ax, _ = _draw(frame, x_column="name", y_column="value", group_by="group")
    assert [t.get_text() for t in ax.get_xticklabels()] == ["A", "B"]
    assert {label.get_rotation() for label in ax.get_xticklabels()} == {0.0}


def test_six_categories_of_two_series_rotate_tick_labels():
    names = [name for name in "ABCDEF" for _ in range(2)]
    frame = pd.DataFrame({"name": names, "group": list("xy") * 6, "value": range(12)})
    ax, _ = _draw(frame, x_column="name", y_column="value", group_by="group")
    assert {label.get_rotation() for label in ax.get_xticklabels()} == {45.0}


def test_single_series_default_chart_gains_no_legend_entry_and_no_warning():
    """group_by=None keeps the one-bar-per-row chart; no series entry (such as
    the y column's name) is added to its legend, and no empty-legend warning
    is raised."""
    df = _frame()
    df = df[df["series"] == "Today"]
    ax, caught = _draw(df, x_column="metric", y_column="value", title="today")
    assert [round(p.get_height(), 2) for p in ax.patches] == [1685.95, 1615.32]
    legend = ax.get_legend()
    assert legend is None or [t.get_text() for t in legend.get_texts()] == []
    assert not [m for m in caught if "put in legend" in m]


def test_each_series_has_one_colour_and_series_colours_differ():
    frame = pd.DataFrame({"name": ["A", "A", "A", "B", "B", "B"], "group": list("xyzxyz"),
                          "value": [1, 2, 3, 4, 5, 6]})
    ax, _ = _draw(frame, x_column="name", y_column="value", group_by="group")
    colours = []
    for container in ax.containers:
        faces = {tuple(patch.get_facecolor()) for patch in container}
        assert len(faces) == 1, f"series {container.get_label()} uses several colours"
        colours.append(faces.pop())
    assert len(set(colours)) == len(colours) == 3


def test_integer_column_label_zero_works_as_group_by():
    """A falsy column label (0, the default name of a first column) still groups."""
    frame = pd.DataFrame([["x", "A", 1], ["y", "A", 2], ["x", "B", 3], ["y", "B", 4]])
    ax, _ = _draw(frame, x_column=1, y_column=2, group_by=0)
    assert [c.get_label() for c in ax.containers] == ["x", "y"]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["x", "y"]


def test_empty_string_column_works_as_group_by():
    frame = pd.DataFrame({"name": ["A", "A", "B", "B"], "": ["x", "y", "x", "y"],
                          "value": [1, 2, 3, 4]})
    ax, _ = _draw(frame, x_column="name", y_column="value", group_by="")
    assert [c.get_label() for c in ax.containers] == ["x", "y"]
