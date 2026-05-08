"""Gazetteers — name → geometry resolution (ELE-2483).

Public API:

* :class:`Gazetteer` — Protocol every backend satisfies.
* :class:`GazetteerResult` — resolved place (name, path, geometry,
  centroid, admin levels).
* :class:`GazetteerCandidate` — search hit (no geometry yet).
* :func:`resolve_gazetteer` — factory that picks the best available
  backend (WKLS by default; falls back to Nominatim, then Census).
* Errors: :class:`GazetteerError`, :class:`GazetteerNotFoundError`,
  :class:`GazetteerAmbiguousError`, :class:`GazetteerBackendError`.

The Etter integration (:func:`etter_to_geometry`) consumes this
interface — see :mod:`siege_utilities.geo.providers.etter_filter`.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import (
    Gazetteer,
    GazetteerAmbiguousError,
    GazetteerBackendError,
    GazetteerCandidate,
    GazetteerError,
    GazetteerNotFoundError,
    GazetteerResult,
)

log = logging.getLogger(__name__)

__all__ = [
    "Gazetteer",
    "GazetteerCandidate",
    "GazetteerResult",
    "GazetteerError",
    "GazetteerNotFoundError",
    "GazetteerAmbiguousError",
    "GazetteerBackendError",
    "resolve_gazetteer",
]


def resolve_gazetteer(
    *,
    prefer: Optional[str] = None,
    cache_size: int = 1024,
) -> Gazetteer:
    """Return a configured :class:`Gazetteer` backend.

    Selection order:

    1. If ``prefer`` is given, use that backend (raises if unavailable).
    2. Otherwise, try WKLS (global coverage, no API key).
    3. Then Nominatim (OSM-backed, public service).
    4. Raise if nothing works.

    Args:
        prefer: ``"wkls"`` / ``"nominatim"`` / ``"census"`` / ``"wikidata"``
            to force a specific backend.
        cache_size: LRU cache size for backends that support it.

    Raises:
        :class:`ImportError` — preferred backend's package isn't installed.
        :class:`RuntimeError` — no usable backend at all.
    """
    if prefer == "wkls":
        from .wkls_gazetteer import WklsGazetteer
        return WklsGazetteer(cache_size=cache_size)
    if prefer == "nominatim":
        from .nominatim_gazetteer import NominatimGazetteer
        return NominatimGazetteer(cache_size=cache_size)
    if prefer in ("census", "wikidata"):
        raise NotImplementedError(
            f"{prefer!r} gazetteer backend is queued for ELE-2483 PR-B2 — "
            "Census uses an address-geocoder + TIGERWeb shape lookup and "
            "Wikidata is SPARQL + OSM relation deref, both worth a focused "
            "PR each. For now use prefer='wkls' (global) or "
            "prefer='nominatim' (OSM)."
        )
    if prefer is not None:
        raise ValueError(
            f"prefer must be one of 'wkls', 'nominatim', 'census', "
            f"'wikidata', got {prefer!r}"
        )

    # Auto-select: try WKLS first (global, no rate limit), then
    # Nominatim (OSM, public, rate-limited). Both modules catch their
    # own ImportError on optional deps and expose an *_AVAILABLE flag.
    from .wkls_gazetteer import WklsGazetteer, WKLS_AVAILABLE
    if WKLS_AVAILABLE:
        return WklsGazetteer(cache_size=cache_size)
    from .nominatim_gazetteer import NominatimGazetteer, GEOPY_AVAILABLE
    if GEOPY_AVAILABLE:
        return NominatimGazetteer(cache_size=cache_size)

    raise RuntimeError(
        "No gazetteer backend available. Install with: "
        "pip install 'siege-utilities[wkls]' (recommended, global) or "
        "pip install 'siege-utilities[geo]' (Nominatim via geopy)."
    )
