#!/usr/bin/env python3
"""Polling analysis — cross-tabulation, longitudinal analysis, change detection.

Operates on long-form DataFrames with at least one dimension column and one
numeric metric column (default ``metric='value'``). Callers supply their own
column names via keyword arguments.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from siege_utilities.core.logging import log_error

from ..chart_generator import ChartGenerator


class PollingAnalysisError(RuntimeError):
    """Raised when polling analysis cannot complete due to bad input or config."""


def _choose_heatmap_fmt(df: pd.DataFrame) -> str:
    """Return ``'d'`` when every column is integer-typed and every value is an
    integer, ``'.2f'`` otherwise.

    Seaborn's ``fmt='d'`` crashes on float values (``ValueError: Unknown format
    code 'd'``). A crosstab built from integer sums can still surface floats if
    ``.fillna(0)`` upcast, so check both dtype and actual values.
    """
    try:
        if not all(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
            return ".2f"
        arr = df.to_numpy()
        if pd.api.types.is_integer_dtype(arr):
            return "d"
        # Float dtype but values round-trip as integers (e.g. 30.0) — keep 'd'.
        if (arr == arr.astype(int)).all():
            return "d"
        return ".2f"
    except (AttributeError, ValueError, TypeError):
        return ".2f"


class PollingAnalyzer:
    """Cross-dimensional analytics for polling and survey data."""

    def __init__(self) -> None:
        self.chart_generator = ChartGenerator()
        self.analysis_results: Dict[str, object] = {}

    def create_cross_tabulation_matrix(
        self,
        data: pd.DataFrame,
        dimensions: List[str],
        *,
        metric: str = "value",
        top_n: int = 10,
    ) -> Dict[str, pd.DataFrame]:
        """Build pairwise cross-tabulations for all dimension combinations.

        Parameters
        ----------
        data : pd.DataFrame
            Input data with one row per observation.
        dimensions : list of str
            Column names to cross-tab. Must exist in ``data``.
        metric : str, keyword-only
            Numeric column to aggregate (sum).
        top_n : int, keyword-only
            Keep only the top ``top_n`` values per dimension.

        Returns
        -------
        dict
            Keys ``"{dim1}_x_{dim2}"``; values are filtered cross-tab DataFrames.

        Raises
        ------
        PollingAnalysisError
            If a required column is missing or aggregation fails.
        """
        try:
            cross_tabs: Dict[str, pd.DataFrame] = {}
            for i, dim1 in enumerate(dimensions):
                for dim2 in dimensions[i + 1:]:
                    crosstab = pd.crosstab(
                        data[dim1],
                        data[dim2],
                        values=data[metric],
                        aggfunc="sum",
                    ).fillna(0)
                    top_dim1 = data.groupby(dim1)[metric].sum().nlargest(top_n).index
                    top_dim2 = data.groupby(dim2)[metric].sum().nlargest(top_n).index
                    cross_tabs[f"{dim1}_x_{dim2}"] = crosstab.loc[top_dim1, top_dim2]
            return cross_tabs
        except (KeyError, ValueError, TypeError) as e:
            log_error(f"cross-tabulation failed (dimensions={dimensions!r}, metric={metric!r}): {e}")
            raise PollingAnalysisError(
                f"cross-tabulation failed for dimensions={dimensions!r}, metric={metric!r}"
            ) from e

    def create_longitudinal_analysis(
        self,
        data: pd.DataFrame,
        time_column: str,
        dimensions: List[str],
        *,
        metric: str = "value",
        periods: Tuple[str, ...] = ("daily", "weekly", "monthly", "quarterly"),
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Aggregate ``data`` by time period and dimension.

        Parameters
        ----------
        data : pd.DataFrame
            Input with a parseable time column.
        time_column : str
            Column to convert to datetime and group by period.
        dimensions : list of str
            Dimension columns to group within each period.
        metric : str, keyword-only
            Numeric column to sum.
        periods : tuple of str, keyword-only
            Subset of ``{"daily", "weekly", "monthly", "quarterly"}``.

        Returns
        -------
        dict
            ``{period: {dimension: DataFrame}}``.

        Raises
        ------
        PollingAnalysisError
            If the time column cannot be parsed or a period name is unknown.
        """
        period_map = {
            "daily": lambda s: s.dt.date,
            "weekly": lambda s: s.dt.to_period("W"),
            "monthly": lambda s: s.dt.to_period("M"),
            "quarterly": lambda s: s.dt.to_period("Q"),
        }
        try:
            data = data.copy()
            data[time_column] = pd.to_datetime(data[time_column])
            results: Dict[str, Dict[str, pd.DataFrame]] = {}
            for period in periods:
                if period not in period_map:
                    raise PollingAnalysisError(
                        f"unknown period {period!r}; expected one of {list(period_map)}"
                    )
                data = data.assign(period=period_map[period](data[time_column]))
                results[period] = {
                    d: data.groupby(["period", d])[metric].sum().reset_index()
                    for d in dimensions
                }
            return results
        except (KeyError, ValueError, TypeError) as e:
            log_error(f"longitudinal analysis failed (time={time_column!r}, dims={dimensions!r}): {e}")
            raise PollingAnalysisError(
                f"longitudinal analysis failed for time_column={time_column!r}"
            ) from e

    def create_performance_rankings(
        self,
        data: pd.DataFrame,
        dimensions: List[str],
        *,
        metric: str = "value",
        top_n: int = 10,
    ) -> Dict[str, List[Tuple[object, float, float]]]:
        """Rank the top-N values per dimension by total ``metric``.

        Parameters
        ----------
        data : pd.DataFrame
        dimensions : list of str
        metric : str, keyword-only
        top_n : int, keyword-only

        Returns
        -------
        dict of list of tuple
            For each dimension, a list of ``(value, sum_metric, percentage)``.
            ``percentage`` is the share of the dimension's total, in [0, 100].

        Raises
        ------
        PollingAnalysisError
            If a required column is missing.
        """
        try:
            rankings: Dict[str, List[Tuple[object, float, float]]] = {}
            for dimension in dimensions:
                agg = data.groupby(dimension)[metric].agg(["sum", "count"]).reset_index()
                total = agg["sum"].sum()
                agg["percentage"] = (agg["sum"] / total * 100) if total else 0.0
                agg = agg.sort_values("sum", ascending=False).head(top_n)
                rankings[dimension] = [
                    (row[dimension], float(row["sum"]), float(row["percentage"]))
                    for _, row in agg.iterrows()
                ]
            return rankings
        except (KeyError, ValueError, TypeError) as e:
            log_error(f"performance rankings failed (dims={dimensions!r}, metric={metric!r}): {e}")
            raise PollingAnalysisError(
                f"performance rankings failed for dimensions={dimensions!r}"
            ) from e

    def create_change_detection_data(
        self,
        current_data: pd.DataFrame,
        historical_data: pd.DataFrame,
        *,
        geographic_column: str = "geography",
        metric: str = "value",
    ) -> pd.DataFrame:
        """Compare current vs historical aggregates and compute growth/decline.

        Parameters
        ----------
        current_data, historical_data : pd.DataFrame
            Long-form data sharing ``geographic_column`` and ``metric`` columns.
        geographic_column : str, keyword-only
            Column to aggregate on.
        metric : str, keyword-only
            Numeric column to sum.

        Returns
        -------
        pd.DataFrame
            Columns: ``geographic_column``, ``{metric}_current``,
            ``{metric}_historical``, ``change_pct``, ``change_direction``.

        Raises
        ------
        PollingAnalysisError
            If either frame is missing the required columns.
        """
        try:
            current_agg = current_data.groupby(geographic_column)[metric].sum().reset_index()
            historical_agg = historical_data.groupby(geographic_column)[metric].sum().reset_index()
            merged = current_agg.merge(
                historical_agg,
                on=geographic_column,
                suffixes=("_current", "_historical"),
                how="outer",
            ).fillna(0)
            baseline = merged[f"{metric}_historical"]
            current = merged[f"{metric}_current"]
            merged["change_pct"] = (
                (current - baseline)
                .div(baseline.replace(0, pd.NA))
                .mul(100)
            )

            # Zero-baseline handling: a new geography (historical=0, current>0)
            # is "growth_from_zero", not silently "stable" via fillna(0).
            new_geography = baseline.eq(0) & current.gt(0)

            def _classify(row) -> str:
                if row["_new"]:
                    return "growth_from_zero"
                pct = row["change_pct"]
                if pd.isna(pct):
                    return "stable"
                return "growth" if pct > 0 else ("decline" if pct < 0 else "stable")

            merged["_new"] = new_geography
            merged["change_direction"] = merged.apply(_classify, axis=1)
            merged["change_pct"] = merged["change_pct"].fillna(0.0)
            return merged.drop(columns=["_new"])
        except (KeyError, ValueError, TypeError) as e:
            log_error(f"change detection failed (col={geographic_column!r}, metric={metric!r}): {e}")
            raise PollingAnalysisError(
                f"change detection failed for geographic_column={geographic_column!r}"
            ) from e

    def create_polling_summary(
        self,
        data: Dict[str, pd.DataFrame],
        *,
        metric: str = "value",
        name_column: Optional[str] = None,
    ) -> str:
        """Build an executive-summary string from a dict of data-type frames.

        Parameters
        ----------
        data : dict of pd.DataFrame
            Keyed by data-type label (e.g. ``"region"``, ``"segment"``).
        metric : str, keyword-only
        name_column : str, keyword-only, optional
            Column to read the top performer's label from. If omitted, the
            first column that is not the metric is used.

        Returns
        -------
        str
            Multi-sentence summary.

        Raises
        ------
        PollingAnalysisError
            If no frame in ``data`` contains the requested ``metric`` column,
            or a frame has no non-metric column to use as a label.
        """
        try:
            frames_with_metric = {k: df for k, df in data.items() if metric in df.columns and not df.empty}
            if not frames_with_metric:
                raise PollingAnalysisError(
                    f"no frame in data contains metric={metric!r}; keys={list(data)}"
                )

            total_value = sum(df[metric].sum() for df in frames_with_metric.values())
            dimensions_info = {k: len(df) for k, df in frames_with_metric.items()}

            top_performers: Dict[str, Dict[str, object]] = {}
            for data_type, df in frames_with_metric.items():
                # Pick a label column explicitly rather than trusting iloc[0]
                # to sit on the dimension. Caller can pin via name_column=.
                if name_column and name_column in df.columns:
                    label_col = name_column
                else:
                    label_col = next((c for c in df.columns if c != metric), None)
                if label_col is None:
                    raise PollingAnalysisError(
                        f"frame for {data_type!r} has no non-metric column to label; "
                        f"pass name_column= explicitly"
                    )
                top_item = df.nlargest(1, metric).iloc[0]
                value = float(top_item[metric])
                top_performers[data_type] = {
                    "name": top_item[label_col],
                    "value": value,
                    "percentage": (value / total_value * 100) if total_value else 0.0,
                }

            parts = [
                f"This comprehensive polling analysis examines {total_value:,.0f} {metric} across multiple dimensions."
            ]
            parts.extend(f"{k.title()}: {n} items" for k, n in dimensions_info.items())
            parts.append("Key findings include:")
            parts.extend(
                f"{p['name']} leads {dt} with {p['value']:,.0f} {metric} ({p['percentage']:.1f}%)"
                for dt, p in top_performers.items()
            )
            parts.append("Cross-dimensional analysis reveals patterns in distribution and performance.")
            return " ".join(parts)
        except PollingAnalysisError:
            raise
        except (KeyError, ValueError, TypeError, IndexError) as e:
            log_error(f"polling summary failed (metric={metric!r}): {e}")
            raise PollingAnalysisError(
                f"polling summary generation failed for metric={metric!r}"
            ) from e

    def create_heatmap_visualization(
        self,
        crosstab_data: pd.DataFrame,
        *,
        title: str = "Cross-Tabulation Heatmap",
        metric: str = "value",
        figsize: Tuple[int, int] = (10, 8),
    ) -> plt.Figure:
        """Render a cross-tab as a Seaborn heatmap.

        ``metric`` is keyword-only; it is used only for the colorbar label.
        The annotation format is chosen automatically from the data dtype
        (integer data gets ``'d'``, float data gets ``'.2f'``).

        Parameters
        ----------
        crosstab_data : pd.DataFrame
            Output of :meth:`create_cross_tabulation_matrix`.
        title : str, keyword-only
        metric : str, keyword-only
        figsize : tuple of int, keyword-only

        Returns
        -------
        matplotlib.figure.Figure

        Raises
        ------
        PollingAnalysisError
            If matplotlib or seaborn cannot render the input.
        """
        try:
            fig, ax = plt.subplots(figsize=figsize)
            fmt = _choose_heatmap_fmt(crosstab_data)
            # Seaborn's fmt='d' expects an integer dtype; cast float-valued
            # integers (e.g. 30.0) to int so ``format(v, 'd')`` doesn't raise.
            data_to_plot = crosstab_data.astype(int) if fmt == "d" else crosstab_data
            sns.heatmap(
                data_to_plot,
                annot=True,
                fmt=fmt,
                cmap="YlOrRd",
                ax=ax,
                cbar_kws={"label": metric.title()},
            )
            ax.set_title(title, fontsize=14, fontweight="bold")
            ax.set_xlabel("")
            ax.set_ylabel("")
            plt.tight_layout()
            return fig
        except (ValueError, TypeError) as e:
            log_error(f"heatmap rendering failed (shape={crosstab_data.shape}): {e}")
            raise PollingAnalysisError("heatmap rendering failed") from e

    def create_trend_analysis_chart(
        self,
        longitudinal_data: Dict[str, pd.DataFrame],
        dimension: str,
        *,
        metric: str = "value",
        figsize: Tuple[int, int] = (12, 6),
    ) -> plt.Figure:
        """Plot per-period trend lines for a single dimension.

        Parameters
        ----------
        longitudinal_data : dict of pd.DataFrame
            Keyed by period label.
        dimension : str
            Dimension column name to title/label with.
        metric : str, keyword-only
        figsize : tuple of int, keyword-only

        Returns
        -------
        matplotlib.figure.Figure

        Raises
        ------
        PollingAnalysisError
            If plotting fails.
        """
        try:
            fig, ax = plt.subplots(figsize=figsize)
            for period, data in longitudinal_data.items():
                if "period" in data.columns and metric in data.columns:
                    period_data = data.groupby("period")[metric].sum()
                    ax.plot(
                        period_data.index.astype(str),
                        period_data.values,
                        marker="o",
                        label=period,
                        linewidth=2,
                    )
            ax.set_title(f"Trend Analysis: {dimension.title()}", fontsize=14, fontweight="bold")
            ax.set_xlabel("Time Period")
            ax.set_ylabel(metric.title())
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            return fig
        except (ValueError, TypeError) as e:
            log_error(f"trend chart rendering failed (dimension={dimension!r}): {e}")
            raise PollingAnalysisError(
                f"trend chart rendering failed for dimension={dimension!r}"
            ) from e
