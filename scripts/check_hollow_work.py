#!/usr/bin/env python3
"""Aggregate runner for hollow-work detection across production Python.

Runs four AST-based checks that catch the structural-emptiness kernel
of hollow-work failure modes (per the modernization session's
hollow-work-prevention memo, adopted as shelf edits in claude-configs-
public#649):

  1. **TODO/FIXME/HACK/XXX without ticket ref** — writing-code:19
     (new shelf rule shipped in claude-configs-public#649). Bare
     placeholder markers in production code without a ticket reference
     or inline-justification block are shipped-incomplete markers with
     no tracking that would ever cause "later" to arrive.

  2. **Tautology asserts** — writing-tests structural smell
     `tautology_assert` (also shipped in #649). Tests whose asserts
     are trivially satisfied by construction cannot fail on any revert
     of the code under test.

  3. **Empty function bodies (pass-only)** — writing-code:11 (silent
     processes must produce observable signals). An empty body fails
     the observable-signal floor.

  4. **NotImplementedError without ticket ref** — writing-code:19
     special case. Same discipline as TODO markers.

The scanner is a RUNNER of existing shelf rules, not a new rule. Each
finding cites the shelf rule it enforces.

## Carve-outs

Three well-defined carve-outs prevent false positives:

- **Abstract methods / Protocol classes** (writing-code:11 carve-out).
  `class Foo(Protocol):` methods and `@abstractmethod`-decorated
  methods legitimately have `pass` or `...` bodies. The scanner
  detects these via AST and skips.

- **Test files** (writing-code:19 carve-out). `tests/**` may carry
  TODO/FIXME markers without ticket ref — test-suite TODOs often
  track "add case when the underlying fix lands" and forcing ticket-
  ref discipline in tests creates noise.

- **Deferred-generation code** (`__init__.py` with `__getattr__`
  lazy shims, `types.SimpleNamespace()`-only bodies). The scanner
  skips module-level `pass` in `__init__.py` files whose body is
  otherwise empty (marker-only files).

## Usage

    python scripts/check_hollow_work.py           # scan siege_utilities/
    python scripts/check_hollow_work.py --strict  # exit non-zero on any hit
    python scripts/check_hollow_work.py --path P  # scan a specific path

Exit code:
    0  No hollow-work markers found (or --strict absent and only warnings).
    1  --strict AND at least one hit found.

Ratcheted per writing-rules:1: run advisory initially, promote to
blocking after per-project cleanup. siege_utilities as of 2026-08-27
has zero TODO/FIXME/HACK markers — meaning the discipline is
achievable and the scanner should exit clean on develop.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parent.parent

# writing-code:19 markers
MARKER_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
TICKET_REF_RE = re.compile(r"#\d+")


def is_test_path(path: Path) -> bool:
    """writing-code:19 carve-out — test files exempt from TODO/FIXME/HACK."""
    return "tests" in path.parts


def is_abstract_or_protocol(node: ast.FunctionDef | ast.AsyncFunctionDef,
                             enclosing_class: ast.ClassDef | None) -> bool:
    """writing-code:11 carve-out — abstract / Protocol methods can be empty."""
    # @abstractmethod / @abc.abstractmethod
    for dec in node.decorator_list:
        name = None
        if isinstance(dec, ast.Name):
            name = dec.id
        elif isinstance(dec, ast.Attribute):
            name = dec.attr
        if name in ("abstractmethod", "abstractproperty", "abstractclassmethod",
                    "abstractstaticmethod"):
            return True

    # Class inherits from Protocol / typing.Protocol
    if enclosing_class is not None:
        for base in enclosing_class.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            elif isinstance(base, ast.Subscript):
                if isinstance(base.value, ast.Name):
                    base_name = base.value.id
                elif isinstance(base.value, ast.Attribute):
                    base_name = base.value.attr
            if base_name in ("Protocol", "ABC", "ABCMeta"):
                return True
    return False


def check_todo_markers(path: Path, source: str) -> Iterator[str]:
    """Check 1: TODO/FIXME/HACK/XXX markers without ticket ref (writing-code:19)."""
    if is_test_path(path):
        return
    lines = source.split("\n")
    for i, line in enumerate(lines, start=1):
        m = MARKER_RE.search(line)
        if not m:
            continue
        # Look at the marker line + previous line for ticket ref
        window = line + "\n" + (lines[i - 2] if i > 1 else "")
        if TICKET_REF_RE.search(window):
            continue
        # Also accept explicit inline-justification block (writing-code:19 carve-out)
        # by looking for a "Reason:" / "Rationale:" keyword on the marker line
        if re.search(r"\b(Reason|Rationale|Justification|Because):", line):
            continue
        yield f"{path}:{i}: {m.group(0)} without ticket-ref (writing-code:19)"


def check_tautology_asserts(path: Path, tree: ast.Module) -> Iterator[str]:
    """Check 2: tautology asserts (writing-tests tautology_assert smell)."""
    if not is_test_path(path):
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        t = node.test
        # assert True / assert 1 / assert "non-empty"
        if isinstance(t, ast.Constant) and t.value:
            yield f"{path}:{node.lineno}: assert <constant-truthy> (tautology_assert)"
            continue
        # assert x == x / assert x is x
        if (isinstance(t, ast.Compare)
                and len(t.comparators) == 1
                and isinstance(t.left, ast.Name)
                and isinstance(t.comparators[0], ast.Name)
                and t.left.id == t.comparators[0].id):
            op = type(t.ops[0]).__name__
            yield f"{path}:{node.lineno}: assert <name> {op} <same-name> (tautology_assert)"


def _collect_function_class_pairs(
    tree: ast.Module,
) -> Iterator[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.ClassDef | None]]:
    """Walk the tree yielding (function_node, enclosing_class_or_None) pairs."""
    def walk(node: ast.AST, enclosing_class: ast.ClassDef | None) -> Iterator:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node, enclosing_class
            for child in ast.iter_child_nodes(node):
                yield from walk(child, None)  # nested funcs lose class context
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                yield from walk(child, node)
        else:
            for child in ast.iter_child_nodes(node):
                yield from walk(child, enclosing_class)

    for pair in walk(tree, None):
        yield pair


def check_empty_bodies(path: Path, tree: ast.Module) -> Iterator[str]:
    """Check 3: pass-only function bodies (writing-code:11 signal floor)."""
    if is_test_path(path):
        return
    for fn, cls in _collect_function_class_pairs(tree):
        if is_abstract_or_protocol(fn, cls):
            continue
        body = fn.body
        # Skip docstring-only bodies
        if (len(body) == 1 and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            continue
        # Detect (docstring? + pass) or (just pass) or (just Ellipsis)
        stmts = body[:]
        if (stmts and isinstance(stmts[0], ast.Expr)
                and isinstance(stmts[0].value, ast.Constant)
                and isinstance(stmts[0].value.value, str)):
            stmts = stmts[1:]  # strip docstring
        if len(stmts) == 1 and isinstance(stmts[0], ast.Pass):
            yield f"{path}:{fn.lineno}: def {fn.name}() has pass-only body (writing-code:11)"
        elif (len(stmts) == 1 and isinstance(stmts[0], ast.Expr)
              and isinstance(stmts[0].value, ast.Constant)
              and stmts[0].value.value is ...):
            yield f"{path}:{fn.lineno}: def {fn.name}() has ellipsis-only body (writing-code:11)"


def check_notimplemented_no_ref(path: Path, tree: ast.Module, source: str) -> Iterator[str]:
    """Check 4: raise NotImplementedError without ticket ref (writing-code:19)."""
    if is_test_path(path):
        return
    lines = source.split("\n")
    for fn, cls in _collect_function_class_pairs(tree):
        if is_abstract_or_protocol(fn, cls):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Raise):
                continue
            exc = node.exc
            exc_name = None
            if isinstance(exc, ast.Call):
                if isinstance(exc.func, ast.Name):
                    exc_name = exc.func.id
                elif isinstance(exc.func, ast.Attribute):
                    exc_name = exc.func.attr
            elif isinstance(exc, ast.Name):
                exc_name = exc.id
            if exc_name != "NotImplementedError":
                continue
            # Look for ticket ref on the raise line or preceding 5 lines
            start = max(0, node.lineno - 5)
            window = "\n".join(lines[start:node.lineno])
            if TICKET_REF_RE.search(window):
                continue
            yield f"{path}:{node.lineno}: raise NotImplementedError without ticket-ref in preceding 5 lines (writing-code:19)"


def scan_file(path: Path) -> list[str]:
    """Run all 4 checks on a single file. Returns list of finding strings."""
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    findings: list[str] = []
    findings.extend(check_todo_markers(path, source))
    findings.extend(check_tautology_asserts(path, tree))
    findings.extend(check_empty_bodies(path, tree))
    findings.extend(check_notimplemented_no_ref(path, tree, source))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="siege_utilities",
                        help="Root path to scan (default: siege_utilities)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero on any finding (default: report only)")
    args = parser.parse_args()

    root = REPO_ROOT / args.path if not Path(args.path).is_absolute() else Path(args.path)
    if not root.exists():
        print(f"ERROR: {root} does not exist", file=sys.stderr)
        return 1

    files = sorted(root.rglob("*.py"))
    findings: list[str] = []
    for path in files:
        if "__pycache__" in path.parts:
            continue
        findings.extend(scan_file(path))

    print(f"check_hollow_work: scanned {len(files)} files under {root}")
    if findings:
        print(f"{len(findings)} finding(s):")
        for f in findings:
            print(f"  {f}")
        if args.strict:
            print("\n--strict: failing due to findings above.")
            return 1
    else:
        print("OK: no hollow-work markers found.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
