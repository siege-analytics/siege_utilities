"""Error-path coverage (SU-4b) for siege_utilities.identifiers.uuid_generation.

Forces the ValueError guards on empty/whitespace seeds, missing attestation
components, and the RS-delimiter (\\x1e) collision guard.
"""

from uuid import NAMESPACE_URL

import pytest

from siege_utilities.identifiers.uuid_generation import (
    attestation_uuid,
    uuid5_from_seed,
)

_RS = "\x1e"

_VALID = dict(
    namespace=NAMESPACE_URL,
    source_artifact_hash="abc123",
    record_line=1,
    parser_version="v1",
    values_hash="def456",
)


@pytest.mark.parametrize("bad_seed", ["", "   ", "\t\n"])
def test_uuid5_from_seed_rejects_empty_seed(bad_seed):
    with pytest.raises(ValueError) as exc_info:
        uuid5_from_seed(NAMESPACE_URL, bad_seed)
    assert "seed must be non-empty" in str(exc_info.value)


@pytest.mark.parametrize(
    "field",
    ["source_artifact_hash", "parser_version", "values_hash"],
)
@pytest.mark.parametrize("bad", ["", "   "])
def test_attestation_uuid_rejects_missing_component(field, bad):
    kwargs = dict(_VALID)
    kwargs[field] = bad
    with pytest.raises(ValueError) as exc_info:
        attestation_uuid(**kwargs)
    assert field in str(exc_info.value)


@pytest.mark.parametrize(
    "field",
    ["source_artifact_hash", "parser_version", "values_hash"],
)
def test_attestation_uuid_rejects_rs_delimiter(field):
    kwargs = dict(_VALID)
    kwargs[field] = f"has{_RS}delimiter"
    with pytest.raises(ValueError) as exc_info:
        attestation_uuid(**kwargs)
    assert "RS delimiter" in str(exc_info.value)


def test_attestation_uuid_is_idempotent_for_valid_inputs():
    # Sanity anchor: valid inputs do not raise and are deterministic.
    assert attestation_uuid(**_VALID) == attestation_uuid(**_VALID)
