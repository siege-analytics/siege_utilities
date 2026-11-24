"""Regression tests for issue #1999.

``create_pie_chart(legend_position="right")`` placed its four-column legend
table with ``bbox=[1.05, 0, 0.6, 0.9]`` in *axes* coordinates. That box is
only ~0.30 of the figure wide and matplotlib tables do not shrink text to
their cells, so the value and percent columns ran past the right edge of the
figure and were clipped from the saved image.

The figure is saved without ``bbox_inches='tight'``, so the saved image is
exactly the figure canvas. These tests draw the figure and assert that every
legend cell, and the text inside it, lies within that canvas.
"""

import pytest

pytest.importorskip("matplotlib")
import pandas as pd
from matplotlib.table import Table

from siege_utilities import ChartGenerator

TOL_PX = 1.0


def _capture_figure(cg):
    """Intercept the figure the engine would convert to a ReportLab Image."""
    captured = {}

    def fake(fig, width, height):
        captured["fig"] = fig
        return "IMG"

    cg._matplotlib_to_reportlab_image = fake
    return captured


def _issue_frame():
    return pd.DataFrame({
        "category": ["Foodservice", "Packaged Beverage", "Tobacco / Nicotine"],
        "revenue": [745.55, 258.34, 52.46],
    })


def _long_label_frame():
    return pd.DataFrame({
        "category": [
            "Foodservice and prepared hot food counter",
            "Packaged Beverage (cold vault, fountain and coffee)",
            "Tobacco / Nicotine / Vapor products",
            "Other",
        ],
        "revenue": [745123.55, 258000.34, 52.46, 1.0],
    })


def _legend_table(fig):
    tables = [child for ax in fig.axes for child in ax.get_children()
              if isinstance(child, Table)]
    assert len(tables) == 1, "expected exactly one legend table"
    return tables[0]


