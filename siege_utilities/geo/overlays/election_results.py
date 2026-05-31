"""Election results overlay for place history.

Shows precinct-level election returns for a queried geography,
reconciled via precinct-VTD mapping where needed.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)

__all__ = [
    "DictElectionDataProvider",
    "ElectionDataProvider",
    "ElectionResultsOverlay",
    "ElectionResultsOverlayResult",
    "ElectionReturn",
]


@dataclass
class ElectionReturn:
    """Election result for a single contest in a single precinct/VTD.

    Attributes:
        precinct_id: Precinct or VTD identifier.
        election_year: Year of the election.
        election_type: general, primary, runoff, special.
        office: Office contested (e.g., US_PRESIDENT, US_HOUSE, GOVERNOR).
        candidate: Candidate name.
        party: Party abbreviation (DEM, REP, LIB, etc.).
        votes: Vote count.
        total_votes: Total votes cast in this contest at this precinct.
        vote_share: Fraction of total votes (0-1).
        state: State abbreviation.
        reconciliation_method: How this precinct was mapped (spatial, name_match, official_crosswalk, or direct).
    """

    precinct_id: str = ""
    election_year: int = 0
    election_type: str = "general"
    office: str = ""
    candidate: str = ""
    party: str = ""
    votes: int = 0
    total_votes: int = 0
    vote_share: float = 0.0
    state: str = ""
    reconciliation_method: str = "direct"


@dataclass
class ElectionResultsOverlayResult:
    """Result of the election results overlay query.

    Attributes:
        geoid: Queried GEOID.
        returns: Election returns ordered by year then office.
        election_years: Distinct years with data.
        offices: Distinct offices with data.
    """

    geoid: str = ""
    returns: list[ElectionReturn] = field(default_factory=list)

    @property
    def election_years(self) -> list[int]:
        return sorted(set(r.election_year for r in self.returns))

    @property
    def offices(self) -> list[str]:
        return sorted(set(r.office for r in self.returns if r.office))

    def for_year(self, year: int) -> list[ElectionReturn]:
        return [r for r in self.returns if r.election_year == year]

    def for_office(self, office: str) -> list[ElectionReturn]:
        return [r for r in self.returns if r.office == office]

    def for_year_office(self, year: int, office: str) -> list[ElectionReturn]:
        return [
            r for r in self.returns
            if r.election_year == year and r.office == office
        ]

    def party_totals(self, year: int, office: str) -> dict[str, int]:
        """Sum votes by party for a specific contest."""
        totals: dict[str, int] = {}
        for r in self.for_year_office(year, office):
            totals[r.party] = totals.get(r.party, 0) + r.votes
        return totals


class ElectionDataProvider(abc.ABC):
    """Protocol for fetching election results for a geography."""

    @abc.abstractmethod
    def get_election_returns(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> list[ElectionReturn]:
        """Get election returns for precincts/VTDs overlapping a geography."""


class DictElectionDataProvider(ElectionDataProvider):
    """In-memory election data provider for testing."""

    def __init__(self):
        self._returns: list[ElectionReturn] = []

    def add(self, ret: ElectionReturn):
        self._returns.append(ret)

    def get_election_returns(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> list[ElectionReturn]:
        results = []
        for r in self._returns:
            if r.election_year < from_year or r.election_year > to_year:
                continue
            if state_fips and r.state.upper() != state_fips.upper():
                continue
            results.append(r)
        return results


class ElectionResultsOverlay(PlaceHistoryOverlay):
    """Place history overlay for precinct-level election results.

    Returns election returns for precincts/VTDs that overlap the
    queried geography, reconciled via precinct-VTD mapping.
    """

    def __init__(self, provider: Optional[ElectionDataProvider] = None):
        self._provider = provider

    @property
    def name(self) -> str:
        return "election_results"

    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> ElectionResultsOverlayResult:
        if self._provider is None:
            log.warning("ElectionResultsOverlay: no provider configured")
            raise RuntimeError("ElectionResultsOverlay requires a provider")

        returns = self._provider.get_election_returns(
            geoid, from_year, to_year, state_fips,
        )
        returns.sort(key=lambda r: (r.election_year, r.office, r.party))

        return ElectionResultsOverlayResult(
            geoid=geoid,
            returns=returns,
        )

    def is_available(self) -> bool:
        return self._provider is not None
