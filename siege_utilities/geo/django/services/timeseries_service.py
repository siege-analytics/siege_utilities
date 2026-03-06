"""
Service for populating DemographicTimeSeries from multi-year Census data.

Fetches Census data across multiple years for a given geography level,
computes trend statistics (CAGR, std_dev, trend direction), and bulk-creates
DemographicTimeSeries records.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class TimeseriesResult:
    """Result of a timeseries population run."""

    variable_code: str
    geography_level: str
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.records_created + self.records_updated + self.records_skipped

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class TimeseriesService:
    """
    Populate DemographicTimeSeries from multi-year Census snapshots.

    This service reads existing DemographicSnapshot records for a boundary,
    assembles time series, computes statistics, and stores the result
    as a DemographicTimeSeries record.

    Example:
        service = TimeseriesService()
        result = service.populate_timeseries(
            variables=['B01001_001E'],
            years=range(2015, 2023),
            geography_level='tract',
            state_fips='06',
        )
    """

    def __init__(self, dataset: str = 'acs5'):
        """
        Args:
            dataset: Census dataset identifier (acs5, acs1, dec)
        """
        self.dataset = dataset

    def populate_timeseries(
        self,
        variables: List[str],
        years: List[int],
        geography_level: str,
        state_fips: Optional[str] = None,
        update_existing: bool = False,
        batch_size: int = 500,
    ) -> List[TimeseriesResult]:
        """
        Build DemographicTimeSeries records from existing DemographicSnapshots.

        Args:
            variables: List of Census variable codes (e.g., ['B01001_001E'])
            years: List of years to include in the series
            geography_level: Geography level ('tract', 'county', etc.)
            state_fips: Optional state FIPS to filter boundaries
            update_existing: If True, update existing series; else skip
            batch_size: Bulk create batch size

        Returns:
            List of TimeseriesResult (one per variable)
        """
        from django.contrib.contenttypes.models import ContentType

        from ..models.demographics import DemographicSnapshot, DemographicTimeSeries

        # Resolve model from geography level
        model_cls = self._resolve_model(geography_level)
        if model_cls is None:
            return [
                TimeseriesResult(
                    variable_code=v,
                    geography_level=geography_level,
                    errors=[f"Unknown geography level: {geography_level}"],
                )
                for v in variables
            ]

        content_type = ContentType.objects.get_for_model(model_cls)
        years_sorted = sorted(years)
        results = []

        for variable in variables:
            result = TimeseriesResult(
                variable_code=variable,
                geography_level=geography_level,
            )

            # Get all boundaries for this level
            qs = model_cls.objects.all()
            if state_fips and hasattr(model_cls, "state_fips"):
                qs = qs.filter(state_fips=state_fips)

            geoids = list(qs.values_list("geoid", flat=True).distinct())
            to_create = []

            for geoid in geoids:
                # Gather snapshots for this boundary across years
                snapshots = DemographicSnapshot.objects.filter(
                    content_type=content_type,
                    object_id=geoid,
                    dataset=self.dataset,
                    year__in=years_sorted,
                ).order_by("year")

                values_by_year = {}
                moe_by_year = {}
                for snap in snapshots:
                    val = snap.values.get(variable)
                    if val is not None:
                        values_by_year[snap.year] = val
                        moe_val = snap.moe_values.get(variable)
                        if moe_val is not None:
                            moe_by_year[snap.year] = moe_val

                if len(values_by_year) < 2:
                    result.records_skipped += 1
                    continue

                series_years = sorted(values_by_year.keys())
                series_values = [values_by_year[y] for y in series_years]
                series_moe = [moe_by_year.get(y) for y in series_years]

                # Compute statistics
                mean_val = sum(series_values) / len(series_values)
                std_dev = self._std_dev(series_values, mean_val)
                cagr = self._cagr(series_values[0], series_values[-1], len(series_years) - 1)
                trend = self._trend_direction(series_values)

                # Check for existing
                existing = DemographicTimeSeries.objects.filter(
                    content_type=content_type,
                    object_id=geoid,
                    variable_code=variable,
                    dataset=self.dataset,
                    start_year=series_years[0],
                    end_year=series_years[-1],
                ).first()

                if existing and not update_existing:
                    result.records_skipped += 1
                    continue

                if existing and update_existing:
                    existing.years = series_years
                    existing.values = series_values
                    existing.moe_values = [m for m in series_moe if m is not None]
                    existing.mean_value = mean_val
                    existing.std_dev = std_dev
                    existing.cagr = cagr
                    existing.trend_direction = trend
                    existing.save()
                    result.records_updated += 1
                    continue

                to_create.append(
                    DemographicTimeSeries(
                        content_type=content_type,
                        object_id=geoid,
                        variable_code=variable,
                        dataset=self.dataset,
                        start_year=series_years[0],
                        end_year=series_years[-1],
                        years=series_years,
                        values=series_values,
                        moe_values=[m for m in series_moe if m is not None],
                        mean_value=mean_val,
                        std_dev=std_dev,
                        cagr=cagr,
                        trend_direction=trend,
                    )
                )

            # Bulk create
            if to_create:
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i: i + batch_size]
                    DemographicTimeSeries.objects.bulk_create(
                        batch, ignore_conflicts=True
                    )
                result.records_created = len(to_create)

            results.append(result)
            log.info(
                f"Timeseries {variable}: created={result.records_created}, "
                f"updated={result.records_updated}, skipped={result.records_skipped}"
            )

        return results

    def _resolve_model(self, geography_level: str):
        """Resolve a geography level string to a Django model class."""
        from django.apps import apps

        LEVEL_TO_MODEL = {
            "state": "State",
            "county": "County",
            "tract": "Tract",
            "block_group": "BlockGroup",
            "block": "Block",
            "place": "Place",
            "zcta": "ZCTA",
            "cd": "CongressionalDistrict",
            "sldu": "StateLegislativeUpper",
            "sldl": "StateLegislativeLower",
            "vtd": "VTD",
        }
        model_name = LEVEL_TO_MODEL.get(geography_level)
        if model_name is None:
            return None
        try:
            return apps.get_model("siege_geo", model_name)
        except LookupError:
            return None

    @staticmethod
    def _std_dev(values: list, mean: float) -> float:
        """Population standard deviation."""
        if len(values) < 2:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    @staticmethod
    def _cagr(start_value: float, end_value: float, periods: int) -> Optional[float]:
        """Compound annual growth rate."""
        if periods <= 0 or start_value <= 0:
            return None
        try:
            return (end_value / start_value) ** (1 / periods) - 1
        except (ZeroDivisionError, ValueError):
            return None

    @staticmethod
    def _trend_direction(values: list) -> str:
        """Classify trend as increasing, decreasing, or stable."""
        if len(values) < 2:
            return "stable"
        # Simple linear trend: compare first half mean to second half mean
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)
        pct_change = (second_half - first_half) / first_half if first_half != 0 else 0
        if pct_change > 0.05:
            return "increasing"
        elif pct_change < -0.05:
            return "decreasing"
        return "stable"
