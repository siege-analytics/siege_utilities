"""
UUID5 generator tests — determinism, parser-version idempotency, error cases.
"""

from uuid import uuid5

import pytest

from siege_utilities.identifiers.namespaces import (
    derive_root,
    derive_sub_namespace,
)
from siege_utilities.identifiers.uuid_generation import (
    attestation_uuid,
    uuid5_from_seed,
)


ROOT = derive_root("test.example.com")
THING_NS = derive_sub_namespace(ROOT, "thing")
OTHER_NS = derive_sub_namespace(ROOT, "other")
ATTESTATION_NS = derive_sub_namespace(ROOT, "attestation")


def test_uuid5_from_seed_is_deterministic():
    a = uuid5_from_seed(THING_NS, "seed:value")
    b = uuid5_from_seed(THING_NS, "seed:value")
    assert a == b


def test_uuid5_from_seed_matches_stdlib():
    assert uuid5_from_seed(THING_NS, "seed") == uuid5(THING_NS, "seed")


def test_uuid5_differs_by_namespace():
    """Different per-type namespaces prevent collisions when seeds collide."""
    assert uuid5_from_seed(THING_NS, "X:1") != uuid5_from_seed(OTHER_NS, "X:1")


def test_uuid5_differs_by_seed():
    assert uuid5_from_seed(THING_NS, "a") != uuid5_from_seed(THING_NS, "b")


def test_uuid5_from_seed_rejects_empty_seed():
    with pytest.raises(ValueError, match="seed"):
        uuid5_from_seed(THING_NS, "")


def test_attestation_uuid_is_idempotent_same_parser():
    a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v1.0.0",
        values_hash="deadbeef",
    )
    b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v1.0.0",
        values_hash="deadbeef",
    )
    assert a == b


def test_attestation_uuid_differs_on_parser_version_bump():
    a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v1.0.0",
        values_hash="deadbeef",
    )
    b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v2.0.0",
        values_hash="deadbeef",
    )
    assert a != b


def test_attestation_uuid_differs_on_values_hash_change():
    a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1",
        values_hash="deadbeef",
    )
    b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1",
        values_hash="cafecafe",
    )
    assert a != b


def test_attestation_uuid_differs_on_record_line():
    a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1",
        values_hash="h",
    )
    b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=2,
        parser_version="v1",
        values_hash="h",
    )
    assert a != b


def test_attestation_uuid_requires_artifact_hash():
    with pytest.raises(ValueError, match="source_artifact_hash"):
        attestation_uuid(
            namespace=ATTESTATION_NS,
            source_artifact_hash="",
            record_line=1,
            parser_version="v",
            values_hash="h",
        )


def test_attestation_uuid_requires_parser_version():
    with pytest.raises(ValueError, match="parser_version"):
        attestation_uuid(
            namespace=ATTESTATION_NS,
            source_artifact_hash="a",
            record_line=1,
            parser_version="",
            values_hash="h",
        )


def test_attestation_uuid_requires_values_hash():
    with pytest.raises(ValueError, match="values_hash"):
        attestation_uuid(
            namespace=ATTESTATION_NS,
            source_artifact_hash="a",
            record_line=1,
            parser_version="v",
            values_hash="",
        )


def test_attestation_uuid_uses_supplied_namespace():
    """Attestation helper composes a deterministic seed and uses the caller's namespace."""
    expected = uuid5_from_seed(
        ATTESTATION_NS,
        "abc123:42:parser-v1.0.0:deadbeef",
    )
    actual = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v1.0.0",
        values_hash="deadbeef",
    )
    assert actual == expected


def test_attestation_uuid_colon_delimiter_collision():
    """Document known limitation: ':' in component values can cause UUID collisions.

    The current seed format ``f"{artifact}:{line}:{parser}:{values}"`` is
    ambiguous when any component contains the ':' separator. These two
    distinct attestations produce the same seed and therefore the same UUID.

    Fix pending Dheeraj's decision (Item 1 in CodeRabbit review #381):
    length-prefix, null-byte delimiter, or ':' escaping.
    """
    uuid_a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1.0:patched",  # contains ':'
        values_hash="xyz",
    )
    uuid_b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1.0",
        values_hash="patched:xyz",  # ':' shifted to next component
    )
    # Both produce seed "abc:1:v1.0:patched:xyz" — collision documents the bug.
    assert uuid_a == uuid_b