def _assert_legend_inside_canvas(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_box = fig.bbox  # display (pixel) coordinates of the saved canvas
    table = _legend_table(fig)
    cells = table.get_celld()
    assert cells, "legend table has no cells"

    for (row, col), cell in cells.items():
        cell_box = cell.get_window_extent(renderer)
        assert cell_box.x0 >= fig_box.x0 - TOL_PX, (row, col, "cell left of canvas")
        assert cell_box.x1 <= fig_box.x1 + TOL_PX, (row, col, "cell right of canvas")
        assert cell_box.y0 >= fig_box.y0 - TOL_PX, (row, col, "cell below canvas")
        assert cell_box.y1 <= fig_box.y1 + TOL_PX, (row, col, "cell above canvas")

        text = cell.get_text()
        if not text.get_text():
            continue
        text_box = text.get_window_extent(renderer)
        # The text is inside its own cell, so no column bleeds into the next
        # one or off the canvas.
        assert text_box.x0 >= cell_box.x0 - TOL_PX, (row, col, text.get_text())
        assert text_box.x1 <= cell_box.x1 + TOL_PX, (row, col, text.get_text())


@pytest.mark.parametrize("frame", [_issue_frame, _long_label_frame],
                         ids=["issue-repro", "long-labels"])
def test_right_legend_fits_inside_saved_image(frame):
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    out = cg.create_pie_chart(frame(), labels_column="category",
                              values_column="revenue",
                              title="Inside sales by category",
                              legend_position="right")
    assert out == "IMG"
    _assert_legend_inside_canvas(captured["fig"])


@pytest.mark.parametrize("frame", [_issue_frame, _long_label_frame],
                         ids=["issue-repro", "long-labels"])
def test_bottom_legend_fits_inside_saved_image(frame):
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    cg.create_pie_chart(frame(), labels_column="category",
                        values_column="revenue", legend_position="bottom")
    _assert_legend_inside_canvas(captured["fig"])


def test_right_legend_keeps_all_four_columns_and_values():
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    cg.create_pie_chart(_issue_frame(), labels_column="category",
                        values_column="revenue", legend_position="right")
    table = _legend_table(captured["fig"])
    cells = table.get_celld()
    header = [cells[(0, c)].get_text().get_text() for c in range(4)]
    assert header == ["", "Label", "Value", "Percent"]
    first_row = [cells[(1, c)].get_text().get_text() for c in range(1, 4)]
    assert first_row == ["Foodservice", "745.55", "70.6%"]


@pytest.mark.parametrize("position", ["right", "bottom"])
def test_extremely_long_label_is_shortened_not_clipped(position):
    """A label too long to fit even at the minimum font size is shortened with
    an ellipsis; the value and percent columns stay intact and visible."""
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    huge = "Category " + "x" * 400
    df = pd.DataFrame({"category": [huge, "B"], "revenue": [3.0, 1.0]})
    cg.create_pie_chart(df, labels_column="category", values_column="revenue",
                        legend_position=position)
    fig = captured["fig"]
    _assert_legend_inside_canvas(fig)
    cells = _legend_table(fig).get_celld()
    label = cells[(1, 1)].get_text().get_text()
    assert label.startswith("Category ") and label.endswith("…")
    assert len(label) < len(huge)
    assert cells[(1, 2)].get_text().get_text() == "3.0"
    assert cells[(1, 3)].get_text().get_text() == "75.0%"


def test_many_categories_fit_vertically():
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    df = pd.DataFrame({"category": [f"Category {i}" for i in range(40)],
                       "revenue": [float(i + 1) for i in range(40)]})
    cg.create_pie_chart(df, labels_column="category", values_column="revenue",
                        legend_position="right")
    _assert_legend_inside_canvas(captured["fig"])


def test_input_labels_are_not_mutated():
    cg = ChartGenerator()
    _capture_figure(cg)
    huge = "y" * 400
    df = pd.DataFrame({"category": [huge, "B"], "revenue": [3.0, 1.0]})
    cg.create_pie_chart(df, labels_column="category", values_column="revenue")
    assert df["category"].tolist() == [huge, "B"]


def test_pie_wedges_stay_inside_canvas_with_long_labels():
    """Reserving room for a wide legend must not push the pie off the canvas."""
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    cg.create_pie_chart(_long_label_frame(), labels_column="category",
                        values_column="revenue", legend_position="right")
    fig = captured["fig"]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    pie_ax = fig.axes[0]
    box = pie_ax.get_window_extent(renderer)
    assert box.width > 0 and box.height > 0
    assert box.x0 >= fig.bbox.x0 - TOL_PX and box.x1 <= fig.bbox.x1 + TOL_PX


# --- the title ---------------------------------------------------------------

LONG_TITLE = "Inside sales by category, fiscal year 2026 third quarter"
VERY_LONG_TITLE = " ".join([LONG_TITLE] * 3)


def _visible_title(fig, title):
    """The Text artist that shows ``title`` (figure-level or axes-level)."""
    candidates = list(fig.texts) + [ax.title for ax in fig.axes]
    shown = [t for t in candidates if t.get_text()
             and " ".join(t.get_text().split()) == " ".join(title.split())]
    assert len(shown) == 1, [t.get_text() for t in candidates if t.get_text()]
    return shown[0]


@pytest.mark.parametrize("frame,title,position,size", [
    (_issue_frame, LONG_TITLE, "right", (6.0, 4.0)),
    (_long_label_frame, "Inside sales by category, FY2026 Q3", "right", (6.0, 4.0)),
    (_long_label_frame, LONG_TITLE, "right", (6.0, 4.0)),
    (_long_label_frame, VERY_LONG_TITLE, "right", (6.0, 4.0)),
    (_issue_frame, "Sales", "right", (3.0, 2.0)),
    (_long_label_frame, LONG_TITLE, "bottom", (6.0, 4.0)),
    (_issue_frame, VERY_LONG_TITLE, "bottom", (3.0, 2.0)),
], ids=["issue-long", "long-medium", "long-long", "long-verylong", "small-fig",
        "bottom-long", "bottom-verylong-small"])
def test_title_is_whole_on_canvas_and_clear_of_legend_and_pie(frame, title, position, size):
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    cg.create_pie_chart(frame(), labels_column="category", values_column="revenue",
                        title=title, legend_position=position,
                        width=size[0], height=size[1])
    fig = captured["fig"]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    title_box = _visible_title(fig, title).get_window_extent(renderer)
    fig_box = fig.bbox
    assert title_box.width > 0
    assert title_box.x0 >= fig_box.x0 - TOL_PX and title_box.x1 <= fig_box.x1 + TOL_PX
    assert title_box.y0 >= fig_box.y0 - TOL_PX and title_box.y1 <= fig_box.y1 + TOL_PX

    table = _legend_table(fig)
    for cell in table.get_celld().values():
        assert not title_box.overlaps(cell.get_window_extent(renderer)), "title over legend"
    for wedge in fig.axes[0].patches:
        assert not title_box.overlaps(wedge.get_window_extent(renderer)), "title over pie"


def test_title_without_legend_is_unchanged():
    """show_legend=False keeps the title on the pie axes as before."""
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    cg.create_pie_chart(_issue_frame(), labels_column="category", values_column="revenue",
                        title="Sales", show_legend=False)
    fig = captured["fig"]
    assert fig.axes[0].get_title() == "Sales"
    assert not [t for t in fig.texts if t.get_text()]


def test_none_label_is_an_empty_cell():
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    df = pd.DataFrame({"category": ["A", None], "revenue": [5.0, 1.0]})
    cg.create_pie_chart(df, labels_column="category", values_column="revenue")
    cells = _legend_table(captured["fig"]).get_celld()
    assert cells[(2, 1)].get_text().get_text() == ""
