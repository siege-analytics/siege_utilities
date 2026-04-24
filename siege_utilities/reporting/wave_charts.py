"""Rendering helpers for WaveSet longitudinal output.

Takes a LONGITUDINAL :class:`~siege_utilities.survey.models.Chain` (typically
from :meth:`~siege_utilities.survey.models.WaveSet.compare_chain`) and
produces matplotlib figures:

* :func:`trend_chart` — line chart of each category across waves
* :func:`heatmap` — category × wave heatmap of percents or counts
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import matplotlib.figure
    from ..survey.models import Chain


class WaveChartError(ValueError):
    """Raised when a WaveSet chart cannot be rendered from the given Chain."""


def _longitudinal_dataframe(chain: "Chain"):
    """Return the chain's DataFrame with any delta column dropped."""
    df = chain.to_dataframe()
    if chain.delta_column and chain.delta_column in df.columns:
        df = df.drop(columns=[chain.delta_column])
    return df


def trend_chart(
    chain: "Chain",
    *,
    title: Optional[str] = None,
    ylabel: str = "%",
    figsize: tuple = (10, 6),
    marker: str = "o",
):
    """Line chart of each row category across waves.

    Parameters
    ----------
    chain:
        A LONGITUDINAL Chain. Each wave is a column; each row_var value
        becomes one line.
    title:
        Optional plot title; defaults to ``f"{chain.row_var} over time"``.
    ylabel:
        Y-axis label; default "%".
    figsize:
        Matplotlib ``figure`` size tuple.
    marker:
        Matplotlib marker style for data points.
    """
    from ..reporting.pages.page_models import TableType

    if chain.table_type is not TableType.LONGITUDINAL:
        raise WaveChartError(
            f"trend_chart requires TableType.LONGITUDINAL, got {chain.table_type}"
        )

    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise WaveChartError(
            "matplotlib is required for wave_charts; "
            "install with pip install 'siege-utilities[reporting]'"
        ) from e

    df = _longitudinal_dataframe(chain)
    if df.empty:
        raise WaveChartError("Chain has no wave views to plot")

    fig, ax = plt.subplots(figsize=figsize)
    for category, row in df.iterrows():
        ax.plot(df.columns, row.values, marker=marker, label=str(category))
    ax.set_title(title or f"{chain.row_var} over time")
    ax.set_xlabel("Wave")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", fontsize="small")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def heatmap(
    chain: "Chain",
    *,
    title: Optional[str] = None,
    figsize: tuple = (10, 6),
    cmap: str = "RdYlBu_r",
    annotate: bool = True,
):
    """Category × wave heatmap.

    Parameters
    ----------
    chain:
        A LONGITUDINAL Chain.
    title:
        Optional plot title.
    figsize:
        Matplotlib figure size.
    cmap:
        Matplotlib colormap name.
    annotate:
        If True, write the numeric value in each cell.
    """
    from ..reporting.pages.page_models import TableType

    if chain.table_type is not TableType.LONGITUDINAL:
        raise WaveChartError(
            f"heatmap requires TableType.LONGITUDINAL, got {chain.table_type}"
        )

    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise WaveChartError(
            "matplotlib is required for wave_charts; "
            "install with pip install 'siege-utilities[reporting]'"
        ) from e

    df = _longitudinal_dataframe(chain)
    if df.empty:
        raise WaveChartError("Chain has no wave views to plot")

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(df.values, aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(df.columns)))
    ax.set_xticklabels(df.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(df.index)))
    ax.set_yticklabels(df.index)
    ax.set_title(title or f"{chain.row_var} × wave")
    fig.colorbar(im, ax=ax)

    if annotate:
        for i in range(len(df.index)):
            for j in range(len(df.columns)):
                val = df.values[i, j]
                ax.text(
                    j, i, f"{val:.1f}",
                    ha="center", va="center",
                    color="black", fontsize="x-small",
                )

    fig.tight_layout()
    return fig
