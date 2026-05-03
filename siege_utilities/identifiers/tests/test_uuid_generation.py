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
    _RS,
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


def test_uuid5_from_seed_rejects_whitespace_only_seed():
    with pytest.raises(ValueError, match="seed"):
        uuid5_from_seed(THING_NS, "   ")
    with pytest.raises(ValueError, match="seed"):
        uuid5_from_seed(THING_NS, "\t\n")


def test_attestation_uuid_rejects_whitespace_only_inputs():
    cases = [
        ("   ", "v1", "h", "source_artifact_hash"),
        ("a", "   ", "h", "parser_version"),
        ("a", "v1", "   ", "values_hash"),
    ]
    for bad_artifact, bad_parser, bad_values, field in cases:
        with pytest.raises(ValueError, match=field):
            attestation_uuid(
                namespace=ATTESTATION_NS,
                source_artifact_hash=bad_artifact,
                record_line=1,
                parser_version=bad_parser,
                values_hash=bad_values,
            )


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
    """Attestation helper composes a deterministic RS-delimited seed."""
    expected = uuid5_from_seed(
        ATTESTATION_NS,
        _RS.join(["abc123", "42", "parser-v1.0.0", "deadbeef"]),
    )
    actual = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc123",
        record_line=42,
        parser_version="parser-v1.0.0",
        values_hash="deadbeef",
    )
    assert actual == expected


def test_attestation_uuid_colon_delimiter_no_collision():
    """':' anywhere in component values does not cause UUID collisions.

    The RS (0x1E) delimiter cannot appear in hash strings or version tags,
    so component boundaries are always unambiguous regardless of content.
    """
    uuid_a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1.0:patched",
        values_hash="xyz",
    )
    uuid_b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="v1.0",
        values_hash="patched:xyz",
    )
    assert uuid_a != uuid_b


def test_attestation_uuid_colon_boundary_no_collision():
    """Component-boundary collision: trailing ':' in one component + leading ':' in next.

    Old '::'-escaping scheme: 'p:' escaped to 'p::' then joined with ':' produces
    'p:::q' for both (parser='p:', values='q') and (parser='p', values=':q').
    RS delimiter has no such boundary ambiguity.
    """
    uuid_a = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="p:",   # trailing colon
        values_hash="q",
    )
    uuid_b = attestation_uuid(
        namespace=ATTESTATION_NS,
        source_artifact_hash="abc",
        record_line=1,
        parser_version="p",
        values_hash=":q",      # leading colon
    )
    assert uuid_a != uuid_b
