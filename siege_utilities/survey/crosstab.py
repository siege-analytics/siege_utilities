"""
Chain builder -- converts a respondent/donor-level DataFrame into a Chain.

Delegates chi-square to siege_utilities.data.cross_tabulation (not reimplemented here).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..reporting.pages.page_models import TableType
from .models import Chain, View

DEFAULT_Z_VALUE = 1.96

__all__ = ["CrosstabInputError", "build_chain"]

try:
    from scipy.stats import t as _scipy_t
    _SCIPY_T_AVAILABLE = True
except ImportError:
    _scipy_t = None
    _SCIPY_T_AVAILABLE = False


def _critical_value(n: float, confidence: float = 0.95) -> float:
    """Return the appropriate critical value: t for n<30, z otherwise."""
    if n < 30:
        if not _SCIPY_T_AVAILABLE:
            from .significance import SignificanceError
            raise SignificanceError(
                "MEAN_SCALE with effective n < 30 requires scipy for a t critical value"
            )
        return float(_scipy_t.ppf((1 + confidence) / 2, df=n - 1))
    return DEFAULT_Z_VALUE


class CrosstabInputError(ValueError):
    """Raised when build_chain receives an empty or schema-incompatible DataFrame.

    Distinct from a successful Chain that happens to contain no rows
    (e.g., every category was filtered out downstream). This signals
    the caller fed in something the builder cannot work with at all --
    typically an upstream filter that returned nothing, or a column
    name typo.
    """


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
    # Up-front shape check. The dispatchers downstream assume `df` has
    # rows and that `row_var` / `break_vars` / `metric` / `weight_var`
    # are real columns; without this guard an empty input produces a
    # silent blank Chain that callers can't distinguish from "no
    # significant results."
    if df is None or len(df) == 0:
        raise CrosstabInputError(
            "build_chain: empty DataFrame. The upstream filter / query "
            "returned nothing; a Chain built from an empty frame would "
            "be indistinguishable from one where every category was "
            "filtered out by downstream logic."
        )
    if row_var not in df.columns:
        raise CrosstabInputError(
            f"build_chain: row_var {row_var!r} not in df.columns "
            f"({list(df.columns)[:10]}{'...' if len(df.columns) > 10 else ''})"
        )
    missing_breaks = [b for b in break_vars if b not in df.columns]
    if missing_breaks:
        raise CrosstabInputError(
            f"build_chain: break_vars {missing_breaks!r} not in df.columns"
        )
    if weight_var is not None and weight_var not in df.columns:
        raise CrosstabInputError(
            f"build_chain: weight_var {weight_var!r} not in df.columns"
        )
    if weight_var is not None:
        weights = df[weight_var]
        if not np.isfinite(weights).all() or (weights < 0).any():
            raise CrosstabInputError("Survey weights must be finite and nonnegative")

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


def _base_respondents(df: pd.DataFrame, weight_var: Optional[str]) -> float:
    """Return the display base -- weighted sum or unweighted count.

    Returns a float so fractional weighted bases (e.g. ``1234.7``) are not
    silently truncated. This is not the effective sample size for inference.
    """
    if weight_var and weight_var in df.columns:
        return float(df[weight_var].sum())
    return float(len(df))


def _effective_n(df: pd.DataFrame, weight_var: Optional[str]) -> float:
    """Return Kish effective n, invariant to a common weight multiplier."""
    if weight_var is None:
        return float(len(df))
    weights = df[weight_var]
    maximum = weights.max()
    if not maximum > 0:
        return 0.0
    weights = weights / maximum
    return float(weights.sum() ** 2 / (weights ** 2).sum())


def _respondent_counts(df, row_var, metric) -> Optional[pd.Series]:
    """Only count tables have respondent-frequency metadata.

    A unit-valued metric is a respondent indicator, used by existing callers.
    Other metrics represent sums, for which count-based inference is invalid.
    """
    if metric in df.columns and not df[metric].eq(1).all():
        return None
    return df.groupby(row_var).size()


def _views_from_counts(
    counts: pd.Series,
    base: float,
    pct_base: Optional[float] = None,
    effective_n: Optional[float] = None,
    respondent_counts: Optional[pd.Series] = None,
) -> List[View]:
    total = pct_base if pct_base is not None else float(counts.sum())
    views = []
    for cat, cnt in counts.items():
        pct = float(cnt) / total if total > 0 else 0.0
        views.append(View(
            metric=str(cat), base=base, count=float(cnt), pct=pct,
            effective_n=effective_n,
            respondent_count=int(respondent_counts.get(cat, 0)) if respondent_counts is not None else None,
        ))
    return views


# ---------------------------------------------------------------------------
# Per-type builders
# ---------------------------------------------------------------------------

def _grouped_counts_views(
    df, row_var, break_vars, metric, weight_var, top_n
) -> Dict[str, List[View]]:
    """Shared loop: for each (break_var, break_value) subset, compute weighted
    counts of row_var and wrap as Views keyed ``"{bv}={bval}"``.

    Used by SINGLE_RESPONSE, CROSS_TAB, and BANNER builders (identical body).
    Separate helper keeps the three type-tagged wrappers honest -- a change
    here ripples to all three without drift.
    """
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            total = float(counts.sum())
            respondents = _respondent_counts(subset, row_var, metric)
            if top_n:
                counts = counts.nlargest(top_n)
            views[f"{bv}={bval}"] = _views_from_counts(
                counts, base, pct_base=total,
                effective_n=_effective_n(subset.dropna(subset=[row_var]), weight_var)
                if respondents is not None else None,
                respondent_counts=respondents,
            )
    return views


def _build_single_response(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    return Chain(
        row_var=row_var, break_vars=break_vars,
        views=_grouped_counts_views(df, row_var, break_vars, metric, weight_var, top_n),
        table_type=TableType.SINGLE_RESPONSE, geo_column=geo_column,
    )


def _build_multiple_response(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Percents are per-respondent (sum can exceed 100%); auto-sets base_note.

    Distinct from ``_grouped_counts_views`` because MULTIPLE_RESPONSE uses
    ``pct_base=n_respondents`` -- items that sum to >100% are the whole point.
    """
    views: Dict[str, List[View]] = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            n_respondents = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            key = f"{bv}={bval}"
            views[key] = _views_from_counts(
                counts, base=n_respondents, pct_base=float(n_respondents),
                effective_n=_effective_n(subset, weight_var),
                respondent_counts=_respondent_counts(subset, row_var, metric),
            )
    n_total = _base_respondents(df, weight_var)
    # Display-only: round for the base_note; downstream math keeps full precision.
    base_note = (
        f"n={int(round(n_total)):,} respondents; multiple responses permitted; "
        "percentages sum to more than 100%"
    )
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.MULTIPLE_RESPONSE,
        base_note=base_note, geo_column=geo_column,
    )


