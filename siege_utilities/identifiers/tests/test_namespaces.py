"""
Namespace derivation helper tests. These verify the mechanism; consumers
verify their own hardcoded constants match their chosen seeds.
"""

from uuid import NAMESPACE_URL, uuid5

import pytest

from siege_utilities.identifiers.namespaces import (
    derive_root,
    derive_sub_namespace,
)


def test_derive_root_matches_uuid5_namespace_url():
    assert derive_root("example.com") == uuid5(NAMESPACE_URL, "example.com")


def test_derive_root_is_deterministic():
    assert derive_root("example.com") == derive_root("example.com")


def test_derive_root_differs_by_seed():
    assert derive_root("a.example.com") != derive_root("b.example.com")


def test_derive_root_rejects_empty_seed():
    with pytest.raises(ValueError, match="root seed"):
        derive_root("")


def test_derive_root_rejects_whitespace_only_seed():
    with pytest.raises(ValueError, match="root seed"):
        derive_root("   ")
    with pytest.raises(ValueError, match="root seed"):
        derive_root("\t\n")


def test_derive_sub_namespace_matches_uuid5_from_root():
    root = derive_root("example.com")
    assert derive_sub_namespace(root, "thing") == uuid5(root, "thing")


def test_derive_sub_namespace_is_deterministic():
    root = derive_root("example.com")
    assert derive_sub_namespace(root, "thing") == derive_sub_namespace(root, "thing")


def test_derive_sub_namespace_differs_by_name():
    root = derive_root("example.com")
    assert derive_sub_namespace(root, "a") != derive_sub_namespace(root, "b")


def test_derive_sub_namespace_differs_by_root():
    a_root = derive_root("a.example.com")
    b_root = derive_root("b.example.com")
    assert derive_sub_namespace(a_root, "thing") != derive_sub_namespace(b_root, "thing")


def test_derive_sub_namespace_rejects_empty_name():
    root = derive_root("example.com")
    with pytest.raises(ValueError, match="sub-namespace"):
        derive_sub_namespace(root, "")


def test_derive_sub_namespace_rejects_whitespace_only_name():
    root = derive_root("example.com")
    with pytest.raises(ValueError, match="sub-namespace"):
        derive_sub_namespace(root, "   ")
    with pytest.raises(ValueError, match="sub-namespace"):
        derive_sub_namespace(root, "\t")
