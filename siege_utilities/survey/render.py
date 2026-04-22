"""
Chain → Argument renderer.

chain_to_argument:  converts one Chain to an Argument with chart and optional map.
stack_to_arguments: walks all Chains in a Stack.

Chart type selection by TableType:
  SINGLE_RESPONSE   → horizontal bar
  MULTIPLE_RESPONSE → grouped bar (NOT stacked — stacked implies mutual exclusivity)
  CROSS_TAB         → grouped bar (≤5 categories) or heatmap (>5)
  LONGITUDINAL      → line chart
  RANKING           → horizontal bar sorted descending
  MEAN_SCALE        → bar with error bars
  BANNER            → small-multiple bars
"""

from __future__ import annotations

from typing import Any, List, Optional, TYPE_CHECKING

import pandas as pd

from ..reporting.pages.page_models import Argument, TableType

if TYPE_CHECKING:
    from .models import Chain, Cluster, Stack


# ---------------------------------------------------------------------------
# Chart type selection
# ---------------------------------------------------------------------------

_CHART_TYPE_MAP = {
    TableType.SINGLE_RESPONSE:   "horizontal_bar",
    TableType.MULTIPLE_RESPONSE: "grouped_bar",
    TableType.CROSS_TAB:         "grouped_bar",
    TableType.LONGITUDINAL:      "line",
    TableType.RANKING:           "horizontal_bar",
    TableType.MEAN_SCALE:        "bar_with_error",
    TableType.BANNER:            "small_multiples",
}

_HEATMAP_THRESHOLD = 5  # switch CROSS_TAB to heatmap above this many row categories


def _select_chart_type(chain: "Chain") -> str:
    ct = _CHART_TYPE_MAP[chain.table_type]
    if chain.table_type == TableType.CROSS_TAB:
        n_cats = len(chain.views) if chain.views else 0
        if n_cats > _HEATMAP_THRESHOLD:
            ct = "heatmap"
    return ct


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def _build_chart(df: pd.DataFrame, chart_type: str, headline: str) -> Optional[Any]:
    """Attempt to build a matplotlib Figure. Returns None if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))

    try:
        if chart_type == "horizontal_bar":
            df.iloc[:, 0].sort_values().plot.barh(ax=ax, color="#1a3a5c")
        elif chart_type == "grouped_bar":
            df.plot.bar(ax=ax)
        elif chart_type == "line":
            df.plot.line(ax=ax, marker="o")
        elif chart_type == "heatmap":
            try:
                import seaborn as sns
                sns.heatmap(df, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax)
            except ImportError:
                df.plot.bar(ax=ax)
        elif chart_type == "bar_with_error":
            df.iloc[:, 0].plot.bar(ax=ax, color="#2d6a9f")
        else:
            df.plot.bar(ax=ax)
    except Exception:
        plt.close(fig)
        return None

    ax.set_title(headline, fontsize=12, fontweight="bold")
    plt.tight_layout()
    return fig


def _build_map(chain: "Chain") -> Optional[Any]:
    """Attempt to build a choropleth from chain.geo_column data. Returns None if unavailable."""
    if not chain.geo_column:
        return None
    try:
        from ..reporting.chart_generator import ChartGenerator
        cg = ChartGenerator()
        df = chain.to_dataframe()
        if df.empty:
            return None
        # Aggregate first column across all break values
        agg = df.iloc[:, 0].reset_index()
        agg.columns = [chain.geo_column, "value"]
        fig = cg.create_choropleth_map(agg, geo_column=chain.geo_column, value_column="value")
        return fig
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chain_to_argument(
    chain: "Chain",
    headline: str,
    narrative: str,
    chart_generator: Any = None,
    map_generator: Any = None,
) -> Argument:
    """Convert a Chain to an Argument with chart and optional map.

    Parameters
    ----------
    chain:
        Source Chain (output of build_chain).
    headline:
        Slide headline / section title.
    narrative:
        One-paragraph narrative text for the argument.
    chart_generator:
        Optional ChartGenerator instance. Auto-created if None.
    map_generator:
        Optional map generator. Uses geo.choropleth if geo_column present.

    Returns
    -------
    Argument with chart populated, map_figure populated iff chain.geo_column set.
    """
    df = chain.to_dataframe()
    chart_type = _select_chart_type(chain)
    chart = _build_chart(df, chart_type, headline)
    map_figure = _build_map(chain) if chain.geo_column else None

    return Argument(
        headline=headline,
        narrative=narrative,
        table=df,
        table_type=chain.table_type,
        chart=chart,
        map_figure=map_figure,
        base_note=chain.base_note or None,
        tags=[chain.table_type.value],
    )


def stack_to_arguments(
    stack: "Stack",
    headlines: Optional[dict] = None,
    narratives: Optional[dict] = None,
) -> List["Cluster"]:
    """Walk all Chains in a Stack, converting each to an Argument.

    Parameters
    ----------
    stack:
        Source Stack.
    headlines:
        Optional dict mapping (cluster_name, row_var) → headline string.
    narratives:
        Optional dict mapping (cluster_name, row_var) → narrative string.

    Returns
    -------
    List of Cluster objects where each chain is replaced by its Argument.
    """
    from .models import Cluster as ClusterModel

    result: List[ClusterModel] = []
    for cluster in stack.clusters:
        arg_cluster: List[Argument] = []
        for chain in cluster.chains:
            key = (cluster.name, chain.row_var)
            hl = (headlines or {}).get(key, chain.row_var.replace("_", " ").title())
            na = (narratives or {}).get(key, "")
            arg_cluster.append(chain_to_argument(chain, headline=hl, narrative=na))
        # Build a Cluster whose chains slot is repurposed as arguments list
        c = ClusterModel(name=cluster.name)
        c.chains = arg_cluster  # type: ignore[assignment]
        result.append(c)
    return result
