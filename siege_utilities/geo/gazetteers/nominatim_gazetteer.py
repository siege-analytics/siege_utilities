"""Nominatim (OSM) gazetteer backend.

Wraps the public OpenStreetMap Nominatim service via :mod:`geopy`. We
ask for ``polygon_geojson=1`` so the response carries admin polygons,
not just point centroids — that's what makes this useful as a
:class:`Gazetteer`.

Operational notes:

* Public Nominatim has a 1 req/s rate limit and a Usage Policy that
  *requires* a meaningful ``user_agent``. We pass one through
  configuration; callers running at scale should self-host.
* ``server_url`` lets you point at a self-hosted Nominatim — when set,
  rate-limiting is dropped to a tiny delay.
* In-process LRU cache wraps the per-name resolution. Nominatim does
  cache server-side, but the round-trip is hundreds of ms; in-process
  caching matters for interactive use.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Optional

from .base import (
    GazetteerAmbiguousError,
    GazetteerBackendError,
    GazetteerCandidate,
    GazetteerNotFoundError,
    GazetteerResult,
)

log = logging.getLogger(__name__)

try:
    from geopy.geocoders import Nominatim  # type: ignore[import-not-found]
    from geopy.exc import GeocoderServiceError, GeocoderTimedOut  # type: ignore[import-not-found]
    GEOPY_AVAILABLE = True
except ImportError:
    Nominatim = None  # type: ignore[assignment, misc]
    GeocoderServiceError = Exception  # type: ignore[assignment, misc]
    GeocoderTimedOut = Exception  # type: ignore[assignment, misc]
    GEOPY_AVAILABLE = False
    log.info("geopy not available — NominatimGazetteer will raise on construct")


__all__ = [
    "GEOPY_AVAILABLE",
    "NominatimGazetteer",
]


# Public Nominatim's Usage Policy: max 1 req/s, identifying user-agent.
_PUBLIC_RATE_LIMIT_S = 1.0
_SELFHOSTED_RATE_LIMIT_S = 0.05
_DEFAULT_USER_AGENT = "siege-utilities-gazetteer (https://github.com/siege-analytics/siege_utilities)"


class NominatimGazetteer:
    """OpenStreetMap-backed gazetteer with polygon geometry.

    Args:
        user_agent: Required per OSM Usage Policy. Override the default
            for any production deployment so OSM ops can reach you.
        server_url: ``None`` for the public Nominatim (rate-limited at
            1 req/s); otherwise a self-hosted Nominatim base URL.
        timeout: Per-request timeout in seconds.
        cache_size: LRU cache size for the (name, country, admin) key.
    """

    provider_name = "nominatim"

    def __init__(
        self,
        *,
        user_agent: str = _DEFAULT_USER_AGENT,
        server_url: Optional[str] = None,
        timeout: float = 10.0,
        cache_size: int = 1024,
    ) -> None:
        if not GEOPY_AVAILABLE:
            raise ImportError(
                "NominatimGazetteer requires geopy. Install with: "
                "pip install 'siege-utilities[geo]' or pip install 'geopy>=2.0'."
            )
        self._user_agent = user_agent
        self._server_url = server_url
        self._timeout = timeout
        self._rate_limit = _SELFHOSTED_RATE_LIMIT_S if server_url else _PUBLIC_RATE_LIMIT_S
        self._client = self._build_client()
        # Per-instance cache keyed on the lookup tuple so different hint
        # combinations don't collide.
        self._cached_lookup = functools.lru_cache(maxsize=cache_size)(
            self._uncached_lookup
        )

    def _build_client(self) -> Any:
        kwargs: dict[str, Any] = {
            "user_agent": self._user_agent,
            "timeout": self._timeout,
        }
        if self._server_url:
            domain = (
                self._server_url
                .replace("http://", "")
                .replace("https://", "")
                .rstrip("/")
            )
            kwargs["domain"] = domain
            kwargs["scheme"] = (
                "https" if self._server_url.startswith("https") else "http"
            )
        return Nominatim(**kwargs)

    def is_available(self) -> bool:
        return GEOPY_AVAILABLE

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
            raise ValueError("NominatimGazetteer.lookup: empty name")
        results = self._cached_lookup(
            name.strip(),
            (country_hint or "").strip().lower() or None,
            (admin_hint or "").strip().lower() or None,
            10,
        )
        if not results:
            raise GazetteerNotFoundError(
                f"Nominatim: no match for {name!r}"
                + (f" (country={country_hint!r})" if country_hint else "")
            )
        if len(results) > 1:
            hint_note = ""
            if country_hint or admin_hint:
                hint_note = (
                    f" (after country_hint={country_hint!r}, "
                    f"admin_hint={admin_hint!r})"
                )
            raise GazetteerAmbiguousError(
                f"Nominatim: {len(results)} matches for {name!r}{hint_note}; "
                "pass tighter hints, or use search() and pick a candidate.",
                candidates=[self._raw_to_candidate(r) for r in results],
            )
        return self._raw_to_result(results[0])

    def search(
        self,
        name: str,
        *,
        country_hint: Optional[str] = None,
        limit: int = 10,
    ) -> list[GazetteerCandidate]:
        if not name or not name.strip():
            return []
        results = self._cached_lookup(
            name.strip(),
            (country_hint or "").strip().lower() or None,
            None,
            limit,
        )
        return [self._raw_to_candidate(r) for r in results]

    # ------------------------------------------------------------------
    # Internal: query + translation
    # ------------------------------------------------------------------

    def _uncached_lookup(
        self,
        name: str,
        country_code: Optional[str],
        admin_hint: Optional[str],
        limit: int,
    ) -> tuple[dict[str, Any], ...]:
        """Hit Nominatim and return raw rows.

        Returned as a tuple-of-frozen-dicts substitute (regular dicts in
        a tuple) so the result is hashable for ``lru_cache``. Rows
        themselves don't need hashing — only the *return value* of the
        cached function does — so a tuple wrapper is enough.
        """
        # Build the query — admin_hint goes inline rather than via a
        # structured query because Nominatim's free-form parser handles
        # "Birmingham, Alabama" cleanly and structured queries don't
        # accept polygon_geojson uniformly across versions.
        query = name if not admin_hint else f"{name}, {admin_hint}"
        kwargs: dict[str, Any] = {
            "exactly_one": False,
            "limit": limit,
            "addressdetails": True,
            "extratags": False,
            # The whole point of using Nominatim as a gazetteer:
            "geometry": "geojson",
        }
        if country_code:
            # geopy accepts 2-letter country codes; map ISO-3 down.
            cc = country_code.lower()
            if len(cc) == 3:
                cc = _ISO3_TO_ISO2.get(cc.upper(), cc)
            kwargs["country_codes"] = cc

        try:
            time.sleep(self._rate_limit)
            results = self._client.geocode(query, **kwargs)
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            raise GazetteerBackendError(
                f"Nominatim request for {name!r} failed: {exc}"
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise GazetteerBackendError(
                f"Nominatim request for {name!r} raised {type(exc).__name__}: {exc}"
            ) from exc

        if not results:
            return ()
        # geopy returns Location objects or a single Location; normalise.
        if not isinstance(results, (list, tuple)):
            results = [results]
        rows = tuple(self._location_to_row(loc) for loc in results)
        return rows

    @staticmethod
    def _location_to_row(loc: Any) -> dict[str, Any]:
        """Pull the fields we care about off a geopy Location."""
        raw = dict(getattr(loc, "raw", {}) or {})
        return {
            "display_name": raw.get("display_name") or getattr(loc, "address", ""),
            "lat": float(getattr(loc, "latitude", 0.0)),
            "lon": float(getattr(loc, "longitude", 0.0)),
            "place_rank": raw.get("place_rank"),
            "address": raw.get("address") or {},
            "geojson": raw.get("geojson"),
            "osm_type": raw.get("osm_type"),
            "osm_id": raw.get("osm_id"),
            "type": raw.get("type"),
        }

    def _raw_to_candidate(self, row: dict[str, Any]) -> GazetteerCandidate:
        addr = row.get("address") or {}
        country = addr.get("country_code")
        return GazetteerCandidate(
            name=_short_name_from_address(row),
            canonical_path=_canonical_path(row),
            country=country.upper() if country else None,
            admin_levels=_admin_levels(addr),
            score=None,
            source=self.provider_name,
        )

    def _raw_to_result(self, row: dict[str, Any]) -> GazetteerResult:
        addr = row.get("address") or {}
        country = addr.get("country_code")
        geometry = _geometry_from_row(row)
        try:
            centroid = geometry.centroid
        except Exception as exc:  # pragma: no cover - shapely failure
            raise GazetteerBackendError(
                f"Nominatim: cannot compute centroid for {row.get('display_name')!r}: {exc}"
            ) from exc
        return GazetteerResult(
            name=_short_name_from_address(row),
            canonical_path=_canonical_path(row),
            geometry=geometry,
            centroid=centroid,
            country=country.upper() if country else None,
            admin_levels=_admin_levels(addr),
            source=self.provider_name,
            raw=row,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _geometry_from_row(row: dict[str, Any]) -> Any:
    """Convert Nominatim's GeoJSON to a shapely shape; fall back to point.

    If ``polygon_geojson`` came back, parse it; otherwise synthesize a
    point from lat/lon so callers always get *some* geometry.
    """
    try:
        from shapely.geometry import Point, shape
    except ImportError as exc:
        raise GazetteerBackendError(
            "shapely required to convert Nominatim GeoJSON to geometry"
        ) from exc
    geojson = row.get("geojson")
    if geojson:
        try:
            return shape(geojson)
        except (TypeError, ValueError, KeyError) as exc:
            log.warning(
                "Nominatim row %r had unparseable geojson: %s",
                row.get("display_name"), exc,
            )
    return Point(row.get("lon", 0.0), row.get("lat", 0.0))


def _short_name_from_address(row: dict[str, Any]) -> str:
    """Pick a reasonable short name from the row.

    Nominatim's ``display_name`` is the comma-separated full path
    (``"Birmingham, Jefferson County, Alabama, United States"``). For
    most consumers a short label is more useful — prefer the first
    address component that matches the entity type.
    """
    addr = row.get("address") or {}
    type_key = row.get("type")
    if type_key and addr.get(type_key):
        return str(addr[type_key])
    for k in ("city", "town", "village", "hamlet", "county", "state", "country"):
        if addr.get(k):
            return str(addr[k])
    return str(row.get("display_name", "")).split(",", 1)[0].strip()


def _canonical_path(row: dict[str, Any]) -> tuple[str, ...]:
    """Build a (country, state, county, locality) breadcrumb."""
    addr = row.get("address") or {}
    parts: list[str] = []
    cc = addr.get("country_code")
    if cc:
        parts.append(cc.upper())
    for k in ("state", "county", "city", "town", "village", "hamlet"):
        if addr.get(k) and addr[k] not in parts:
            parts.append(str(addr[k]))
    name = _short_name_from_address(row)
    if name and name not in parts:
        parts.append(name)
    return tuple(parts)


def _admin_levels(address: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for src, dst in (
        ("country_code", "country"),
        ("state", "state"),
        ("county", "county"),
        ("city", "city"),
        ("town", "town"),
        ("village", "village"),
    ):
        if address.get(src):
            out[dst] = str(address[src])
    return out


# Reused from wkls_gazetteer's table; small enough to copy rather than
# carrying a cross-module import.
_ISO3_TO_ISO2 = {
    "USA": "US", "GBR": "GB", "DEU": "DE", "FRA": "FR", "CAN": "CA",
    "MEX": "MX", "ESP": "ES", "ITA": "IT", "JPN": "JP", "CHN": "CN",
    "IND": "IN", "BRA": "BR", "AUS": "AU", "NZL": "NZ", "ZAF": "ZA",
    "RUS": "RU", "TUR": "TR", "EGY": "EG", "ARG": "AR", "CHL": "CL",
    "COL": "CO", "PER": "PE", "VEN": "VE", "NLD": "NL", "BEL": "BE",
    "CHE": "CH", "AUT": "AT", "SWE": "SE", "NOR": "NO", "DNK": "DK",
    "FIN": "FI", "POL": "PL", "PRT": "PT", "IRL": "IE", "ISR": "IL",
    "SAU": "SA", "ARE": "AE", "KOR": "KR", "IDN": "ID", "PHL": "PH",
    "VNM": "VN", "THA": "TH", "MYS": "MY", "SGP": "SG", "NGA": "NG",
    "KEN": "KE", "ETH": "ET", "GHA": "GH",
}
