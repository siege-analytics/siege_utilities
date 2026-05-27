"""Spatio-temporal place history query API.

Answers "what's the story of this place over time?" by composing
crosswalk chains and overlay data into a unified response.

Usage::

    result = place_history("17031010100", from_year=2000, to_year=2020)
    print(result.lineage)
    print(result.overlays)

The overlay system is extensible — see :mod:`overlay_registry` for
registering custom overlays.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Union

log = logging.getLogger(__name__)

CENSUS_DECADE_YEARS = [1990, 2000, 2010, 2020, 2030]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class LineageStep:
    """A single step in the crosswalk chain.

    Attributes:
        source_geoid: GEOID before transition.
        target_geoid: GEOID after transition.
        source_year: Source vintage year.
        target_year: Target vintage year.
        weight: Allocation weight (1.0 = identical).
        relationship: IDENTICAL, SPLIT, MERGED, PARTIAL, RENAMED.
    """

    source_geoid: str
    target_geoid: str
    source_year: int
    target_year: int
    weight: float = 1.0
    relationship: str = "IDENTICAL"


@dataclass
class Lineage:
    """Complete crosswalk chain for a GEOID across time.

    Attributes:
        origin_geoid: Starting GEOID.
        origin_year: Year of the starting GEOID.
        steps: Ordered list of transitions.
        terminal_geoids: Final GEOID(s) at the end of the chain.
        direction: "forward" or "reverse".
    """

    origin_geoid: str
    origin_year: int
    steps: list[LineageStep] = field(default_factory=list)
    terminal_geoids: list[str] = field(default_factory=list)
    direction: str = "forward"

    @property
    def is_unchanged(self) -> bool:
        return (
            len(self.terminal_geoids) == 1
            and self.terminal_geoids[0] == self.origin_geoid
        )


@dataclass
class PlaceHistoryResult:
    """Unified response for a place history query.

    Attributes:
        geoid: The queried GEOID.
        from_year: Start of the query range.
        to_year: End of the query range.
        lineage: Crosswalk chain showing boundary evolution.
        overlays: Dict of overlay name to overlay data.
        errors: Any errors encountered during the query.
    """

    geoid: str
    from_year: int
    to_year: int
    lineage: Optional[Lineage] = None
    overlays: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def has_lineage(self) -> bool:
        return self.lineage is not None and len(self.lineage.steps) > 0

    @property
    def direction(self) -> str:
        if self.from_year <= self.to_year:
            return "forward"
        return "reverse"


# ---------------------------------------------------------------------------
# Crosswalk data provider protocol
# ---------------------------------------------------------------------------


@dataclass
class CrosswalkRecord:
    """A single crosswalk mapping between two GEOIDs."""

    source_geoid: str
    target_geoid: str
    weight: float = 1.0
    relationship: str = "IDENTICAL"


class CrosswalkProvider(abc.ABC):
    """Protocol for fetching crosswalk data.

    Implementations provide crosswalk records for a given GEOID
    and vintage transition. The Django-backed provider queries
    TemporalCrosswalk; test providers use in-memory data.
    """

    @abc.abstractmethod
    def get_forward_mappings(
        self,
        geoid: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> list[CrosswalkRecord]:
        """Get target GEOIDs for a source GEOID transitioning between vintages."""

    @abc.abstractmethod
    def get_reverse_mappings(
        self,
        geoid: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> list[CrosswalkRecord]:
        """Get source GEOIDs that map to a target GEOID."""


class DictCrosswalkProvider(CrosswalkProvider):
    """In-memory crosswalk provider for testing.

    Data is keyed by (source_year, target_year) → dict of
    source_geoid → list[CrosswalkRecord].
    """

    def __init__(self, data: Optional[dict] = None):
        self._data: dict[tuple[int, int], dict[str, list[CrosswalkRecord]]] = data or {}

    def add(
        self,
        source_year: int,
        target_year: int,
        source_geoid: str,
        target_geoid: str,
        weight: float = 1.0,
        relationship: str = "IDENTICAL",
    ):
        key = (source_year, target_year)
        if key not in self._data:
            self._data[key] = {}
        if source_geoid not in self._data[key]:
            self._data[key][source_geoid] = []
        self._data[key][source_geoid].append(
            CrosswalkRecord(
                source_geoid=source_geoid,
                target_geoid=target_geoid,
                weight=weight,
                relationship=relationship,
            )
        )

    def get_forward_mappings(
        self,
        geoid: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> list[CrosswalkRecord]:
        key = (source_year, target_year)
        return self._data.get(key, {}).get(geoid, [])

    def get_reverse_mappings(
        self,
        geoid: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> list[CrosswalkRecord]:
        key = (source_year, target_year)
        records = []
        for src_geoid, mappings in self._data.get(key, {}).items():
            for rec in mappings:
                if rec.target_geoid == geoid:
                    records.append(rec)
        return records


# ---------------------------------------------------------------------------
# Crosswalk chaining
# ---------------------------------------------------------------------------


def _decade_transitions(from_year: int, to_year: int) -> list[tuple[int, int]]:
    """Determine the decade transitions needed between two years.

    Returns pairs of (source_decade, target_decade) in chronological order.
    For forward queries (from_year < to_year), chains forward.
    For reverse queries (from_year > to_year), chains backward.
    """
    if from_year == to_year:
        return []

    forward = from_year < to_year

    if forward:
        start_decade = max(d for d in CENSUS_DECADE_YEARS if d <= from_year)
        end_decade = max(d for d in CENSUS_DECADE_YEARS if d <= to_year)
    else:
        start_decade = max(d for d in CENSUS_DECADE_YEARS if d <= from_year)
        end_decade = max(d for d in CENSUS_DECADE_YEARS if d <= to_year)

    if start_decade == end_decade:
        return []

    transitions = []
    if forward:
        decades = sorted(d for d in CENSUS_DECADE_YEARS if start_decade <= d <= end_decade)
        for i in range(len(decades) - 1):
            transitions.append((decades[i], decades[i + 1]))
    else:
        decades = sorted(
            (d for d in CENSUS_DECADE_YEARS if end_decade <= d <= start_decade),
            reverse=True,
        )
        for i in range(len(decades) - 1):
            transitions.append((decades[i], decades[i + 1]))

    return transitions


def _build_lineage(
    geoid: str,
    from_year: int,
    to_year: int,
    provider: CrosswalkProvider,
    state_fips: Optional[str] = None,
    min_weight: float = 0.01,
) -> Lineage:
    """Build a crosswalk chain for a GEOID across decades."""
    forward = from_year <= to_year
    transitions = _decade_transitions(from_year, to_year)

    lineage = Lineage(
        origin_geoid=geoid,
        origin_year=from_year,
        direction="forward" if forward else "reverse",
    )

    if not transitions:
        lineage.terminal_geoids = [geoid]
        return lineage

    current = [(geoid, 1.0)]

    for src_year, tgt_year in transitions:
        next_geoids = []

        for cur_geoid, cum_weight in current:
            if forward:
                records = provider.get_forward_mappings(
                    cur_geoid, src_year, tgt_year, state_fips
                )
            else:
                records = provider.get_reverse_mappings(
                    cur_geoid, tgt_year, src_year, state_fips
                )

            if not records:
                next_geoids.append((cur_geoid, cum_weight))
                continue

            for rec in records:
                new_weight = cum_weight * rec.weight
                if new_weight < min_weight:
                    continue

                step = LineageStep(
                    source_geoid=rec.source_geoid if forward else rec.target_geoid,
                    target_geoid=rec.target_geoid if forward else rec.source_geoid,
                    source_year=src_year if forward else tgt_year,
                    target_year=tgt_year if forward else src_year,
                    weight=rec.weight,
                    relationship=rec.relationship,
                )
                lineage.steps.append(step)

                target = rec.target_geoid if forward else rec.source_geoid
                next_geoids.append((target, new_weight))

        current = next_geoids

    lineage.terminal_geoids = [g for g, _ in current]
    return lineage


# ---------------------------------------------------------------------------
# Main query function
# ---------------------------------------------------------------------------


def place_history(
    geoid: str,
    from_year: int,
    to_year: int,
    overlays: Optional[list[str]] = None,
    state_fips: Optional[str] = None,
    provider: Optional[CrosswalkProvider] = None,
    overlay_registry: Optional[Any] = None,
) -> PlaceHistoryResult:
    """Query the history of a geographic place over time.

    Composes crosswalk chains and optional overlays into a unified
    response showing how a place has evolved.

    Args:
        geoid: Census GEOID to query (tract, block group, county, etc.).
        from_year: Start year of the query range.
        to_year: End year of the query range.
        overlays: List of overlay names to include (e.g., ["seats", "demographics"]).
        state_fips: Optional state FIPS code for filtering crosswalks.
        provider: CrosswalkProvider for fetching crosswalk data.
            If None, attempts to use the Django-backed provider.
        overlay_registry: Registry for resolving overlay names to implementations.
            If None, overlays are skipped.

    Returns:
        PlaceHistoryResult with lineage and overlay data.
    """
    result = PlaceHistoryResult(
        geoid=geoid,
        from_year=from_year,
        to_year=to_year,
    )

    if provider is None:
        provider = _get_default_provider()

    if provider is None:
        result.errors.append(
            "No crosswalk provider available (Django not configured?)"
        )
        return result

    try:
        result.lineage = _build_lineage(
            geoid, from_year, to_year, provider, state_fips
        )
    except Exception as exc:
        result.errors.append(f"Lineage build failed: {exc}")
        log.error("Failed to build lineage for %s: %s", geoid, exc)

    if overlays and overlay_registry is not None:
        for name in overlays:
            try:
                overlay_impl = overlay_registry.get(name)
                if overlay_impl is None:
                    result.errors.append(f"Unknown overlay: {name}")
                    continue
                result.overlays[name] = overlay_impl.fetch(
                    geoid, from_year, to_year, state_fips
                )
            except Exception as exc:
                result.errors.append(f"Overlay '{name}' failed: {exc}")
                log.warning("Overlay %s failed for %s: %s", name, geoid, exc)

    return result


def _get_default_provider() -> Optional[CrosswalkProvider]:
    """Attempt to create a Django-backed crosswalk provider."""
    try:
        from siege_utilities.geo.django.providers import DjangoCrosswalkProvider
        return DjangoCrosswalkProvider()
    except Exception:
        return None
