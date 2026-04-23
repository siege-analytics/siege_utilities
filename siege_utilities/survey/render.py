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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import pandas as pd

from ..reporting.pages.page_models import Argument, TableType

if TYPE_CHECKING:
    from .models import Chain, Stack


class RenderError(RuntimeError):
    """Raised when Chain-to-Argument rendering hits a configuration or data issue."""


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

def _build_chart(
    df: pd.DataFrame,
    chart_type: str,
    headline: str,
    chart_generator: Optional[Any] = None,
) -> Optional[Any]:
    """Render a Figure for ``chart_type``.

    When ``chart_generator`` is provided it must be callable as
    ``chart_generator(df, chart_type, headline) -> Figure | None`` — the
    caller's generator is used directly and its return value is the chart.

    When ``chart_generator`` is None, uses the library's default matplotlib
    path (described below).

    Returns ``None`` when matplotlib is unavailable OR when ``df`` is empty.
    Any plotting failure raises :class:`RenderError`.
    """
    if chart_generator is not None:
        return chart_generator(df, chart_type, headline)

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
    except (ValueError, TypeError, KeyError) as e:
        plt.close(fig)
        raise RenderError(
            f"chart rendering failed for chart_type={chart_type!r}, "
            f"shape={df.shape}, columns={list(df.columns)[:5]}: {e}"
        ) from e

    ax.set_title(headline, fontsize=12, fontweight="bold")
    plt.tight_layout()
    return fig


def _build_map(chain: "Chain", map_generator: Optional[Any] = None) -> Optional[Any]:
    """Render a choropleth for geographically-keyed Chains.

    When ``map_generator`` is provided it must expose a
    ``create_choropleth_map(df, geo_column, value_column)`` method; it is
    used instead of the default :class:`ChartGenerator`.

    The Chain's ``row_var`` MUST equal its ``geo_column`` — otherwise the
    values in the row index aren't geographic features and labeling them
    as such would mislabel (e.g. relabeling ``"Democrat"`` / ``"Republican"``
    as states).

    Returns ``None`` when no ``geo_column`` is set or when the geo-rendering
    library is unavailable. Raises :class:`RenderError` on a configuration
    mismatch or a rendering failure — callers should not silently ship
    reports missing maps.
    """
    if not chain.geo_column:
        return None

    if chain.row_var != chain.geo_column:
        raise RenderError(
            f"Chain.geo_column={chain.geo_column!r} but Chain.row_var="
            f"{chain.row_var!r}. Map generation requires the row variable "
            f"to be the geographic key; otherwise row categories would be "
            f"mislabeled as geo features."
        )

    if map_generator is None:
        try:
            from ..reporting.chart_generator import ChartGenerator
            map_generator = ChartGenerator()
        except ImportError:
            return None

    df = chain.to_dataframe()
    if df.empty:
        return None

    # With row_var == geo_column, the DataFrame index holds geographic values
    # (e.g. state FIPS, state abbreviations). Aggregate across break columns.
    agg = df.iloc[:, 0].reset_index()
    agg.columns = [chain.geo_column, "value"]

    try:
        return map_generator.create_choropleth_map(
            agg, geo_column=chain.geo_column, value_column="value"
        )
    except (ValueError, TypeError, KeyError) as e:
        raise RenderError(
            f"choropleth rendering failed for geo_column={chain.geo_column!r}: {e}"
        ) from e


# ---------------------------------------------------------------------------
# ArgumentCluster — carrier for stack_to_arguments output
# ---------------------------------------------------------------------------

@dataclass
class ArgumentCluster:
    """A named group of rendered :class:`Argument` objects.

    This is the output of :func:`stack_to_arguments` — a typed companion
    to :class:`models.Cluster` (which holds Chains). Separate type prevents
    callers from accidentally feeding Argument-bearing objects into code
    that expects Chain-bearing Clusters.
    """
    name: str
    arguments: List[Argument] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chain_to_argument(
    chain: "Chain",
    headline: str,
    narrative: str,
    *,
    chart_generator: Optional[Any] = None,
    map_generator: Optional[Any] = None,
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
        Optional callable for chart rendering, invoked as
        ``chart_generator(df, chart_type, headline) -> Figure | None``.
        When ``None``, the library's default matplotlib path is used
        (no branding required for sensible output).
    map_generator:
        Optional object exposing
        ``create_choropleth_map(df, geo_column, value_column)``. When
        ``None``, a default :class:`ChartGenerator` instance is used.

    These kwargs make three cases work:

    1. *Ad hoc* — both ``None``, no branding configured: defaults run.
    2. *Override on a one-off* — caller passes a pre-configured generator
       without mutating global branding state.
    3. *Alternative backend* — caller passes a Plotly-based callable / object
       that matches the interface.

    Returns
    -------
    Argument
        chart populated when matplotlib is available; map_figure populated
        only when ``chain.geo_column`` is set and equals ``chain.row_var``.

    Raises
    ------
    RenderError
        On plotting failure or geo_column/row_var mismatch.
    """
    df = chain.to_dataframe()
    chart_type = _select_chart_type(chain)
    chart = _build_chart(df, chart_type, headline, chart_generator=chart_generator)
    map_figure = _build_map(chain, map_generator=map_generator)

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
    headlines: Optional[Dict] = None,
    narratives: Optional[Dict] = None,
) -> List[ArgumentCluster]:
    """Walk all Chains in a Stack, converting each to an Argument.

    Returns a list of :class:`ArgumentCluster` (not :class:`Cluster`) so the
    result type is explicit: these hold Arguments, not Chains.

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
    List[ArgumentCluster]
        One per input :class:`Cluster`; preserves cluster name.
    """
    result: List[ArgumentCluster] = []
    for cluster in stack.clusters:
        args: List[Argument] = []
        for chain in cluster.chains:
            key = (cluster.name, chain.row_var)
            hl = (headlines or {}).get(key, chain.row_var.replace("_", " ").title())
            na = (narratives or {}).get(key, "")
            args.append(chain_to_argument(chain, headline=hl, narrative=na))
        result.append(ArgumentCluster(name=cluster.name, arguments=args))
    return result
