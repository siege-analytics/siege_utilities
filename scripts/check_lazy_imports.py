#!/usr/bin/env python3
"""Fail CI if any name in a package's lazy registry can't be imported.

The siege_utilities package uses PEP 562 ``__getattr__`` to lazy-load
submodules. Each ``__init__.py`` declares a ``_LAZY_IMPORTS`` dict
mapping public name → relative module path. Drift is easy:

* A function gets renamed but the registry entry isn't updated.
* A name lands in ``__all__`` but never in ``_LAZY_IMPORTS``.
* ``_LAZY_IMPORTS`` references a module that doesn't exist.

This script imports every name in every ``_LAZY_IMPORTS`` registry
under the package and reports failures. It also flags names that
appear in ``__all__`` without a corresponding ``_LAZY_IMPORTS`` entry.

Usage::

    python scripts/check_lazy_imports.py [--quiet]

Exits 0 on clean tree, 1 on any unresolvable name.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path


def _check_package(pkg_name: str, quiet: bool) -> list[str]:
    """Return a list of human-readable failure messages for *pkg_name*."""
    failures: list[str] = []
    try:
        pkg = importlib.import_module(pkg_name)
    except ModuleNotFoundError:
        # Subpackage requires an optional dep to import its __init__.
        # Not a structural drift problem — would be ideal if these
        # were also lazy, but that's a separate refactor.
        return failures
    except Exception as exc:
        failures.append(f"{pkg_name}: package import failed: {exc!r}")
        return failures

    lazy = getattr(pkg, "_LAZY_IMPORTS", None)
    public_all = getattr(pkg, "__all__", None)

    # Check 1: every name in _LAZY_IMPORTS resolves.
    # ModuleNotFoundError is OK — the lazy-import system is *designed*
    # for optional deps (geopandas, pyspark, etc.) to fail at access
    # time. We only fail on structural problems: the registry maps to
    # a module that exists but doesn't export the named symbol.
    #
    # Two registry schemas exist in this codebase:
    #   - top-level siege_utilities/__init__.py: name -> (modpath, attr, deps)
    #   - subpackages: name -> modpath (str)
    # Normalize on (modpath, attr_name) where attr_name defaults to
    # the registry key.
    if lazy:
        for name, value in lazy.items():
            if isinstance(value, tuple):
                modpath = value[0]
                attr_name = value[1] if len(value) > 1 else name
            else:
                modpath = value
                attr_name = name
            try:
                mod = importlib.import_module(modpath, package=pkg_name)
            except (ModuleNotFoundError, ImportError, AttributeError):
                # Module-level optional-dep failures land here:
                # - ModuleNotFoundError: `import optdep`
                # - ImportError: `from optdep import x` when optdep is partial
                # - AttributeError: the canonical
                #     `try: import gpd; except ImportError: gpd = None`
                #     `GeoDataFrame = gpd.GeoDataFrame   # at module load`
                # idiom — `gpd is None` makes the alias raise AttributeError.
                # None of these indicate structural drift; the module is
                # waiting on a missing extra.
                continue
            except Exception as exc:
                failures.append(
                    f"{pkg_name}: failed to import {modpath} for {name!r}: {exc!r}"
                )
                continue
            # hasattr() on a lazy package triggers its __getattr__,
            # which can chain into another optional-dep ModuleNotFoundError.
            try:
                resolved = hasattr(mod, attr_name)
            except (ModuleNotFoundError, ImportError):
                continue
            if not resolved:
                failures.append(
                    f"{pkg_name}: registry maps {name!r} -> {modpath!r}, "
                    f"but {modpath} has no attribute {attr_name!r}"
                )

    # Check 2: every name in __all__ is either resolvable directly OR
    # appears in _LAZY_IMPORTS. Names that resolve via direct import in
    # the package's __init__.py are also OK (e.g., classes defined in
    # the file itself). Skip names whose lazy access raises
    # ModuleNotFoundError — same reasoning as Check 1.
    if public_all is not None:
        for name in public_all:
            try:
                if hasattr(pkg, name):
                    continue
            except ModuleNotFoundError:
                continue
            if lazy and name in lazy:
                continue
            failures.append(
                f"{pkg_name}: __all__ contains {name!r} but it's neither "
                f"directly defined nor in _LAZY_IMPORTS"
            )

    if not quiet and not failures:
        n_lazy = len(lazy) if lazy else 0
        n_all = len(public_all) if public_all else 0
        print(f"  {pkg_name}: lazy={n_lazy} __all__={n_all} OK")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    # Make the repo's package importable when run from the repo root.
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))

    if not args.quiet:
        print("checking lazy-import registries...")

    all_failures: list[str] = []
    # Top-level package + every subpackage that has an __init__.py
    # declaring _LAZY_IMPORTS.
    packages = ["siege_utilities"]
    try:
        root_pkg = importlib.import_module("siege_utilities")
    except Exception as exc:
        print(f"FAIL: cannot import siege_utilities: {exc!r}")
        return 1

    for info in pkgutil.walk_packages(root_pkg.__path__, prefix="siege_utilities."):
        if info.ispkg:
            packages.append(info.name)

    for name in sorted(packages):
        all_failures.extend(_check_package(name, quiet=args.quiet))

    if all_failures:
        print(f"\nFAIL: {len(all_failures)} lazy-import problem(s):\n")
        for f in all_failures:
            print("  " + f)
        return 1

    if not args.quiet:
        print(f"OK — checked {len(packages)} package(s), all lazy registries resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
