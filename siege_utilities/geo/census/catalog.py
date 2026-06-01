"""
Census table catalog — hierarchical metadata for Census tables and variables.

Hierarchy: Dataset → Subject → Family → Table → Variable

The key abstraction is **Family**, which the Census Bureau does not expose
natively. Two family types exist:

- **Race iteration families**: tables like B19001 / B19001A–I share a root
  table; the letter suffix signals the race/ethnicity iteration.
- **Topical kinship families**: tables like B19001, B19013, B19025 share a
  subject-area prefix and related concepts (all income-related).

Both family types are first-class objects in the catalog.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)

# Table ID pattern: prefix letter(s) + 5-digit number + optional letter suffix
# Examples: B19001, B19001A, C17001, CP05
_TABLE_ID_RE = re.compile(
    r"^(?P<prefix>[A-Z]{1,3})"
    r"(?P<number>\d{5})"
    r"(?P<suffix>[A-Z])?$"
)

# Variable code pattern: table_id + underscore + sequence number + estimate/moe
# Examples: B19001_001E, B19001_001M
_VARIABLE_CODE_RE = re.compile(
    r"^(?P<table>[A-Z]{1,3}\d{5}[A-Z]?)"
    r"_"
    r"(?P<seq>\d{3})"
    r"(?P<stat_type>[EM]?)$"
)

__all__ = ["CensusCatalog", "CensusCatalogDataset", "CensusFamily", "CensusSubject", "CensusTable", "CensusVariable", "FamilyType", "SearchLevel", "SearchResult", "detect_race_iteration_families", "detect_topical_families", "parse_table_id"]


class SearchLevel(Enum):
    DATASET = "dataset"
    SUBJECT = "subject"
    FAMILY = "family"
    TABLE = "table"
    VARIABLE = "variable"


@dataclass
class SearchResult:
    level: SearchLevel
    id: str
    label: str
    score: float
    obj: object = field(repr=False)


class FamilyType(Enum):
    RACE_ITERATION = "race_iteration"
    TOPICAL_KINSHIP = "topical_kinship"


@dataclass
class CensusVariable:
    code: str
    label: str
    concept: str
    table_id: str
    stat_type: str = "E"

    @classmethod
    def parse_code(cls, code: str) -> Optional[dict]:
        m = _VARIABLE_CODE_RE.match(code)
        if not m:
            return None
        return {
            "table_id": m.group("table"),
            "seq": m.group("seq"),
            "stat_type": m.group("stat_type") or "E",
        }


@dataclass
class CensusTable:
    table_id: str
    label: str
    concept: str
    universe: str = ""
    variables: list[CensusVariable] = field(default_factory=list)
    geography_levels: list[str] = field(default_factory=list)

    @property
    def parsed_id(self) -> Optional[dict]:
        return parse_table_id(self.table_id)

    @property
    def root_table_id(self) -> Optional[str]:
        parsed = self.parsed_id
        if parsed is None:
            return None
        return f"{parsed['prefix']}{parsed['number']}"

    @property
    def race_suffix(self) -> Optional[str]:
        parsed = self.parsed_id
        if parsed is None:
            return None
        return parsed.get("suffix")


@dataclass
class CensusFamily:
    family_id: str
    family_type: FamilyType
    root_table_id: str
    tables: list[CensusTable] = field(default_factory=list)
    description: str = ""

    @property
    def table_ids(self) -> list[str]:
        return [t.table_id for t in self.tables]


@dataclass
class CensusSubject:
    subject_id: str
    label: str
    families: list[CensusFamily] = field(default_factory=list)
    tables: list[CensusTable] = field(default_factory=list)

    @property
    def all_tables(self) -> list[CensusTable]:
        family_tables = [t for f in self.families for t in f.tables]
        return family_tables + self.tables


@dataclass
class CensusCatalogDataset:
    dataset_id: str
    survey_type: str
    year: int
    subjects: list[CensusSubject] = field(default_factory=list)
    tables: dict[str, CensusTable] = field(default_factory=dict)


def parse_table_id(table_id: str) -> Optional[dict]:
    m = _TABLE_ID_RE.match(table_id)
    if not m:
        return None
    return {
        "prefix": m.group("prefix"),
        "number": m.group("number"),
        "suffix": m.group("suffix"),
    }


def detect_race_iteration_families(
    tables: list[CensusTable],
) -> list[CensusFamily]:
    roots: dict[str, list[CensusTable]] = {}
    for table in tables:
        parsed = parse_table_id(table.table_id)
        if parsed is None:
            continue
        if parsed["suffix"] is None:
            continue
        root = f"{parsed['prefix']}{parsed['number']}"
        roots.setdefault(root, []).append(table)

    families = []
    for root_id, suffixed_tables in sorted(roots.items()):
        base_table = _find_table_by_id(tables, root_id)
        all_members = ([base_table] if base_table else []) + sorted(
            suffixed_tables, key=lambda t: t.table_id
        )
        families.append(
            CensusFamily(
                family_id=f"race:{root_id}",
                family_type=FamilyType.RACE_ITERATION,
                root_table_id=root_id,
                tables=all_members,
                description=f"Race/ethnicity iterations of {root_id}",
            )
        )

    return families


def detect_topical_families(
    tables: list[CensusTable],
    max_number_gap: int = 100,
) -> list[CensusFamily]:
    base_tables: dict[str, list[CensusTable]] = {}
    for table in tables:
        parsed = parse_table_id(table.table_id)
        if parsed is None or parsed["suffix"] is not None:
            continue
        prefix = parsed["prefix"]
        base_tables.setdefault(prefix, []).append(table)

    families = []
    for prefix, prefix_tables in sorted(base_tables.items()):
        sorted_tables = sorted(
            prefix_tables, key=lambda t: int(parse_table_id(t.table_id)["number"])
        )

        groups = _cluster_by_numeric_proximity(sorted_tables, max_number_gap)

        for group in groups:
            if len(group) < 2:
                continue

            concept_groups = _subgroup_by_concept(group)

            for concept_key, members in concept_groups.items():
                if len(members) < 2:
                    continue

                root = members[0]
                families.append(
                    CensusFamily(
                        family_id=f"topic:{root.table_id}",
                        family_type=FamilyType.TOPICAL_KINSHIP,
                        root_table_id=root.table_id,
                        tables=members,
                        description=(
                            f"Topically related tables near {root.table_id}"
                        ),
                    )
                )

    return families


def _cluster_by_numeric_proximity(
    sorted_tables: list[CensusTable],
    max_gap: int,
) -> list[list[CensusTable]]:
    if not sorted_tables:
        return []
    clusters: list[list[CensusTable]] = [[sorted_tables[0]]]
    for table in sorted_tables[1:]:
        prev = clusters[-1][-1]
        prev_num = int(parse_table_id(prev.table_id)["number"])
        curr_num = int(parse_table_id(table.table_id)["number"])
        if curr_num - prev_num <= max_gap:
            clusters[-1].append(table)
        else:
            clusters.append([table])
    return clusters


def _subgroup_by_concept(
    tables: list[CensusTable],
    min_keyword_overlap: int = 1,
) -> dict[str, list[CensusTable]]:
    if not tables:
        return {}

    keywords_per_table = [
        (table, _concept_keywords(table.concept)) for table in tables
    ]

    # Greedy clustering: each table joins the first cluster it shares
    # enough keywords with, or starts a new cluster.
    clusters: list[list[CensusTable]] = []
    cluster_keywords: list[set[str]] = []

    for table, kws in keywords_per_table:
        placed = False
        for i, ckws in enumerate(cluster_keywords):
            if len(kws & ckws) >= min_keyword_overlap:
                clusters[i].append(table)
                cluster_keywords[i] |= kws
                placed = True
                break
        if not placed:
            clusters.append([table])
            cluster_keywords.append(set(kws))

    return {
        clusters[i][0].table_id: clusters[i] for i in range(len(clusters))
    }


_CONCEPT_STOP_WORDS = frozenset({
    "IN", "THE", "OF", "FOR", "BY", "AND", "OR", "TO", "A", "AN",
    "WITH", "PAST", "LAST", "MONTHS", "YEARS", "YEAR", "12",
})


def _concept_keywords(concept: str) -> set[str]:
    if not concept:
        return set()
    words = concept.upper().split()
    # Strip parenthesized race qualifiers
    cleaned = []
    depth = 0
    for w in words:
        if "(" in w:
            depth += 1
        if depth == 0:
            cleaned.append(w)
        if ")" in w:
            depth = max(0, depth - 1)
    return {w for w in cleaned if w not in _CONCEPT_STOP_WORDS}


def _find_table_by_id(
    tables: list[CensusTable], table_id: str
) -> Optional[CensusTable]:
    for table in tables:
        if table.table_id == table_id:
            return table
    return None


def _tokenize_query(query: str) -> list[str]:
    return [w for w in query.upper().split() if w not in _CONCEPT_STOP_WORDS]


def _text_score(text: str, tokens: list[str]) -> float:
    upper = text.upper()
    words = set(upper.split())
    score = 0.0
    for token in tokens:
        if token in words:
            score += 1.0
        elif token in upper:
            score += 0.5
    return score


def _id_score(obj_id: str, tokens: list[str]) -> float:
    upper = obj_id.upper()
    for token in tokens:
        if token == upper:
            return 2.0
        if token in upper:
            return 1.0
    return 0.0


def _score_table(table: CensusTable, tokens: list[str]) -> float:
    score = _id_score(table.table_id, tokens)
    score += _text_score(table.concept, tokens)
    score += _text_score(table.label, tokens) * 0.5
    return score


def _score_family(family: CensusFamily, tokens: list[str]) -> float:
    score = _text_score(family.description, tokens)
    score += _id_score(family.root_table_id, tokens)
    for table in family.tables:
        ts = _text_score(table.concept, tokens)
        if ts > 0:
            score += ts * 0.3
            break
    return score


def _score_subject(subject: CensusSubject, tokens: list[str]) -> float:
    return _text_score(subject.label, tokens) + _id_score(subject.subject_id, tokens)


def _score_variable(var: CensusVariable, tokens: list[str]) -> float:
    score = _id_score(var.code, tokens)
    score += _text_score(var.label, tokens) * 0.8
    score += _text_score(var.concept, tokens) * 0.3
    return score


def _score_dataset(ds: CensusCatalogDataset, tokens: list[str]) -> float:
    score = _id_score(ds.dataset_id, tokens)
    score += _text_score(ds.survey_type, tokens)
    for token in tokens:
        if token == str(ds.year):
            score += 1.0
    return score


class CensusCatalog:
    def __init__(self) -> None:
        self._datasets: dict[str, CensusCatalogDataset] = {}
        self._tables: dict[str, CensusTable] = {}
        self._families: dict[str, CensusFamily] = {}
        self._subjects: dict[str, CensusSubject] = {}

    # -- Registration --

    def add_table(self, table: CensusTable) -> None:
        self._tables[table.table_id] = table

    def add_tables(self, tables: list[CensusTable]) -> None:
        for table in tables:
            self.add_table(table)

    def add_family(self, family: CensusFamily) -> None:
        self._families[family.family_id] = family

    def add_subject(self, subject: CensusSubject) -> None:
        self._subjects[subject.subject_id] = subject

    def add_dataset(self, dataset: CensusCatalogDataset) -> None:
        self._datasets[dataset.dataset_id] = dataset

    # -- Lookup --

    def get_table(self, table_id: str) -> Optional[CensusTable]:
        return self._tables.get(table_id)

    def get_family(self, family_id: str) -> Optional[CensusFamily]:
        return self._families.get(family_id)

    def get_subject(self, subject_id: str) -> Optional[CensusSubject]:
        return self._subjects.get(subject_id)

    def get_dataset(self, dataset_id: str) -> Optional[CensusCatalogDataset]:
        return self._datasets.get(dataset_id)

    # -- Queries --

    @property
    def tables(self) -> dict[str, CensusTable]:
        return dict(self._tables)

    @property
    def families(self) -> dict[str, CensusFamily]:
        return dict(self._families)

    @property
    def subjects(self) -> dict[str, CensusSubject]:
        return dict(self._subjects)

    @property
    def datasets(self) -> dict[str, CensusCatalogDataset]:
        return dict(self._datasets)

    def tables_for_geography(self, geo_level: str) -> list[CensusTable]:
        return [
            t
            for t in self._tables.values()
            if geo_level in t.geography_levels
        ]

    def geography_for_table(self, table_id: str) -> list[str]:
        """Return the geography levels supported by *table_id*.

        Raises:
            KeyError: If *table_id* is not in the catalog.
        """
        table = self._tables.get(table_id)
        if table is None:
            raise KeyError(
                f"Table {table_id!r} not found in catalog; "
                f"use search() to discover valid table IDs"
            )
        return list(table.geography_levels)

    def families_for_table(self, table_id: str) -> list[CensusFamily]:
        return [
            f
            for f in self._families.values()
            if table_id in f.table_ids
        ]

    # -- Search --

    def search(
        self,
        query: str,
        level: Optional[SearchLevel] = None,
        dataset: Optional[str] = None,
        max_results: int = 25,
    ) -> list[SearchResult]:
        """Search the catalog across multiple levels.

        Args:
            query: Free-text search query.
            level: Restrict to a single search level, or None for all.
            dataset: Filter TABLE and VARIABLE results to tables belonging
                to this dataset. Has no effect on FAMILY, SUBJECT, or
                DATASET level results (those are cross-dataset).
            max_results: Maximum results to return.
        """
        tokens = _tokenize_query(query)
        if not tokens:
            return []

        dataset_table_ids: Optional[set[str]] = None
        if dataset:
            ds = self._datasets.get(dataset)
            if ds is not None:
                dataset_table_ids = set(ds.tables.keys())

        results: list[SearchResult] = []

        if level is None or level == SearchLevel.TABLE:
            for table in self._tables.values():
                if dataset_table_ids is not None and table.table_id not in dataset_table_ids:
                    continue
                score = _score_table(table, tokens)
                if score > 0:
                    results.append(SearchResult(
                        level=SearchLevel.TABLE,
                        id=table.table_id,
                        label=table.label or table.concept,
                        score=score,
                        obj=table,
                    ))

        if level is None or level == SearchLevel.FAMILY:
            for family in self._families.values():
                score = _score_family(family, tokens)
                if score > 0:
                    results.append(SearchResult(
                        level=SearchLevel.FAMILY,
                        id=family.family_id,
                        label=family.description,
                        score=score,
                        obj=family,
                    ))

        if level is None or level == SearchLevel.SUBJECT:
            for subject in self._subjects.values():
                score = _score_subject(subject, tokens)
                if score > 0:
                    results.append(SearchResult(
                        level=SearchLevel.SUBJECT,
                        id=subject.subject_id,
                        label=subject.label,
                        score=score,
                        obj=subject,
                    ))

        if level is None or level == SearchLevel.VARIABLE:
            for table in self._tables.values():
                if dataset_table_ids is not None and table.table_id not in dataset_table_ids:
                    continue
                for var in table.variables:
                    score = _score_variable(var, tokens)
                    if score > 0:
                        results.append(SearchResult(
                            level=SearchLevel.VARIABLE,
                            id=var.code,
                            label=var.label,
                            score=score,
                            obj=var,
                        ))

        if level is None or level == SearchLevel.DATASET:
            for ds in self._datasets.values():
                score = _score_dataset(ds, tokens)
                if score > 0:
                    results.append(SearchResult(
                        level=SearchLevel.DATASET,
                        id=ds.dataset_id,
                        label=f"{ds.survey_type} {ds.year}",
                        score=score,
                        obj=ds,
                    ))

        results.sort(key=lambda r: (-r.score, r.id))
        return results[:max_results]

    # -- Bulk operations --

    def build_families(self, max_topical_gap: int = 100) -> None:
        all_tables = list(self._tables.values())

        race_families = detect_race_iteration_families(all_tables)
        for f in race_families:
            self._families[f.family_id] = f

        topical_families = detect_topical_families(
            all_tables, max_number_gap=max_topical_gap
        )
        for f in topical_families:
            self._families[f.family_id] = f

        log.info(
            "Built %d race iteration families and %d topical families from %d tables",
            len(race_families),
            len(topical_families),
            len(all_tables),
        )

    def __len__(self) -> int:
        return len(self._tables)

    def __repr__(self) -> str:
        return (
            f"CensusCatalog("
            f"tables={len(self._tables)}, "
            f"families={len(self._families)}, "
            f"subjects={len(self._subjects)}, "
            f"datasets={len(self._datasets)})"
        )
