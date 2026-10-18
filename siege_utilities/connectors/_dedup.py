"""
Cross-CRM deduplication pipeline.

Composes ``identifiers/`` primitives (``normalize_name_v1``,
``uuid5_from_seed``) with CRM DataFrames to produce a merge table
of canonical IDs across CRM systems.

Match strategy: exact normalized name plus available strong identifiers,
with lower-confidence name-only matching when identifiers are absent.
Fuzzy matching is future work — the ``normalizer`` parameter allows
swapping the normalization function when a v2 ships.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable
from uuid import UUID

import pandas as pd

from siege_utilities.identifiers.normalize import normalize_name_v1
from siege_utilities.identifiers.uuid_generation import uuid5_from_seed

log = logging.getLogger(__name__)

CRM_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
_NULL_IDENTIFIER_TOKENS = {"nan", "none", "null", "<na>", "nat"}

__all__ = ["crm_dedup_pipeline"]


def crm_dedup_pipeline(
    dataframes: list[pd.DataFrame],
    *,
    name_columns: list[str] | None = None,
    identifier_columns: list[str] | None = None,
    source_system_column: str = "source_system",
    source_id_column: str = "source_id",
    normalizer: Callable[[str], str] = normalize_name_v1,
    namespace: UUID = CRM_NAMESPACE,
) -> pd.DataFrame:
    """Deduplicate contacts across CRM systems.

    Accepts a list of DataFrames (each with ``source_system`` and
    ``source_id`` columns) and produces a merge table with canonical IDs.

    Name normalization handles "First Last" format. "Last, First" format
    is NOT automatically detected — callers should pre-process if their
    data uses that convention.

    Args:
        dataframes: CRM DataFrames to deduplicate.
        name_columns: Columns to concatenate for the name seed. Defaults
            to ``["first_name", "last_name"]``.
        identifier_columns: Strong identifier columns to include in the
            seed alongside the normalized name. Defaults to ``["email"]``.
            Non-null, non-blank values are stripped and lowercased. Whole
            tokens ``nan``, ``none``, ``null``, ``<na>`` and ``nat`` are
            ignored after stripping and casefolding. All available
            column/value pairs must match; column order does not matter.
            Missing columns and values are ignored. Pass ``[]`` to use
            name-only matching explicitly.
        source_system_column: Column identifying the CRM source.
        source_id_column: Column with the record ID in the source CRM.
        normalizer: Name normalization function. Defaults to
            ``normalize_name_v1``.
        namespace: UUID namespace for deterministic ID generation.

    Returns:
        DataFrame with columns: ``canonical_id``, ``normalized_name``,
        ``source_system``, ``source_id``, ``match_confidence``.

        ``match_confidence`` is 1.0 when the seed includes a strong
        identifier, otherwise 0.5 when all configured name parts are present
        and 0.25 when any name part is missing. Partial names without an
        identifier (such as surname-only rows) still group by name but are
        weaker candidates than full names. These values are not calibrated
        probabilities. Name-only seeds retain their v1 canonical IDs;
        identifier-aware seeds produce different IDs.
        Frames missing either required source column and rows with no
        non-empty normalized name are skipped. Null name parts are ignored.
    """
    if not dataframes:
        return pd.DataFrame(columns=[
            "canonical_id", "normalized_name",
            source_system_column, source_id_column, "match_confidence",
        ])

    name_cols = name_columns or ["first_name", "last_name"]
    identifier_cols = ["email"] if identifier_columns is None else identifier_columns
    all_rows: list[dict[str, Any]] = []

    for df_idx, df in enumerate(dataframes):
        if df.empty:
            continue

        missing = [
            col for col in (source_system_column, source_id_column)
            if col not in df.columns
        ]
        if missing:
            log.warning("DataFrame %d missing columns %s, skipping", df_idx, missing)
            continue

        for _, row in df.iterrows():
            parts = []
            for col in name_cols:
                val = row.get(col)
                if pd.notna(val) and str(val).strip():
                    parts.append(str(val).strip())

            if not parts:
                continue

            raw_name = " ".join(parts)
            normalized = normalizer(raw_name)
            if not normalized:
                continue

            identifiers = {}
            for col in identifier_cols:
                val = row.get(col)
                if pd.notna(val):
                    identifier = str(val).strip()
                    if identifier and identifier.casefold() not in _NULL_IDENTIFIER_TOKENS:
                        identifiers[col] = identifier.lower()

            # Structured seeds distinguish identifier types and prevent
            # delimiter collisions; sort keys for stable column ordering.
            seed = json.dumps([normalized, identifiers], sort_keys=True) if identifiers else normalized
            canonical_id = str(uuid5_from_seed(namespace, seed))
            # Partial names are weaker evidence than complete names.
            # Reserve 1.0 for matches corroborated by a strong identifier.
            if identifiers:
                match_confidence = 1.0
            else:
                match_confidence = 0.5 if len(parts) == len(name_cols) else 0.25

            all_rows.append({
                "canonical_id": canonical_id,
                "normalized_name": normalized,
                source_system_column: row[source_system_column],
                source_id_column: row[source_id_column],
                "match_confidence": match_confidence,
            })

    result = pd.DataFrame(all_rows)
    if result.empty:
        return pd.DataFrame(columns=[
            "canonical_id", "normalized_name",
            source_system_column, source_id_column, "match_confidence",
        ])

    dup_count = result.duplicated(subset=["canonical_id"], keep=False).sum()
    unique_count = result["canonical_id"].nunique()
    log.info(
        "Dedup pipeline: %d records → %d canonical IDs (%d cross-system matches)",
        len(result), unique_count, dup_count,
    )

    return result.sort_values(["canonical_id", source_system_column]).reset_index(drop=True)
