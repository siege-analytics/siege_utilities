#!/usr/bin/env python3
"""Scan a Python tree for blocking I/O calls that lack a timeout kwarg.

Evidence-gathering tool for the v2.6.0 writing-code:15 rule. Run against
any Python repo:

    python3 scan_unbounded_io.py <path> [--exclude-tests]

Reports each violation as ``<path>:<line>: <call> -- missing timeout``
and exits 1 if any violations are found, 0 otherwise.

The scanner is conservative: it flags only the well-known surfaces
listed below where 'timeout' is the canonical kwarg name. False
positives are preferred to false negatives -- a reviewer can dismiss a
false positive with a one-line comment; a false negative ships a bug.

Targeted surfaces:
  - subprocess.run / Popen.communicate / Popen.wait
  - requests.{get,post,put,delete,head,patch,request}
  - httpx.{get,post,...}
  - urllib.request.urlopen
  - socket.create_connection
  - sqlite3.connect (param is also 'timeout')
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterator


# (module-prefix, attr_name) pairs we recognize. Module-prefix matches
# the LEAF of the dotted attribute chain; we'll walk back to confirm.
SUBPROCESS_FUNCS = {"run", "call", "check_call", "check_output", "communicate", "wait"}
REQUESTS_FUNCS = {"get", "post", "put", "delete", "head", "patch", "request"}
HTTPX_FUNCS = REQUESTS_FUNCS
URLLIB_FUNCS = {"urlopen"}
SOCKET_FUNCS = {"create_connection"}
SQLITE_FUNCS = {"connect"}


def _leftmost_name(node: ast.AST) -> str | None:
    """Return the leftmost Name in an attribute chain, or None."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _attr_chain(node: ast.Attribute) -> str:
    """Return the dotted attribute chain as a string."""
    parts: list[str] = [node.attr]
    cur: ast.AST = node.value
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _check_call(call: ast.Call) -> str | None:
    """Return the rule violation label, or None if call is fine."""
    func = call.func
    # Resolve the function name + likely module
    if not isinstance(func, ast.Attribute):
        return None
    attr = func.attr
    leftmost = _leftmost_name(func)
    chain = _attr_chain(func)

    # Map to canonical rule label
    label: str | None = None
    if leftmost == "subprocess" and attr in SUBPROCESS_FUNCS:
        label = f"subprocess.{attr}"
    elif leftmost == "requests" and attr in REQUESTS_FUNCS:
        label = f"requests.{attr}"
    elif leftmost == "httpx" and attr in HTTPX_FUNCS:
        label = f"httpx.{attr}"
    elif chain.endswith("urllib.request.urlopen") or (leftmost == "urllib" and attr == "urlopen"):
        label = "urllib.request.urlopen"
    elif leftmost == "socket" and attr in SOCKET_FUNCS:
        label = f"socket.{attr}"
    elif leftmost == "sqlite3" and attr in SQLITE_FUNCS:
        label = f"sqlite3.{attr}"

    if label is None:
        return None

    # Does the call have a timeout kwarg?
    for kw in call.keywords:
        if kw.arg == "timeout":
            return None  # explicit timeout present (incl. timeout=None)
    return label


def scan_file(path: Path) -> Iterator[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            label = _check_call(node)
            if label is not None:
                yield node.lineno, label


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--exclude-tests", action="store_true",
                   help="Skip tests/, test_*.py, *_test.py")
    p.add_argument("--exclude", action="append", default=[],
                   help="Glob to exclude (repeatable)")
    args = p.parse_args(argv)

    total = 0
    files_with_violations = 0
    for py in sorted(args.root.rglob("*.py")):
        rel = py.relative_to(args.root)
        if any(rel.match(g) for g in args.exclude):
            continue
        if args.exclude_tests and (
            rel.parts and rel.parts[0] == "tests"
            or py.name.startswith("test_")
            or py.name.endswith("_test.py")
        ):
            continue
        hits = list(scan_file(py))
        if hits:
            files_with_violations += 1
            for line, label in hits:
                print(f"{rel}:{line}: {label} -- missing timeout=")
                total += 1
    print(f"\n--- summary: {total} violation(s) across {files_with_violations} file(s) ---",
          file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
