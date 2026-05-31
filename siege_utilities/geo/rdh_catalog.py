"""RDH dataset catalog and discovery.

Pre-indexes available Redistricting Data Hub datasets by state, year,
chamber, dataset type, and format for browsable discovery without
trial-and-error API calls.
"""

from __future__ import annotations

import abc
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

__all__ = [
    "CatalogEntry",
    "CoverageCell",
    "DEFAULT_CACHE_TTL",
    "DictRDHCatalogProvider",
    "RDHCatalog",
    "RDHCatalogProvider",
    "SearchResult",
]

DEFAULT_CACHE_TTL = 30 * 24 * 3600  # 30 days in seconds
CACHE_FILENAME = "rdh_catalog.json"


@dataclass
class CatalogEntry:
    """Indexed metadata for a single RDH dataset.

    Attributes:
        title: Human-readable dataset title.
        url: Download URL.
        state: Two-letter state abbreviation.
        year: Publication or vintage year.
        chamber: Legislative chamber (congress, state_senate, state_house, or empty).
        dataset_type: Category (pl94171, cvap, election, legislative, etc.).
        format: File format (csv, shp).
        geography: Geographic level (block, tract, precinct, district, etc.).
        official: Whether this is an official/authoritative source.
        file_size: Human-readable file size string.
    """

    title: str = ""
    url: str = ""
    state: str = ""
    year: str = ""
    chamber: str = ""
    dataset_type: str = ""
    format: str = ""
    geography: str = ""
    official: bool = False
    file_size: str = ""

    def matches(
        self,
        state: Optional[str] = None,
        year: Optional[str] = None,
        chamber: Optional[str] = None,
        dataset_type: Optional[str] = None,
        format: Optional[str] = None,
    ) -> bool:
        if state and self.state.upper() != state.upper():
            return False
        if year and self.year != str(year):
            return False
        if chamber and self.chamber.lower() != chamber.lower():
            return False
        if dataset_type and self.dataset_type.lower() != dataset_type.lower():
            return False
        if format and self.format.lower() != format.lower():
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "state": self.state,
            "year": self.year,
            "chamber": self.chamber,
            "dataset_type": self.dataset_type,
            "format": self.format,
            "geography": self.geography,
            "official": self.official,
            "file_size": self.file_size,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CatalogEntry:
        return cls(
            title=d.get("title", ""),
            url=d.get("url", ""),
            state=d.get("state", ""),
            year=d.get("year", ""),
            chamber=d.get("chamber", ""),
            dataset_type=d.get("dataset_type", ""),
            format=d.get("format", ""),
            geography=d.get("geography", ""),
            official=d.get("official", False),
            file_size=d.get("file_size", ""),
        )


@dataclass
class SearchResult:
    """Ranked search result from the catalog.

    Attributes:
        entry: The matching CatalogEntry.
        score: Relevance score (higher = better match).
    """

    entry: CatalogEntry
    score: float = 1.0


@dataclass
class CoverageCell:
    """Single cell in the coverage matrix.

    Attributes:
        state: State abbreviation.
        year: Year.
        dataset_type: Dataset type.
        count: Number of datasets matching this combination.
        formats: Set of available formats.
    """

    state: str = ""
    year: str = ""
    dataset_type: str = ""
    count: int = 0
    formats: list[str] = field(default_factory=list)


class RDHCatalogProvider(abc.ABC):
    """Protocol for fetching the full RDH dataset inventory."""

    @abc.abstractmethod
    def fetch_all_datasets(self) -> list[CatalogEntry]:
        """Fetch the complete dataset inventory from all states."""


class DictRDHCatalogProvider(RDHCatalogProvider):
    """In-memory catalog provider for testing."""

    def __init__(self, entries: Optional[list[CatalogEntry]] = None):
        self._entries: list[CatalogEntry] = entries or []

    def add(self, entry: CatalogEntry):
        self._entries.append(entry)

    def fetch_all_datasets(self) -> list[CatalogEntry]:
        return list(self._entries)


CHAMBER_KEYWORDS = {
    "congress": ["congress", "congressional", " cd ", " cd_"],
    "state_senate": ["state senate", "upper chamber", "ssd", "sldu", "state_senate"],
    "state_house": ["state house", "lower chamber", "shd", "sldl", "state_house"],
}


def _infer_chamber(title: str) -> str:
    lower = title.lower()
    for chamber, keywords in CHAMBER_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return chamber
    return ""


def _score_entry(
    entry: CatalogEntry,
    state: Optional[str] = None,
    year: Optional[str] = None,
    chamber: Optional[str] = None,
    dataset_type: Optional[str] = None,
    query: Optional[str] = None,
) -> float:
    score = 0.0
    if state and entry.state.upper() == state.upper():
        score += 10.0
    if year and entry.year == str(year):
        score += 5.0
    if chamber and entry.chamber.lower() == chamber.lower():
        score += 5.0
    if dataset_type and entry.dataset_type.lower() == dataset_type.lower():
        score += 5.0
    if entry.official:
        score += 2.0
    if query:
        query_lower = query.lower()
        title_lower = entry.title.lower()
        if query_lower in title_lower:
            score += 3.0
        else:
            words = query_lower.split()
            matched = sum(1 for w in words if w in title_lower)
            if words:
                score += (matched / len(words)) * 2.0
    return score


