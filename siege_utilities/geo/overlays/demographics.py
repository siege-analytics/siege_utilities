"""Demographics overlay for place history.

Assembles DemographicSnapshot time series for a queried geography,
handling GEOID changes via the crosswalk chain from the lineage.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)

__all__ = [
    "DemographicPoint",
    "DemographicsDataProvider",
    "DemographicsOverlay",
    "DemographicsOverlayResult",
    "DictDemographicsProvider",
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class DemographicPoint:
    """A single demographic data point for a year.

    Attributes:
        year: Data year.
        geoid: GEOID this data belongs to.
        dataset: Dataset identifier (acs5, acs1, dec, dec_pl).
        total_population: Total population if available.
        median_household_income: Median HH income if available.
        median_age: Median age if available.
        values: Full variable code → value mapping.
    """

    year: int = 0
    geoid: str = ""
    dataset: str = ""
    total_population: Optional[int] = None
    median_household_income: Optional[float] = None
    median_age: Optional[float] = None
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class DemographicsOverlayResult:
    """Result of the demographics overlay query.

    Attributes:
        geoid: Queried GEOID.
        time_series: Ordered list of demographic data points.
        geoids_queried: All GEOIDs queried (includes crosswalk targets).
    """

    geoid: str = ""
    time_series: list[DemographicPoint] = field(default_factory=list)
    geoids_queried: list[str] = field(default_factory=list)

    @property
    def years(self) -> list[int]:
        return sorted(set(p.year for p in self.time_series))

    @property
    def has_data(self) -> bool:
        return len(self.time_series) > 0

    def for_year(self, year: int) -> list[DemographicPoint]:
        return [p for p in self.time_series if p.year == year]

    def population_series(self) -> list[tuple[int, Optional[int]]]:
        return [
            (p.year, p.total_population)
            for p in self.time_series
            if p.total_population is not None
        ]


# ---------------------------------------------------------------------------
# Data provider protocol
# ---------------------------------------------------------------------------


class DemographicsDataProvider(abc.ABC):
    """Protocol for fetching demographic snapshot data."""

    @abc.abstractmethod
    def get_snapshots(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        dataset: Optional[str] = None,
    ) -> list[DemographicPoint]:
        """Get demographic data points for a GEOID and year range."""


class DictDemographicsProvider(DemographicsDataProvider):
    """In-memory demographics provider for testing."""

    def __init__(self):
        self._data: list[DemographicPoint] = []

    def add(self, point: DemographicPoint):
        self._data.append(point)

    def get_snapshots(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        dataset: Optional[str] = None,
    ) -> list[DemographicPoint]:
        lo = min(from_year, to_year)
        hi = max(from_year, to_year)
        results = []
        for p in self._data:
            if p.geoid != geoid:
                continue
            if p.year < lo or p.year > hi:
                continue
            if dataset and p.dataset != dataset:
                continue
            results.append(p)
        return sorted(results, key=lambda x: x.year)


# ---------------------------------------------------------------------------
# Overlay implementation
# ---------------------------------------------------------------------------


class DemographicsOverlay(PlaceHistoryOverlay):
    """Place history overlay for demographic time series.

    Queries DemographicSnapshot data for the queried GEOID and any
    related GEOIDs from the crosswalk chain (when a GEOID changes
    across decades).

    Args:
        provider: DemographicsDataProvider for fetching snapshot data.
        dataset: Restrict to a specific dataset (e.g., "acs5").
        terminal_geoids: Additional GEOIDs to query (from lineage).
    """

    def __init__(
        self,
        provider: Optional[DemographicsDataProvider] = None,
        dataset: Optional[str] = None,
    ):
        self._provider = provider
        self._dataset = dataset

    @property
    def name(self) -> str:
        return "demographics"

    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
        terminal_geoids: Optional[list[str]] = None,
    ) -> DemographicsOverlayResult:
        provider = self._provider or self._get_default_provider()
        if provider is None:
            raise RuntimeError("No demographics data provider available")

        all_geoids = [geoid]
        if terminal_geoids:
            for g in terminal_geoids:
                if g not in all_geoids:
                    all_geoids.append(g)

        all_points = []
        for g in all_geoids:
            points = provider.get_snapshots(g, from_year, to_year, self._dataset)
            all_points.extend(points)

        all_points.sort(key=lambda p: (p.year, p.geoid))

        return DemographicsOverlayResult(
            geoid=geoid,
            time_series=all_points,
            geoids_queried=all_geoids,
        )

    def _get_default_provider(self) -> Optional[DemographicsDataProvider]:
        try:
            from siege_utilities.geo.django.providers import DjangoDemographicsProvider
            return DjangoDemographicsProvider()
        except ImportError:
            log.debug("Django demographics provider not available (Django not installed or not configured)")
            return None
