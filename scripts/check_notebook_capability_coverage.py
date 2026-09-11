#!/usr/bin/env python3
"""Validate notebook capability coverage inventory.

The inventory is not a grep-based proof that notebooks cover every symbol. It is
an explicit review surface: every top-level package must be classified as a
notebook-demonstrated user surface, support/internal surface, or docs/tests-only
surface with rationale. This prevents new package directories from silently
falling outside the notebook governance conversation.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "siege_utilities"
NOTEBOOK_ROOT = REPO_ROOT / "notebooks"
INVENTORY_PATH = NOTEBOOK_ROOT / "capability_coverage.json"
HYGIENE_TEST = REPO_ROOT / "tests" / "test_notebook_hygiene.py"
EXECUTION_TEST = REPO_ROOT / "tests" / "test_notebooks.py"
VALID_STATUSES = {"demonstrated", "support", "docs_tests"}


def _literal_from_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return ast.literal_eval(node.value)
    raise RuntimeError(f"Could not find {name} assignment in {path}")


def _top_level_packages() -> set[str]:
    return {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }


def _governed_notebooks() -> set[str]:
    hygiene = set(_literal_from_assignment(HYGIENE_TEST, "RE_WRITTEN"))
    groups = _literal_from_assignment(EXECUTION_TEST, "NOTEBOOK_GROUPS")
    execution: set[str] = set()
    for values in groups.values():
        execution.update(values)
    return hygiene & execution


def build_report() -> dict[str, Any]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    packages = inventory.get("packages", {})
    top_level = _top_level_packages()
    governed = _governed_notebooks()

    failures: list[str] = []
    warnings: list[str] = []

    if not isinstance(packages, dict):
        failures.append("inventory packages must be an object")
        packages = {}

    inventory_names = set(packages)
    missing = sorted(top_level - inventory_names)
    extra = sorted(inventory_names - top_level)
    if missing:
        failures.append(f"missing top-level package coverage entries: {', '.join(missing)}")
    if extra:
        failures.append(f"coverage entries without top-level packages: {', '.join(extra)}")

    for name in sorted(inventory_names & top_level):
        entry = packages[name]
        if not isinstance(entry, dict):
            failures.append(f"{name}: entry must be an object")
            continue
        status = entry.get("status")
        notebooks = entry.get("notebooks", [])
        rationale = str(entry.get("rationale", "")).strip()
        if status not in VALID_STATUSES:
            failures.append(
                f"{name}: status must be one of {sorted(VALID_STATUSES)}, got {status!r}"
            )
        if not isinstance(notebooks, list) or not all(isinstance(n, str) for n in notebooks):
            failures.append(f"{name}: notebooks must be a list of strings")
            continue
        missing_notebooks = sorted(n for n in notebooks if not (NOTEBOOK_ROOT / n).exists())
        ungoverned_notebooks = sorted(n for n in notebooks if n not in governed)
        if missing_notebooks:
            failures.append(f"{name}: referenced notebooks do not exist: {missing_notebooks}")
        if ungoverned_notebooks:
            failures.append(f"{name}: referenced notebooks are not live governed notebooks: {ungoverned_notebooks}")
        if status == "demonstrated" and not notebooks:
            failures.append(f"{name}: demonstrated packages must cite at least one governed notebook")
        if status in {"support", "docs_tests"} and not rationale:
            failures.append(f"{name}: {status} entries must include rationale")
        if status != "demonstrated" and notebooks and not rationale:
            warnings.append(f"{name}: non-demonstrated entry cites notebooks without rationale")

    return {
        "inventory": str(INVENTORY_PATH.relative_to(REPO_ROOT)),
        "top_level_package_count": len(top_level),
        "coverage_entry_count": len(inventory_names),
        "governed_notebook_count": len(governed),
        "missing_entries": missing,
        "extra_entries": extra,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--check", action="store_true", help="Fail on invalid coverage inventory")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "packages="
            f"{report['top_level_package_count']} coverage_entries={report['coverage_entry_count']} "
            f"governed_notebooks={report['governed_notebook_count']}"
        )
        print(f"missing_entries={len(report['missing_entries'])} extra_entries={len(report['extra_entries'])}")
        for warning in report["warnings"]:
            print(f"WARN: {warning}")
        for failure in report["failures"]:
            print(f"FAIL: {failure}")

    return 1 if args.check and report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