class RDHCatalog:
    """Pre-indexed catalog of available RDH datasets.

    Provides browsable discovery of datasets by state, year, chamber,
    dataset type, and format without trial-and-error API calls.

    Args:
        provider: Source for fetching the full dataset inventory.
        cache_dir: Directory for persisting the catalog index.
        cache_ttl: Cache time-to-live in seconds (default 30 days).
    """

    def __init__(
        self,
        provider: Optional[RDHCatalogProvider] = None,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        self._provider = provider
        self._cache_dir = cache_dir
        self._cache_ttl = cache_ttl
        self._entries: list[CatalogEntry] = []
        self._loaded = False
        self._loaded_at: Optional[float] = None

    @property
    def entries(self) -> list[CatalogEntry]:
        return list(self._entries)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def load(self, force: bool = False) -> int:
        """Load the catalog, using cache if available and fresh.

        Args:
            force: If True, bypass cache and fetch from provider.

        Returns:
            Number of entries loaded.
        """
        if not force and self._try_load_cache():
            return len(self._entries)

        if self._provider is None:
            raise RuntimeError("No provider configured; cannot load catalog")

        entries = self._provider.fetch_all_datasets()
        self._entries = entries
        self._loaded = True
        self._loaded_at = time.time()

        self._save_cache()

        log.info("Loaded %d entries into RDH catalog", len(entries))
        return len(entries)

    def search(
        self,
        state: Optional[str] = None,
        year: Optional[str] = None,
        chamber: Optional[str] = None,
        dataset_type: Optional[str] = None,
        format: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> list[SearchResult]:
        """Search the catalog with ranked results.

        At least one filter or query must be provided.

        Args:
            state: Two-letter state abbreviation.
            year: Publication year.
            chamber: Legislative chamber (congress, state_senate, state_house).
            dataset_type: Dataset category.
            format: File format (csv, shp).
            query: Free-text search against title.
            limit: Maximum results to return.

        Returns:
            List of SearchResult sorted by relevance score (descending).
        """
        results: list[SearchResult] = []

        for entry in self._entries:
            if format and entry.format.lower() != format.lower():
                continue

            score = _score_entry(
                entry,
                state=state,
                year=year,
                chamber=chamber,
                dataset_type=dataset_type,
                query=query,
            )

            if score > 0:
                results.append(SearchResult(entry=entry, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def coverage_matrix(
        self,
        dataset_type: Optional[str] = None,
    ) -> list[CoverageCell]:
        """Build a coverage matrix of state x year x dataset_type.

        Args:
            dataset_type: Optionally filter to a single dataset type.

        Returns:
            List of CoverageCell entries with counts and available formats.
        """
        buckets: dict[tuple[str, str, str], list[str]] = {}

        for entry in self._entries:
            if dataset_type and entry.dataset_type.lower() != dataset_type.lower():
                continue

            key = (entry.state, entry.year, entry.dataset_type)
            if key not in buckets:
                buckets[key] = []
            if entry.format and entry.format not in buckets[key]:
                buckets[key].append(entry.format)

        cells = []
        for (state, year, dtype), formats in sorted(buckets.items()):
            cells.append(CoverageCell(
                state=state,
                year=year,
                dataset_type=dtype,
                count=len([
                    e for e in self._entries
                    if e.state == state and e.year == year and e.dataset_type == dtype
                ]),
                formats=sorted(formats),
            ))

        return cells

    def states(self) -> list[str]:
        """Return sorted list of states with datasets in the catalog."""
        return sorted(set(e.state for e in self._entries if e.state))

    def years(self) -> list[str]:
        """Return sorted list of years with datasets in the catalog."""
        return sorted(set(e.year for e in self._entries if e.year))

    def dataset_types(self) -> list[str]:
        """Return sorted list of dataset types in the catalog."""
        return sorted(set(e.dataset_type for e in self._entries if e.dataset_type))

    def for_state(self, state: str) -> list[CatalogEntry]:
        """Return all entries for a given state."""
        return [e for e in self._entries if e.state.upper() == state.upper()]

    # -- Cache management -------------------------------------------------------

    def _cache_path(self) -> Optional[Path]:
        if self._cache_dir is None:
            return None
        return self._cache_dir / CACHE_FILENAME

    def _try_load_cache(self) -> bool:
        path = self._cache_path()
        if path is None or not path.exists():
            return False

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.debug("Cache file unreadable, will refetch")
            return False

        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > self._cache_ttl:
            log.debug("Cache expired (age %.0fs > TTL %ds)", time.time() - cached_at, self._cache_ttl)
            return False

        entries = [CatalogEntry.from_dict(d) for d in data.get("entries", [])]
        self._entries = entries
        self._loaded = True
        self._loaded_at = cached_at

        log.debug("Loaded %d entries from cache", len(entries))
        return True

    def _save_cache(self):
        path = self._cache_path()
        if path is None:
            return

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "cached_at": time.time(),
            "entry_count": len(self._entries),
            "entries": [e.to_dict() for e in self._entries],
        }

        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log.debug("Saved %d entries to cache", len(self._entries))
