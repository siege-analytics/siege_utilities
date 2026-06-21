"""Error-path + determinism tests for siege_utilities.identifiers.namespaces.

Exercises the ValueError raises in derive_root and derive_sub_namespace
(empty/whitespace seed and name) plus the deterministic happy path, per
SU-4b / writing-tests:5.
"""

import pytest

from siege_utilities.identifiers.namespaces import (
    derive_root,
    derive_sub_namespace,
)


class TestDeriveRoot:
    def test_empty_seed_raises(self):
        with pytest.raises(ValueError, match="root seed must be non-empty"):
            derive_root("")

    def test_whitespace_seed_raises(self):
        with pytest.raises(ValueError, match="root seed must be non-empty"):
            derive_root("   ")

    def test_valid_seed_is_deterministic(self):
        assert derive_root("example.com") == derive_root("example.com")
        assert derive_root("example.com") != derive_root("other.com")


class TestDeriveSubNamespace:
    def test_empty_name_raises(self):
        root = derive_root("example.com")
        with pytest.raises(ValueError, match="sub-namespace name must be non-empty"):
            derive_sub_namespace(root, "")

    def test_whitespace_name_raises(self):
        root = derive_root("example.com")
        with pytest.raises(ValueError, match="sub-namespace name must be non-empty"):
            derive_sub_namespace(root, "\t")

    def test_valid_name_is_deterministic_and_distinct(self):
        root = derive_root("example.com")
        assert derive_sub_namespace(root, "person") == derive_sub_namespace(root, "person")
        assert derive_sub_namespace(root, "person") != derive_sub_namespace(root, "committee")
