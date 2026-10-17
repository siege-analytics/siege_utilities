#!/usr/bin/env python3
"""Reject unsafe credential writes, write-then-chmod, and fixed /tmp paths.

Scan library Python sources. A credential scope contains a dict key, dict()
keyword, or subscript matching token|secret|password|api_key|private_key|refresh.
Known persistence entry points are also protected when their payload comes from
another function or model. Each direct sink is checked independently: calling
secure_write_text elsewhere in the function does not exempt an unsafe write.
This guard is syntactic, not general interprocedural data-flow analysis.

The allow-list pins individual findings by file, scope, rule and source digest,
with a reason. Stale entries fail. Unreadable/invalid/empty sources fail closed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re


SECRET = re.compile(r"token|secret|password|api_key|private_key|refresh", re.I)
PERSISTENCE = {
    "save_facebook_account_profile", "save_instagram_account_profile",
    "save_x_account_profile", "save_ga_account_profile", "_save_credentials",
    "save_connection_profile", "save_user_profile", "save_client_profile",
    "create_temporary_service_account_file", "export_config_yaml",
    "export_entities", "to_yaml", "save_database_config",
}
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "siege_utilities"
DEFAULT_ALLOWLIST = Path(__file__).with_name("secure_write_allowlist.json")


def _name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value, aliases)}.{node.attr}"
    return ""


def _arg(call: ast.Call, index: int, keyword: str):
    if len(call.args) > index:
        return call.args[index]
    return next((kw.value for kw in call.keywords if kw.arg == keyword), None)


def _constant(node):
    return node.value if isinstance(node, ast.Constant) else None


def _scope_nodes(node):
    """Walk a scope without attributing nested functions' payloads to it."""
    yield node
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _scope_nodes(child)


def _has_secret(nodes) -> bool:
    for node in nodes:
        keys = []
        if isinstance(node, ast.Dict):
            keys = [_constant(key) for key in node.keys]
        elif isinstance(node, ast.Subscript):
            keys = [_constant(node.slice)]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
            keys = [kw.arg for kw in node.keywords]
        if any(isinstance(key, str) and SECRET.search(key) for key in keys):
            return True
    return False


def _write_target(node, aliases):
    if not isinstance(node, ast.Call):
        return None
    name = _name(node.func, aliases)
    if name in {"open", "builtins.open", "io.open"} or name.endswith(".open"):
        mode = _arg(node, 1 if name in {"open", "builtins.open", "io.open"} else 0, "mode")
        if isinstance(_constant(mode), str) and any(c in mode.value for c in "wax+"):
            return (_arg(node, 0, "file") if name in {"open", "builtins.open", "io.open"}
                    else node.func.value)
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes"}:
        return node.func.value
    if name in {"json.dump", "yaml.dump", "yaml.safe_dump"}:
        return _arg(node, 1, "fp" if name == "json.dump" else "stream")
    return None


def _path_key(node, aliases):
    if isinstance(node, ast.Call) and _name(node.func, aliases) in {"Path", "pathlib.Path", "str"} and node.args:
        node = node.args[0]
    return ast.dump(node, include_attributes=False)


def scan_file(path: Path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    findings = {}

    def report(node, scope, rule):
        digest = hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
        findings[(node.lineno, rule)] = (node.lineno, scope, rule, digest)

    def visit(scope, name):
        nodes = list(_scope_nodes(scope))
        sensitive = _has_secret(nodes) or name.split(".")[-1] in PERSISTENCE
        for node in nodes:
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/tmp/"):
                report(node, name, "fixed-tmp-path")
            if sensitive and _write_target(node, aliases) is not None:
                report(node, name, "credential-write")
            # Adjacent statements, including a with-open block then chmod.
            for _, body in ast.iter_fields(node):
                if not isinstance(body, list):
                    continue
                for before, after in zip(body, body[1:]):
                    if not isinstance(after, ast.Expr) or not isinstance(after.value, ast.Call):
                        continue
                    call = after.value
                    if _name(call.func, aliases) != "os.chmod" or _constant(_arg(call, 1, "mode")) != 0o600:
                        continue
                    path_arg = _arg(call, 0, "path")
                    if path_arg is None or not isinstance(before, ast.AST):
                        continue
                    targets = [_write_target(n, aliases) for n in ast.walk(before)]
                    if any(t is not None and _path_key(t, aliases) == _path_key(path_arg, aliases) for t in targets):
                        report(call, name, "write-then-chmod")
        for node in nodes:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit(child, f"{name}.{child.name}" if name else child.name)

    visit(tree, "")
    return sorted(findings.values())


def main(argv: list[str] | None = None) -> int:
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
        for entry in entries:
            key = tuple(entry[field] for field in ("file", "scope", "rule", "sha256"))
            if not entry["reason"].strip() or key in allowed:
                raise ValueError("invalid or duplicate allow-list entry")
            allowed[key] = False
        paths = sorted(args.root.rglob("*.py"))
        if not paths:
            raise ValueError("No Python sources found")
        failures = 0
        for path in paths:
            relative = path.relative_to(args.root).as_posix()
            for line, scope, rule, digest in scan_file(path):
                key = (relative, scope, rule, digest)
                if key in allowed:
                    allowed[key] = True
                else:
                    print(f"{relative}:{line}: {rule} ({scope or '<module>'})")
                    failures += 1
        for key, used in allowed.items():
            if not used:
                print(f"{key[0]}:1: stale allow-list entry ({key[1]}, {key[2]})")
                failures += 1
    except (OSError, UnicodeError, SyntaxError, ValueError, KeyError, TypeError) as exc:
        print(f"{getattr(exc, 'filename', None) or args.root}:{getattr(exc, 'lineno', None) or 1}: cannot complete secure-write scan ({type(exc).__name__})")
        return 1
    print(f"{'FAIL' if failures else 'PASS'}: {failures} secure-write violation(s) in {len(paths)} files")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
