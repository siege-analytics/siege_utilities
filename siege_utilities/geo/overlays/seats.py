"""Seats overlay for place history.

Shows which congressional/state legislative districts contained a
geography over time, under which redistricting plans.

Key design constraint from the ST model: "Seat is identity, not
geography." The overlay returns Seat + Plan, not raw CD geometry.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)

__all__ = [
    "DictSeatsProvider",
    "SeatAssignment",
    "SeatsDataProvider",
    "SeatsOverlay",
    "SeatsOverlayResult",
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class SeatAssignment:
    """A seat-to-geography assignment for a time period.

    Attributes:
        seat_label: Human-readable seat label (e.g., "US House CA-12").
        office: Office type (US_HOUSE, US_SENATE, STATE_UPPER, STATE_LOWER).
        district_label: District number/label.
        state_fips: State FIPS code.
        plan_name: Name of the redistricting plan.
        plan_year: Year the plan took effect.
        from_year: Start year of this assignment.
        to_year: End year of this assignment (None = ongoing).
        containment_pct: Fraction of the queried geography in this district.
    """

    seat_label: str = ""
    office: str = ""
    district_label: str = ""
    state_fips: str = ""
    plan_name: str = ""
    plan_year: Optional[int] = None
    from_year: Optional[int] = None
    to_year: Optional[int] = None
    containment_pct: float = 1.0


def _current_districts_at(
    assignments: list[SeatAssignment], reference_year: int,
) -> list[SeatAssignment]:
    """Prefer ongoing rows covering the reference, then the newest start group."""
    current = [
        a for a in assignments
        if a.to_year is None and (a.from_year or 0) <= reference_year
    ]
    if not current:
        current = [
            a for a in assignments
            if (a.from_year or 0) <= reference_year
            and (a.to_year is None or reference_year <= a.to_year)
        ]
    latest_start = max((a.from_year or 0 for a in current), default=0)
    return [a for a in current if (a.from_year or 0) == latest_start]


@dataclass
class SeatsOverlayResult:
    """Result of the seats overlay query.

    Attributes:
        geoid: Queried GEOID.
        assignments: Seat assignments ordered by time.
        current_districts: All current district memberships in each office's latest period.
    """

    geoid: str = ""
    assignments: list[SeatAssignment] = field(default_factory=list)

    @property
    def current_districts(self) -> list[SeatAssignment]:
        """Select current districts per office at one shared reference year.

        The reference is the latest end year (or start year for an ongoing row)
        across all assignments and can be in the past. Within each office,
        prefer ongoing rows covering that year; otherwise use all rows covering
        it, including finite rows at their end year. Omit offices with no row
        covering the reference. Keep every district in the newest start-year
        group, treating an unknown start as earlier than a known start.
        Preserve first-seen office order and row order within each office.
        """
        if not self.assignments:
            return []
        reference_year = max(
            a.to_year if a.to_year is not None else (a.from_year or 0)
            for a in self.assignments
        )
        assignments_by_office: dict[str, list[SeatAssignment]] = {}
        for assignment in self.assignments:
            assignments_by_office.setdefault(assignment.office, []).append(assignment)
        result = []
        for assignments in assignments_by_office.values():
            result.extend(_current_districts_at(assignments, reference_year))
        return result

    @property
    def offices(self) -> list[str]:
        return sorted(set(a.office for a in self.assignments if a.office))

    def for_office(self, office: str) -> list[SeatAssignment]:
        return [a for a in self.assignments if a.office == office]


# ---------------------------------------------------------------------------
# Data provider protocol
# ---------------------------------------------------------------------------


class SeatsDataProvider(abc.ABC):
    """Protocol for fetching seat assignment data.

    Implementations query PlanDistrictAssignment + BoundaryIntersection
    to find which districts contained a GEOID over time.
    """

    @abc.abstractmethod
    def get_assignments(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> list[SeatAssignment]:
        """Get seat assignments for a GEOID and time range."""


class DictSeatsProvider(SeatsDataProvider):
    """In-memory seats provider for testing."""

    def __init__(self):
        self._assignments: list[SeatAssignment] = []

    def add(self, assignment: SeatAssignment):
        self._assignments.append(assignment)

    def get_assignments(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> list[SeatAssignment]:
        lo = min(from_year, to_year)
        hi = max(from_year, to_year)
        results = []
        for a in self._assignments:
            a_from = a.from_year or 0
            a_to = a.to_year or 9999
            if a_to >= lo and a_from <= hi:
                if state_fips and a.state_fips and a.state_fips != state_fips:
                    continue
                results.append(a)
        return sorted(results, key=lambda x: x.from_year or 0)


# ---------------------------------------------------------------------------
# Overlay implementation
# ---------------------------------------------------------------------------


class SeatsOverlay(PlaceHistoryOverlay):
    """Place history overlay showing district/seat assignments over time.

    Args:
        provider: SeatsDataProvider for fetching assignment data.
            If None, attempts to use the Django-backed provider.
    """

    def __init__(self, provider: Optional[SeatsDataProvider] = None):
        self._provider = provider

    @property
    def name(self) -> str:
        return "seats"

    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> SeatsOverlayResult:
        provider = self._provider or self._get_default_provider()
        if provider is None:
            raise RuntimeError("No seats data provider available")

        assignments = provider.get_assignments(
            geoid, from_year, to_year, state_fips
        )
        return SeatsOverlayResult(
            geoid=geoid,
            assignments=assignments,
        )

    def _get_default_provider(self) -> Optional[SeatsDataProvider]:
        try:
            from siege_utilities.geo.django.providers import DjangoSeatsProvider
            return DjangoSeatsProvider()
        except ImportError:
            log.debug("Django seats provider not available (Django not installed or not configured)")
            return None
