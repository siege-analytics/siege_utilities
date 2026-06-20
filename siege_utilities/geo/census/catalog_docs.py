"""
Census catalog documentation generator.

Produces Markdown documentation from a CensusCatalog instance:
- Index page with Subject → Family → Table tree
- Per-table pages with variable list, geography availability, dataset membership
"""

from __future__ import annotations

import logging
from pathlib import Path

from .catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusTable,
    FamilyType,
)

__all__ = [
    'generate_catalog_docs',
    'generate_catalog_markdown',
]

log = logging.getLogger(__name__)


def generate_catalog_docs(
    catalog: CensusCatalog,
    output_dir: Path,
    title: str = "Census Table Catalog",
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    index_path = output_dir / "index.md"
    index_path.write_text(
        _render_index(catalog, title), encoding="utf-8"
    )
    written.append(index_path)

    for table in sorted(catalog.tables.values(), key=lambda t: t.table_id):
        families = catalog.families_for_table(table.table_id)
        datasets = _datasets_for_table(catalog, table.table_id)
        page_path = output_dir / "tables" / f"{table.table_id}.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            _render_table_page(table, families, datasets), encoding="utf-8"
        )
        written.append(page_path)

    log.info(
        "Generated %d doc pages in %s", len(written), output_dir
    )
    return written


def generate_catalog_markdown(
    catalog: CensusCatalog,
    title: str = "Census Table Catalog",
) -> str:
    return _render_index(catalog, title)


def _render_index(catalog: CensusCatalog, title: str) -> str:
    lines = [f"# {title}", ""]

    subjects = sorted(catalog.subjects.values(), key=lambda s: s.subject_id)
    if subjects:
        lines.append("## Subjects")
        lines.append("")
        for subject in subjects:
            lines.append(f"### {subject.label}")
            lines.append("")
            if subject.tables:
                for table in sorted(subject.tables, key=lambda t: t.table_id):
                    lines.append(
                        f"- [{table.table_id}](tables/{table.table_id}.md)"
                        f" — {table.concept or table.label}"
                    )
                lines.append("")

    families = sorted(catalog.families.values(), key=lambda f: f.family_id)
    race_families = [f for f in families if f.family_type == FamilyType.RACE_ITERATION]
    topical_families = [f for f in families if f.family_type == FamilyType.TOPICAL_KINSHIP]

    if race_families:
        lines.append("## Race Iteration Families")
        lines.append("")
        for fam in race_families:
            lines.append(f"### {fam.root_table_id}")
            lines.append("")
            lines.append(f"{fam.description}")
            lines.append("")
            for table in fam.tables:
                lines.append(
                    f"- [{table.table_id}](tables/{table.table_id}.md)"
                    f" — {table.concept or table.label}"
                )
            lines.append("")

    if topical_families:
        lines.append("## Topical Families")
        lines.append("")
        for fam in topical_families:
            lines.append(f"### {fam.root_table_id}")
            lines.append("")
            lines.append(f"{fam.description}")
            lines.append("")
            for table in fam.tables:
                lines.append(
                    f"- [{table.table_id}](tables/{table.table_id}.md)"
                    f" — {table.concept or table.label}"
                )
            lines.append("")

    orphan_tables = _orphan_tables(catalog)
    if orphan_tables:
        lines.append("## Other Tables")
        lines.append("")
        for table in sorted(orphan_tables, key=lambda t: t.table_id):
            lines.append(
                f"- [{table.table_id}](tables/{table.table_id}.md)"
                f" — {table.concept or table.label}"
            )
        lines.append("")

    datasets = sorted(catalog.datasets.values(), key=lambda d: d.dataset_id)
    if datasets:
        lines.append("## Datasets")
        lines.append("")
        for ds in datasets:
            lines.append(f"- **{ds.dataset_id}**: {ds.survey_type} ({ds.year})")
        lines.append("")

    return "\n".join(lines)


def _render_table_page(
    table: CensusTable,
    families: list[CensusFamily],
    datasets: list[CensusCatalogDataset],
) -> str:
    lines = [f"# {table.table_id}", ""]

    if table.concept:
        lines.append(f"**Concept:** {table.concept}")
        lines.append("")
    if table.universe:
        lines.append(f"**Universe:** {table.universe}")
        lines.append("")

    if table.geography_levels:
        lines.append("## Geography Levels")
        lines.append("")
        for geo in table.geography_levels:
            lines.append(f"- {geo}")
        lines.append("")

    if table.variables:
        lines.append("## Variables")
        lines.append("")
        lines.append("| Code | Label |")
        lines.append("|------|-------|")
        for var in table.variables:
            label = var.label.replace("|", "\\|")
            lines.append(f"| `{var.code}` | {label} |")
        lines.append("")

    if families:
        lines.append("## Family Membership")
        lines.append("")
        for fam in families:
            ftype = "Race Iteration" if fam.family_type == FamilyType.RACE_ITERATION else "Topical Kinship"
            lines.append(f"- **{fam.family_id}** ({ftype}): {fam.description}")
        lines.append("")

    if datasets:
        lines.append("## Datasets")
        lines.append("")
        for ds in datasets:
            lines.append(f"- {ds.dataset_id} ({ds.survey_type}, {ds.year})")
        lines.append("")

    lines.append("[← Back to index](../index.md)")
    lines.append("")

    return "\n".join(lines)


def _datasets_for_table(
    catalog: CensusCatalog, table_id: str
) -> list[CensusCatalogDataset]:
    return [
        ds
        for ds in catalog.datasets.values()
        if table_id in ds.tables
    ]


def _orphan_tables(catalog: CensusCatalog) -> list[CensusTable]:
    covered: set[str] = set()
    for subject in catalog.subjects.values():
        for table in subject.tables:
            covered.add(table.table_id)
    for family in catalog.families.values():
        for table in family.tables:
            covered.add(table.table_id)
    return [
        t for t in catalog.tables.values()
        if t.table_id not in covered
    ]
