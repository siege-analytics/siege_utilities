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
from typing import Any, Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)


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
        to_year: End year of this assignment.
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


@dataclass
class SeatsOverlayResult:
    """Result of the seats overlay query.

    Attributes:
        geoid: Queried GEOID.
        assignments: Seat assignments ordered by time.
        current_districts: Districts containing the GEOID now.
    """

    geoid: str = ""
    assignments: list[SeatAssignment] = field(default_factory=list)

    @property
    def current_districts(self) -> list[SeatAssignment]:
        if not self.assignments:
            return []
        max_year = max(
            (a.to_year or a.from_year or 0) for a in self.assignments
        )
        return [
            a for a in self.assignments
            if (a.to_year or a.from_year or 0) == max_year
        ]

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
        except (RuntimeError, ValueError, TypeError, AttributeError, OSError) as exc:
            log.warning("Failed to initialise Django seats provider: %s", exc)
            return None
