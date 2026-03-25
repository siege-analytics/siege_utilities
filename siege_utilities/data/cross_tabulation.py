"""Cross-tabulation engine for geographic longitudinal analysis.

Provides functions to build contingency tables from joined datasets,
compute rates and proportions, run chi-square independence tests,
and propagate ACS margins of error through cross-tabulation operations.

Designed to consume output from:
- :meth:`siege_utilities.data.redistricting_data_hub.RDHClient.to_crosstab_input`
- :class:`siege_utilities.geo.timeseries.longitudinal_data.LongitudinalAligner`

Usage::

    from siege_utilities.data.cross_tabulation import contingency_table, chi_square_test

    ct = contingency_table(df, row_var="race", col_var="county")
    result = chi_square_test(ct)
    print(result.p_value)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Union

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ChiSquareResult:
    """Result of a chi-square test of independence.

    Attributes:
        statistic: Chi-square test statistic.
        p_value: p-value under the null hypothesis of independence.
        dof: Degrees of freedom.
        expected_freq: Expected frequency table under independence.
    """

    statistic: float
    p_value: float
    dof: int
    expected_freq: pd.DataFrame


@dataclass
class CrossTabSpec:
    """Specification for a cross-tabulation operation.

    Attributes:
        row_var: Column name for rows.
        col_var: Column name for columns.
        value_var: Column to aggregate (default ``None`` → counts).
        weight_var: Optional weight column.
        aggfunc: Aggregation function name (``'sum'``, ``'mean'``, ``'count'``).
        geography: Optional geography column for stratified cross-tabs.
    """

    row_var: str
    col_var: str
    value_var: Optional[str] = None
    weight_var: Optional[str] = None
    aggfunc: str = "sum"
    geography: Optional[str] = None


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def contingency_table(
    df: pd.DataFrame,
    row_var: str,
    col_var: str,
    value_var: Optional[str] = None,
    weight_var: Optional[str] = None,
    aggfunc: str = "sum",
    margins: bool = True,
) -> pd.DataFrame:
    """Build a contingency table (cross-tabulation) from *df*.

    Parameters
    ----------
    df : DataFrame
        Input data.
    row_var : str
        Column for rows.
    col_var : str
        Column for columns.
    value_var : str, optional
        Column to aggregate. If ``None``, counts occurrences.
    weight_var : str, optional
        Column of weights (multiplied into *value_var* before aggregation).
    aggfunc : str
        Aggregation function: ``'sum'``, ``'mean'``, or ``'count'``.
    margins : bool
        If ``True``, add row/column totals.

    Returns
    -------
    DataFrame with row_var as index, col_var as columns, and aggregated values.
    """
    work = df.copy()

    if value_var is None:
        work["_count"] = 1
        value_var = "_count"

    if weight_var is not None and weight_var in work.columns:
        work[value_var] = work[value_var] * work[weight_var]

    agg_map = {"sum": "sum", "mean": "mean", "count": "count"}
    agg_fn = agg_map.get(aggfunc, aggfunc)

    ct = pd.pivot_table(
        work,
        values=value_var,
        index=row_var,
        columns=col_var,
        aggfunc=agg_fn,
        fill_value=0,
        margins=margins,
        margins_name="Total",
    )

    return ct


def rate_table(
    ct: pd.DataFrame,
    normalize: str = "all",
) -> pd.DataFrame:
    """Normalize a contingency table to proportions.

    Parameters
    ----------
    ct : DataFrame
        Contingency table (output of :func:`contingency_table`).
    normalize : str
        ``'all'`` (divide by grand total), ``'index'`` (row proportions),
        ``'columns'`` (column proportions).

    Returns
    -------
    DataFrame of proportions summing to 1.0 along the requested axis.
    """
    # Strip margins if present before normalizing
    has_total_row = "Total" in ct.index
    has_total_col = "Total" in ct.columns

    inner = ct
    if has_total_row:
        inner = inner.drop(index="Total")
    if has_total_col:
        inner = inner.drop(columns="Total")

    if normalize == "all":
        total = inner.values.sum()
        result = inner / total if total != 0 else inner * 0
    elif normalize == "index":
        row_sums = inner.sum(axis=1)
        result = inner.div(row_sums, axis=0).fillna(0)
    elif normalize == "columns":
        col_sums = inner.sum(axis=0)
        result = inner.div(col_sums, axis=1).fillna(0)
    else:
        raise ValueError(f"normalize must be 'all', 'index', or 'columns', got '{normalize}'")

    return result


def chi_square_test(ct: pd.DataFrame) -> ChiSquareResult:
    """Run a chi-square test of independence on a contingency table.

    Parameters
    ----------
    ct : DataFrame
        Contingency table (without margins). If margins are present
        (row/column named ``'Total'``), they are stripped automatically.

    Returns
    -------
    ChiSquareResult
    """
    try:
        from scipy.stats import chi2_contingency
    except ImportError as exc:
        raise ImportError(
            "scipy is required for chi-square tests. "
            "Install with: pip install 'siege-utilities[analytics]'"
        ) from exc

    # Strip margins
    inner = ct
    if "Total" in inner.index:
        inner = inner.drop(index="Total")
    if "Total" in inner.columns:
        inner = inner.drop(columns="Total")

    stat, p, dof, expected = chi2_contingency(inner.values)

    expected_df = pd.DataFrame(
        expected, index=inner.index, columns=inner.columns,
    )

    return ChiSquareResult(
        statistic=round(stat, 6),
        p_value=round(p, 6),
        dof=dof,
        expected_freq=expected_df,
    )


def moe_cross_tab(
    estimates_df: pd.DataFrame,
    moes_df: pd.DataFrame,
    row_var: str,
    col_var: str,
    value_var: str,
    moe_var: str,
) -> pd.DataFrame:
    """Propagate ACS margins of error through a cross-tabulation.

    Computes the MOE of each cell sum using the Census Bureau's root-sum-of-
    squares rule.  Returns a DataFrame shaped like the contingency table with
    the propagated MOE in each cell.

    Parameters
    ----------
    estimates_df : DataFrame
        Data with estimate values.
    moes_df : DataFrame
        Data with corresponding MOE values (same structure as *estimates_df*).
    row_var, col_var : str
        Row and column variables.
    value_var : str
        Name of the estimate column in *estimates_df*.
    moe_var : str
        Name of the MOE column in *moes_df*.

    Returns
    -------
    DataFrame of propagated MOEs with shape matching the contingency table.
    """
    from .moe_propagation import moe_sum, Estimate

    # Group by (row, col) and collect MOEs
    merged = estimates_df[[row_var, col_var, value_var]].copy()
    merged["_moe"] = moes_df[moe_var].values

    result_records = []
    for (rv, cv), group in merged.groupby([row_var, col_var]):
        estimates = [
            Estimate(value=row[value_var], moe=row["_moe"])
            for _, row in group.iterrows()
        ]
        combined = moe_sum(estimates)
        result_records.append({
            row_var: rv,
            col_var: cv,
            "estimate": combined.value,
            "moe": combined.moe,
        })

    result = pd.DataFrame(result_records)

    # Pivot to table form
    moe_table = result.pivot(index=row_var, columns=col_var, values="moe").fillna(0)
    return moe_table


__all__ = [
    "ChiSquareResult",
    "CrossTabSpec",
    "chi_square_test",
    "contingency_table",
    "moe_cross_tab",
    "rate_table",
]
