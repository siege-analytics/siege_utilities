"""Census Geocoder + TIGERWeb gazetteer.

US-only. Two upstreams chained:

1. Census Geocoder's ``onelineaddress``-style endpoint accepts a place
   name and returns matching geographies with FIPS codes (state +
   county + place + tract).
2. TIGERWeb ArcGIS REST returns the polygon for a given (layer, FIPS)
   pair.

The split exists because Census Geocoder is address-centric and only
returns coords + FIPS for a place. The polygon comes from TIGER. We
hand back a unified :class:`GazetteerResult` with shapely geometry,
hiding the two-call shape from callers.

Useful when the consumer already has a FIPS lookup pipeline downstream
(electoral / NCES / Decennial workflows) and would prefer to skip the
WKLS / Nominatim translation step.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Mapping, Optional
from urllib.parse import urlencode

from .base import (
    GazetteerAmbiguousError,
    GazetteerBackendError,
    GazetteerCandidate,
    GazetteerNotFoundError,
    GazetteerResult,
)

log = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover - requests is a core dep
    REQUESTS_AVAILABLE = False

try:
    import shapely.geometry  # noqa: F401
    SHAPELY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SHAPELY_AVAILABLE = False

__all__ = ["CensusGazetteer", "REQUESTS_AVAILABLE", "SHAPELY_AVAILABLE"]


_GEOCODER_BASE = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
_TIGERWEB_BASE = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "State_County/MapServer"
)
_DEFAULT_BENCHMARK = "Public_AR_Current"
_DEFAULT_VINTAGE = "Current_Current"
_DEFAULT_TIMEOUT = 15.0

# Map common-name admin layers in TIGERWeb. Layer IDs are stable in the
# State_County MapServer; if Census ever renumbers we'll see test
# failures, not silent geometry corruption.
_LAYER_STATE = 0
_LAYER_COUNTY = 1


class CensusGazetteer:
    """US Census-backed gazetteer with admin polygons from TIGER.

    Args:
        timeout: Per-request HTTP timeout (seconds).
        cache_size: LRU cache size for the (name, hints) key.
        benchmark / vintage: Census Geocoder benchmark/vintage strings.
            Defaults pin to "current"; consumers stuck to a fixed
            vintage (e.g. for reproducibility against a published
            decennial roll) can override.
    """

    provider_name = "census"

    def __init__(
        self,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        cache_size: int = 1024,
        benchmark: str = _DEFAULT_BENCHMARK,
        vintage: str = _DEFAULT_VINTAGE,
    ) -> None:
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "CensusGazetteer requires requests. It ships as a core "
                "dependency; if it's missing the install is broken."
            )
        if not SHAPELY_AVAILABLE:
            raise ImportError(
                "CensusGazetteer requires shapely to parse TIGER polygons. "
                "Install with: pip install 'siege-utilities[geo]'."
            )
        self._timeout = timeout
        self._benchmark = benchmark
        self._vintage = vintage
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "siege-utilities-gazetteer",
        })
        self._cached_lookup = functools.lru_cache(maxsize=cache_size)(
            self._uncached_lookup
        )

    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE and SHAPELY_AVAILABLE

    # ------------------------------------------------------------------
    # Gazetteer protocol
    # ------------------------------------------------------------------

    def lookup(
        self,
        name: str,
        *,
        country_hint: Optional[str] = None,
        admin_hint: Optional[str] = None,
    ) -> GazetteerResult:
        if not name or not name.strip():
            raise ValueError("CensusGazetteer.lookup: empty name")
        if country_hint and country_hint.upper() not in ("US", "USA"):
            raise GazetteerNotFoundError(
                f"CensusGazetteer is US-only; country_hint={country_hint!r}"
            )
        rows = self._cached_lookup(name.strip(), (admin_hint or "").strip() or None)
        if not rows:
            raise GazetteerNotFoundError(
                f"Census: no match for {name!r}"
                + (f" (admin_hint={admin_hint!r})" if admin_hint else "")
            )
        if len(rows) > 1:
            raise GazetteerAmbiguousError(
                f"Census: {len(rows)} matches for {name!r}; "
                "pass admin_hint or use search() and pick a candidate.",
                candidates=[self._row_to_candidate(r) for r in rows],
            )
        return self._row_to_result(rows[0])

    def search(
        self,
        name: str,
        *,
        country_hint: Optional[str] = None,
        limit: int = 10,
    ) -> list[GazetteerCandidate]:
        if limit < 0:
            raise ValueError(f"CensusGazetteer.search: limit must be >= 0, got {limit}")
        if not name or not name.strip():
            return []
        if country_hint and country_hint.upper() not in ("US", "USA"):
            return []
        rows = self._cached_lookup(name.strip(), None)
        return [self._row_to_candidate(r) for r in rows[:limit]]

    # ------------------------------------------------------------------
    # Internal: HTTP + translation
    # ------------------------------------------------------------------

    def _uncached_lookup(
        self,
        name: str,
        admin_hint: Optional[str],
    ) -> tuple[Mapping[str, Any], ...]:
        query = name if not admin_hint else f"{name}, {admin_hint}"
        params = {
            "address": query,
            "benchmark": self._benchmark,
            "vintage": self._vintage,
            "format": "json",
        }
        url = f"{_GEOCODER_BASE}?{urlencode(params)}"
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            raise GazetteerBackendError(
                f"Census geocoder request for {name!r} failed: {exc}"
            ) from exc
        if resp.status_code != 200:
            raise GazetteerBackendError(
                f"Census geocoder returned {resp.status_code} for "
                f"{name!r}: {resp.text[:200]}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise GazetteerBackendError(
                f"Census geocoder returned non-JSON for {name!r}"
            ) from exc
        # `data.get("result", {})` only substitutes {} when the key is
        # absent. The Census API also returns {"result": null, ...} on
        # certain error envelopes; the `or {}` guard handles both.
        result = data.get("result") or {}
        matches = result.get("addressMatches") or []
        # Each match has a `geographies` dict keyed by layer name.
        # Counties is the canonical admin level we resolve here; consumers
        # who want state / tract can read raw.geographies themselves.
        rows = []
        for m in matches:
            geos = m.get("geographies", {}) or {}
            counties = geos.get("Counties", []) or []
            states = geos.get("States", []) or []
            if not counties and not states:
                continue
            target = counties[0] if counties else states[0]
            layer = _LAYER_COUNTY if counties else _LAYER_STATE
            # Coordinates missing -> skip rather than silently emit
            # (0.0, 0.0). A real match always carries x/y; the only way
            # to get the fallback was an upstream malformed response,
            # which should not produce a result at Null Island.
            coords = m.get("coordinates") or {}
            lat_raw = coords.get("y")
            lon_raw = coords.get("x")
            if lat_raw is None or lon_raw is None:
                continue
            rows.append({
                "name": target.get("BASENAME") or target.get("NAME") or name,
                "state_fips": target.get("STATE"),
                "county_fips": target.get("COUNTY") if counties else None,
                "lat": float(lat_raw),
                "lon": float(lon_raw),
                "_layer": layer,
                "_geoid": target.get("GEOID"),
                "raw": m,
            })
        # Census Geocoder returns one addressMatch per matching street
        # range, but many ranges collapse to the same county or state
        # GEOID. Without dedup, two addressMatches for the same county
        # produce two rows and `lookup` raises GazetteerAmbiguousError
        # for a single effective admin polygon. Collapse by (_layer,
        # _geoid) keeping the first occurrence.
        seen: set = set()
        deduped: list = []
        for row in rows:
            key = (row["_layer"], row["_geoid"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return tuple(deduped)

    def _fetch_polygon(self, layer: int, geoid: str) -> Any:
        """Fetch the polygon for a (layer, GEOID) pair from TIGERWeb."""
        from shapely.geometry import shape as shapely_shape

        params = {
            "where": f"GEOID='{geoid}'",
            "outFields": "GEOID,NAME",
            "f": "geojson",
            "returnGeometry": "true",
        }
        url = f"{_TIGERWEB_BASE}/{layer}/query?{urlencode(params)}"
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            raise GazetteerBackendError(
                f"TIGERWeb request for GEOID={geoid!r} failed: {exc}"
            ) from exc
        if resp.status_code != 200:
            raise GazetteerBackendError(
                f"TIGERWeb returned {resp.status_code} for GEOID={geoid!r}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise GazetteerBackendError(
                f"TIGERWeb returned non-JSON for GEOID={geoid!r}"
            ) from exc
        features = data.get("features") or []
        if not features:
            raise GazetteerBackendError(
                f"TIGERWeb returned no feature for GEOID={geoid!r}"
            )
        return shapely_shape(features[0]["geometry"])

    def _row_to_candidate(self, row: Mapping[str, Any]) -> GazetteerCandidate:
        admin: dict[str, str] = {}
        if row.get("state_fips"):
            admin["state_fips"] = str(row["state_fips"])
        if row.get("county_fips"):
            admin["county_fips"] = str(row["county_fips"])
        path: tuple[str, ...] = ("US",)
        if row.get("state_fips"):
            path = path + (str(row["state_fips"]),)
        if row.get("name"):
            path = path + (str(row["name"]),)
        return GazetteerCandidate(
            name=str(row.get("name", "")),
            canonical_path=path,
            country="US",
            admin_levels=admin,
            source=self.provider_name,
        )

    def _row_to_result(self, row: Mapping[str, Any]) -> GazetteerResult:
        from shapely.geometry import Point

        geoid = row.get("_geoid")
        if geoid:
            geometry = self._fetch_polygon(int(row["_layer"]), str(geoid))
            centroid = geometry.centroid
        else:
            geometry = Point(row["lon"], row["lat"])
            centroid = geometry
        admin: dict[str, str] = {}
        if row.get("state_fips"):
            admin["state_fips"] = str(row["state_fips"])
        if row.get("county_fips"):
            admin["county_fips"] = str(row["county_fips"])
        path: tuple[str, ...] = ("US",)
        if row.get("state_fips"):
            path = path + (str(row["state_fips"]),)
        if row.get("name"):
            path = path + (str(row["name"]),)
        return GazetteerResult(
            name=str(row.get("name", "")),
            canonical_path=path,
            geometry=geometry,
            centroid=centroid,
            country="US",
            admin_levels=admin,
            source=self.provider_name,
            raw=row.get("raw"),
        )
