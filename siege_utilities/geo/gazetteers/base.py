"""Gazetteer protocol — name → geometry resolution.

A gazetteer takes a place name (``"Birmingham, AL"``, ``"Lausanne"``,
``"Texas"``) and returns a structured :class:`GazetteerResult` carrying
the canonical hierarchy path, the geometry, and a centroid. Backends
live in sibling modules (:mod:`.wkls_gazetteer`,
:mod:`.nominatim_gazetteer`, etc.) and are selected via the factory in
:mod:`siege_utilities.geo.gazetteers`.

The protocol is **typed-Protocol** rather than an ABC so backends can be
plain classes without inheritance ceremony — useful for adapters
wrapping foreign libraries.

Failure-mode discipline (matches the rest of siege_utilities, see
``docs/FAILURE_MODES.md``): every method raises a typed exception on
failure rather than returning ``None`` or an empty container that
silently looks like a successful empty result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

__all__ = [
    "Gazetteer",
    "GazetteerResult",
    "GazetteerCandidate",
    "GazetteerError",
    "GazetteerNotFoundError",
    "GazetteerAmbiguousError",
    "GazetteerBackendError",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GazetteerError(RuntimeError):
    """Base class for all gazetteer failures."""


class GazetteerNotFoundError(GazetteerError):
    """No place matched the lookup criteria."""


class GazetteerAmbiguousError(GazetteerError):
    """The query is ambiguous and the caller didn't pass enough hints.

    Carries the candidates so the caller can surface them to a user or
    pick programmatically.
    """

    def __init__(self, message: str, candidates: list["GazetteerCandidate"]):
        super().__init__(message)
        self.candidates = candidates


class GazetteerBackendError(GazetteerError):
    """The backend raised an error we couldn't translate.

    Network failure, malformed upstream response, missing optional
    dependency at lookup time. Always chains the original via
    ``__cause__``.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GazetteerCandidate:
    """A search hit — a place that *might* be the answer.

    Search returns multiple of these; lookup picks one. Keep the
    structure small and JSON-safe so it round-trips through APIs and
    logs cleanly.
    """

    name: str
    canonical_path: tuple[str, ...]
    country: Optional[str] = None
    admin_levels: Mapping[str, str] = field(default_factory=dict)
    score: Optional[float] = None
    source: str = ""


@dataclass(frozen=True)
class GazetteerResult:
    """A resolved place: name, hierarchy, geometry, centroid.

    Attributes:
        name: Display name of the matched place.
        canonical_path: Hierarchical breadcrumb the source resolves the
            place through, e.g. ``("US", "AL", "Birmingham")``. Useful
            for downstream filtering and for re-querying the same
            backend without going through fuzzy search again.
        geometry: shapely shape (Polygon / MultiPolygon for admin areas;
            may be a Point for cities-as-points).
        centroid: shapely Point. Pre-computed because half the consumer
            code needs it and recomputing on every call is wasteful.
        country: Optional ISO-3166-1 alpha-2 country code.
        admin_levels: Optional mapping of admin level name → value
            (e.g. ``{"region": "Alabama", "county": "Jefferson"}``).
            Backend-specific; not assumed by the resolver layer.
        source: Backend name (``"wkls"``, ``"nominatim"``, etc.) — for
            audit / log lineage.
        raw: Backend-native object for callers that need full fidelity.
            Excluded from ``repr`` and ``hash`` so the dataclass stays
            sane to print and stable as a cache key.
    """

    name: str
    canonical_path: tuple[str, ...]
    geometry: Any  # shapely geometry; typed loose to avoid module-level shapely import
    centroid: Any
    country: Optional[str] = None
    admin_levels: Mapping[str, str] = field(default_factory=dict)
    source: str = ""
    raw: Any = field(default=None, repr=False, compare=False)

    # Mutable mapping in metadata means the dataclass is not safely
    # hashable; mark it explicitly so callers can't smuggle one of these
    # into a dict key and get burned later.
    __hash__ = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class Gazetteer(Protocol):
    """Name → geometry resolver.

    The protocol is intentionally narrow — four methods. Backends layer
    LRU caches, ISO-code translation, and other plumbing internally;
    callers just see this surface.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable backend identifier (``"wkls"``, etc.)."""
        ...

    def lookup(
        self,
        name: str,
        *,
        country_hint: Optional[str] = None,
        admin_hint: Optional[str] = None,
    ) -> GazetteerResult:
        """Best match for *name*.

        Args:
            name: Place name in human form (``"Birmingham, AL"``).
            country_hint: Optional ISO-3166-1 alpha-2 (``"US"``) or
                alpha-3 (``"USA"``) hint to disambiguate places that
                exist in multiple countries.
            admin_hint: Optional region/state hint (``"Alabama"``,
                ``"AL"``, ``"01"``).

        Raises:
            GazetteerNotFoundError: No match.
            GazetteerAmbiguousError: Multiple matches; caller should
                pass more hints or use :meth:`search` and pick.
            GazetteerBackendError: Network / dependency / parse failure.
        """
        ...

    def search(
        self,
        name: str,
        *,
        country_hint: Optional[str] = None,
        limit: int = 10,
    ) -> list[GazetteerCandidate]:
        """Top-N candidate matches.

        Used to surface ambiguity to a caller (interactive UI, or
        programmatic disambiguation when the caller has external
        knowledge to pick a candidate).
        """
        ...

    def is_available(self) -> bool:
        """Return True if the backend's dependencies are installed and
        the backend can answer queries.

        Should NOT make a network round-trip — this is a fast probe used
        by the factory to pick a default backend.
        """
        ...
