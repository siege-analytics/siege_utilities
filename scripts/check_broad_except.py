#!/usr/bin/env python3
"""SU-1 Tier 1 check for broad exception handlers, delegating to the contract guard.

The SU-1 rule names this script as the automated check for exception type
breadth: bare ``except:``, ``except Exception`` and ``except BaseException``.
It used to keep its own rules and a ``# noqa: SU1`` escape that no handler
used. It therefore reported deliberate, already reviewed handlers on every
run, and CI never ran it (#1971).

It now delegates to ``scripts/check_exception_contracts.py``, the guard that
CI runs, so that one rule set and one review record decide SU-1. That guard's
BROAD rule exempts a broad handler only when its body ends in a raise and
nothing in the handler's own scope returns, breaks, continues or yields. Every
other broad handler needs a justified, digest-bound entry in
``scripts/exception_contracts_allowlist.json``. The allow-list is read and
validated by the guard's own loader. This script reports the BROAD findings
that have no such entry. The guard itself also reports its DEFAULT and
LOGONLY rules and stale entries.

Usage::

    python scripts/check_broad_except.py

Exits 0 when every broad handler is reviewed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().with_name("check_exception_contracts.py")


def _load_guard():
    """Load the contract guard from its file; ``scripts/`` is not a package."""
    spec = importlib.util.spec_from_file_location("check_exception_contracts", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    guard = _load_guard()
    parser = argparse.ArgumentParser(
        description="Report broad exception handlers without a reviewed allow-list entry (SU-1)."
    )
    parser.add_argument("--root", type=Path, default=guard.ROOT)
    parser.add_argument("--allowlist", type=Path)
    args = parser.parse_args(argv)

    try:
        allow = guard.load_allowlist(args.root, args.allowlist)
    except ValueError as exc:
        parser.error(str(exc))
    broad = [item for item in guard.scan(args.root) if item["rule"] == "BROAD"]
    unreviewed = [item for item in broad if item["key"] not in allow]

    print(f"broad handlers flagged: {len(broad)}; unreviewed: {len(unreviewed)}")
    for item in unreviewed:
        print(f"  {item['location']} {item['key']}")
    if unreviewed:
        print(
            f"\nFAIL: {len(unreviewed)} broad exception handler(s) without a reviewed entry. "
            "Narrow the handler to the exceptions that can actually be raised, end it in a "
            "raise with no return, break, continue or yield before it, or add a justified "
            "entry to scripts/exception_contracts_allowlist.json."
        )
        return 1
    print("\nOK: every broad exception handler is reviewed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