def _build_cross_tab(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    return Chain(
        row_var=row_var, break_vars=break_vars,
        views=_grouped_counts_views(df, row_var, break_vars, metric, weight_var, top_n),
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
        total = float(counts.sum())
        respondents = _respondent_counts(subset, row_var, metric)
        if top_n:
            counts = counts.nlargest(top_n)
        key = str(period)
        views[key] = _views_from_counts(
            counts, base, pct_base=total,
            effective_n=_effective_n(subset.dropna(subset=[row_var]), weight_var)
            if respondents is not None else None,
            respondent_counts=respondents,
        )

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
            total = float(counts.sum())
            respondents = _respondent_counts(subset, row_var, metric)
            if top_n:
                counts = counts.head(top_n)
            key = f"{bv}={bval}"
            views[key] = _views_from_counts(
                counts, base, pct_base=total,
                effective_n=_effective_n(subset.dropna(subset=[row_var]), weight_var)
                if respondents is not None else None,
                respondent_counts=respondents,
            )
    return Chain(
        row_var=row_var, break_vars=break_vars, views=views,
        table_type=TableType.RANKING, geo_column=geo_column,
    )


def _build_mean_scale(
    df, row_var, break_vars, metric, weight_var, top_n, geo_column
) -> Chain:
    """Computes mean + 95% CI per break variable value.

    MEAN_SCALE requires the ``metric`` column -- unlike count-based types,
    there is no fallback to row counts. Missing metric raises so callers
    don't receive a silently-empty chain that'd render as a blank page
    with no diagnostic.

    Weights are treated as reliability weights: the variance divides by
    sum(w) - sum(w**2)/sum(w), and SE is sqrt(variance / Kish n). The CI
    uses effective n - 1 degrees of freedom for small samples. This is a
    weight-only approximation, not a correction for clustering/strata.
    """
    if metric not in df.columns:
        raise ValueError(
            f"MEAN_SCALE requires numeric metric column {metric!r}; "
            f"available columns: {list(df.columns)}"
        )

    views: Dict[str, List[View]] = {}

    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            key = f"{bv}={bval}"
            cell_views = []
            for cat in df[row_var].dropna().unique():
                sample = subset[subset[row_var] == cat].dropna(subset=[metric])
                if weight_var is not None:
                    sample = sample[sample[weight_var] > 0]
                if sample.empty:
                    continue
                cat_vals = sample[metric]
                n_eff = _effective_n(sample, weight_var)
                if weight_var is not None:
                    weights = sample[weight_var] / sample[weight_var].max()
                    mean = float((cat_vals * weights).sum() / weights.sum())
                    variance = (
                        float((weights * (cat_vals - mean) ** 2).sum())
                        / float(weights.sum() - (weights ** 2).sum() / weights.sum())
                        if n_eff > 1 else 0.0
                    )
                else:
                    mean = float(cat_vals.mean())
                    variance = float(cat_vals.var(ddof=1)) if n_eff > 1 else 0.0
                ci = _critical_value(n_eff) * (variance / n_eff) ** 0.5 if n_eff > 1 else None
                v = View(metric=str(cat), base=base, count=mean, pct=None, ci=ci,
                         effective_n=n_eff)
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
    return Chain(
        row_var=row_var, break_vars=break_vars,
        views=_grouped_counts_views(df, row_var, break_vars, metric, weight_var, top_n),
        table_type=TableType.BANNER, geo_column=geo_column,
    )
