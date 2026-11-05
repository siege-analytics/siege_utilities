"""
Cross-CRM deduplication pipeline.

Composes ``identifiers/`` primitives (``normalize_name_v1``,
``uuid5_from_seed``) with CRM DataFrames to produce a merge table
of canonical IDs across CRM systems.

Match strategy: exact normalized name plus at least one equal strong
identifier (email, normalized phone or normalized address), chained
transitively, with conflicting identifier values refusing a merge. A name
match without a corroborating identifier is never merged; it is exposed only
as a review candidate through ``name_candidate_id``.
Fuzzy matching is future work — the ``normalizer`` parameter allows
swapping the normalization function when a v2 ships.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Mapping
from uuid import UUID

import pandas as pd

from siege_utilities.identifiers.normalize import (
    normalize_address_v1,
    normalize_name_v1,
    normalize_phone_v1,
)
from siege_utilities.identifiers.uuid_generation import uuid5_from_seed

log = logging.getLogger(__name__)

CRM_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
_NULL_IDENTIFIER_TOKENS = {"nan", "none", "null", "<na>", "nat"}
_DEFAULT_IDENTIFIER_COLUMNS = ["email", "phone"]
_DEFAULT_IDENTIFIER_NORMALIZERS: dict[str, Callable[[str], str]] = {"phone": normalize_phone_v1}
# CRMContact.to_dataframe flattens CRMAddress fields with an ``address_`` prefix.
_DEFAULT_ADDRESS_COLUMNS = ["address_street", "address_city", "address_state", "address_postal_code"]
_ADDRESS_KEY = "address"

__all__ = ["crm_dedup_pipeline"]


def _empty_result(source_system_column: str, source_id_column: str) -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "canonical_id", "normalized_name",
        source_system_column, source_id_column, "match_confidence",
        "name_candidate_id",
    ])


def _is_missing_key(value: Any) -> bool:
    return pd.isna(value) or (isinstance(value, str) and not value.strip())


def _identifier_text(value: Any) -> str:
    """Return stripped text for an identifier cell, or "" when it is missing."""
    if not pd.api.types.is_scalar(value) or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        # Numeric phone or ZIP columns upcast to float when they hold nulls.
        value = int(value)
    text = str(value).strip()
    return "" if text.casefold() in _NULL_IDENTIFIER_TOKENS else text


def _group_corroborated(records: list[dict[str, Any]]) -> tuple[dict[int, str], int]:
    """Union records that share a name and one identifier, refusing conflicts.

    Returns the winning seed per record index and the number of refused links.
    Keys and members are visited in sorted order so the result does not depend
    on row order.
    """
    parent: dict[int, int] = {}
    values: dict[int, dict[str, str]] = {}
    members_by_key: dict[tuple[str, str, str], list[int]] = {}
    for index, record in enumerate(records):
        if not record["identifiers"]:
            continue
        parent[index] = index
        values[index] = dict(record["identifiers"])
        for column, value in record["identifiers"].items():
            members_by_key.setdefault((record["normalized"], column, value), []).append(index)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    refused = 0
    for key in sorted(members_by_key):
        members = sorted(members_by_key[key], key=lambda i: records[i]["order_key"])
        # Try every earlier member, so one conflicting member cannot keep two
        # compatible members apart.
        for position, member in enumerate(members[1:], start=1):
            for earlier in members[:position]:
                root, other = find(earlier), find(member)
                if root == other:
                    continue
                mine, theirs = values[root], values[other]
                if any(column in mine and mine[column] != value for column, value in theirs.items()):
                    # Conflicting evidence (for example two different emails)
                    # means distinct people, even when another key is shared.
                    refused += 1
                    continue
                parent[other] = root
                mine.update(theirs)

    smallest_seed: dict[int, str] = {}
    for index in parent:
        root, seed = find(index), records[index]["seed"]
        smallest_seed[root] = min(smallest_seed.get(root, seed), seed)
    return {index: smallest_seed[find(index)] for index in parent}, refused


def crm_dedup_pipeline(
    dataframes: list[pd.DataFrame],
    *,
    name_columns: list[str] | None = None,
    identifier_columns: list[str] | None = None,
    identifier_normalizers: Mapping[str, Callable[[str], str]] | None = None,
    address_columns: list[str] | None = None,
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
        identifier_columns: Strong identifier columns that can corroborate a
            name match. Defaults to ``["email", "phone"]``. Non-null,
            non-blank values are stripped and normalized: through
            ``identifier_normalizers`` when the column has an entry, otherwise
            lowercased. Whole tokens ``nan``, ``none``, ``null``, ``<na>`` and
            ``nat`` are ignored after stripping and casefolding. Missing
            columns and values are ignored.
        identifier_normalizers: Per-column normalizers for
            ``identifier_columns``, added to the default
            ``{"phone": normalize_phone_v1}`` (an entry for ``phone`` replaces
            it). A normalizer returning ``""`` means no identifier. Values
            must be callable, else ``ValueError``.
        address_columns: Up to four columns, in order street, city, state and
            postal code, combined into one ``address`` identifier via
            ``normalize_address_v1``. Defaults to ``["address_street",
            "address_city", "address_state", "address_postal_code"]``
            (``CRMContact.to_dataframe`` names). An empty street yields no
            address; city, state or ZIP alone is never identity evidence.
            More than four columns raises ``ValueError``. Pass ``[]`` for both
            ``identifier_columns`` and ``address_columns`` to disable
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

        ``canonical_id`` is the merge key. Records with identifiers are
        linked when their normalized names are equal and at least one
        identifier value is equal, and links chain transitively (a shares an
        email with b, b shares a phone with c). A link is refused when the
        two groups hold different values for any identifier column (for
        example two different emails), because conflicting evidence means
        distinct people; refused links are logged and the records stay
        separate, sharing only ``name_candidate_id``. Each group's
        ``canonical_id`` comes from the smallest member seed
        (``json([normalized_name, identifiers])``), so it does not depend on
        row order. It can change between runs when a new record with a
        smaller seed joins a group, so regenerate persisted merge tables
        rather than appending to them.

        Residual risk: two distinct people with the same normalized name
        who share one identifier (for example a parent and child recorded
        without a suffix, sharing a household email, phone or address) and
        hold no conflicting identifier will merge. This is the same evidence
        standard as name plus an equal email; the name guard and conflict
        guard stop it from spreading to anyone with a different name or
        conflicting evidence. Because the conflict guard covers every
        identifier column, the same person recorded with a different phone,
        or with a fuller or partial address, in another CRM is split rather
        than merged, and surfaces for review through ``name_candidate_id``.

        A record without a corroborating identifier gets a canonical ID seeded
        from its own source record (``source_system`` and ``source_id``), so
        namesakes are never merged by name alone. If either source key is
        null or blank, the seed uses the frame position and row position
        instead, which is deterministic only for identical input.

        ``name_candidate_id`` is the v1 name-only ID
        (``uuid5_from_seed(namespace, normalized_name)``). It is a review
        key, not a merge key. Rows that share it but differ in
        ``canonical_id`` are review candidates (every pair within the group
        is a candidate pair) with confidence below 1.0 unless identifier
        evidence exists. It also
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
    identifier_cols = list(_DEFAULT_IDENTIFIER_COLUMNS if identifier_columns is None else identifier_columns)
    normalizers = {**_DEFAULT_IDENTIFIER_NORMALIZERS, **(identifier_normalizers or {})}
    not_callable = sorted(col for col, fn in normalizers.items() if not callable(fn))
    if not_callable:
        raise ValueError(f"identifier_normalizers values must be callable: {not_callable}")
    address_cols = list(_DEFAULT_ADDRESS_COLUMNS if address_columns is None else address_columns)
    if len(address_cols) > 4:
        raise ValueError(
            "address_columns takes at most 4 columns in order: street, city, state, postal code"
        )
    if address_cols and _ADDRESS_KEY in identifier_cols:
        raise ValueError(
            f"identifier_columns contains {_ADDRESS_KEY!r}, which collides with the composite "
            "address identifier; rename the column or pass address_columns=[]"
        )
    records: list[dict[str, Any]] = []

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
                text = _identifier_text(row.get(col))
                if text:
                    value = normalizers[col](text) if col in normalizers else text.lower()
                    if value:
                        identifiers[col] = value
            if address_cols:
                # Positional: street, city, state, postal code. An empty street
                # yields no address, since city, state or ZIP alone is shared
                # by too many people to be identity evidence.
                address = normalize_address_v1(*(_identifier_text(row.get(col)) for col in address_cols))
                if address:
                    identifiers[_ADDRESS_KEY] = address

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

            records.append({
                "normalized": normalized,
                "identifiers": identifiers,
                "seed": seed,
                "order_key": (seed, str(row[source_system_column]), str(row[source_id_column])),
                "source_system": row[source_system_column],
                "source_id": row[source_id_column],
                "match_confidence": match_confidence,
            })

    if not records:
        return _empty_result(source_system_column, source_id_column)

    group_seed, refused = _group_corroborated(records)
    if refused:
        log.warning(
            "%d identifier links not merged because identifiers conflict; "
            "review them through name_candidate_id",
            refused,
        )
    result = pd.DataFrame([
        {
            "canonical_id": str(uuid5_from_seed(namespace, group_seed.get(index, record["seed"]))),
            "normalized_name": record["normalized"],
            source_system_column: record["source_system"],
            source_id_column: record["source_id"],
            "match_confidence": record["match_confidence"],
            "name_candidate_id": str(uuid5_from_seed(namespace, record["normalized"])),
        }
        for index, record in enumerate(records)
    ])

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
