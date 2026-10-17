#!/usr/bin/env python3
"""Reject unreviewed writes to final paths in siege_utilities.

Track temporary paths/streams through lexical scopes, assignments, and context
managers. This is a conservative AST guard, not interprocedural proof. Unknown
sinks need a reviewed exception pinned to file, scope, call digest and count;
stale exceptions also fail. No file-wide or name-based exemptions are allowed.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "siege_utilities"
DEFAULT_ALLOWLIST = Path(__file__).with_name("atomic_write_allowlist.json")
ATOMIC = "siege_utilities.files.operations.atomic_write_path"
SERIALIZERS = {"to_parquet": "path", "to_csv": "path_or_buf", "to_file": "filename"}


def call_digest(node):
    """Keep reviewed fingerprints identical across supported Python versions."""
    # Python 3.13 added show_empty=False, changing the default dump for calls
    # without keywords (among other nodes). Explicitly retain the 3.11 form.
    options = {"show_empty": True} if sys.version_info >= (3, 13) else {}
    dumped = ast.dump(node, include_attributes=False, **options)
    return hashlib.sha256(dumped.encode()).hexdigest()


def argument(call, index, keyword):
    if len(call.args) > index:
        return call.args[index]
    return next((kw.value for kw in call.keywords if kw.arg == keyword), None)


class WriteScanner(ast.NodeVisitor):
    """Track only proven temporary destinations, never a variable's spelling."""

    def __init__(self):
        self.aliases = {}
        self.safe = {}
        self.scope = ""
        self.findings = []

    def name(self, node):
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return f"{self.name(node.value)}.{node.attr}"
        return ""

    def kind(self, node):
        if self.name(node) in {"sys.stdout", "sys.stderr", "sys.stdout.buffer", "sys.stderr.buffer"}:
            return "stream"
        if isinstance(node, ast.Name):
            return self.safe.get(node.id)
        if isinstance(node, ast.Attribute) and node.attr == "name" and self.kind(node.value) == "tempfile":
            return "path"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and self.kind(node.left) == "directory":
            # Joining an absolute/unknown component could escape the temp dir.
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
                part = Path(node.right.value)
                if not part.is_absolute() and ".." not in part.parts:
                    return "path"
        if isinstance(node, ast.Call):
            name = self.name(node.func)
            if name in {"str", "Path", "pathlib.Path"} and len(node.args) == 1 and not node.keywords:
                return self.kind(node.args[0])
            if name == "tempfile.NamedTemporaryFile":
                return "tempfile"
            if name in {"tempfile.TemporaryDirectory", "tempfile.mkdtemp"}:
                return "directory"
            if name in {"io.StringIO", "io.BytesIO"}:
                return "stream"
            if name in {"open", "builtins.open", "io.open", "os.fdopen"}:
                if self.kind(argument(node, 0, "fd" if name == "os.fdopen" else "file")):
                    return "stream"
            if isinstance(node.func, ast.Attribute) and node.func.attr == "open":
                if self.kind(node.func.value) in {"path", "tempfile"}:
                    return "stream"
        return None

    def bind(self, target, kind):
        if isinstance(target, ast.Name):
            self.safe.pop(target.id, None)
            self.aliases.pop(target.id, None)
            if kind:
                self.safe[target.id] = kind
        elif isinstance(target, (ast.Tuple, ast.List)):
            for child in target.elts:
                self.bind(child, None)

    def visit_Import(self, node):
        for alias in node.names:
            self.aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    def visit_Assign(self, node):
        self.visit(node.value)
        for target in node.targets:
            kind = self.kind(node.value)
            self.bind(target, kind)
            if isinstance(node.value, ast.Call) and self.name(node.value.func) == "tempfile.mkstemp":
                if isinstance(target, (ast.Tuple, ast.List)) and len(target.elts) == 2:
                    self.bind(target.elts[0], "fd")
                    self.bind(target.elts[1], "path")

    def visit_AnnAssign(self, node):
        if node.value:
            self.visit(node.value)
        self.bind(node.target, self.kind(node.value))

    def visit_AugAssign(self, node):
        self.visit(node.value)
        self.bind(node.target, None)

    def visit_NamedExpr(self, node):
        self.visit(node.value)
        self.bind(node.target, self.kind(node.value))

    def visit_With(self, node):
        bound = []
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                kind = self.kind(item.context_expr)
                if isinstance(item.context_expr, ast.Call) and self.name(item.context_expr.func) == ATOMIC:
                    kind = "path"
                self.bind(item.optional_vars, kind)
                bound.append(item.optional_vars)
        for statement in node.body:
            self.visit(statement)
        # Temp context destinations are no longer valid after context exit.
        for target in bound:
            self.bind(target, None)

    visit_AsyncWith = visit_With

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is not None:
                    self.visit(default)
        old = self.safe, self.aliases, self.scope
        self.safe, self.aliases = {}, self.aliases.copy()
        self.scope = f"{self.scope}.{node.name}".lstrip(".")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                        + [node.args.vararg, node.args.kwarg]):
                if arg is None:
                    continue
                self.bind(ast.Name(id=arg.arg), None)
        for statement in node.body:
            self.visit(statement)
        self.safe, self.aliases, self.scope = old
        self.bind(ast.Name(id=node.name), None)

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef

    def visit_If(self, node):
        self.visit(node.test)
        self.branches([node.body, node.orelse])

    def branches(self, bodies):
        before = self.safe.copy(), self.aliases.copy()
        states = []
        for body in bodies:
            self.safe, self.aliases = before[0].copy(), before[1].copy()
            for statement in body:
                self.visit(statement)
            states.append((self.safe.copy(), self.aliases.copy()))
        self.safe = {k: v for k, v in states[0][0].items() if all(s[0].get(k) == v for s in states)}
        self.aliases = {k: v for k, v in states[0][1].items() if all(s[1].get(k) == v for s in states)}

    def visit_Try(self, node):
        # Exception paths cannot rely on assignments completing in the try.
        self.branches([node.body + node.orelse] + [h.body for h in node.handlers] + [[]])
        for statement in node.finalbody:
            self.visit(statement)

    def visit_For(self, node):
        self.visit(node.iter)
        self.bind(node.target, None)
        self.branches([node.body, []])
        for statement in node.orelse:
            self.visit(statement)

    visit_AsyncFor = visit_For

    def visit_While(self, node):
        self.visit(node.test)
        self.branches([node.body, []])
        for statement in node.orelse:
            self.visit(statement)

    def visit_Call(self, node):
        name = self.name(node.func)
        target = None
        rule = None
        if name in {"open", "builtins.open", "io.open"}:
            mode = argument(node, 1, "mode")
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and any(c in mode.value for c in "wax+"):
                target, rule = argument(node, 0, "file"), "open"
        elif isinstance(node.func, ast.Attribute):
            method = node.func.attr
            if method == "open":
                mode = argument(node, 0, "mode")
                if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and any(c in mode.value for c in "wax+"):
                    target, rule = node.func.value, "open"
            elif method in {"write_text", "write_bytes"}:
                target, rule = node.func.value, method
            elif method in SERIALIZERS:
                target, rule = argument(node, 0, SERIALIZERS[method]), method
                # pandas returns serialized data with a missing/None path.
                if target is None or isinstance(target, ast.Constant) and target.value is None:
                    rule = None
        if rule and not self.kind(target):
            self.findings.append({"line": node.lineno, "scope": self.scope, "rule": rule,
                                  "sha256": call_digest(node), "call": ast.unparse(node)})
        self.generic_visit(node)


