#!/usr/bin/env python3
"""Audit the public API surface — reports the delta between __all__ and
_LAZY_IMPORTS with a proposed categorization for each symbol.

Closes the tooling half of #1176 (Public API categorization: 283 lazy
symbols not in __all__). Produces a markdown report classifying each
uncategorized lazy symbol into one of three tiers:

  - **canonical**  Documented in README / notebooks / release notes;
                   should be added to __all__.
  - **extension**  Subclass base, plugin registry, protocol marker;
                   should be in __all__ with an extension-tier
                   stability contract comment.
  - **internal**   Happens to be lazy-loadable for backward compat but
                   not part of any documented API; should stay out of
                   __all__; considered for `_` prefix on next major.

Heuristic assignment (pending human review of the report):

  - **canonical** if the symbol is referenced in:
      README.md, docs/**, notebooks/**
  - **extension** if the symbol name matches:
      /^(Abstract|Base|Protocol|Config|Result|Report|Error)$/ or ends
      in the same
  - **internal** everything else — the default; safest classification
      to move a symbol out of the public contract without breaking
      documented consumers

Manual override: create `scripts/public_api_overrides.toml` with a
`[canonical]` / `[extension]` / `[internal]` table mapping symbol
names to justification strings. Overrides win over heuristics.

Usage:
    python scripts/audit_public_api_surface.py --report [--markdown]

Exit code:
    0  Always (this is a report tool, not a ratchet — the per-tier
       promotion is a design decision).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

EXTENSION_PATTERNS = [
    re.compile(r"^Abstract"),
    re.compile(r"^Base[A-Z]"),
    re.compile(r"Protocol$"),
    re.compile(r"^[A-Z][a-zA-Z]*(Config|Registry|Provider|Backend|Engine)$"),
    re.compile(r"Error$"),
    re.compile(r"^SU[A-Z][a-zA-Z]*"),
]


def grep_public_references(name: str) -> int:
    """Count references to *name* in user-visible surfaces.

    Higher count → stronger signal for 'canonical' classification.
    Only counts docs / README / notebooks — not test files (tests
    exercise internal symbols too).
    """
    total = 0
    for surface in ("README.md", "docs", "notebooks"):
        target = REPO_ROOT / surface
        if not target.exists():
            continue
        # Word-boundary grep to avoid substring matches
        result = subprocess.run(
            ["grep", "-rc", f"\\b{name}\\b", str(target)],
            capture_output=True, text=True, timeout=30,  # writing-code:15
        )
        for line in result.stdout.splitlines():
            if ":" in line:
                try:
                    total += int(line.rsplit(":", 1)[1])
                except ValueError:
                    pass
    return total


def load_overrides() -> dict[str, tuple[str, str]]:
    """Return {name: (tier, reason)} from public_api_overrides.toml."""
    path = REPO_ROOT / "scripts" / "public_api_overrides.toml"
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_bytes().decode())
    out: dict[str, tuple[str, str]] = {}
    for tier in ("canonical", "extension", "internal"):
        for name, reason in data.get(tier, {}).items():
            out[name] = (tier, reason)
    return out


def classify(name: str, overrides: dict[str, tuple[str, str]]) -> tuple[str, str]:
    """Return (tier, justification) for a symbol."""
    if name in overrides:
        tier, reason = overrides[name]
        return tier, f"override: {reason}"

    for pattern in EXTENSION_PATTERNS:
        if pattern.search(name):
            return "extension", f"matches pattern {pattern.pattern!r}"

    refs = grep_public_references(name)
    if refs > 0:
        return "canonical", f"{refs} reference(s) in README/docs/notebooks"

    return "internal", "no public-surface references + no extension-pattern match"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true",
                        help="Emit a markdown report (default: plain-text summary)")
    parser.add_argument("--report", action="store_true",
                        help="Full per-symbol report (default: summary only)")
    args = parser.parse_args()

    # Import siege_utilities lazily since this script needs to work
    # from a checkout without the package installed.
    sys.path.insert(0, str(REPO_ROOT))
    import siege_utilities  # noqa: E402

    all_ = set(siege_utilities.__all__)
    lazy = getattr(siege_utilities, "_LAZY_IMPORTS", {})
    uncategorized = {name: entry for name, entry in lazy.items() if name not in all_}

    overrides = load_overrides()

    tiers: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for name, entry in sorted(uncategorized.items()):
        tier, why = classify(name, overrides)
        origin = entry[0] if isinstance(entry, tuple) else str(entry)
        tiers[tier].append((name, origin, why))

    total = sum(len(v) for v in tiers.values())

    if args.markdown:
        print("# Public API surface audit (#1176)")
        print()
        print(f"**Total lazy symbols not in `__all__`:** {total}")
        print(f"**Symbols in `__all__`:** {len(all_)}")
        print(f"**Symbols in `_LAZY_IMPORTS`:** {len(lazy)}")
        print()
        print("## Summary by tier")
        print()
        print("| Tier | Count | Meaning |")
        print("|---|---:|---|")
        print(f"| canonical | {len(tiers['canonical'])} | Documented in README/docs/notebooks — promote to `__all__` |")
        print(f"| extension | {len(tiers['extension'])} | Subclass base / registry / protocol — add to `__all__` with extension-tier contract comment |")
        print(f"| internal | {len(tiers['internal'])} | No public-surface reference; keep out of `__all__`; consider `_` prefix on next major |")
        print()
        if args.report:
            for tier in ("canonical", "extension", "internal"):
                print(f"## Tier: {tier} ({len(tiers[tier])} symbols)")
                print()
                print("| Symbol | Origin module | Justification |")
                print("|---|---|---|")
                for name, origin, why in tiers[tier]:
                    print(f"| `{name}` | `{origin}` | {why} |")
                print()
    else:
        print(f"Public API surface audit — {total} lazy symbols outside __all__:")
        for tier, entries in tiers.items():
            print(f"  {tier}: {len(entries)}")
        print()
        print("Run with --markdown --report for the full per-symbol table.")
        print(f"Add overrides at {REPO_ROOT / 'scripts' / 'public_api_overrides.toml'}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
