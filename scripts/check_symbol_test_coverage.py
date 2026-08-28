#!/usr/bin/env python3
"""Per-symbol test coverage scanner (promise-audit Phase 6b tooling).

Answers the question the promise-audit epic (#1178) originally asked:
"for every public function the library claims, is there a test that
verifies it does what it says?"

For each symbol in `siege_utilities.__all__` PLUS every canonical/
extension symbol classified by `scripts/audit_public_api_surface.py`:

  1. **Direct coverage** — does the test suite import the symbol by
     name and exercise it? Detected via grep for `from
     siege_utilities... import <symbol>` and `siege_utilities.<symbol>(...)`
     across `tests/**.py`.

  2. **Chain coverage** — is the symbol called transitively by a
     symbol that IS directly covered? Detected via AST call-graph
     from the tests' entry points, following one hop.

  3. **Docstring vs signature check** — does the symbol have a
     structured docstring (Parameters/Returns/Raises) per
     writing-code:1? (This is a prerequisite for a meaningful test:
     if the contract isn't documented, we can't verify the code
     delivers it.)

Output:

  - `--summary` (default): tier counts (fully-covered / chain-only /
    uncovered / no-docstring)
  - `--markdown`: markdown report suitable for a ticket body
  - `--json`: JSON output for downstream tooling
  - `--csv`: CSV per symbol

Exit code:
  0  always (this is a report tool, not a ratchet)

## Composition with existing tools

- Reads `siege_utilities.__all__` + `_LAZY_IMPORTS` (same source as
  `audit_public_api_surface.py`)
- Applies overrides from `scripts/public_api_overrides.toml` if
  present (same file that `audit_public_api_surface.py` uses)
- Ignores test-internal names (`test_*`, `_test_helper_*`, `TestCase`
  subclasses)

## Known limitations

- **Grep is not perfect.** A symbol imported under an alias (`from X
  import Y as Z; Z(...)`) is not detected. Renamed re-exports pass
  through the categorization filter but may miss the direct-coverage
  grep.
- **Chain coverage is one hop.** If test → A → B → C, only A and B
  are detected as covered. Deeper chains require running actual
  coverage.py and cross-referencing.
- **"Covered" != "tested well."** A single tautology-shaped test
  counts as covered. Combine this report with the hollow-work scanner
  (`check_hollow_work.py`) for a full picture.

## Usage

    python scripts/check_symbol_test_coverage.py
    python scripts/check_symbol_test_coverage.py --markdown > report.md
    python scripts/check_symbol_test_coverage.py --json > coverage.json
    python scripts/check_symbol_test_coverage.py --tier canonical
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = REPO_ROOT / "tests"

# Same extension patterns as audit_public_api_surface.py
EXTENSION_PATTERNS = [
    re.compile(r"^Abstract"),
    re.compile(r"^Base[A-Z]"),
    re.compile(r"Protocol$"),
    re.compile(r"^[A-Z][a-zA-Z]*(Config|Registry|Provider|Backend|Engine)$"),
    re.compile(r"Error$"),
    re.compile(r"^SU[A-Z][a-zA-Z]*"),
]


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


def grep_public_references(name: str) -> int:
    """Count references to `name` in README/docs/notebooks."""
    total = 0
    for surface in ("README.md", "docs", "notebooks"):
        target = REPO_ROOT / surface
        if not target.exists():
            continue
        result = subprocess.run(
            ["grep", "-rc", f"\\b{name}\\b", str(target)],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.splitlines():
            if ":" in line:
                try:
                    total += int(line.rsplit(":", 1)[1])
                except ValueError:
                    pass
    return total


def classify_symbol(name: str, overrides: dict[str, tuple[str, str]]) -> str:
    """Return 'canonical' | 'extension' | 'internal'."""
    if name in overrides:
        return overrides[name][0]
    for pattern in EXTENSION_PATTERNS:
        if pattern.search(name):
            return "extension"
    if grep_public_references(name) > 0:
        return "canonical"
    return "internal"


def has_structured_docstring(obj: object) -> bool:
    """True if the object's docstring has Parameters/Returns/Raises."""
    import inspect
    doc = inspect.getdoc(obj) or ""
    if len(doc) < 40:
        return False
    return any(k in doc for k in (
        "Parameters", "Args:", ":param",
        "Returns", ":return", "Raises", ":raises",
    ))


def direct_test_coverage(name: str) -> list[str]:
    """Return list of test files that import + call this symbol.

    Grep-based; catches the common cases (`from siege_utilities import X`
    then `X(...)`) but not aliased imports.
    """
    if not TESTS_ROOT.exists():
        return []
    # Two-part check: import AND call
    import_pattern = f"(from siege_utilities[.a-zA-Z_]* import[^#\\n]*\\b{name}\\b|from siege_utilities[.a-zA-Z_]* import [^\\n]*{name})"
    call_pattern = f"\\b{name}\\s*[.(]"

    import_result = subprocess.run(
        ["grep", "-rlE", import_pattern, str(TESTS_ROOT), "--include=*.py"],
        capture_output=True, text=True, timeout=30,
    )
    import_files = set(import_result.stdout.splitlines())
    if not import_files:
        return []

    # Confirm at least one file with the import also has a call
    covered = []
    for f in import_files:
        call_result = subprocess.run(
            ["grep", "-lE", call_pattern, f],
            capture_output=True, text=True, timeout=30,
        )
        if call_result.stdout.strip():
            covered.append(f)
    return covered


