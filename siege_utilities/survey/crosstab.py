"""
Chain builder — converts a respondent/donor-level DataFrame into a Chain.

Delegates chi-square to siege_utilities.data.cross_tabulation (not reimplemented here).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..reporting.pages.page_models import TableType
from .models import Chain, View


def build_chain(
    df: pd.DataFrame,
    row_var: str,
    break_vars: List[str],
    metric: str = "value",
    weight_var: Optional[str] = None,
    table_type: TableType = TableType.CROSS_TAB,
    top_n: Optional[int] = None,
    geo_column: Optional[str] = None,
) -> Chain:
    """Build a Chain from a respondent/donor-level DataFrame.

    Parameters
    ----------
    df:
        Input DataFrame; one row per respondent.
    row_var:
        Column whose distinct values become row categories.
    break_vars:
        Columns to cross-tab against (become column groups).
    metric:
        Numeric column to aggregate (default "value"; use column count if absent).
    weight_var:
        Optional weight column name.
    table_type:
        Drives cell computation, chart type, and base note.
    top_n:
        If set, keep only the top N row categories by total volume.
    geo_column:
        If set, attached to Chain to signal map generation.

    Returns
    -------
    Chain
    """
    dispatchers = {
        TableType.SINGLE_RESPONSE:   _build_single_response,
        TableType.MULTIPLE_RESPONSE: _build_multiple_response,
        TableType.CROSS_TAB:         _build_cross_tab,
        TableType.LONGITUDINAL:      _build_longitudinal,
        TableType.RANKING:           _build_ranking,
        TableType.MEAN_SCALE:        _build_mean_scale,
        TableType.BANNER:            _build_banner,
    }
    fn = dispatchers[table_type]
    return fn(
        df=df,
        row_var=row_var,
        break_vars=break_vars,
        metric=metric,
        weight_var=weight_var,
        top_n=top_n,
        geo_column=geo_column,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _weighted_counts(
    df: pd.DataFrame,
    group_col: str,
    metric: str,
    weight_var: Optional[str],
) -> pd.Series:
    """Return weighted sum (or unweighted count if metric absent)."""
    if metric in df.columns:
        if weight_var and weight_var in df.columns:
            return df.groupby(group_col).apply(
                lambda g: (g[metric] * g[weight_var]).sum(), include_groups=False
            )
        return df.groupby(group_col)[metric].sum()
    # Fall back to respondent count
    if weight_var and weight_var in df.columns:
        return df.groupby(group_col)[weight_var].sum()
    return df.groupby(group_col).size().astype(float)


def _base_respondents(df: pd.DataFrame, weight_var: Optional[str]) -> int:
    if weight_var and weight_var in df.columns:
        return int(df[weight_var].sum())
    return len(df)


def _views_from_counts(
    counts: pd.Series,
    base: int,
    pct_base: Optional[float] = None,
) -> List[View]:
    total = pct_base if pct_base is not None else float(counts.sum())
    views = []
    for cat, cnt in counts.items():
        pct = float(cnt) / total if total > 0 else 0.0
        views.append(View(metric=str(cat), base=base, count=float(cnt), pct=pct))
    return views


# ---------------------------------------------------------------------------
# Per-type builders
# ---------------------------------------------------------------------------

def _build_single_response(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            key = f"{bv}={bval}"
            views[key] = _views_from_counts(counts, base)
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.SINGLE_RESPONSE, geo_column=geo_column,
    )


def _build_multiple_response(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Percents are per-respondent (sum can exceed 100%); auto-sets base_note."""
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            n_respondents = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            key = f"{bv}={bval}"
            # Percent base = respondents, not responses (items sum > 100%)
            views[key] = _views_from_counts(
                counts, base=n_respondents, pct_base=float(n_respondents)
            )
    n_total = _base_respondents(df, weight_var)
    base_note = f"n={n_total:,} respondents; multiple responses permitted; percentages sum to more than 100%"
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.MULTIPLE_RESPONSE,
        base_note=base_note, geo_column=geo_column,
    )


def _build_cross_tab(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            key = f"{bv}={bval}"
            views[key] = _views_from_counts(counts, base)
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.CROSS_TAB, geo_column=geo_column,
    )


def _build_longitudinal(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Time periods become columns; adds a delta column (last − first period)."""
    views: Dict[str, List[View]] = {}
    time_col = break_vars[0] if break_vars else row_var
    periods = sorted(df[time_col].dropna().unique())

    for period in periods:
        subset = df[df[time_col] == period]
        base = _base_respondents(subset, weight_var)
        counts = _weighted_counts(subset, row_var, metric, weight_var)
        if top_n:
            counts = counts.nlargest(top_n)
        key = str(period)
        views[key] = _views_from_counts(counts, base)

    # Compute delta: last period − first period
    delta_col = None
    if len(periods) >= 2:
        first_key = str(periods[0])
        last_key = str(periods[-1])
        first_map = {v.metric: v.count for v in views.get(first_key, [])}
        last_map  = {v.metric: v.count for v in views.get(last_key, [])}
        all_cats = set(first_map) | set(last_map)
        base = _base_respondents(df, weight_var)
        delta_views = []
        for cat in sorted(all_cats):
            d = last_map.get(cat, 0.0) - first_map.get(cat, 0.0)
            delta_views.append(View(metric=cat, base=base, count=d, pct=None))
        delta_col = "Δ (change)"
        views[delta_col] = delta_views

    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.LONGITUDINAL,
        delta_column=delta_col, geo_column=geo_column,
    )


def _build_ranking(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Sorted descending; includes rank and share columns."""
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            counts = counts.sort_values(ascending=False)
            if top_n:
                counts = counts.head(top_n)
            key = f"{bv}={bval}"
            views[key] = _views_from_counts(counts, base)
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.RANKING, geo_column=geo_column,
    )


def _build_mean_scale(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Computes mean + 95% CI per break variable value."""
    views: Dict[str, List[View]] = {}
    if metric not in df.columns:
        return Chain(
            row_var=row_var, break_vars=break_vars, views={},
            table_type=TableType.MEAN_SCALE, geo_column=geo_column,
        )

    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            key = f"{bv}={bval}"
            cell_views = []
            for cat in df[row_var].dropna().unique():
                cat_vals = subset[subset[row_var] == cat][metric].dropna()
                if len(cat_vals) == 0:
                    continue
                mean = float(cat_vals.mean())
                ci = 1.96 * float(cat_vals.std(ddof=1)) / (len(cat_vals) ** 0.5) if len(cat_vals) > 1 else 0.0
                v = View(metric=str(cat), base=base, count=mean, pct=None)
                v.ci = ci  # type: ignore[attr-defined]  # attached dynamically
                cell_views.append(v)
            if top_n:
                cell_views = sorted(cell_views, key=lambda v: v.count, reverse=True)[:top_n]
            views[key] = cell_views

    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.MEAN_SCALE, geo_column=geo_column,
    )


def _build_banner(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Multi-column cross-tab (OSCAR-style): each break var is a banner column."""
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            key = f"{bv}={bval}"
            views[key] = _views_from_counts(counts, base)
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.BANNER, geo_column=geo_column,
    )
