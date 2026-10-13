#!/usr/bin/env python3
"""Require review of credential-bearing URL construction across the package.

This conservative AST guard flags construction even without proving a path to a
log or exception: a request library can include its URL in an exception. It finds
literal/f-string query fields and urlencode(dict) fields, following assignments,
updates and aliases within a file. It is not an interprocedural taint analyzer.
Each exemption identifies one expression in one function and explains its sinks.
Run: python scripts/check_credential_urls.py [package-directory]
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote_plus


# Independent of the runtime redactor so removing a protected name cannot weaken
# the guard as well as the diagnostics.
SENSITIVE = frozenset({
    "key", "password", "access_token", "token", "apikey", "api_key",
    "client_secret", "secret", "sig", "x-amz-signature", "auth",
})
QUERY_FIELD = re.compile(r"[?&]([^=&#\s]+)=")

# (package-relative path, qualified function, canonical AST expression): reason.
ALLOWLIST = {
    ("geo/census/api.py", "CensusAPI._build_url", "f'&key={self.api_key}'"):
        "Census query authentication: _make_request_with_retry redacts diagnostics "
        "and raises fresh exceptions outside handlers; census sentinel tests enforce it.",
    ("geo/providers/tamu_batch.py", "TAMUBatchGeocoder._tamu_request",
     "urllib.parse.urlencode(params)"):
        "TAMU v4.01 documents query authentication. _tamu_request raises a fresh "
        "redacted error outside handlers and _geocode_single redacts its warning; "
        "TAMU sentinel tests enforce both sinks.",
}


@dataclass(frozen=True)
class Site:
    path: str
    line: int
    function: str
    expression: str
    parameters: tuple[str, ...]

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.path, self.function, self.expression

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.function}: {', '.join(self.parameters)} in {self.expression}"


def credential_url_sites(source: str, path: str) -> list[Site]:
    """Find sensitive query construction, ignoring comments and docstrings."""
    tree = ast.parse(source, filename=path)
    bindings: dict[str, list[ast.AST]] = {}
    docstrings = set()
    encoders = {"urlencode"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "urllib.parse":
            encoders.update(alias.asname or alias.name for alias in node.names if alias.name == "urlencode")
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstrings.add(id(node.body[0].value))
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and node.value is not None:
                    bindings.setdefault(target.id, []).append(node.value)
                elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                    bindings.setdefault(target.value.id, []).append(ast.Dict(
                        keys=[target.slice], values=[node.value],
                    ))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "update" and isinstance(node.func.value, ast.Name):
                bindings.setdefault(node.func.value.id, []).extend(node.args)
                bindings[node.func.value.id].append(ast.Dict(
                    keys=[ast.Constant(kw.arg) for kw in node.keywords],
                    values=[kw.value for kw in node.keywords],
                ))

    def keys(expr: ast.AST, seen: frozenset[str] = frozenset()) -> set[str]:
        if isinstance(expr, ast.Name) and expr.id not in seen:
            return set().union(*(keys(value, seen | {expr.id})
                                 for value in bindings.get(expr.id, [])))
        if isinstance(expr, ast.Dict):
            result = {unquote_plus(key.value).lower() for key in expr.keys
                      if isinstance(key, ast.Constant) and isinstance(key.value, str)}
            for key, value in zip(expr.keys, expr.values):
                if key is None:
                    result |= keys(value, seen)
            return result
        if isinstance(expr, ast.Call):
            result = {kw.arg.lower() for kw in expr.keywords if kw.arg}
            for argument in expr.args + [kw.value for kw in expr.keywords if kw.arg is None]:
                result |= keys(argument, seen)
            return result
        if isinstance(expr, (ast.List, ast.Tuple)):
            return {item.elts[0].value.lower() for item in expr.elts
                    if isinstance(item, (ast.List, ast.Tuple)) and item.elts
                    and isinstance(item.elts[0], ast.Constant)
                    and isinstance(item.elts[0].value, str)}
        return set()

    sites = []

    def visit(node: ast.AST, scope: tuple[str, ...] = ()) -> None:
        if id(node) in docstrings:
            return
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            scope += (node.name,)
        parameters = set()
        if isinstance(node, (ast.JoinedStr, ast.Constant)):
            parts = node.values if isinstance(node, ast.JoinedStr) else [node]
            literal = "".join(part.value for part in parts
                              if isinstance(part, ast.Constant) and isinstance(part.value, str))
            parameters = {match.lower() for match in QUERY_FIELD.findall(unquote_plus(literal))}
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in encoders:
                arguments = node.args or [kw.value for kw in node.keywords if kw.arg == "query"]
                if arguments:
                    parameters = keys(arguments[0])
        parameters &= SENSITIVE
        if parameters:
            sites.append(Site(path, node.lineno, ".".join(scope) or "<module>",
                              ast.unparse(node), tuple(sorted(parameters))))
        for child in ast.iter_child_nodes(node):
            # Literal segments are already examined with their entire f-string.
            if isinstance(node, ast.JoinedStr) and isinstance(child, ast.Constant):
                continue
            visit(child, scope)

    visit(tree)
    return sites


def scan_tree(root: Path) -> list[Site]:
    return [site for path in sorted(root.rglob("*.py"))
            for site in credential_url_sites(path.read_text(encoding="utf-8"),
                                             path.relative_to(root).as_posix())]


def unreviewed_sites(root: Path) -> list[Site]:
    return [site for site in scan_tree(root) if not ALLOWLIST.get(site.identity)]


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "siege_utilities"
    findings = unreviewed_sites(root)
    for site in findings:
        print(site)
    print(f"Credential URL guard: {len(findings)} unreviewed sites")
    return bool(findings)


if __name__ == "__main__":
    sys.exit(main())
