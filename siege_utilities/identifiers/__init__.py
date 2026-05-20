"""
Deterministic identifier generation — UUID5 namespaces, name normalization,
and attestation UUID helpers.

This module is deliberately **generic**. It knows nothing about Persons,
Committees, Organizations, elect.info, FEC, or any domain concept.
Consumers declare their own root seed and per-entity-type sub-namespaces
using the factory helpers here.

Typical usage from a consumer project::

    from siege_utilities.identifiers import (
        derive_root,
        derive_sub_namespace,
        uuid5_from_seed,
        normalize_name_v1,
        attestation_uuid,
    )

    # consumer constants (declared once, hardcoded after first derivation):
    ROOT = derive_root("mydomain.example.com")
    PERSON_NS = derive_sub_namespace(ROOT, "person")

    # generate a deterministic person UUID from a canonical seed:
    pid = uuid5_from_seed(PERSON_NS, "FEC_CAND:H4VA07136")

    # derive the attestation sub-namespace (like any other sub-namespace):
    ATTESTATION_NS = derive_sub_namespace(ROOT, "attestation")

    # generate an idempotent attestation UUID:
    aid = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v1.0.0",
        values_hash="deadbeef",
    )
"""

from siege_utilities.identifiers.namespaces import (
    derive_root,
    derive_sub_namespace,
)
from siege_utilities.identifiers.normalize import (
    NORMALIZER_VERSIONS,
    normalize_name_v1,
)
from siege_utilities.identifiers.uuid_generation import (
    attestation_uuid,
    uuid5_from_seed,
)

__all__ = [
    "NORMALIZER_VERSIONS",
    "attestation_uuid",
    "derive_root",
    "derive_sub_namespace",
    "normalize_name_v1",
    "uuid5_from_seed",
]
