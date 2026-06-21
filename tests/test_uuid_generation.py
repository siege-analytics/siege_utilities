"""Error-path + determinism tests for siege_utilities.identifiers.uuid_generation.

Exercises every ValueError raise in uuid5_from_seed and attestation_uuid
(empty/whitespace inputs and the RS-delimiter guard) plus the deterministic
happy path, per SU-4b / writing-tests:5 (each test forces the actual exception).
"""

from uuid import UUID

import pytest

from siege_utilities.identifiers.uuid_generation import (
    attestation_uuid,
    uuid5_from_seed,
)

NS = UUID("12345678-1234-5678-1234-567812345678")


class TestUuid5FromSeed:
    def test_empty_seed_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            uuid5_from_seed(NS, "")

    def test_whitespace_seed_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            uuid5_from_seed(NS, "   ")

    def test_valid_seed_is_deterministic(self):
        assert uuid5_from_seed(NS, "abc") == uuid5_from_seed(NS, "abc")
        assert uuid5_from_seed(NS, "abc") != uuid5_from_seed(NS, "def")


class TestAttestationUuid:
    _valid = dict(
        namespace=NS,
        source_artifact_hash="deadbeef",
        record_line=1,
        parser_version="v1",
        values_hash="cafef00d",
    )

    def test_empty_source_artifact_hash_raises(self):
        with pytest.raises(ValueError, match="source_artifact_hash"):
            attestation_uuid(**{**self._valid, "source_artifact_hash": "  "})

    def test_empty_parser_version_raises(self):
        with pytest.raises(ValueError, match="parser_version"):
            attestation_uuid(**{**self._valid, "parser_version": ""})

    def test_empty_values_hash_raises(self):
        with pytest.raises(ValueError, match="values_hash"):
            attestation_uuid(**{**self._valid, "values_hash": "\t"})

    def test_rs_delimiter_in_source_artifact_hash_raises(self):
        with pytest.raises(ValueError, match="RS delimiter"):
            attestation_uuid(**{**self._valid, "source_artifact_hash": "dead\x1ebeef"})

    def test_rs_delimiter_in_parser_version_raises(self):
        with pytest.raises(ValueError, match="RS delimiter"):
            attestation_uuid(**{**self._valid, "parser_version": "v\x1e1"})

    def test_rs_delimiter_in_values_hash_raises(self):
        with pytest.raises(ValueError, match="RS delimiter"):
            attestation_uuid(**{**self._valid, "values_hash": "cafe\x1ef00d"})

    def test_valid_inputs_deterministic_and_version_aware(self):
        a = attestation_uuid(**self._valid)
        assert a == attestation_uuid(**self._valid)
        # Bumping the parser version yields a distinct attestation UUID.
        assert a != attestation_uuid(**{**self._valid, "parser_version": "v2"})
