"""
Cross-CRM deduplication pipeline.

Composes ``identifiers/`` primitives (``normalize_name_v1``,
``uuid5_from_seed``) with CRM DataFrames to produce a merge table
of canonical IDs across CRM systems.

Match strategy v1: exact normalized name match. Fuzzy matching is
future work — the ``normalizer`` parameter allows swapping the
normalization function when a v2 ships.
"""

from __future__ import annotations

import logging
from typing import Any, Callable
from uuid import UUID

import pandas as pd

from siege_utilities.identifiers.normalize import normalize_name_v1
from siege_utilities.identifiers.uuid_generation import uuid5_from_seed

log = logging.getLogger(__name__)

CRM_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

__all__ = ["crm_dedup_pipeline"]


def crm_dedup_pipeline(
    dataframes: list[pd.DataFrame],
    *,
    name_columns: list[str] | None = None,
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
        source_system_column: Column identifying the CRM source.
        source_id_column: Column with the record ID in the source CRM.
        normalizer: Name normalization function. Defaults to
            ``normalize_name_v1``.
        namespace: UUID namespace for deterministic ID generation.

    Returns:
        DataFrame with columns: ``canonical_id``, ``normalized_name``,
        ``source_system``, ``source_id``, ``match_confidence``.

        ``match_confidence`` is 1.0 for exact normalized matches (v1).
    """
    if not dataframes:
        return pd.DataFrame(columns=[
            "canonical_id", "normalized_name",
            source_system_column, source_id_column, "match_confidence",
        ])

    name_cols = name_columns or ["first_name", "last_name"]
    all_rows: list[dict[str, Any]] = []

    for df_idx, df in enumerate(dataframes):
        if df.empty:
            continue

        for col in [source_system_column, source_id_column]:
            if col not in df.columns:
                log.warning(
                    "DataFrame %d missing column '%s', skipping",
                    df_idx, col,
                )
                continue

        for _, row in df.iterrows():
            parts = []
            for col in name_cols:
                val = row.get(col)
                if val and str(val).strip():
                    parts.append(str(val).strip())

            if not parts:
                continue

            raw_name = " ".join(parts)
            normalized = normalizer(raw_name)
            if not normalized:
                continue

            canonical_id = str(uuid5_from_seed(namespace, normalized))

            all_rows.append({
                "canonical_id": canonical_id,
                "normalized_name": normalized,
                source_system_column: row.get(source_system_column, "unknown"),
                source_id_column: row.get(source_id_column, ""),
                "match_confidence": 1.0,
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
