"""Regression tests for issue #1992.

`ChartGenerator.create_bar_chart(group_by=...)` documented a `group_by`
parameter but never used it: the body drew a single ``ax.bar(x, y)`` on the raw
columns, so a long-form frame with a grouping column produced overlapping bars
at duplicate x positions and an empty-legend warning. These tests pin the fixed
behaviour (one labeled, clustered bar group per series) and guard the unchanged
single-series path.
"""

import pytest

pytest.importorskip("matplotlib")
import pandas as pd

from siege_utilities import ChartGenerator


def _capture_figure(cg):
    """Intercept the figure the engine would convert to a ReportLab Image."""
    captured = {}

    def fake(fig, width, height):
        captured["fig"] = fig
        return "IMG"

    cg._matplotlib_to_reportlab_image = fake
    return captured


def _frame():
    return pd.DataFrame(
        {
            "metric": ["Total Sales", "Total Sales", "Inside Sales", "Inside Sales"],
            "value": [1685.95, 4067.69, 1615.32, 3942.53],
            "series": ["Today", "Benchmark", "Today", "Benchmark"],
        }
    )


def test_group_by_draws_clustered_labeled_bars():
    cg = ChartGenerator()
    captured = _capture_figure(cg)

    out = cg.create_bar_chart(
        _frame(), x_column="metric", y_column="value",
        title="Today vs benchmark", group_by="series",
    )
    assert out == "IMG"
    ax = captured["fig"].axes[0]

    # 2 categories x 2 series = 4 bars, each at a distinct x position (clustered,
    # not overlapping at duplicate x like the pre-fix single ax.bar call).
    assert len(ax.patches) == 4
    distinct_x = {round(p.get_x(), 4) for p in ax.patches}
    assert len(distinct_x) == 4

    # Series are labeled and a real legend is produced (no "No artists with
    # labels" fallback).
    legend = ax.get_legend()
    assert legend is not None
    assert [t.get_text() for t in legend.get_texts()] == ["Today", "Benchmark"]

    # Bar heights match the source values (no silent reshuffle).
    heights = sorted(round(p.get_height(), 2) for p in ax.patches)
    assert heights == [1615.32, 1685.95, 3942.53, 4067.69]


def test_group_by_preserves_category_and_series_order():
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    cg.create_bar_chart(
        _frame(), x_column="metric", y_column="value", group_by="series",
    )
    ax = captured["fig"].axes[0]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Total Sales", "Inside Sales"]


def test_single_series_unchanged():
    """group_by=None keeps the original one-bar-per-row behaviour."""
    cg = ChartGenerator()
    captured = _capture_figure(cg)
    df = _frame()
    df = df[df["series"] == "Today"]
    cg.create_bar_chart(df, x_column="metric", y_column="value", title="today")
    ax = captured["fig"].axes[0]
    assert len(ax.patches) == 2
