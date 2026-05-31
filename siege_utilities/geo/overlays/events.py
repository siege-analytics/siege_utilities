"""Events overlay for place history.

SpatioTemporalEvents intersecting the queried geography and time range.
Events include court rulings, natural disasters, redistricting actions,
and other discrete occurrences with both spatial and temporal extent.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class EventRecord:
    """A single spatio-temporal event.

    Attributes:
        event_id: Unique identifier.
        event_type: Category (e.g., "court_ruling", "natural_disaster",
            "redistricting", "election", "policy_change").
        title: Short description.
        description: Longer description.
        date: Event date.
        end_date: End date for events with duration.
        geoids_affected: GEOIDs intersecting this event's geography.
        source: Data source or citation.
        metadata: Additional event-specific data.
    """

    event_id: str = ""
    event_type: str = ""
    title: str = ""
    description: str = ""
    date: Optional[date] = None
    end_date: Optional[date] = None
    geoids_affected: list[str] = field(default_factory=list)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def year(self) -> int:
        return self.date.year if self.date else 0

    @property
    def has_duration(self) -> bool:
        return self.end_date is not None and self.date is not None


@dataclass
class EventsOverlayResult:
    """Result of the events overlay query.

    Attributes:
        geoid: Queried GEOID.
        events: Events intersecting the geography and time range.
    """

    geoid: str = ""
    events: list[EventRecord] = field(default_factory=list)

    @property
    def has_events(self) -> bool:
        return len(self.events) > 0

    @property
    def event_types(self) -> list[str]:
        return sorted(set(e.event_type for e in self.events if e.event_type))

    def for_type(self, event_type: str) -> list[EventRecord]:
        return [e for e in self.events if e.event_type == event_type]

    @property
    def count(self) -> int:
        return len(self.events)


# ---------------------------------------------------------------------------
# Data provider protocol
# ---------------------------------------------------------------------------


class EventsDataProvider(abc.ABC):
    """Protocol for fetching spatio-temporal event data."""

    @abc.abstractmethod
    def get_events(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        event_types: Optional[list[str]] = None,
    ) -> list[EventRecord]:
        """Get events intersecting a GEOID within a time range."""


class DictEventsProvider(EventsDataProvider):
    """In-memory events provider for testing."""

    def __init__(self):
        self._events: list[EventRecord] = []

    def add(self, event: EventRecord):
        self._events.append(event)

    def get_events(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        event_types: Optional[list[str]] = None,
    ) -> list[EventRecord]:
        lo = min(from_year, to_year)
        hi = max(from_year, to_year)
        results = []
        for e in self._events:
            if geoid not in e.geoids_affected:
                continue
            if e.year < lo or e.year > hi:
                continue
            if event_types and e.event_type not in event_types:
                continue
            results.append(e)
        return sorted(results, key=lambda e: (e.date or date.min))


# ---------------------------------------------------------------------------
# Overlay implementation
# ---------------------------------------------------------------------------


class EventsOverlay(PlaceHistoryOverlay):
    """Place history overlay for spatio-temporal events.

    Finds events that intersect the queried geography and time range.

    Args:
        provider: EventsDataProvider for fetching events.
        event_types: Optional filter for specific event types.
    """

    def __init__(
        self,
        provider: Optional[EventsDataProvider] = None,
        event_types: Optional[list[str]] = None,
    ):
        self._provider = provider
        self._event_types = event_types

    @property
    def name(self) -> str:
        return "events"

    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> EventsOverlayResult:
        provider = self._provider or self._get_default_provider()
        if provider is None:
            raise RuntimeError("No events data provider available")

        events = provider.get_events(
            geoid, from_year, to_year, self._event_types
        )
        return EventsOverlayResult(geoid=geoid, events=events)

    def _get_default_provider(self) -> Optional[EventsDataProvider]:
        try:
            from siege_utilities.geo.django.providers import DjangoEventsProvider
            return DjangoEventsProvider()
        except ImportError:
            log.debug("Django events provider not available (Django not installed or not configured)")
            return None
