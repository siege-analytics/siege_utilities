"""Extensible overlay registry for place history queries.

Overlays add contextual data layers (seats, demographics, urbanicity,
events) to :func:`place_history` results. New overlays plug in via
the decorator-based registry without changing core query logic.

Usage::

    from siege_utilities.geo.overlay_registry import (
        PlaceHistoryOverlay,
        overlay_registry,
    )

    @overlay_registry.register("my_overlay")
    class MyOverlay(PlaceHistoryOverlay):
        def fetch(self, geoid, from_year, to_year, state_fips=None):
            return {"data": "..."}
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

__all__ = [
    "OverlayRegistry",
    "PlaceHistoryOverlay",
    "overlay_registry",
]


class PlaceHistoryOverlay(abc.ABC):
    """Base class for place history overlays.

    Subclasses implement :meth:`fetch` to retrieve overlay-specific data
    for a queried GEOID and time range.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short identifier for this overlay (e.g., 'seats', 'demographics')."""

    @abc.abstractmethod
    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> Any:
        """Fetch overlay data for a place and time range.

        Args:
            geoid: Census GEOID to query.
            from_year: Start year.
            to_year: End year.
            state_fips: Optional state FIPS for filtering.

        Returns:
            Overlay-specific data (dict, list, dataclass, etc.).
        """

    def is_available(self) -> bool:
        """Check if this overlay's data source is accessible."""
        return True


class OverlayRegistry:
    """Registry for place history overlays.

    Supports both decorator-based and imperative registration.

    Decorator usage::

        @overlay_registry.register("seats")
        class SeatsOverlay(PlaceHistoryOverlay):
            ...

    Imperative usage::

        overlay_registry.register_instance("seats", SeatsOverlay())
    """

    def __init__(self):
        self._overlays: dict[str, PlaceHistoryOverlay] = {}
        self._classes: dict[str, type] = {}

    def register(self, name: str):
        """Decorator to register an overlay class.

        The class is instantiated on first use (lazy).

        Args:
            name: Overlay identifier used in place_history(overlays=[...]).

        Returns:
            Decorator that registers the class.
        """
        def decorator(cls):
            if not issubclass(cls, PlaceHistoryOverlay):
                raise TypeError(
                    f"{cls.__name__} must subclass PlaceHistoryOverlay"
                )
            self._classes[name] = cls
            return cls
        return decorator

    def register_instance(self, name: str, instance: PlaceHistoryOverlay):
        """Register a pre-instantiated overlay.

        Args:
            name: Overlay identifier.
            instance: PlaceHistoryOverlay instance.
        """
        if not isinstance(instance, PlaceHistoryOverlay):
            raise TypeError(
                f"{type(instance).__name__} must be a PlaceHistoryOverlay"
            )
        self._overlays[name] = instance

    def get(self, name: str) -> Optional[PlaceHistoryOverlay]:
        """Look up an overlay by name.

        Lazily instantiates class-registered overlays on first access.

        Args:
            name: Overlay identifier.

        Returns:
            PlaceHistoryOverlay instance, or None if not registered.

        Raises:
            Exception: If the registered overlay class fails to instantiate.
        """
        if name in self._overlays:
            return self._overlays[name]

        if name in self._classes:
            instance = self._classes[name]()
            self._overlays[name] = instance
            return instance

        return None

    def list_overlays(self) -> list[str]:
        """Return names of all registered overlays."""
        return sorted(set(self._overlays.keys()) | set(self._classes.keys()))

    def is_registered(self, name: str) -> bool:
        """Check if an overlay name is registered."""
        return name in self._overlays or name in self._classes

    def unregister(self, name: str) -> bool:
        """Remove an overlay registration.

        Args:
            name: Overlay identifier.

        Returns:
            True if the overlay was found and removed.
        """
        removed = False
        if name in self._overlays:
            del self._overlays[name]
            removed = True
        if name in self._classes:
            del self._classes[name]
            removed = True
        return removed

    def clear(self):
        """Remove all registrations."""
        self._overlays.clear()
        self._classes.clear()


overlay_registry = OverlayRegistry()
