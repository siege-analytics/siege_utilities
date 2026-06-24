"""
Census catalog populator — fetches metadata from Census API discovery endpoints.

Populates CensusCatalog instances from:
- ``/data/{year}/{dataset}/variables.json`` — variable definitions
- ``/data/{year}/{dataset}/groups.json`` — concept groupings

Separated from ``catalog.py`` to keep the data model I/O-free.
"""

from __future__ import annotations

import logging
import re

import requests

from siege_utilities.config import CENSUS_API_BASE_URL
from .catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusSubject,
    CensusTable,
    CensusVariable,
    parse_table_id,
)

__all__ = [
    'CensusCatalogPopulator',
]

log = logging.getLogger(__name__)

_DATASET_PATHS = {
    "acs5": "acs/acs5",
    "acs1": "acs/acs1",
    "dec/pl": "dec/pl",
    "dec/dhc": "dec/dhc",
    "dec/dp": "dec/dp",
    "dec/sf1": "dec/sf1",
}

_VARIABLE_CODE_RE = re.compile(
    r"^[A-Z]{1,3}\d{5}[A-Z]?_\d{3}[EM]?$"
)


class CensusCatalogPopulator:
    def __init__(
        self,
        base_url: str = CENSUS_API_BASE_URL,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def populate(
        self,
        dataset: str,
        year: int,
        survey_type: str = "",
    ) -> CensusCatalog:
        dataset_path = _DATASET_PATHS.get(dataset, dataset)
        raw_variables = self._fetch_variables(dataset_path, year)
        raw_groups = self._fetch_groups(dataset_path, year)

        tables = self._build_tables(raw_variables)
        subjects = self._build_subjects(raw_groups, tables)

        catalog = CensusCatalog()
        catalog.add_tables(tables)
        catalog.build_families()

        for subject in subjects:
            catalog.add_subject(subject)

        ds = CensusCatalogDataset(
            dataset_id=f"{dataset}_{year}",
            survey_type=survey_type or dataset,
            year=year,
            subjects=subjects,
            tables={t.table_id: t for t in tables},
        )
        catalog.add_dataset(ds)

        log.info(
            "Populated catalog for %s/%d: %d tables, %d families, %d subjects",
            dataset,
            year,
            len(catalog.tables),
            len(catalog.families),
            len(catalog.subjects),
        )
        return catalog

    def _fetch_variables(self, dataset_path: str, year: int) -> dict:
        url = f"{self.base_url}/data/{year}/{dataset_path}/variables.json"
        log.debug("Fetching variables from %s", url)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("variables", {})

    def _fetch_groups(self, dataset_path: str, year: int) -> list[dict]:
        url = f"{self.base_url}/data/{year}/{dataset_path}/groups.json"
        log.debug("Fetching groups from %s", url)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("groups", [])

    def _build_tables(self, raw_variables: dict) -> list[CensusTable]:
        table_vars: dict[str, list[CensusVariable]] = {}
        table_meta: dict[str, dict] = {}

        for code, meta in raw_variables.items():
            if not _VARIABLE_CODE_RE.match(code):
                continue

            parsed = parse_table_id(code.rsplit("_", 1)[0])
            if parsed is None:
                continue

            table_id = code.rsplit("_", 1)[0]
            label = meta.get("label", "")
            concept = meta.get("concept", "")

            var = CensusVariable(
                code=code,
                label=label,
                concept=concept,
                table_id=table_id,
                stat_type="M" if code.endswith("M") else "E",
            )

            table_vars.setdefault(table_id, []).append(var)
            if table_id not in table_meta:
                table_meta[table_id] = {
                    "concept": concept,
                    "group": meta.get("group", ""),
                }

        tables = []
        for table_id, variables in sorted(table_vars.items()):
            meta = table_meta.get(table_id, {})
            estimate_vars = [v for v in variables if v.stat_type == "E"]
            tables.append(
                CensusTable(
                    table_id=table_id,
                    label=meta.get("concept", ""),
                    concept=meta.get("concept", ""),
                    variables=sorted(estimate_vars, key=lambda v: v.code),
                )
            )

        return tables

    def _build_subjects(
        self,
        raw_groups: list[dict],
        tables: list[CensusTable],
    ) -> list[CensusSubject]:
        table_lookup = {t.table_id: t for t in tables}

        group_to_tables: dict[str, list[CensusTable]] = {}
        for group_info in raw_groups:
            group_name = group_info.get("name", "")
            if not group_name or group_name == "N/A":
                continue

            table = table_lookup.get(group_name)
            if table is None:
                continue

            description = group_info.get("description", "")
            concept_key = _subject_key(description)
            group_to_tables.setdefault(concept_key, []).append(table)

        subjects = []
        for concept_key, group_tables in sorted(group_to_tables.items()):
            if not concept_key:
                continue
            subjects.append(
                CensusSubject(
                    subject_id=concept_key.lower().replace(" ", "_"),
                    label=concept_key,
                    tables=sorted(group_tables, key=lambda t: t.table_id),
                )
            )

        return subjects


def _subject_key(description: str) -> str:
    if not description:
        return ""
    parts = description.upper().split("--")
    if len(parts) >= 2:
        return parts[0].strip().title()
    return description.strip().title()
