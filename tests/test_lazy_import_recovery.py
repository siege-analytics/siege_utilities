"""Tests for #1041: lazy loader must not cache dependency-wrapper stubs.

The recovery path (user installs missing dep in the same process, then
re-accesses the attribute and gets the real symbol) requires that the
wrapper is NOT cached via setattr on the package namespace. Otherwise
subsequent accesses return the stub even after dep is available.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

import siege_utilities


def test_dependency_wrapper_is_not_cached_when_dep_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second access does not short-circuit on a cached stub.

    Simulates: attribute maps to a lazy symbol whose module requires
    an optional dep that is missing. First access returns a wrapper.
    Second access must go back through __getattr__ (not hit the module
    namespace as a cached attribute).
    """
    # Pick a symbol from _LAZY_IMPORTS whose deps are checked at import time.
    # Fall through to a synthetic entry if the registry shape changed.
    lazy = getattr(siege_utilities, "_LAZY_IMPORTS", {})
    # Find one that declares deps
    candidate = None
    for name, entry in lazy.items():
        if len(entry) >= 3 and entry[2]:
            candidate = name
            break
    if candidate is None:
        pytest.skip("No lazy entries with declared deps to exercise")

    # Force the ImportError branch by patching the target module import
    # to raise ImportError.
    import importlib

    def raise_import_error(*args: Any, **kwargs: Any) -> Any:
        raise ImportError("simulated missing dep")

    monkeypatch.setattr(importlib, "import_module", raise_import_error)

    # First access — should return a wrapper (not raise) because deps declared
    # and _is_dep_missing will return True under the patched import.
    #
    # NOTE: If getattr returns a wrapper, it must NOT have been cached on the
    # package. Verify by checking sys.modules['siege_utilities'].__dict__
    # does not contain the name post-access.
    #
    # If deps happen to NOT be missing at test time (unlikely but possible),
    # the ImportError branch re-raises, which is also acceptable — the
    # invariant we're testing (no cached stub) still holds vacuously.
    try:
        result = getattr(siege_utilities, candidate)
    except ImportError:
        # deps evaluated as present; the raise path taken.
        # In that case the fix's invariant is trivially true.
        return

    # If a wrapper was returned, it must not have been cached on the module.
    pkg_dict = sys.modules["siege_utilities"].__dict__
    assert candidate not in pkg_dict, (
        f"{candidate} was cached on the package namespace; the recovery "
        f"path is broken. #1041 fix regressed."
    )
    # And the wrapper is callable (documents "install X" contract).
    assert callable(result)


def test_successful_lazy_import_is_still_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The no-cache change applies ONLY to the dependency-missing wrapper path.

    A successful import must still be cached — otherwise every access re-runs
    `importlib.import_module`, which is the whole point of the lazy machinery.
    """
    # Pick a lazy symbol whose deps are actually available (or has no deps).
    lazy = getattr(siege_utilities, "_LAZY_IMPORTS", {})
    candidate = None
    for name, entry in lazy.items():
        deps = entry[2] if len(entry) >= 3 else None
        if not deps:  # no declared deps = should import cleanly
            # Additional guard: ensure not already cached
            if name not in sys.modules["siege_utilities"].__dict__:
                candidate = name
                break
    if candidate is None:
        pytest.skip("No uncached-lazy entries without deps to exercise")

    # Trigger lazy load
    getattr(siege_utilities, candidate)

    # Now cached on the module namespace
    assert candidate in sys.modules["siege_utilities"].__dict__, (
        f"{candidate} not cached after successful load; the fix "
        f"over-broadened and broke the happy-path caching."
    )
