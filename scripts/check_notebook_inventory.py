#!/usr/bin/env python3
"""Report and enforce notebook inventory/governance/path-leak truth.

This is intentionally lightweight: it does not execute notebooks. It makes the
notebook system's claimed shape scriptable so docs and governance cannot drift
silently.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_ROOT = REPO_ROOT / "notebooks"
HYGIENE_TEST = REPO_ROOT / "tests" / "test_notebook_hygiene.py"
EXECUTION_TEST = REPO_ROOT / "tests" / "test_notebooks.py"

HOME_PATH_RE = re.compile(r"(/Users/[^\s'\"),]+|/home/[^\s'\"),]+|[A-Za-z]:\\\\Users\\\\[^\s'\"),]+)")


def _notebook_paths() -> list[Path]:
    return sorted(NOTEBOOK_ROOT.rglob("*.ipynb"))


def _rel_notebook(path: Path) -> str:
    return path.relative_to(NOTEBOOK_ROOT).as_posix()


def _is_archive(path: Path) -> bool:
    return "archive" in path.relative_to(NOTEBOOK_ROOT).parts


def _literal_from_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return ast.literal_eval(node.value)
    raise RuntimeError(f"Could not find {name} assignment in {path}")


def hygiene_notebooks() -> set[str]:
    return set(_literal_from_assignment(HYGIENE_TEST, "RE_WRITTEN"))


def execution_notebooks() -> set[str]:
    groups = _literal_from_assignment(EXECUTION_TEST, "NOTEBOOK_GROUPS")
    result: set[str] = set()
    for values in groups.values():
        result.update(values)
    return result


def path_leaks(paths: Iterable[Path]) -> list[dict[str, object]]:
    leaks: list[dict[str, object]] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        rel = _rel_notebook(path)
        for cell_index, cell in enumerate(data.get("cells", [])):
            text = json.dumps(cell, ensure_ascii=False)
            matches = sorted(set(HOME_PATH_RE.findall(text)))
            if matches:
                leaks.append({"notebook": rel, "cell": cell_index, "matches": matches})
    return leaks


def build_report() -> dict[str, object]:
    all_paths = _notebook_paths()
    live_paths = [p for p in all_paths if not _is_archive(p)]
    archive_paths = [p for p in all_paths if _is_archive(p)]
    live = {_rel_notebook(p) for p in live_paths}
    hygiene = hygiene_notebooks()
    execution = execution_notebooks()
    governed = hygiene | execution
    return {
        "total": len(all_paths),
        "live": len(live_paths),
        "archive": len(archive_paths),
        "live_notebooks": sorted(live),
        "archive_notebooks": sorted(_rel_notebook(p) for p in archive_paths),
        "hygiene_count": len(hygiene),
        "execution_count": len(execution),
        "ungoverned_live_notebooks": sorted(live - governed),
        "hygiene_only_notebooks": sorted(hygiene - execution),
        "execution_only_notebooks": sorted(execution - hygiene),
        "missing_hygiene_files": sorted(hygiene - live),
        "missing_execution_files": sorted(execution - live),
        "path_leaks": path_leaks(live_paths),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--check", action="store_true", help="Fail on missing files or local home path leaks")
    parser.add_argument(
        "--require-all-live-governed",
        action="store_true",
        help="Also fail if any live notebook is outside hygiene/execution governance",
    )
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"total={report['total']} live={report['live']} archive={report['archive']}")
        print(f"hygiene={report['hygiene_count']} execution={report['execution_count']}")
        print("ungoverned_live_notebooks:")
        for rel in report["ungoverned_live_notebooks"]:
            print(f"  - {rel}")
        print(f"path_leaks={len(report['path_leaks'])}")
        for leak in report["path_leaks"][:20]:
            print(f"  - {leak['notebook']} cell {leak['cell']}: {', '.join(leak['matches'])}")

    failures: list[str] = []
    if report["missing_hygiene_files"]:
        failures.append("hygiene list references missing notebooks")
    if report["missing_execution_files"]:
        failures.append("execution list references missing notebooks")
    if report["path_leaks"]:
        failures.append("live notebook outputs/source contain local home paths")
    if args.require_all_live_governed and report["ungoverned_live_notebooks"]:
        failures.append("live notebooks exist outside hygiene/execution governance")

    if args.check and failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