def scan_file(path):
    source = path.read_text(encoding="utf-8")
    if not source.strip():
        # Empty namespace __init__ files are legitimate; ast.parse still runs.
        source = "\n"
    scanner = WriteScanner()
    scanner.visit(ast.parse(source, filename=str(path)))
    return scanner.findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--allowlist", type=Path)
    args = parser.parse_args(argv)
    allow_path = args.allowlist
    if allow_path is None and args.root.resolve() == DEFAULT_ROOT.resolve():
        allow_path = DEFAULT_ALLOWLIST
    try:
        entries = json.loads(allow_path.read_text()) if allow_path else []
        allowed = {}
        fields = ("file", "scope", "rule", "sha256")
        for entry in entries:
            key = tuple(entry[field] for field in fields)
            if key in allowed or not entry["reason"].strip() or not isinstance(entry["count"], int) or entry["count"] < 1:
                raise ValueError("invalid or duplicate allow-list entry")
            allowed[key] = entry["count"]
        paths = sorted(args.root.rglob("*.py"))
        if not paths:
            raise ValueError("No Python sources found")
        seen = Counter()
        unlisted = 0
        for path in paths:
            for finding in scan_file(path):
                finding["file"] = path.relative_to(args.root).as_posix()
                key = tuple(finding[field] for field in fields)
                seen[key] += 1
                if seen[key] > allowed.get(key, 0):
                    print(f"{finding['file']}:{finding['line']}: {finding['rule']} ({finding['scope']}): {finding['call']}")
                    unlisted += 1
        stale = sum(seen[key] < count for key, count in allowed.items())
        for key, count in allowed.items():
            if seen[key] < count:
                print(f"{key[0]}: stale allow-list entry ({key[1]}, {key[2]})")
    except (OSError, UnicodeError, SyntaxError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"FAIL: cannot complete atomic-write scan ({type(exc).__name__}: {exc})")
        return 1
    print(f"{'FAIL' if unlisted or stale else 'PASS'}: {unlisted} unlisted atomic writes; "
          f"{stale} stale exceptions; {sum(allowed.values())} reviewed exceptions; {len(paths)} files")
    return int(bool(unlisted or stale))


if __name__ == "__main__":
    raise SystemExit(main())
