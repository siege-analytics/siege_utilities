#!/usr/bin/env python3
"""Reject secret-named plain string fields exposed by generated representations.

Scan every Python module under siege_utilities/ by default. BaseModel,
NamedTuple and dataclass fields (including inherited models and import aliases)
must use SecretStr or field-level repr=False. Optional, union, Annotated and
quoted string annotations are recognized. This is a static class guard, not
analysis of dynamically constructed models or runtime annotation changes.
Unreadable or unparseable sources fail instead of being skipped.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re

SECRET_NAME = re.compile(
    r"password|secret|token|api_key|private_key|client_secret|refresh|"
    r"google_analytics_key|facebook_business_key", re.IGNORECASE,
)
MODEL_BASES = {"pydantic.BaseModel", "pydantic.main.BaseModel", "typing.NamedTuple",
               "typing_extensions.NamedTuple"}
DATACLASSES = {"dataclasses.dataclass", "pydantic.dataclasses.dataclass"}


def _name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value, aliases)}.{node.attr}"
    return ""


def _unquote(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return ast.parse(node.value, mode="eval").body
    return node


def _plain_string(node: ast.AST, aliases: dict[str, str]) -> bool:
    node = _unquote(node)
    if _name(node, aliases) in {"str", "builtins.str"}:
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _plain_string(node.left, aliases) or _plain_string(node.right, aliases)
    if isinstance(node, ast.Subscript):
        name = _name(node.value, aliases)
        args = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        if name in {"typing.Annotated", "typing_extensions.Annotated"}:
            return _plain_string(args[0], aliases)
        if name in {"typing.Optional", "typing.Union"}:
            return any(_plain_string(arg, aliases) for arg in args)
    return False


def _repr_disabled(node: ast.AST | None, aliases: dict[str, str]) -> bool:
    if node is None:
        return False
    node = _unquote(node)
    if isinstance(node, ast.Call) and _name(node.func, aliases) in {
        "pydantic.Field", "pydantic.fields.Field", "dataclasses.field",
    }:
        return any(kw.arg == "repr" and isinstance(kw.value, ast.Constant)
                   and kw.value.value is False for kw in node.keywords)
    if isinstance(node, ast.Subscript) and _name(node.value, aliases) in {
        "typing.Annotated", "typing_extensions.Annotated",
    } and isinstance(node.slice, ast.Tuple):
        return any(_repr_disabled(arg, aliases) for arg in node.slice.elts[1:])
    return False


def scan_tree(root: Path) -> tuple[int, list[str]]:
    """Return the source count and file:line:Class.field violations."""
    paths = sorted(root.rglob("*.py"))
    if not paths:
        raise ValueError(f"No Python sources found under {root}")
    classes = []
    exports: dict[str, str] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parts = [root.name, *path.relative_to(root).with_suffix("").parts]
        package = parts[:-1]
        if parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    aliases[alias.asname or alias.name.split(".")[0]] = (
                        alias.name if alias.asname else alias.name.split(".")[0]
                    )
            elif isinstance(node, ast.ImportFrom):
                prefix = node.module or ""
                if node.level:
                    prefix = ".".join(package[:len(package) - node.level + 1]
                                      + ([prefix] if prefix else []))
                for alias in node.names:
                    aliases[alias.asname or alias.name] = f"{prefix}.{alias.name}"
            elif isinstance(node, ast.ClassDef):
                aliases[node.name] = f"{module}.{node.name}"
        exports.update({f"{module}.{local}": target for local, target in aliases.items()})
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append((path, node, aliases, f"{module}.{node.name}"))
    models = set(MODEL_BASES)
    while True:
        previous = len(models)
        models.update(name for name, target in exports.items() if target in models)
        for _, node, aliases, name in classes:
            if any(_name(base, aliases) in models for base in node.bases) or any(
                _name(dec.func if isinstance(dec, ast.Call) else dec, aliases) in DATACLASSES
                for dec in node.decorator_list
            ):
                models.add(name)
        if len(models) == previous:
            break
    violations = []
    for path, node, aliases, name in classes:
        if name not in models:
            continue
        for field in node.body:
            if not isinstance(field, ast.AnnAssign) or not isinstance(field.target, ast.Name):
                continue
            if (SECRET_NAME.search(field.target.id) and _plain_string(field.annotation, aliases)
                    and not _repr_disabled(field.value, aliases)
                    and not _repr_disabled(field.annotation, aliases)):
                violations.append(f"{path.relative_to(root)}:{field.lineno}:"
                                  f"{node.name}.{field.target.id}")
    return len(paths), sorted(violations)


def main(argv: list[str] | None = None) -> int:
    """Print every unsafe field and exit nonzero unless the count is zero."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1] / "siege_utilities")
    count, violations = scan_tree(parser.parse_args(argv).root)
    for violation in violations:
        print(violation)
    status = "FAIL" if violations else "PASS"
    print(f"{status}: {len(violations)} secret repr violation(s) in {count} files")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
