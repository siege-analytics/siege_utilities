#!/usr/bin/env python3
"""Fail CI if any source file contains placeholder/stub docstring text.

Stub markers like ``"Description needed"`` are auto-generated when a
new function ships without a written docstring. Several have leaked
into production over the years; this guard prevents future drift.

Usage::

    python scripts/check_no_stub_docstrings.py [--quiet]

Exits 0 on clean tree, 1 on detection. Prints offending file:line for
each match.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Any of these substrings in a Python source file is a fail.
_BAD_PHRASES = (
    "Description needed",
    "TODO: write docstring",
    "Auto-discovered and available",  # generic boilerplate from a docstring generator
)

# Where to scan. We only check the published library; tests and
# scripts are exempt because their docstrings serve a different
# audience.
_ROOTS = ("siege_utilities",)

# Files exempt from the check:
# - hygiene/generate_docstrings.py *creates* placeholder docstrings as
#   a feature; its source quotes them as examples. Banning the strings
#   inside this file would defeat its own job.
_EXEMPT_FILES = frozenset({
    "siege_utilities/hygiene/generate_docstrings.py",
})

# Per-occurrence ratchet baseline: known stub markers we accept as a
# backlog, keyed on "path:line:marker". A NEW stub at any other path:line
# fails CI, including new stubs in the same file as a baselined one —
# whole-file exemptions create a permanent blind spot. Driving an entry
# off this list is how the count shrinks.
_BASELINE_OCCURRENCES = frozenset({
    "siege_utilities/distributed/spark_utils.py:155:Auto-discovered and available",
    "siege_utilities/distributed/spark_utils.py:158:Description needed",
    "siege_utilities/distributed/spark_utils.py:312:Auto-discovered and available",
    "siege_utilities/distributed/spark_utils.py:315:Description needed",
    "siege_utilities/distributed/spark_utils.py:355:Auto-discovered and available",
    "siege_utilities/distributed/spark_utils.py:358:Description needed",
    "siege_utilities/distributed/spark_utils.py:848:Auto-discovered and available",
    "siege_utilities/distributed/spark_utils.py:851:Description needed",
    "siege_utilities/distributed/spark_utils.py:912:Auto-discovered and available",
    "siege_utilities/distributed/spark_utils.py:915:Description needed",
    "siege_utilities/geo/geocoding.py:501:Auto-discovered and available",
    "siege_utilities/geo/geocoding.py:504:Description needed",
    "siege_utilities/geo/geocoding.py:522:Auto-discovered and available",
    "siege_utilities/geo/geocoding.py:525:Description needed",
    "siege_utilities/geo/geocoding.py:546:Auto-discovered and available",
    "siege_utilities/geo/geocoding.py:549:Description needed",
    "siege_utilities/geo/geocoding.py:570:Auto-discovered and available",
    "siege_utilities/geo/geocoding.py:573:Description needed",
})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    failures: list[tuple[Path, int, str, str]] = []
    files_scanned = 0

    for root in _ROOTS:
        root_dir = repo / root
        if not root_dir.exists():
            continue
        for py in root_dir.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            rel = py.relative_to(repo).as_posix()
            if rel in _EXEMPT_FILES:
                continue
            files_scanned += 1
            try:
                lines = py.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                print(f"WARN: cannot read {py}: {exc}", file=sys.stderr)
                continue
            for lineno, line in enumerate(lines, start=1):
                for bad in _BAD_PHRASES:
                    if bad in line:
                        key = f"{rel}:{lineno}:{bad}"
                        if key in _BASELINE_OCCURRENCES:
                            continue
                        failures.append((py.relative_to(repo), lineno, bad, line.strip()))

    if not args.quiet:
        print(f"scanned {files_scanned} files under {_ROOTS}")

    if failures:
        print(f"\nFAIL: {len(failures)} stub-docstring marker(s) found:\n")
        for path, lineno, marker, text in failures:
            print(f"  {path}:{lineno}  [{marker!r}]  {text}")
        print(
            "\nRewrite each placeholder docstring to describe the *why* of "
            "the function. See CLAUDE.md for the project's docstring policy."
        )
        return 1

    if not args.quiet:
        print("OK — no stub docstring markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
