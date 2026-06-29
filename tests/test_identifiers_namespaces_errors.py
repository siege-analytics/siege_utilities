"""Error-path coverage (SU-4b) for siege_utilities.identifiers.namespaces.

Forces the ValueError guards on empty/whitespace seeds and names.
"""

from uuid import uuid4

import pytest

from siege_utilities.identifiers.namespaces import (
    derive_root,
    derive_sub_namespace,
)


@pytest.mark.parametrize("bad_seed", ["", "   ", "\t\n"])
def test_derive_root_rejects_empty_seed(bad_seed):
    with pytest.raises(ValueError) as exc_info:
        derive_root(bad_seed)
    assert "root seed must be non-empty" in str(exc_info.value)


@pytest.mark.parametrize("bad_name", ["", "   ", "\t"])
def test_derive_sub_namespace_rejects_empty_name(bad_name):
    root = derive_root("example.com")
    with pytest.raises(ValueError) as exc_info:
        derive_sub_namespace(root, bad_name)
    assert "sub-namespace name must be non-empty" in str(exc_info.value)


def test_derive_root_is_deterministic_for_valid_seed():
    # Sanity anchor so the guard test cannot pass vacuously.
    assert derive_root("example.com") == derive_root("example.com")
    assert derive_sub_namespace(derive_root("example.com"), "person") != uuid4()
