#!/usr/bin/env python3
"""Verify a built siege_utilities wheel ships the library and nothing else (#1420).

Checks, each of which failed on a published wheel:

1. The only top-level package is ``siege_utilities`` (plus its ``.dist-info``).
   The 4.0.0 wheel also installed a top-level ``spikes`` package.
2. Every data file the library loads through ``Path(__file__)`` or
   ``importlib.resources`` is inside the wheel. No wheel up to 4.0.0 shipped
   ``political/migrations/V*.sql`` or ``configs/**/*.yaml``.
3. No member name contains whitespace. The 3.22.0 wheel shipped Finder
   duplicates such as ``examples/enhanced_features_demo 2.py``.
4. No bytecode or ``__pycache__`` entries.

The data-path list is kept honest by scanning the source tree. Any module
that resolves a path against ``__file__`` or uses ``importlib.resources`` must
appear in ``FILE_RELATIVE_REFERENCES`` with the globs it reads. A new reference
that is not listed fails the check, and so does a listed glob that no longer
matches any source file.

Usage::

    python -m build
    python scripts/check_wheel_contents.py dist/*.whl

Exit code 0 when every wheel passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "siege_utilities"

# Module (repo-relative) -> globs (repo-relative) of the files it loads.
# An empty tuple means the reference was reviewed and nothing is shipped for
# it; the reason is in the comment.
FILE_RELATIVE_REFERENCES: dict[str, tuple[str, ...]] = {
    # political.schema_migrations_dir() -> <package>/political/migrations
    "siege_utilities/political/__init__.py": (
        "siege_utilities/political/migrations/V*.sql",
    ),
    # Hydra config dir defaults to <package>/configs; HydraConfigManager
    # raises FileNotFoundError when it is missing.
    "siege_utilities/config/hydra_manager.py": (
        "siege_utilities/configs/*/*.yaml",
        "siege_utilities/configs/*/*/*.yaml",
    ),
    "siege_utilities/config/enhanced_config.py": (
        "siege_utilities/configs/*/*.yaml",
        "siege_utilities/configs/*/*/*.yaml",
    ),
    "siege_utilities/config/migration.py": (
        "siege_utilities/configs/*/*.yaml",
        "siege_utilities/configs/*/*/*.yaml",
    ),
    # Writable directory created at runtime with mkdir(); no tracked files.
    "siege_utilities/reporting/templates/page_templates.py": (),
    # Resolves to <site-packages>/profiles, outside the package; it is a
    # user-writable location, not package data.
    "siege_utilities/admin/profile_manager.py": (),
}

# Always required, independent of any code reference.
ALWAYS_REQUIRED: tuple[str, ...] = ("siege_utilities/py.typed",)

REFERENCE_RE = re.compile(
    r"Path\(\s*__file__\s*\)"
    r"|os\.path\.(?:dirname|abspath|realpath)\(\s*__file__"
    r"|importlib\.resources|importlib_resources|pkg_resources|pkgutil\.get_data"
)


def find_reference_modules(root: Path) -> set[str]:
    """Return repo-relative paths of package modules that resolve data paths."""
    found = set()
    for path in sorted((root / PACKAGE).rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue
            if REFERENCE_RE.search(line):
                found.add(path.relative_to(root).as_posix())
                break
    return found


def required_data_files(root: Path) -> tuple[set[str], list[str]]:
    """Expand the reference globs against the source tree.

    Returns the set of repo-relative files that must be in the wheel and a
    list of configuration errors (unlisted or stale references, empty globs).
    """
    errors: list[str] = []
    found = find_reference_modules(root)
    for module in sorted(found - FILE_RELATIVE_REFERENCES.keys()):
        errors.append(
            f"{module} resolves a path against __file__/importlib.resources but is "
            "not listed in FILE_RELATIVE_REFERENCES; declare what it loads"
        )
    for module in sorted(FILE_RELATIVE_REFERENCES.keys() - found):
        errors.append(
            f"FILE_RELATIVE_REFERENCES lists {module}, which no longer references "
            "a file-relative path; remove the stale entry"
        )

    required: set[str] = set()
    globs = set(ALWAYS_REQUIRED)
    for patterns in FILE_RELATIVE_REFERENCES.values():
        globs.update(patterns)
    for pattern in sorted(globs):
        matches = [p for p in root.glob(pattern) if p.is_file()]
        if not matches:
            errors.append(f"data glob {pattern!r} matches no source file")
        required.update(p.relative_to(root).as_posix() for p in matches)
    return required, errors


def check_wheel(wheel: Path, required: set[str]) -> list[str]:
    """Return the list of problems found in one wheel."""
    problems: list[str] = []
    with zipfile.ZipFile(wheel) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]

    top_level = {n.split("/", 1)[0] for n in names}
    dist_info = {t for t in top_level if t.endswith(".dist-info")}
    unexpected = sorted(top_level - {PACKAGE} - dist_info)
    if PACKAGE not in top_level:
        problems.append(f"top-level package {PACKAGE!r} is missing")
    if unexpected:
        problems.append(
            f"unexpected top-level entries (only {{{PACKAGE}}} may ship): {unexpected}"
        )
    if len(dist_info) != 1:
        problems.append(f"expected exactly one .dist-info directory, found {sorted(dist_info)}")

    with_space = sorted(n for n in names if re.search(r"\s", n))
    if with_space:
        problems.append(f"member names containing whitespace: {with_space}")

    bytecode = sorted(n for n in names if n.endswith((".pyc", ".pyo")) or "__pycache__/" in n)
    if bytecode:
        problems.append(f"bytecode entries: {bytecode}")

    missing = sorted(required - set(names))
    if missing:
        problems.append(f"data files referenced by the code but absent from the wheel: {missing}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("wheels", nargs="+", type=Path, help="wheel file(s) to check")
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="source tree the wheel was built from"
    )
    args = parser.parse_args(argv)

    required, errors = required_data_files(args.root.resolve())
    failed = bool(errors)
    for error in errors:
        print(f"CONFIG ERROR: {error}")

    for wheel in args.wheels:
        problems = check_wheel(wheel, required)
        if problems:
            failed = True
            print(f"{wheel.name}: FAIL")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"{wheel.name}: PASS ({len(required)} required data files present)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
