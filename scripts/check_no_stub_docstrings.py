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

# Per-file count cap: how many occurrences of each marker we tolerate
# in a baselined file. Line-based baselines drifted on every commit
# that added/removed lines above the marker; count-based baselines
# detect *new* stubs (count goes up) while ignoring line shifts.
# To drive the backlog down: fix a stub, decrement the cap; CI then
# blocks regressions.
#
# Empty — the backlog has been cleared. Future placeholder docstrings
# fail CI on first appearance; there's no exempt file.
_BASELINE_FILE_CAPS: dict[str, dict[str, int]] = {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    failures: list[tuple[Path, int, str, str]] = []
    files_scanned = 0

    # Track per-file counts so we can compare against the baseline caps.
    counts: dict[str, dict[str, list[tuple[int, str]]]] = {}

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
                        counts.setdefault(rel, {}).setdefault(bad, []).append((lineno, line.strip()))

    for rel, markers in counts.items():
        caps = _BASELINE_FILE_CAPS.get(rel, {})
        for bad, occs in markers.items():
            cap = caps.get(bad, 0)
            if len(occs) > cap:
                # Flag the new ones (anything beyond the cap).
                for lineno, text in occs[cap:]:
                    failures.append((Path(rel), lineno, bad, text))

    if not args.quiet:
        print(f"scanned {files_scanned} files under {_ROOTS}")

    if failures:
        print(f"\nFAIL: {len(failures)} stub-docstring marker(s) over cap:\n")
        for path, lineno, marker, text in failures:
            print(f"  {path}:{lineno}  [{marker!r}]  {text}")
        print(
            "\nRewrite each placeholder docstring to describe the *why* of "
            "the function. See CLAUDE.md for the project's docstring policy. "
            "Cleaning up a stub means decrementing the cap in "
            "_BASELINE_FILE_CAPS so CI prevents regressions."
        )
        return 1

    if not args.quiet:
        print("OK — no stub docstring markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
