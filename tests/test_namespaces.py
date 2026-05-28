"""Error-path tests for siege_utilities.identifiers.namespaces (SU-4b)."""

from uuid import UUID

import pytest

from siege_utilities.identifiers.namespaces import derive_root, derive_sub_namespace


class TestDeriveRootErrors:
    """Error paths for derive_root."""

    def test_empty_string_raises(self):
        """Empty seed must raise ValueError (Pattern 4)."""
        with pytest.raises(ValueError, match="non-empty"):
            derive_root("")

    def test_whitespace_only_raises(self):
        """Whitespace-only seed must raise ValueError (Pattern 4)."""
        with pytest.raises(ValueError, match="non-empty"):
            derive_root("   ")


class TestDeriveSubNamespaceErrors:
    """Error paths for derive_sub_namespace."""

    def test_empty_name_raises(self):
        """Empty sub-namespace name must raise ValueError (Pattern 4)."""
        root = derive_root("example.com")
        with pytest.raises(ValueError, match="non-empty"):
            derive_sub_namespace(root, "")

    def test_whitespace_name_raises(self):
        """Whitespace-only name must raise ValueError (Pattern 4)."""
        root = derive_root("example.com")
        with pytest.raises(ValueError, match="non-empty"):
            derive_sub_namespace(root, "   ")


class TestDeriveRootHappyPath:
    """Sanity checks for derive_root."""

    def test_returns_uuid(self):
        """derive_root returns a UUID instance."""
        result = derive_root("example.com")
        assert isinstance(result, UUID)

    def test_deterministic(self):
        """Same seed produces same UUID."""
        assert derive_root("example.com") == derive_root("example.com")

    def test_different_seeds_differ(self):
        """Different seeds produce different UUIDs."""
        assert derive_root("a.com") != derive_root("b.com")
