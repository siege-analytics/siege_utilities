"""WKLS (Well Known Locations) gazetteer backend.

Wraps the upstream `wkls <https://github.com/wherobots/wkls>`_ package
to resolve place names against Overture Maps administrative
boundaries (~625k globally). Why this is the default global backend:

* No API key, no rate limit (reads from public S3 via embedded sedonadb).
* sedonadb is Rust + Arrow-native — **no JVM / Spark dependency**, just
  a 302 MB install.
* Source data is Overture Maps, the well-curated successor to
  patchwork-of-everything that older gazetteers carried.

Two siege_utilities-specific pieces this backend adds on top of the raw
wkls API:

1. **Free-text → ISO code** resolver. Etter outputs ``"Alabama"``;
   wkls wants ``wkls.us.al``. We use the wkls metadata search to map
   the human form into the chained-attribute form before calling the
   geometry getter.

2. **In-process LRU cache.** The upstream library does *not* cache
   geometry fetches in-process — every ``.wkt()`` call hits S3 (~6s
   cold). For interactive use that's a deal-breaker. We wrap the path
   ``(country, region, place_id)`` → shapely geometry with
   :func:`functools.lru_cache`.

Verified against ``wkls==1.1.0`` on 2026-05-07.
"""

from __future__ import annotations

import functools
import logging
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
    import wkls  # type: ignore[import-not-found]
    WKLS_AVAILABLE = True
except ImportError:
    wkls = None  # type: ignore[assignment]
    WKLS_AVAILABLE = False
    log.info("wkls not available — WklsGazetteer will raise on construct")


__all__ = [
    "WKLS_AVAILABLE",
    "WklsGazetteer",
]


