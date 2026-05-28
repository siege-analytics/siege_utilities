"""Error-path tests for siege_utilities.identifiers.uuid_generation (SU-4b)."""

from uuid import UUID

import pytest

from siege_utilities.identifiers.namespaces import derive_root
from siege_utilities.identifiers.uuid_generation import (
    attestation_uuid,
    uuid5_from_seed,
)

NS = derive_root("test.example.com")


class TestUuid5FromSeedErrors:
    """Error paths for uuid5_from_seed."""

    def test_empty_seed_raises(self):
        """Empty seed must raise ValueError (Pattern 4)."""
        with pytest.raises(ValueError, match="non-empty"):
            uuid5_from_seed(NS, "")

    def test_whitespace_seed_raises(self):
        """Whitespace-only seed must raise ValueError (Pattern 4)."""
        with pytest.raises(ValueError, match="non-empty"):
            uuid5_from_seed(NS, "   ")


class TestAttestationUuidEmptyInputErrors:
    """Empty/whitespace input validation for attestation_uuid."""

    def _call(self, **overrides):
        defaults = dict(
            namespace=NS,
            source_artifact_hash="abc123",
            record_line=1,
            parser_version="v1.0",
            values_hash="def456",
        )
        defaults.update(overrides)
        return attestation_uuid(**defaults)

    def test_empty_source_hash_raises(self):
        """Empty source_artifact_hash must raise ValueError."""
        with pytest.raises(ValueError, match="source_artifact_hash"):
            self._call(source_artifact_hash="")

    def test_whitespace_source_hash_raises(self):
        """Whitespace-only source_artifact_hash must raise ValueError."""
        with pytest.raises(ValueError, match="source_artifact_hash"):
            self._call(source_artifact_hash="   ")

    def test_empty_parser_version_raises(self):
        """Empty parser_version must raise ValueError."""
        with pytest.raises(ValueError, match="parser_version"):
            self._call(parser_version="")

    def test_whitespace_parser_version_raises(self):
        """Whitespace-only parser_version must raise ValueError."""
        with pytest.raises(ValueError, match="parser_version"):
            self._call(parser_version="   ")

    def test_empty_values_hash_raises(self):
        """Empty values_hash must raise ValueError."""
        with pytest.raises(ValueError, match="values_hash"):
            self._call(values_hash="")

    def test_whitespace_values_hash_raises(self):
        """Whitespace-only values_hash must raise ValueError."""
        with pytest.raises(ValueError, match="values_hash"):
            self._call(values_hash="   ")


class TestAttestationUuidDelimiterErrors:
    """RS delimiter rejection for attestation_uuid."""

    def _call(self, **overrides):
        defaults = dict(
            namespace=NS,
            source_artifact_hash="abc123",
            record_line=1,
            parser_version="v1.0",
            values_hash="def456",
        )
        defaults.update(overrides)
        return attestation_uuid(**defaults)

    def test_source_hash_with_rs_raises(self):
        """source_artifact_hash containing RS delimiter must raise ValueError."""
        with pytest.raises(ValueError, match="RS delimiter"):
            self._call(source_artifact_hash="abc\x1e123")

    def test_parser_version_with_rs_raises(self):
        """parser_version containing RS delimiter must raise ValueError."""
        with pytest.raises(ValueError, match="RS delimiter"):
            self._call(parser_version="v1\x1e0")

    def test_values_hash_with_rs_raises(self):
        """values_hash containing RS delimiter must raise ValueError."""
        with pytest.raises(ValueError, match="RS delimiter"):
            self._call(values_hash="def\x1e456")


class TestAttestationUuidHappyPath:
    """Sanity checks for attestation_uuid."""

    def test_returns_uuid(self):
        """Valid inputs produce a UUID."""
        result = attestation_uuid(
            namespace=NS,
            source_artifact_hash="abc123",
            record_line=1,
            parser_version="v1.0",
            values_hash="def456",
        )
        assert isinstance(result, UUID)

    def test_deterministic(self):
        """Same inputs produce same UUID."""
        kwargs = dict(
            namespace=NS,
            source_artifact_hash="abc123",
            record_line=1,
            parser_version="v1.0",
            values_hash="def456",
        )
        assert attestation_uuid(**kwargs) == attestation_uuid(**kwargs)

    def test_different_parser_version_differs(self):
        """Bumping parser_version produces a different UUID."""
        base = dict(
            namespace=NS,
            source_artifact_hash="abc123",
            record_line=1,
            values_hash="def456",
        )
        assert attestation_uuid(parser_version="v1.0", **base) != attestation_uuid(
            parser_version="v2.0", **base
        )
