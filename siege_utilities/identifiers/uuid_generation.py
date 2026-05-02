"""
Generic UUID5 generators — domain-agnostic.

Callers supply the namespace (derived via ``namespaces.derive_root`` /
``derive_sub_namespace`` and hardcoded in their own code) plus the seed.
This module knows nothing about Persons, Committees, Attestations as
domain concepts — it provides the deterministic generator only.

For entities that are **resolved artifacts** (not pre-existing-identity
entities with stable external IDs), callers should use ``uuid.uuid4()``
directly, not these helpers.
"""

from uuid import UUID, uuid5


def _esc_colon(s: str) -> str:
    # Escape ':' as '::' so the ':' delimiter in attestation seeds is unambiguous.
    return s.replace(":", "::")


def uuid5_from_seed(namespace: UUID, seed: str) -> UUID:
    """
    Generate a deterministic UUID5 under a given namespace.

    Args:
        namespace: A namespace UUID (typically a per-entity-type sub-namespace).
        seed: Non-empty string — the canonical identifier input. Consumers are
            responsible for seed-ladder logic (picking the best available
            identifier at resolution time).

    Returns:
        The UUID5 derived from ``namespace`` and ``seed``.

    Raises:
        ValueError: if ``seed`` is empty.
    """
    if not seed:
        raise ValueError("UUID5 seed must be non-empty")
    return uuid5(namespace, seed)


def attestation_uuid(
    *,
    namespace: UUID,
    source_artifact_hash: str,
    record_line: int,
    parser_version: str,
    values_hash: str,
) -> UUID:
    """
    Generate a parser-version-aware attestation UUID.

    Re-processing the same source line with the same parser version
    produces the same UUID (write-path idempotency). Bumping the parser
    version produces a new UUID, so the re-parse is correctly treated
    as a new attestation rather than silently clobbering the old one.

    This helper is deliberately generic about what an "attestation" is —
    it just requires a namespace and four stable inputs. Consumers with
    different attestation structures (e.g., different record identifiers
    like a byte offset instead of a line number) are free to build their
    own seed and call :func:`uuid5_from_seed` directly.

    Args:
        namespace: The consumer's attestation namespace UUID.
        source_artifact_hash: Stable hash of the source artifact
            (e.g., the file the record came from).
        record_line: The record's identifier within the artifact
            (line number, row index, etc.).
        parser_version: Identifier of the parser version that produced
            the attested values.
        values_hash: Hash of the attested values for integrity.

    Returns:
        A deterministic UUID5 combining the inputs.

    Raises:
        ValueError: if any of the non-int inputs is empty.
    """
    if not source_artifact_hash:
        raise ValueError("source_artifact_hash is required")
    if not parser_version:
        raise ValueError("parser_version is required")
    if not values_hash:
        raise ValueError("values_hash is required")
    seed = ":".join([
        _esc_colon(source_artifact_hash),
        str(record_line),
        _esc_colon(parser_version),
        _esc_colon(values_hash),
    ])
    return uuid5_from_seed(namespace, seed)
