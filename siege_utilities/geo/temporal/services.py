"""
Pure-Python services for building demographic time series.

Ports the core logic from django/services/timeseries_service.py to work
with DataFrames and TemporalDataStore instead of Django ORM.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import pandas as pd

from ..schemas.demographics import (
    DemographicSnapshotSchema,
    DemographicTimeSeriesSchema,
)

log = logging.getLogger(__name__)


@dataclass
class TimeseriesBuildResult:
    """Result of a time-series build run."""

    variable_code: str
    geography_type: str
    records_created: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.records_created + self.records_skipped

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class TemporalTimeseriesBuilder:
    """Pure-Python equivalent of django/services/timeseries_service.py.

    Builds DemographicTimeSeriesSchema instances from snapshot DataFrames,
    computing the same statistics (mean, std_dev, CAGR, trend_direction)
    as the Django service.

    Example:
        builder = TemporalTimeseriesBuilder(store=store, dataset='acs5')
        results = builder.build(
            variables=['B01001_001E'],
            years=[2015, 2016, 2017, 2018, 2019, 2020],
            geography_type='tract',
        )
    """

    def __init__(
        self,
        store: Optional["TemporalDataStore"] = None,
        dataset: str = "acs5",
    ) -> None:
        self.store = store
        self.dataset = dataset

    def build(
        self,
        variables: list[str],
        years: list[int],
        geography_type: str,
        snapshots_df: Optional["pd.DataFrame"] = None,
    ) -> list[TimeseriesBuildResult]:
        """Build time-series schemas from snapshot data.

        Args:
            variables: Census variable codes (e.g. ['B01001_001E'])
            years: Years to include in the series
            geography_type: Geography level name
            snapshots_df: Pre-loaded snapshots DataFrame with columns:
                boundary_id, year, values (dict column), moe_values (dict column).
                If None, loads from self.store.

        Returns:
            List of TimeseriesBuildResult (one per variable), with
            created DemographicTimeSeriesSchema instances accessible
            via result.series.
        """
        import pandas as _pd

        years_sorted = sorted(years)

        if snapshots_df is None:
            if self.store is None:
                raise ValueError(
                    "Either snapshots_df or a store must be provided"
                )
            frames = []
            for y in years_sorted:
                try:
                    df = self.store.load_demographics(
                        geography_type, year=y, dataset=self.dataset
                    )
                    frames.append(df)
                except FileNotFoundError:
                    continue
            if not frames:
                return [
                    TimeseriesBuildResult(
                        variable_code=v, geography_type=geography_type,
                        errors=[f"No snapshot data found for {geography_type}"],
                    )
                    for v in variables
                ]
            snapshots_df = _pd.concat(frames, ignore_index=True)

        results = []
        for variable in variables:
            result = TimeseriesBuildResult(
                variable_code=variable,
                geography_type=geography_type,
            )
            series_list: list[DemographicTimeSeriesSchema] = []

            boundary_ids = snapshots_df["boundary_id"].unique()
            for bid in boundary_ids:
                bid_rows = snapshots_df[snapshots_df["boundary_id"] == bid]

                values_by_year: dict[int, float | int] = {}
                moe_by_year: dict[int, float | int] = {}

                for _, row in bid_rows.iterrows():
                    yr = int(row["year"])
                    if yr not in years_sorted:
                        continue
                    vals = row.get("values", {})
                    if isinstance(vals, dict) and variable in vals:
                        val = vals[variable]
                        if val is not None:
                            values_by_year[yr] = val
                            moe_vals = row.get("moe_values", {})
                            if isinstance(moe_vals, dict) and variable in moe_vals:
                                moe_by_year[yr] = moe_vals[variable]

                if len(values_by_year) < 2:
                    result.records_skipped += 1
                    continue

                s_years = sorted(values_by_year.keys())
                s_values = [values_by_year[y] for y in s_years]
                s_moe = [moe_by_year.get(y) for y in s_years]

                mean_val = sum(s_values) / len(s_values)
                std_dev = self._std_dev(s_values, mean_val)
                elapsed_years = s_years[-1] - s_years[0]
                cagr = self._cagr(s_values[0], s_values[-1], elapsed_years)
                trend = self._trend_direction(s_values)

                ts = DemographicTimeSeriesSchema(
                    boundary_type=geography_type,
                    boundary_id=str(bid),
                    variable_code=variable,
                    dataset=self.dataset,
                    start_year=s_years[0],
                    end_year=s_years[-1],
                    years=s_years,
                    values=s_values,
                    moe_values=s_moe,
                    mean_value=mean_val,
                    std_dev=std_dev,
                    cagr=cagr,
                    trend_direction=trend,
                )
                series_list.append(ts)
                result.records_created += 1

            result.series = series_list  # type: ignore[attr-defined]
            results.append(result)
            log.info(
                "Timeseries %s: created=%d, skipped=%d",
                variable, result.records_created, result.records_skipped,
            )

        return results

    @staticmethod
    def _std_dev(values: list, mean: float) -> float:
        """Population standard deviation (matches Django TimeseriesService)."""
        if len(values) < 2:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    @staticmethod
    def _cagr(
        start_value: float, end_value: float, periods: int
    ) -> float | None:
        """Compound annual growth rate (matches Django TimeseriesService)."""
        if periods <= 0 or start_value <= 0:
            return None
        try:
            return (end_value / start_value) ** (1 / periods) - 1
        except (ZeroDivisionError, ValueError):
            return None

    @staticmethod
    def _trend_direction(values: list) -> str:
        """Classify trend (matches Django TimeseriesService)."""
        if len(values) < 2:
            return "stable"
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)
        pct_change = (
            (second_half - first_half) / first_half if first_half != 0 else 0
        )
        if pct_change > 0.05:
            return "increasing"
        elif pct_change < -0.05:
            return "decreasing"
        return "stable"


class TemporalDemographicService:
    """Build demographic snapshots from Census API data.

    Converts raw Census API DataFrames into DemographicSnapshotSchema
    instances and optionally persists them via TemporalDataStore.
    """

    def __init__(
        self,
        store: Optional["TemporalDataStore"] = None,
        api_key: str | None = None,
    ) -> None:
        self.store = store
        self.api_key = api_key

    def build_snapshots(
        self,
        df: "pd.DataFrame",
        geography_type: str,
        year: int,
        dataset: str = "acs5",
        geoid_column: str = "GEOID",
        variable_columns: list[str] | None = None,
    ) -> list[DemographicSnapshotSchema]:
        """Convert a Census API DataFrame to snapshot schema instances.

        Args:
            df: DataFrame from Census API (columns: GEOID + variable codes)
            geography_type: Geography level name
            year: Census/ACS year
            dataset: Census dataset
            geoid_column: Column containing GEOIDs
            variable_columns: Explicit list of variable columns. If None,
                uses all columns except geoid_column and 'NAME'.

        Returns:
            List of DemographicSnapshotSchema instances
        """
        if variable_columns is None:
            exclude = {geoid_column, "NAME", "name", "state", "county", "tract"}
            variable_columns = [
                c for c in df.columns if c not in exclude
            ]

        estimate_cols = [c for c in variable_columns if c.endswith("E")]
        moe_cols = [c for c in variable_columns if c.endswith("M")]

        snapshots = []
        for _, row in df.iterrows():
            geoid = str(row[geoid_column])

            values: dict[str, float | int | str] = {}
            for col in estimate_cols:
                val = row.get(col)
                if val is not None and str(val) != "nan":
                    if hasattr(val, "item"):
                        val = val.item()
                    values[col] = val

            moe_values: dict[str, float | int | str] = {}
            for col in moe_cols:
                val = row.get(col)
                if val is not None and str(val) != "nan":
                    if hasattr(val, "item"):
                        val = val.item()
                    moe_values[col] = val

            snapshot = DemographicSnapshotSchema(
                boundary_type=geography_type,
                boundary_id=geoid,
                year=year,
                dataset=dataset,
                values=values,
                moe_values=moe_values,
            )
            snapshots.append(snapshot)

        return snapshots