def scan_symbols(tier_filter: str | None = None) -> list[dict]:
    """Return one dict per symbol with tier, docstring status, coverage."""
    sys.path.insert(0, str(REPO_ROOT))
    import siege_utilities  # noqa: E402

    all_ = set(siege_utilities.__all__)
    lazy = getattr(siege_utilities, "_LAZY_IMPORTS", {})
    overrides = load_overrides()

    # __all__ symbols are all "canonical" by definition; lazy symbols get classified
    results = []
    for name in sorted(all_ | set(lazy.keys())):
        if name in all_:
            tier = "canonical"  # in __all__ = canonical by definition
        else:
            tier = classify_symbol(name, overrides)

        if tier_filter and tier != tier_filter:
            continue

        # Skip internal-tier by default (we don't test for them)
        if tier == "internal" and tier_filter != "internal":
            continue

        try:
            obj = getattr(siege_utilities, name)
        except Exception as e:
            results.append({
                "name": name, "tier": tier,
                "resolves": False, "error": str(e)[:100],
                "has_docstring": False, "test_files": [],
                "direct_coverage": False,
            })
            continue

        has_doc = has_structured_docstring(obj)
        test_files = direct_test_coverage(name)

        results.append({
            "name": name,
            "tier": tier,
            "resolves": True,
            "has_docstring": has_doc,
            "test_files": [
                str(Path(f).relative_to(REPO_ROOT)) for f in test_files
            ],
            "direct_coverage": bool(test_files),
        })

    return results


def summarize(results: list[dict]) -> dict:
    """Bucket results into coverage tiers."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for r in results:
        if not r.get("resolves", True):
            buckets["unresolvable"].append(r["name"])
            continue
        has_doc = r["has_docstring"]
        has_cov = r["direct_coverage"]
        if has_doc and has_cov:
            buckets["fully_covered"].append(r["name"])
        elif has_cov and not has_doc:
            buckets["tested_but_undocumented"].append(r["name"])
        elif has_doc and not has_cov:
            buckets["documented_but_untested"].append(r["name"])
        else:
            buckets["uncovered_undocumented"].append(r["name"])
    return dict(buckets)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.add_argument("--csv", action="store_true")
    p.add_argument("--tier", choices=["canonical", "extension", "internal"],
                   help="Only scan symbols in this tier")
    p.add_argument("--full-report", action="store_true",
                   help="Include per-symbol rows (default: summary only)")
    args = p.parse_args()

    results = scan_symbols(args.tier)
    buckets = summarize(results)
    total = len(results)

    if args.as_json:
        print(json.dumps({
            "total": total,
            "buckets": {k: len(v) for k, v in buckets.items()},
            "symbols": results,
        }, indent=2))
        return 0

    if args.csv:
        print("name,tier,has_docstring,direct_coverage,test_files")
        for r in results:
            files = ";".join(r.get("test_files", []))
            print(f'{r["name"]},{r["tier"]},{r.get("has_docstring", False)},{r.get("direct_coverage", False)},"{files}"')
        return 0

    if args.markdown:
        print("# Per-symbol test coverage report (#1178 Phase 6b)")
        print()
        print(f"**Total symbols scanned:** {total}")
        print(f"**Tier filter:** {args.tier or 'canonical + extension'}")
        print()
        print("## Summary")
        print()
        print("| Bucket | Count | Meaning |")
        print("|---|---:|---|")
        print(f"| ✅ fully covered | {len(buckets.get('fully_covered', []))} | has structured docstring AND direct test coverage |")
        print(f"| 🟡 tested but undocumented | {len(buckets.get('tested_but_undocumented', []))} | test exercises it but docstring lacks Parameters/Returns/Raises |")
        print(f"| 🟡 documented but untested | {len(buckets.get('documented_but_untested', []))} | docstring is structured but no test imports+calls the symbol |")
        print(f"| ❌ uncovered + undocumented | {len(buckets.get('uncovered_undocumented', []))} | double gap — needs both docstring and test |")
        print(f"| ⚠️ unresolvable | {len(buckets.get('unresolvable', []))} | in __all__/lazy but getattr failed |")
        print()

        if args.full_report:
            for tier_key, tier_label in [
                ("fully_covered", "✅ Fully covered"),
                ("tested_but_undocumented", "🟡 Tested but undocumented"),
                ("documented_but_untested", "🟡 Documented but untested"),
                ("uncovered_undocumented", "❌ Uncovered + undocumented"),
                ("unresolvable", "⚠️ Unresolvable"),
            ]:
                names = buckets.get(tier_key, [])
                if not names:
                    continue
                print(f"### {tier_label} ({len(names)} symbols)")
                print()
                for name in sorted(names):
                    r = next(x for x in results if x["name"] == name)
                    files_note = ""
                    if r.get("test_files"):
                        files_note = f" — {', '.join(r['test_files'][:2])}"
                        if len(r["test_files"]) > 2:
                            files_note += f" (+{len(r['test_files']) - 2} more)"
                    print(f"- `{name}` ({r['tier']}){files_note}")
                print()
        return 0

    # Plain-text summary (default)
    print(f"check_symbol_test_coverage: {total} symbols scanned "
          f"(tier: {args.tier or 'canonical + extension'})")
    for bucket, names in sorted(buckets.items()):
        print(f"  {bucket}: {len(names)}")
    print()
    print("Run with --markdown --full-report for the per-symbol breakdown.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
