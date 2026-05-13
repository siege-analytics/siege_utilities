"""Wikidata + OSM gazetteer.

Two-step lookup:

1. SPARQL query against Wikidata Query Service for an entity matching
   the place name. Pull ``wdt:P402`` (OSM relation ID) and
   ``wdt:P625`` (coordinate location) for each candidate.
2. Deref the OSM relation ID against the Overpass API to get the
   admin polygon.

Useful for non-administrative places that WKLS / Nominatim's admin
boundary indexes miss: cultural regions, historical entities,
informal areas. The fallback path (when P402 is absent) returns the
P625 point with no polygon.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Mapping, Optional

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
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

__all__ = ["WikidataGazetteer", "REQUESTS_AVAILABLE"]


_WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_DEFAULT_TIMEOUT = 30.0
_USER_AGENT = "siege-utilities-gazetteer (https://github.com/siege-analytics/siege_utilities)"


# Find entities matching `?name` (English label, exact or alias), pull
# the OSM relation ID and coordinate location if either exists.
_SPARQL_TEMPLATE = """
SELECT ?item ?itemLabel ?countryLabel ?osmRel ?coord WHERE {
  ?item rdfs:label|skos:altLabel "%s"@en .
  OPTIONAL { ?item wdt:P17 ?country . }
  OPTIONAL { ?item wdt:P402 ?osmRel . }
  OPTIONAL { ?item wdt:P625 ?coord . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT %d
"""


class WikidataGazetteer:
    """Wikidata SPARQL + OSM Overpass gazetteer.

    Args:
        timeout: Per-request HTTP timeout.
        cache_size: LRU cache for the (name, country) key.
        sparql_url / overpass_url: Override for self-hosted instances.
    """

    provider_name = "wikidata"

    def __init__(
        self,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        cache_size: int = 1024,
        sparql_url: str = _WIKIDATA_SPARQL_URL,
        overpass_url: str = _OVERPASS_URL,
    ) -> None:
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "WikidataGazetteer requires requests."
            )
        self._timeout = timeout
        self._sparql_url = sparql_url
        self._overpass_url = overpass_url
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/sparql-results+json",
            "User-Agent": _USER_AGENT,
        })
        self._cached_lookup = functools.lru_cache(maxsize=cache_size)(
            self._uncached_lookup
        )

    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE

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
            raise ValueError("WikidataGazetteer.lookup: empty name")
        rows = self._cached_lookup(name.strip(), (country_hint or "").strip().upper() or None, 10)
        if not rows:
            raise GazetteerNotFoundError(
                f"Wikidata: no match for {name!r}"
                + (f" (country={country_hint!r})" if country_hint else "")
            )
        if len(rows) > 1:
            raise GazetteerAmbiguousError(
                f"Wikidata: {len(rows)} matches for {name!r}; "
                "pass country_hint or use search() and pick a candidate.",
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
        if not name or not name.strip():
            return []
        rows = self._cached_lookup(
            name.strip(),
            (country_hint or "").strip().upper() or None,
            limit,
        )
        return [self._row_to_candidate(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal: SPARQL + Overpass
    # ------------------------------------------------------------------

    def _uncached_lookup(
        self,
        name: str,
        country: Optional[str],
        limit: int,
    ) -> tuple[Mapping[str, Any], ...]:
        # SPARQL injection guard: the place name lands inside a double-
        # quoted literal. Reject embedded quotes and backslashes outright;
        # legitimate place names don't contain either.
        if '"' in name or '\\' in name:
            raise ValueError(
                f"WikidataGazetteer: name contains illegal character: {name!r}"
            )
        query = _SPARQL_TEMPLATE % (name, limit)
        try:
            resp = self._session.get(
                self._sparql_url,
                params={"query": query, "format": "json"},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise GazetteerBackendError(
                f"Wikidata SPARQL request for {name!r} failed: {exc}"
            ) from exc
        if resp.status_code != 200:
            raise GazetteerBackendError(
                f"Wikidata SPARQL returned {resp.status_code} for {name!r}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise GazetteerBackendError(
                f"Wikidata SPARQL returned non-JSON for {name!r}"
            ) from exc
        bindings = data.get("results", {}).get("bindings", [])
        rows: list[Mapping[str, Any]] = []
        for b in bindings:
            row = {
                "item": b.get("item", {}).get("value"),
                "name": b.get("itemLabel", {}).get("value") or name,
                "country": b.get("countryLabel", {}).get("value"),
                "osm_rel": b.get("osmRel", {}).get("value"),
                "coord": b.get("coord", {}).get("value"),  # "Point(lon lat)"
            }
            if country and row["country"]:
                if country.lower() not in row["country"].lower():
                    continue
            rows.append(row)
        return tuple(rows)

    def _fetch_osm_relation_geometry(self, osm_rel_id: str) -> Any:
        """Pull an OSM relation polygon via Overpass."""
        # Reject anything that isn't a positive integer relation ID;
        # Overpass QL injection is a real concern even though the
        # endpoint normally rejects malformed input.
        try:
            rel = int(osm_rel_id)
        except (TypeError, ValueError) as exc:
            raise GazetteerBackendError(
                f"OSM relation id {osm_rel_id!r} is not numeric"
            ) from exc
        if rel <= 0:
            raise GazetteerBackendError(
                f"OSM relation id must be positive, got {osm_rel_id!r}"
            )
        ql = f"[out:json];relation({rel});out geom;"
        try:
            resp = self._session.post(
                self._overpass_url,
                data={"data": ql},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise GazetteerBackendError(
                f"Overpass request for relation {rel} failed: {exc}"
            ) from exc
        if resp.status_code != 200:
            raise GazetteerBackendError(
                f"Overpass returned {resp.status_code} for relation {rel}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise GazetteerBackendError(
                f"Overpass returned non-JSON for relation {rel}"
            ) from exc
        # Overpass returns members with geometry inline when `out geom;`
        # is used. Reassemble outer ways into a polygon. For full
        # robustness we'd need to handle multipolygon roles; the simple
        # case covers the majority of admin relations.
        elements = data.get("elements") or []
        if not elements:
            raise GazetteerBackendError(
                f"Overpass returned no elements for relation {rel}"
            )
        relation = elements[0]
        coords: list[list[tuple[float, float]]] = []
        for m in relation.get("members") or []:
            if m.get("role") != "outer":
                continue
            geom = m.get("geometry") or []
            if geom:
                coords.append([(p["lon"], p["lat"]) for p in geom])
        if not coords:
            raise GazetteerBackendError(
                f"Overpass relation {rel} has no outer ring geometry"
            )
        # Build via shapely Polygon for the single-ring case; multi-ring
        # outer members get unioned. This is intentionally simple; if
        # consumers need fuller multipolygon support, file a Phase-3
        # follow-up rather than building it speculatively here.
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        polys = [Polygon(ring) for ring in coords if len(ring) >= 4]
        if not polys:
            raise GazetteerBackendError(
                f"Overpass relation {rel} outer rings are degenerate"
            )
        return unary_union(polys) if len(polys) > 1 else polys[0]

    @staticmethod
    def _parse_wkt_point(point_wkt: Optional[str]) -> Optional[tuple[float, float]]:
        if not point_wkt or not point_wkt.startswith("Point("):
            return None
        inside = point_wkt[len("Point("):].rstrip(")")
        parts = inside.split()
        if len(parts) != 2:
            return None
        try:
            return (float(parts[0]), float(parts[1]))
        except ValueError:
            return None

    def _row_to_candidate(self, row: Mapping[str, Any]) -> GazetteerCandidate:
        return GazetteerCandidate(
            name=str(row.get("name", "")),
            canonical_path=(str(row["country"]),) if row.get("country") else (),
            country=row.get("country"),
            source=self.provider_name,
        )

    def _row_to_result(self, row: Mapping[str, Any]) -> GazetteerResult:
        from shapely.geometry import Point

        if row.get("osm_rel"):
            geometry = self._fetch_osm_relation_geometry(row["osm_rel"])
            centroid = geometry.centroid
        else:
            coord = self._parse_wkt_point(row.get("coord"))
            if coord is None:
                raise GazetteerNotFoundError(
                    f"Wikidata: {row.get('name')!r} has neither OSM "
                    f"relation (P402) nor coordinate (P625); cannot "
                    f"resolve to geometry."
                )
            geometry = Point(coord)
            centroid = geometry

        return GazetteerResult(
            name=str(row.get("name", "")),
            canonical_path=(str(row["country"]),) if row.get("country") else (),
            geometry=geometry,
            centroid=centroid,
            country=row.get("country"),
            source=self.provider_name,
            raw=dict(row),
        )
