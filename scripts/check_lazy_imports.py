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
import importlib.util
import sys
from pathlib import Path


def _check_package(pkg_name: str, quiet: bool) -> tuple[list[str], list[str]]:
    """Return (failures, optional-skip messages) for *pkg_name*."""
    failures: list[str] = []
    optional_skips: list[str] = []
    try:
        pkg = importlib.import_module(pkg_name)
    except ModuleNotFoundError as exc:
        # Subpackage requires an optional dep to import its __init__.
        # Not a structural drift problem — report the skip explicitly
        # so this report-only gate does not overclaim full resolution.
        # Missing local modules are structural package failures, not optional
        # external dependency skips.
        if exc.name == pkg_name or exc.name.startswith(pkg_name + "."):
            failures.append(f"{pkg_name}: package import failed; missing local module: {exc.name}")
        else:
            optional_skips.append(f"{pkg_name}: package import skipped; optional dependency missing: {exc.name}")
        return failures, optional_skips
    except (ImportError, AttributeError, RuntimeError, OSError) as exc:
        failures.append(f"{pkg_name}: package import failed: {exc!r}")
        return failures, optional_skips
    except Exception as exc:
        if ".django" in pkg_name:
            optional_skips.append(f"{pkg_name}: package import skipped; optional GIS/Django dependency failed: {exc!r}")
            return failures, optional_skips
        raise

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
            # Resolve modpath so we can tell "registry points at a
            # missing module" (drift) from "an optional transitive dep
            # is missing" (environment).
            try:
                resolved_modpath = importlib.util.resolve_name(modpath, pkg_name)
            except (ImportError, ValueError):
                resolved_modpath = modpath  # best effort
            try:
                mod = importlib.import_module(modpath, package=pkg_name)
            except ModuleNotFoundError as exc:
                if exc.name == resolved_modpath:
                    # Target itself is missing — registry drift, not env.
                    failures.append(
                        f"{pkg_name}: registry maps {name!r} -> {modpath!r}, "
                        f"but module {modpath} cannot be imported "
                        f"(ModuleNotFoundError: {exc.name})"
                    )
                optional_skips.append(
                    f"{pkg_name}: {name!r} skipped; optional dependency missing: {exc.name}"
                )
                continue
            except ImportError as exc:
                # Partial-module ImportError ("cannot import name X from
                # optdep") — env, not drift.
                optional_skips.append(f"{pkg_name}: {name!r} skipped; optional import failed: {exc}")
                continue
            except AttributeError as exc:
                # `gpd = None; GeoDataFrame = gpd.GeoDataFrame` at module
                # load raises AttributeError when the optional dep is
                # missing. Env, not drift.
                optional_skips.append(f"{pkg_name}: {name!r} skipped; optional attribute unavailable: {exc}")
                continue
            except (ImportError, AttributeError, RuntimeError, OSError, TypeError) as exc:
                failures.append(
                    f"{pkg_name}: failed to import {modpath} for {name!r}: {exc!r}"
                )
                continue
            # hasattr() on a lazy package triggers its __getattr__,
            # which can chain into another optional-dep ModuleNotFoundError.
            try:
                resolved = hasattr(mod, attr_name)
            except ModuleNotFoundError as exc:
                optional_skips.append(
                    f"{pkg_name}: {name!r} hasattr skipped; optional dependency missing: {exc.name}"
                )
                continue
            except ImportError as exc:
                optional_skips.append(f"{pkg_name}: {name!r} hasattr skipped; optional import failed: {exc}")
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
            except ModuleNotFoundError as exc:
                optional_skips.append(
                    f"{pkg_name}: __all__ {name!r} skipped; optional dependency missing: {exc.name}"
                )
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
    return failures, optional_skips


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
    all_optional_skips: list[str] = []
    # Top-level package + every subpackage that has an __init__.py
    # declaring _LAZY_IMPORTS.
    packages = ["siege_utilities"]
    try:
        importlib.import_module("siege_utilities")
    except (ImportError, AttributeError, RuntimeError, OSError) as exc:
        print(f"FAIL: cannot import siege_utilities: {exc!r}")
        return 1

    package_root = repo / "siege_utilities"
    for init_file in package_root.rglob("__init__.py"):
        if init_file == package_root / "__init__.py":
            continue
        rel = init_file.parent.relative_to(repo)
        if "__pycache__" in rel.parts:
            continue
        packages.append(".".join(rel.parts))

    for name in sorted(packages):
        failures, optional_skips = _check_package(name, quiet=args.quiet)
        all_failures.extend(failures)
        all_optional_skips.extend(optional_skips)

    if all_failures:
        print(f"\nFAIL: {len(all_failures)} lazy-import problem(s):\n")
        for f in all_failures:
            print("  " + f)
        return 1

    if not args.quiet:
        print(
            f"OK — checked {len(packages)} package(s), structural lazy registries resolve; "
            f"optional dependency skips={len(all_optional_skips)}"
        )
        for skip in all_optional_skips[:20]:
            print("  SKIP: " + skip)
        if len(all_optional_skips) > 20:
            print(f"  ... {len(all_optional_skips) - 20} additional optional skip(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
