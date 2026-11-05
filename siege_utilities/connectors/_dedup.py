"""
Cross-CRM deduplication pipeline.

Composes ``identifiers/`` primitives (``normalize_name_v1``,
``uuid5_from_seed``) with CRM DataFrames to produce a merge table
of canonical IDs across CRM systems.

Match strategy: exact normalized name plus available strong identifiers.
A name match without a corroborating identifier is never merged; it is
exposed only as a review candidate through ``name_candidate_id``.
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


def _empty_result(source_system_column: str, source_id_column: str) -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "canonical_id", "normalized_name",
        source_system_column, source_id_column, "match_confidence",
        "name_candidate_id",
    ])


def _is_missing_key(value: Any) -> bool:
    return pd.isna(value) or (isinstance(value, str) and not value.strip())


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
            Missing columns and values are ignored. Pass ``[]`` to disable
            identifier matching; every record then stays a distinct entity
            and name matches appear only through ``name_candidate_id``.
        source_system_column: Column identifying the CRM source.
        source_id_column: Column with the record ID in the source CRM.
        normalizer: Name normalization function. Defaults to
            ``normalize_name_v1``.
        namespace: UUID namespace for deterministic ID generation.

    Returns:
        DataFrame with columns: ``canonical_id``, ``normalized_name``,
        ``source_system``, ``source_id``, ``match_confidence``,
        ``name_candidate_id``.

        ``canonical_id`` is the merge key. Records share it only when the
        normalized name and every available strong identifier agree, or
        when they are rows for the same source record. A
        record without a corroborating identifier gets a canonical ID seeded
        from its own source record (``source_system`` and ``source_id``), so
        namesakes are never merged by name alone. If either source key is
        null or blank, the seed uses the frame position and row position
        instead, which is deterministic only for identical input.

        ``name_candidate_id`` is the v1 name-only ID
        (``uuid5_from_seed(namespace, normalized_name)``). It is a review
        key, not a merge key. Rows that share it but differ in
        ``canonical_id`` are candidate pairs for human review. It also
        joins merge tables persisted by earlier versions, whose name-only
        ``canonical_id`` values equal it.

        ``match_confidence`` is 1.0 when the seed includes a strong
        identifier. Without one it rates the name candidate: 0.5 when all
        configured name parts are present and 0.25 when any name part is
        missing (such as surname-only rows). These values are not
        calibrated probabilities.
        Frames missing either required source column and rows with no
        non-empty normalized name are skipped. Null name parts are ignored.
    """
    if not dataframes:
        return _empty_result(source_system_column, source_id_column)

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

        for row_pos, (_, row) in enumerate(df.iterrows()):
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
            if identifiers:
                seed = json.dumps([normalized, identifiers], sort_keys=True)
                match_confidence = 1.0
            else:
                # A name alone never merges records: seed from the source
                # record so namesakes stay distinct entities.
                source_key = [row[source_system_column], row[source_id_column]]
                if any(_is_missing_key(value) for value in source_key):
                    # Row position, not the index label: labels repeat after concat.
                    seed = json.dumps(["unidentified_record", df_idx, row_pos])
                else:
                    seed = json.dumps(["source_record", *map(str, source_key)])
                # Partial names are weaker candidates than complete names.
                match_confidence = 0.5 if len(parts) == len(name_cols) else 0.25

            all_rows.append({
                "canonical_id": str(uuid5_from_seed(namespace, seed)),
                "normalized_name": normalized,
                source_system_column: row[source_system_column],
                source_id_column: row[source_id_column],
                "match_confidence": match_confidence,
                "name_candidate_id": str(uuid5_from_seed(namespace, normalized)),
            })

    result = pd.DataFrame(all_rows)
    if result.empty:
        return _empty_result(source_system_column, source_id_column)

    corroborated = result[result["match_confidence"].eq(1.0)]
    dup_count = corroborated.duplicated(subset=["canonical_id"], keep=False).sum()
    unique_count = result["canonical_id"].nunique()
    review_groups = (result.groupby("name_candidate_id")["canonical_id"].nunique() > 1).sum()
    log.info(
        "Dedup pipeline: %d records → %d canonical IDs (%d records in identifier-corroborated "
        "matches, %d name candidate groups left unmerged for review)",
        len(result), unique_count, dup_count, review_groups,
    )

    return result.sort_values(["canonical_id", source_system_column]).reset_index(drop=True)
