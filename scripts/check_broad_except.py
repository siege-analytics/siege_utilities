#!/usr/bin/env python3
"""Enforce SU-1: no broad ``except Exception`` or bare ``except:`` catches.

AST-walks every source file under ``siege_utilities/`` and reports every
handler that catches ``Exception`` (or uses a bare ``except:``) without
unconditionally re-raising.  These are SU-1 violations because they
swallow errors and return valid-shaped empty results, making failures
indistinguishable from success.

Exemptions (not reported):
- ``except Exception`` / bare ``except:`` whose body is a single
  ``raise`` (re-raise) — these are cleanup-style handlers.
- ``except ImportError`` / ``except ModuleNotFoundError`` flag guards
  (``HAS_X = False``).
- Lines annotated with ``# noqa: SU1``.

Usage::

    python scripts/check_broad_except.py           # violations only
    python scripts/check_broad_except.py --report   # all handlers
    python scripts/check_broad_except.py --json      # machine-readable

Exits 0 when clean, 1 when violations found.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path


def _enclosing_function(ancestors: list[ast.AST]) -> str:
    """Walk ancestor chain to find the nearest enclosing function name."""
    for node in reversed(ancestors):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return "<module>"


def _is_unconditional_reraise(body: list[ast.stmt]) -> bool:
    """True if the handler body unconditionally re-raises.

    Catches two patterns:
    1. Body is a single ``raise`` (bare re-raise).
    2. Body is N statements ending with ``raise`` where none of the
       preceding statements are return/yield/break/continue (i.e. the
       raise is always reached on the non-exception path).
    """
    if not body:
        return False
    last = body[-1]
    if not isinstance(last, ast.Raise):
        return False
    for stmt in body[:-1]:
        if isinstance(stmt, (ast.Return, ast.Yield, ast.YieldFrom)):
            return False
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Yield, ast.YieldFrom)):
            return False
        if isinstance(stmt, (ast.Break, ast.Continue)):
            return False
    return True


def _has_noqa_su1(source_lines: list[str], lineno: int) -> bool:
    """Check whether the except line has a ``# noqa: SU1`` comment."""
    if lineno < 1 or lineno > len(source_lines):
        return False
    line = source_lines[lineno - 1]
    return "noqa: SU1" in line or "noqa:SU1" in line


def _is_broad_handler(node: ast.ExceptHandler) -> bool:
    """True if the handler catches ``Exception`` or is a bare ``except:``."""
    if node.type is None:
        return True
    if isinstance(node.type, ast.Name) and node.type.id == "Exception":
        return True
    if isinstance(node.type, ast.Tuple):
        for elt in node.type.elts:
            if isinstance(elt, ast.Name) and elt.id == "Exception":
                return True
    return False


def _is_import_guard(node: ast.ExceptHandler) -> bool:
    """ImportError/ModuleNotFoundError flag guard (``HAS_X = False``)."""
    if node.type is None:
        return False
    names: list[str] = []
    if isinstance(node.type, ast.Name):
        names.append(node.type.id)
    elif isinstance(node.type, ast.Tuple):
        for elt in node.type.elts:
            if isinstance(elt, ast.Name):
                names.append(elt.id)
    if "ImportError" not in names and "ModuleNotFoundError" not in names:
        return False
    if len(node.body) == 1:
        stmt = node.body[0]
        if isinstance(stmt, ast.Assign):
            if isinstance(stmt.value, ast.Constant) and stmt.value.value is False:
                return True
    return False


class _AncestorTracker(ast.NodeVisitor):
    """AST visitor that tracks the ancestor chain for each node."""

    def __init__(self) -> None:
        self.ancestors: list[ast.AST] = []
        self.handlers: list[tuple[ast.ExceptHandler, str]] = []

    def generic_visit(self, node: ast.AST) -> None:
        self.ancestors.append(node)
        super().generic_visit(node)
        self.ancestors.pop()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        func_name = _enclosing_function(self.ancestors)
        self.handlers.append((node, func_name))
        self.generic_visit(node)


def scan_file(source_path: Path) -> list[dict]:
    """Scan a single file for SU-1 violations.

    Returns a list of dicts with keys: file, line, handler, function, exempt, reason.
    """
    try:
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    source_lines = source.splitlines()

    visitor = _AncestorTracker()
    visitor.visit(tree)

    results: list[dict] = []
    for handler, func_name in visitor.handlers:
        if not _is_broad_handler(handler):
            continue

        if _is_import_guard(handler):
            continue

        handler_desc = "bare except" if handler.type is None else "except Exception"
        lineno = handler.lineno

        exempt = False
        reason = ""

        if _is_unconditional_reraise(handler.body):
            exempt = True
            reason = "unconditional re-raise"
        elif _has_noqa_su1(source_lines, lineno):
            exempt = True
            reason = "noqa: SU1"

        results.append({
            "file": str(source_path),
            "line": lineno,
            "handler": handler_desc,
            "function": func_name,
            "exempt": exempt,
            "reason": reason,
        })

    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check for broad except handlers (SU-1)."
    )
    ap.add_argument(
        "--report",
        action="store_true",
        help="Show all broad handlers, including exempt ones.",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON.",
    )
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    src_root = repo / "siege_utilities"

    if not src_root.is_dir():
        print(f"ERROR: source root not found: {src_root}", file=sys.stderr)
        return 1

    modules = sorted(
        p for p in src_root.rglob("*.py")
        if "__pycache__" not in p.parts
    )

    all_findings: list[dict] = []
    for mod_path in modules:
        rel = mod_path.relative_to(repo)
        findings = scan_file(mod_path)
        for f in findings:
            f["file"] = str(rel)
        all_findings.extend(findings)

    violations = [f for f in all_findings if not f["exempt"]]
    display = all_findings if args.report else violations

    if args.json_output:
        print(json.dumps(display, indent=2))
        return 1 if violations else 0

    if display:
        print(
            f"{'File':<55s} {'Line':>5s}  {'Handler':<18s} "
            f"{'Function':<30s} {'Status':>8s}"
        )
        print("-" * 120)
        for f in display:
            status = "exempt" if f["exempt"] else "VIOLN"
            reason = f"  ({f['reason']})" if f["reason"] else ""
            print(
                f"{f['file']:<55s} {f['line']:>5d}  {f['handler']:<18s} "
                f"{f['function']:<30s} {status:>8s}{reason}"
            )

    total_broad = len(all_findings)
    exempt_count = sum(1 for f in all_findings if f["exempt"])
    violation_count = len(violations)

    print()
    print(
        f"Scanned {len(modules)} modules: {total_broad} broad handlers found, "
        f"{exempt_count} exempt, {violation_count} violations."
    )

    if violations:
        print(
            f"\nFAIL — {violation_count} SU-1 violation(s).\n"
            "Narrow each `except Exception` to the specific exceptions that "
            "can actually be raised (e.g., OSError, ValueError, KeyError).\n"
            "If a broad catch is genuinely necessary, add `# noqa: SU1` with "
            "a comment explaining why."
        )
        return 1

    print("\nOK — no SU-1 broad-exception violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
