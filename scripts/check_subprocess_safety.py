#!/usr/bin/env python3
"""Reject shell execution in the published library using AST inspection.

Run ``python scripts/check_subprocess_safety.py [root]``. The default root is
siege_utilities/. Exits 1 for subprocess calls with shell other than literal
False, or any os.system/os.popen call. Import aliases and from-imports are
recognized; comments and strings are ignored. This is a static class guard,
not data-flow analysis of dynamically assigned callables or **kwargs.
Unreadable or unparseable sources fail the check instead of being skipped.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _qualified_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return f"{_qualified_name(node.value, aliases)}.{node.attr}"
    return ""


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Return line numbers and violations; propagate read and parse errors."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"subprocess", "os"}:
                    aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module in {"subprocess", "os"}:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _qualified_name(node.func, aliases)
        if name in {"os.system", "os.popen"}:
            violations.append((node.lineno, f"{name} is forbidden; use argv execution"))
        elif name.startswith("subprocess.") or name == "Popen":
            for keyword in node.keywords:
                if keyword.arg == "shell" and not (
                    isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                ):
                    violations.append((node.lineno, f"{name}: shell must be literal False"))
    return sorted(violations)


def main(argv: list[str] | None = None) -> int:
    """Scan a source tree and return nonzero when forbidden calls are found."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[1] / "siege_utilities",
    )
    root = parser.parse_args(argv).root
    sources = sorted(root.rglob("*.py"))
    if not sources:
        raise ValueError(f"No Python sources found under {root}")
    total = 0
    for path in sources:
        for line, message in scan_file(path):
            print(f"{path.relative_to(root)}:{line}: {message}")
            total += 1
    status = "FAIL" if total else "PASS"
    print(f"{status}: {total} subprocess safety violation(s) in {len(sources)} files")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
