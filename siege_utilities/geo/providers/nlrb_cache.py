"""NLRB data caching — disk persistence with TTL for NLRBFetchResult.

Stores fetched NLRB case data as JSON in ``~/.siege_utilities/cache/nlrb/``.
The loader orchestrates: **cache hit → API fetch → cache write**.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .nlrb_clients import (
    ElectionRecord,
    NLRBCaseRecord,
    NLRBFetchResult,
    ULPRecord,
)

log = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path.home() / ".siege_utilities" / "cache" / "nlrb"
_DEFAULT_TTL_DAYS = 30


def _date_to_str(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _str_to_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _result_to_dict(result: NLRBFetchResult) -> dict:
    return {
        "source": result.source,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        "cases": [
            {
                "case_number": c.case_number,
                "case_type": c.case_type,
                "case_name": c.case_name,
                "status": c.status,
                "date_filed": _date_to_str(c.date_filed),
                "date_closed": _date_to_str(c.date_closed),
                "region": c.region,
                "city": c.city,
                "state": c.state,
                "union_name": c.union_name,
                "unit_description": c.unit_description,
                "naics_code": c.naics_code,
                "employee_count": c.employee_count,
                "source": c.source,
            }
            for c in result.cases
        ],
        "elections": [
            {
                "case_number": e.case_number,
                "tally_date": _date_to_str(e.tally_date),
                "eligible_voters": e.eligible_voters,
                "votes_for": e.votes_for,
                "votes_against": e.votes_against,
                "void_ballots": e.void_ballots,
                "union_name": e.union_name,
                "source": e.source,
            }
            for e in result.elections
        ],
        "ulp_charges": [
            {
                "case_number": u.case_number,
                "allegation": u.allegation,
                "charging_party": u.charging_party,
                "charged_party": u.charged_party,
                "section_of_act": u.section_of_act,
                "date_filed": _date_to_str(u.date_filed),
                "source": u.source,
            }
            for u in result.ulp_charges
        ],
    }


def _dict_to_result(data: dict) -> NLRBFetchResult:
    cases = [
        NLRBCaseRecord(
            case_number=c["case_number"],
            case_type=c.get("case_type", ""),
            case_name=c.get("case_name", ""),
            status=c.get("status", "Unknown"),
            date_filed=_str_to_date(c.get("date_filed")),
            date_closed=_str_to_date(c.get("date_closed")),
            region=c.get("region"),
            city=c.get("city", ""),
            state=c.get("state", ""),
            union_name=c.get("union_name", ""),
            unit_description=c.get("unit_description", ""),
            naics_code=c.get("naics_code", ""),
            employee_count=c.get("employee_count"),
            source=c.get("source", ""),
        )
        for c in data.get("cases", [])
    ]
    elections = [
        ElectionRecord(
            case_number=e["case_number"],
            tally_date=_str_to_date(e.get("tally_date")),
            eligible_voters=e.get("eligible_voters"),
            votes_for=e.get("votes_for"),
            votes_against=e.get("votes_against"),
            void_ballots=e.get("void_ballots"),
            union_name=e.get("union_name", ""),
            source=e.get("source", ""),
        )
        for e in data.get("elections", [])
    ]
    ulp_charges = [
        ULPRecord(
            case_number=u["case_number"],
            allegation=u.get("allegation", ""),
            charging_party=u.get("charging_party", ""),
            charged_party=u.get("charged_party", ""),
            section_of_act=u.get("section_of_act", ""),
            date_filed=_str_to_date(u.get("date_filed")),
            source=u.get("source", ""),
        )
        for u in data.get("ulp_charges", [])
    ]
    return NLRBFetchResult(
        cases=cases,
        elections=elections,
        ulp_charges=ulp_charges,
        source=data.get("source", "cache"),
    )


class NLRBCache:
    """JSON disk cache for NLRB fetch results.

    Args:
        cache_dir: Directory for cache files. Defaults to
            ``~/.siege_utilities/cache/nlrb/``.
        ttl_days: Cache entry lifetime in days. Default 30.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_days: int = _DEFAULT_TTL_DAYS,
    ):
        self._cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self._ttl = timedelta(days=ttl_days)

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[NLRBFetchResult]:
        """Load a cached result if it exists and is not expired."""
        path = self._cache_path(key)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Cache read error for %s: %s", key, exc)
            return None

        fetched_at = data.get("fetched_at")
        if fetched_at:
            try:
                cached_time = datetime.fromisoformat(fetched_at)
                if datetime.now(cached_time.tzinfo) - cached_time > self._ttl:
                    log.info("Cache expired for %s", key)
                    return None
            except (ValueError, TypeError):
                pass

        return _dict_to_result(data)

    def put(self, key: str, result: NLRBFetchResult) -> None:
        """Write a result to the cache."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        data = _result_to_dict(result)
        path = self._cache_path(key)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log.info("Cached %d records to %s", result.total_records, path)

    def invalidate(self, key: str) -> bool:
        """Remove a cache entry. Returns True if removed."""
        path = self._cache_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def invalidate_all(self) -> int:
        """Remove all cache entries. Returns count removed."""
        if not self._cache_dir.exists():
            return 0
        count = 0
        for path in self._cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count


class NLRBLoader:
    """Cache-aware loader: cache hit → fetch → cache write.

    Args:
        cache: NLRBCache instance. If None, creates default.
        client: NLRBDataClient or similar with ``fetch_all()`` method.
    """

    def __init__(
        self,
        cache: Optional[NLRBCache] = None,
        client=None,
    ):
        self._cache = cache or NLRBCache()
        self._client = client

    def load(
        self,
        key: str = "unified",
        force_refresh: bool = False,
    ) -> NLRBFetchResult:
        """Load NLRB data, using cache when available.

        Args:
            key: Cache key (e.g., 'unified', 'labordata', 'datagov').
            force_refresh: Skip cache and fetch fresh data.
        """
        if not force_refresh:
            cached = self._cache.get(key)
            if cached is not None:
                log.info("Cache hit for %s (%d records)", key, cached.total_records)
                return cached

        if self._client is None:
            from .nlrb_clients import NLRBDataClient
            self._client = NLRBDataClient()

        result = self._client.fetch_all()
        if result.success or result.total_records > 0:
            self._cache.put(key, result)

        return result