class WklsGazetteer:
    """WKLS-backed gazetteer with in-process LRU caching."""

    provider_name = "wkls"

    def __init__(self, *, cache_size: int = 1024) -> None:
        if not WKLS_AVAILABLE:
            raise ImportError(
                "WklsGazetteer requires wkls. Install with: "
                "pip install 'siege-utilities[wkls]' or pip install 'wkls>=1.1.0'."
            )
        self._cache_size = cache_size
        # Per-instance cache. Module-level cache would be tempting for
        # cross-instance sharing, but instances may be configured with
        # different overture_version, etc., and mixing those in one
        # cache is silently wrong.
        self._cached_geometry = functools.lru_cache(maxsize=cache_size)(
            self._fetch_geometry
        )

    def is_available(self) -> bool:
        return WKLS_AVAILABLE

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
            raise ValueError("WklsGazetteer.lookup: empty name")
        candidates = self._search_metadata(
            name, country_hint=country_hint, admin_hint=admin_hint, limit=10,
        )
        if not candidates:
            raise GazetteerNotFoundError(
                f"WKLS: no match for {name!r}"
                + (f" (country={country_hint!r})" if country_hint else "")
            )
        if len(candidates) > 1:
            # Always surface ambiguity rather than silently picking the
            # first match — hints narrow the search space, they don't
            # promise uniqueness.
            hint_note = ""
            if country_hint or admin_hint:
                hint_note = (
                    f" (after country_hint={country_hint!r}, "
                    f"admin_hint={admin_hint!r})"
                )
            raise GazetteerAmbiguousError(
                f"WKLS: {len(candidates)} matches for {name!r}{hint_note}; "
                "pass tighter hints, or use search() and pick a candidate.",
                candidates=[self._row_to_candidate(r) for r in candidates],
            )
        chosen = candidates[0]
        return self._row_to_result(chosen)

    def search(
        self,
        name: str,
        *,
        country_hint: Optional[str] = None,
        limit: int = 10,
    ) -> list[GazetteerCandidate]:
        if not name or not name.strip():
            return []
        rows = self._search_metadata(
            name, country_hint=country_hint, admin_hint=None, limit=limit,
        )
        return [self._row_to_candidate(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal: search + fetch
    # ------------------------------------------------------------------

    def _search_metadata(
        self,
        name: str,
        *,
        country_hint: Optional[str],
        admin_hint: Optional[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Run the WKLS wildcard search; return the top-N rows.

        ``limit`` bounds the rows we materialize into Python; it does
        NOT bound the upstream sedonadb scan, which is driven by the
        wildcard pattern and any preceding country/admin chain access.
        Tight ``country_hint`` / ``admin_hint`` are the right way to
        keep the upstream cost down.

        Tolerant of upstream API drift: catches all exceptions and
        translates into :class:`GazetteerBackendError`.
        """
        # Resolve country_hint outside the upstream-error try/except so
        # caller errors (unknown ISO-3) surface as ValueError rather than
        # being relabeled as backend failures.
        country_code: Optional[str] = None
        if country_hint:
            country_code = country_hint.strip()
            if len(country_code) == 3:
                iso2 = _ISO3_TO_ISO2.get(country_code.upper())
                if iso2 is None:
                    raise ValueError(
                        f"WKLS: unknown ISO-3 country code {country_code!r}; "
                        f"pass an ISO-2 code or extend _ISO3_TO_ISO2."
                    )
                country_code = iso2.lower()
            else:
                country_code = country_code.lower()
        try:
            # Walk the chain top-down using the hints we have. Both
            # hints are best-effort; missing hints just mean a wider
            # search.
            df = wkls
            if country_code:
                # Try direct chain access; fall back to wildcard.
                try:
                    df = getattr(wkls, country_code)
                except AttributeError:
                    df = wkls[f"%{country_code}%"]
            if admin_hint:
                admin = admin_hint.strip().lower()
                # Admin hints can be region codes ("al"), full names
                # ("alabama"), or FIPS — try each.
                try:
                    df = getattr(df, admin)
                except (AttributeError, TypeError):
                    df = df[f"%{admin}%"]

            df = df[f"%{name}%"]
            # to_arrow_table avoids the optional pandas dep (we can
            # iterate Arrow rows directly).
            arrow = df.to_arrow_table()
        except Exception as exc:
            raise GazetteerBackendError(
                f"WKLS search for {name!r} failed: {exc}"
            ) from exc

        rows: list[dict[str, Any]] = []
        for batch in arrow.to_batches():
            cols = {field.name: batch.column(i).to_pylist()
                    for i, field in enumerate(arrow.schema)}
            for i in range(len(batch)):
                rows.append({k: v[i] for k, v in cols.items()})
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        return rows

    def _fetch_geometry(self, place_id: str) -> Any:
        """Fetch the WKT for a given Overture place ID.

        This is the slow path — first call is ~6s; subsequent calls hit
        the LRU cache. ``functools.lru_cache`` requires a hashable
        argument, hence the str ID rather than the row dict.
        """
        try:
            from shapely import wkt as _wkt
        except ImportError as exc:
            raise GazetteerBackendError(
                "shapely required to convert WKLS WKT to geometry"
            ) from exc
        try:
            wkt_str = wkls.resolve(place_id).wkt()
        except Exception as exc:
            raise GazetteerBackendError(
                f"WKLS geometry fetch for id={place_id!r} failed: {exc}"
            ) from exc
        return _wkt.loads(wkt_str)

    def _row_to_candidate(self, row: dict[str, Any]) -> GazetteerCandidate:
        return GazetteerCandidate(
            name=str(row.get("name_primary") or row.get("name_en") or ""),
            canonical_path=_canonical_path_from_row(row),
            country=row.get("country") or None,
            admin_levels=_admin_levels_from_row(row),
            score=None,
            source=self.provider_name,
        )

    def _row_to_result(self, row: dict[str, Any]) -> GazetteerResult:
        place_id = str(row["id"])
        geometry = self._cached_geometry(place_id)
        # `centroid` only fails for empty / structurally invalid GEOS
        # geometries; let everything else propagate as a real bug.
        try:
            from shapely.errors import GEOSException
        except ImportError:  # pragma: no cover - shapely already required upstream
            GEOSException = Exception  # type: ignore[assignment, misc]
        try:
            centroid = geometry.centroid
        except (GEOSException, ValueError) as exc:
            raise GazetteerBackendError(
                f"WKLS: cannot compute centroid for id={place_id!r}: {exc}"
            ) from exc
        return GazetteerResult(
            name=str(row.get("name_primary") or row.get("name_en") or ""),
            canonical_path=_canonical_path_from_row(row),
            geometry=geometry,
            centroid=centroid,
            country=row.get("country") or None,
            admin_levels=_admin_levels_from_row(row),
            source=self.provider_name,
            raw=row,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_path_from_row(row: dict[str, Any]) -> tuple[str, ...]:
    """Build the ``(country, region, name)`` breadcrumb."""
    parts = []
    if row.get("country"):
        parts.append(str(row["country"]))
    if row.get("region") and row["region"] != row.get("country"):
        parts.append(str(row["region"]))
    name = row.get("name_primary") or row.get("name_en")
    if name:
        parts.append(str(name))
    return tuple(parts)


def _admin_levels_from_row(row: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    if row.get("country"):
        out["country"] = str(row["country"])
    if row.get("region"):
        out["region"] = str(row["region"])
    if row.get("subtype"):
        out["subtype"] = str(row["subtype"])
    return out


# Minimal ISO-3 → ISO-2 fallback map for common cases. Not exhaustive —
# WKLS uses ISO-2; if the caller passes ISO-3 we try this map first,
# then fall back to truncating ("USA" → "US", which is correct here).
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
