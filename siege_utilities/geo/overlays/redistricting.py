"""Redistricting overlay for place history.

Shows which redistricting plan(s) and district(s) applied to a
geography over a queried time range, using plan lifecycle data.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)

__all__ = [
    "DictRedistrictingDataProvider",
    "DistrictAssignment",
    "RedistrictingDataProvider",
    "RedistrictingOverlay",
    "RedistrictingOverlayResult",
]


@dataclass
class DistrictAssignment:
    """A district assignment for a geography under a specific plan.

    Attributes:
        plan_id: Plan identifier.
        plan_name: Human-readable plan name.
        plan_type: Congressional, state senate, or state house.
        district_id: District identifier (e.g., "TX-28").
        state: State abbreviation.
        from_date: When this assignment began.
        to_date: When this assignment ended (None = still active).
        enacted_by: Who enacted the plan.
        court_case: Court case if court-ordered.
        containment_pct: Fraction of queried geography in this district.
    """

    plan_id: str = ""
    plan_name: str = ""
    plan_type: str = ""
    district_id: str = ""
    state: str = ""
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    enacted_by: str = ""
    court_case: str = ""
    containment_pct: float = 1.0


@dataclass
class RedistrictingOverlayResult:
    """Result of the redistricting overlay query.

    Attributes:
        geoid: Queried GEOID.
        assignments: District assignments ordered by time.
        plan_count: Number of distinct plans that applied.
        had_court_intervention: Whether any plan was court-ordered.
    """

    geoid: str = ""
    assignments: list[DistrictAssignment] = field(default_factory=list)

    @property
    def plan_count(self) -> int:
        return len(set(a.plan_id for a in self.assignments))

    @property
    def had_court_intervention(self) -> bool:
        return any(a.court_case for a in self.assignments)

    @property
    def plan_types(self) -> list[str]:
        return sorted(set(a.plan_type for a in self.assignments if a.plan_type))

    def for_plan_type(self, plan_type: str) -> list[DistrictAssignment]:
        return [a for a in self.assignments if a.plan_type == plan_type]

    def active_at(self, when: date) -> list[DistrictAssignment]:
        result = []
        for a in self.assignments:
            if a.from_date and a.from_date > when:
                continue
            if a.to_date and a.to_date < when:
                continue
            result.append(a)
        return result


class RedistrictingDataProvider(abc.ABC):
    """Protocol for fetching redistricting plan assignments for a geography."""

    @abc.abstractmethod
    def get_district_assignments(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> list[DistrictAssignment]:
        """Get district assignments for a geography over a time range."""


class DictRedistrictingDataProvider(RedistrictingDataProvider):
    """In-memory redistricting data provider for testing."""

    def __init__(self):
        self._assignments: list[DistrictAssignment] = []

    def add(self, assignment: DistrictAssignment):
        self._assignments.append(assignment)

    def get_district_assignments(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> list[DistrictAssignment]:
        from_date = date(from_year, 1, 1)
        to_date = date(to_year, 12, 31)
        results = []
        for a in self._assignments:
            if state_fips and a.state.upper() != state_fips.upper():
                continue
            if a.to_date and a.to_date < from_date:
                continue
            if a.from_date and a.from_date > to_date:
                continue
            results.append(a)
        return results


class RedistrictingOverlay(PlaceHistoryOverlay):
    """Place history overlay for redistricting plan assignments.

    Shows which plan(s) and district(s) applied to a geography
    over the queried time range.
    """

    def __init__(self, provider: Optional[RedistrictingDataProvider] = None):
        self._provider = provider

    @property
    def name(self) -> str:
        return "redistricting"

    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> RedistrictingOverlayResult:
        if self._provider is None:
            log.warning("RedistrictingOverlay: no provider configured")
            raise RuntimeError("RedistrictingOverlay requires a provider")

        assignments = self._provider.get_district_assignments(
            geoid, from_year, to_year, state_fips,
        )
        assignments.sort(key=lambda a: a.from_date or date.min)

        return RedistrictingOverlayResult(
            geoid=geoid,
            assignments=assignments,
        )

    def is_available(self) -> bool:
        return self._provider is not None
