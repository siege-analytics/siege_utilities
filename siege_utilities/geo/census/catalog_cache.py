"""
Census catalog caching — disk persistence with TTL for CensusCatalog instances.

Stores serialized catalogs as JSON in ``~/.siege_utilities/cache/census_catalog/``.
Follows the same cache-dir convention as :class:`CensusAPI` and
:class:`PLFileDownloader`.

The loader orchestrates: **cache hit → API fetch → cache write**.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusSubject,
    CensusTable,
    CensusVariable,
    FamilyType,
)

log = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path.home() / ".siege_utilities" / "cache" / "census_catalog"
_DEFAULT_TTL_DAYS = 30


def _catalog_to_dict(catalog: CensusCatalog) -> dict:
    variables_by_table: dict[str, list[dict]] = {}
    for table in catalog.tables.values():
        variables_by_table[table.table_id] = [
            {
                "code": v.code,
                "label": v.label,
                "concept": v.concept,
                "table_id": v.table_id,
                "stat_type": v.stat_type,
            }
            for v in table.variables
        ]

    tables = [
        {
            "table_id": t.table_id,
            "label": t.label,
            "concept": t.concept,
            "universe": t.universe,
            "geography_levels": t.geography_levels,
        }
        for t in catalog.tables.values()
    ]

    families = [
        {
            "family_id": f.family_id,
            "family_type": f.family_type.value,
            "root_table_id": f.root_table_id,
            "table_ids": f.table_ids,
            "description": f.description,
        }
        for f in catalog.families.values()
    ]

    subjects = [
        {
            "subject_id": s.subject_id,
            "label": s.label,
            "table_ids": [t.table_id for t in s.tables],
        }
        for s in catalog.subjects.values()
    ]

    datasets = [
        {
            "dataset_id": d.dataset_id,
            "survey_type": d.survey_type,
            "year": d.year,
            "subject_ids": [s.subject_id for s in d.subjects],
            "table_ids": list(d.tables.keys()),
        }
        for d in catalog.datasets.values()
    ]

    return {
        "tables": tables,
        "variables": variables_by_table,
        "families": families,
        "subjects": subjects,
        "datasets": datasets,
    }


def _catalog_from_dict(data: dict) -> CensusCatalog:
    catalog = CensusCatalog()

    variables_by_table: dict[str, list[CensusVariable]] = {}
    for table_id, var_list in data.get("variables", {}).items():
        variables_by_table[table_id] = [
            CensusVariable(**v) for v in var_list
        ]

    for t in data.get("tables", []):
        table = CensusTable(
            table_id=t["table_id"],
            label=t["label"],
            concept=t["concept"],
            universe=t.get("universe", ""),
            variables=variables_by_table.get(t["table_id"], []),
            geography_levels=t.get("geography_levels", []),
        )
        catalog.add_table(table)

    for f in data.get("families", []):
        family = CensusFamily(
            family_id=f["family_id"],
            family_type=FamilyType(f["family_type"]),
            root_table_id=f["root_table_id"],
            tables=[
                catalog.get_table(tid)
                for tid in f["table_ids"]
                if catalog.get_table(tid) is not None
            ],
            description=f.get("description", ""),
        )
        catalog.add_family(family)

    for s in data.get("subjects", []):
        subject = CensusSubject(
            subject_id=s["subject_id"],
            label=s["label"],
            tables=[
                catalog.get_table(tid)
                for tid in s.get("table_ids", [])
                if catalog.get_table(tid) is not None
            ],
        )
        catalog.add_subject(subject)

    for d in data.get("datasets", []):
        dataset = CensusCatalogDataset(
            dataset_id=d["dataset_id"],
            survey_type=d["survey_type"],
            year=d["year"],
            subjects=[
                catalog.get_subject(sid)
                for sid in d.get("subject_ids", [])
                if catalog.get_subject(sid) is not None
            ],
            tables={
                tid: catalog.get_table(tid)
                for tid in d.get("table_ids", [])
                if catalog.get_table(tid) is not None
            },
        )
        catalog.add_dataset(dataset)

    return catalog


class CatalogCache:
    """Disk-backed JSON cache with TTL for CensusCatalog instances."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_days: int = _DEFAULT_TTL_DAYS,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self.ttl_days = ttl_days

    def _cache_path(self, dataset: str, year: int) -> Path:
        return self.cache_dir / f"{dataset}_{year}.json"

    def get(self, dataset: str, year: int) -> Optional[CensusCatalog]:
        path = self._cache_path(dataset, year)
        if not path.exists():
            return None

        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if datetime.now(tz=timezone.utc) - mtime > timedelta(days=self.ttl_days):
            log.debug("Cache expired for %s/%d", dataset, year)
            path.unlink()
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            catalog = _catalog_from_dict(data)
            log.debug("Cache hit for %s/%d", dataset, year)
            return catalog
        except (OSError, ValueError, UnicodeDecodeError) as e:
            log.warning("Failed to read cache for %s/%d: %s", dataset, year, e)
            return None

    def put(self, dataset: str, year: int, catalog: CensusCatalog) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(dataset, year)
        try:
            data = _catalog_to_dict(catalog)
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.debug("Cached catalog for %s/%d to %s", dataset, year, path)
        except (OSError, ValueError, TypeError) as e:
            log.warning("Failed to cache catalog for %s/%d: %s", dataset, year, e)

    def clear(self, dataset: str = "", year: int = 0) -> int:
        if not self.cache_dir.exists():
            return 0
        if dataset and year:
            path = self._cache_path(dataset, year)
            try:
                path.unlink()
                return 1
            except FileNotFoundError:
                return 0
        count = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            count += 1
        return count


class CatalogLoader:
    """
    Cache-aware catalog loader.

    Resolution order: cache → API fetch → cache write.
    """

    def __init__(
        self,
        cache: Optional[CatalogCache] = None,
        base_url: str = "",
    ):
        self.cache = cache or CatalogCache()
        self.base_url = base_url

    def load(
        self,
        dataset: str,
        year: int,
        survey_type: str = "",
        force_refresh: bool = False,
    ) -> CensusCatalog:
        if not force_refresh:
            cached = self.cache.get(dataset, year)
            if cached is not None:
                return cached

        from .catalog_populator import CensusCatalogPopulator

        kwargs: dict = {}
        if self.base_url:
            kwargs["base_url"] = self.base_url

        populator = CensusCatalogPopulator(**kwargs)
        catalog = populator.populate(dataset, year, survey_type=survey_type)

        self.cache.put(dataset, year, catalog)
        return catalog
