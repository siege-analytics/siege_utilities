"""Regressions for #1882: package introspection walks only package modules and
never evaluates lazy objects.

On CI the virtualenv path contains ``siege_utilities``, so the old path-based
recursion walked every installed package; there, ``isinstance`` checks forced
Django lazy objects (``staticfiles_storage``) to set themselves up and raise.
"""

import sys
import types

import pytest

from siege_utilities.development.architecture import (
    analyze_module,
    analyze_package_structure,
)

CI_SITE_PACKAGES = (
    "/home/runner/work/siege_utilities/siege_utilities/.venv/lib/python3.13/site-packages"
)


class _LazyStandIn:
    """Mimics a Django LazyObject: reading ``__class__`` triggers setup.

    ``isinstance`` (and so ``inspect.isfunction``/``isclass``/``ismodule``)
    consults ``__class__`` when it differs from ``type(obj)``; Django's
    ``LazyObject`` evaluates itself there. Here setup raises, as
    ``staticfiles_storage`` does without ``STATIC_URL``.
    """

    setups = 0

    @property
    def __class__(self):
        type(self).setups += 1
        raise RuntimeError("lazy object was evaluated")


def _module(name, path, **attrs):
    module = types.ModuleType(name)
    module.__file__ = path
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _third_party_function():
    return None


def _package_function():
    return None


def test_third_party_module_with_siege_utilities_in_path_is_not_walked():
    third_party = _module(
        "fake_thirdparty_1882",
        f"{CI_SITE_PACKAGES}/fake_thirdparty_1882/__init__.py",
        leaked=_third_party_function,
    )
    child = _module(
        "siege_utilities._probe_1882.child",
        "/srv/checkout/siege_utilities/_probe_1882/child.py",
        helper=_package_function,
    )
    package = _module(
        "siege_utilities._probe_1882",
        "/srv/checkout/siege_utilities/_probe_1882/__init__.py",
        dep=third_party,
        child=child,
    )

    info = analyze_module(package, "_probe_1882")

    assert "dep" not in info["submodules"], "a third-party module was walked"
    assert info["submodules"]["child"]["functions"].keys() == {"helper"}


def test_lazy_object_in_a_walked_module_is_never_evaluated():
    _LazyStandIn.setups = 0
    package = _module(
        "siege_utilities._probe_1882_lazy",
        "/srv/checkout/siege_utilities/_probe_1882_lazy.py",
        storage=_LazyStandIn(),
        helper=_package_function,
    )

    info = analyze_module(package, "_probe_1882_lazy")

    assert _LazyStandIn.setups == 0
    assert "error" not in info
    assert info["functions"].keys() == {"helper"}


def test_lazy_object_at_package_top_level_is_never_evaluated(monkeypatch):
    _LazyStandIn.setups = 0
    package = _module(
        "siege_utilities_probe_1882_pkg",
        "/srv/checkout/siege_utilities_probe_1882_pkg/__init__.py",
        storage=_LazyStandIn(),
    )
    monkeypatch.setitem(sys.modules, "siege_utilities_probe_1882_pkg", package)

    structure = analyze_package_structure("siege_utilities_probe_1882_pkg")

    assert _LazyStandIn.setups == 0
    assert "error" not in structure


def test_ci_path_module_holding_staticfiles_storage_does_not_break_introspection():
    """The CI failure, deterministically: a third-party module under a
    virtualenv path containing ``siege_utilities`` exposes Django's real
    ``staticfiles_storage``; the test settings have no ``STATIC_URL``, so
    setting it up raises ImproperlyConfigured. Introspection must not walk
    into the module, so the storage is never set up."""
    pytest.importorskip("django")
    from django.contrib.staticfiles.storage import staticfiles_storage

    third_party = _module(
        "fake_django_contrib_1882",
        f"{CI_SITE_PACKAGES}/django/contrib/staticfiles/storage.py",
        staticfiles_storage=staticfiles_storage,
    )
    package = _module(
        "siege_utilities._probe_1882_ci",
        "/srv/checkout/siege_utilities/_probe_1882_ci.py",
        storage_module=third_party,
        helper=_package_function,
    )

    info = analyze_module(package, "_probe_1882_ci")

    assert "storage_module" not in info["submodules"]
    assert info["functions"].keys() == {"helper"}


def test_real_django_lazy_object_is_never_set_up():
    pytest.importorskip("django")
    from django.utils.functional import SimpleLazyObject

    setups = []

    def _setup():
        setups.append(1)
        raise RuntimeError("SimpleLazyObject was set up")

    package = _module(
        "siege_utilities._probe_1882_django",
        "/srv/checkout/siege_utilities/_probe_1882_django.py",
        storage=SimpleLazyObject(_setup),
    )

    info = analyze_module(package, "_probe_1882_django")

    assert setups == []
    assert "error" not in info
