#!/usr/bin/env python3
"""Reject hard-coded credential values in the published package using AST inspection.

Run ``python scripts/check_secret_literals.py [root]`` (default: siege_utilities/).
Reject string credential keywords, function/argparse defaults, and AWS-key-shaped
strings anywhere, including docstrings. Resolve one level of module assignments
to string literals; this is not general data-flow or secret-entropy analysis.
Documentation containing placeholders is fine: snippets in strings are not code.

An isolated dummy fixture may exempt a literal/use on its own line with a comment
``# secret-guard: allow-dummy -- <reason>``. There are no file-wide exemptions.
Diagnostics contain file:line and a fixed rule description, never source values.
Unreadable/unparseable sources and empty trees fail closed without a traceback.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import tokenize
from pathlib import Path


_SENSITIVE_NAME = re.compile(
    r"(?:^|_)(?:(?:password|passwd|token|api_key|access_key|access_key_id|private_key)$|secret\w*|aws_(?:secret|access|session))",
    re.IGNORECASE,
)
_AWS_KEY = re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")
_DUMMY_COMMENT = re.compile(r"#\s*secret-guard: allow-dummy\s+--\s+\S.*")


def _sensitive(name: str) -> bool:
    """Match credential names without treating every key or token file as secret."""
    return bool(_SENSITIVE_NAME.search(name.lstrip("-").replace("-", "_")))


def scan_file(path: Path) -> list[tuple[int, str]]:
    """Return safe diagnostics for credential literals or unreadable source."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [(exc.lineno or 1, "cannot parse Python source")]
    except (OSError, UnicodeError):
        return [(1, "cannot read Python source")]

    # Tokenize comments so a marker embedded in a string cannot disable a rule.
    dummy_lines = {
        token.start[0]
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and _DUMMY_COMMENT.fullmatch(token.string)
    }
    constants = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value

    def literal(node):
        if isinstance(node, ast.Name):
            node = constants.get(node.id)
        return node if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    findings = set()

    def report(node, rule):
        if node.lineno not in dummy_lines:
            findings.add((node.lineno, rule))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _AWS_KEY.search(node.value):
                report(node, "AWS-key-shaped string literal")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            positional = args.posonlyargs + args.args
            defaults = list(zip(positional[len(positional) - len(args.defaults):], args.defaults))
            defaults.extend(zip(args.kwonlyargs, args.kw_defaults))
            for parameter, default in defaults:
                if _sensitive(parameter.arg) and literal(default) is not None:
                    report(default, "literal credential parameter default")
        elif isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg and _sensitive(keyword.arg) and literal(keyword.value) is not None:
                    report(keyword.value, "literal credential keyword")
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                names = [literal(arg) for arg in node.args]
                names.extend(literal(kw.value) for kw in node.keywords if kw.arg == "dest")
                if any(name is not None and _sensitive(name.value) for name in names):
                    for keyword in node.keywords:
                        if keyword.arg == "default" and literal(keyword.value) is not None:
                            report(keyword.value, "literal credential argparse default")
    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    """Scan all Python sources and return nonzero on violations or scan failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[1] / "siege_utilities",
    )
    root = parser.parse_args(argv).root
    sources = sorted(root.rglob("*.py"))
    if not sources:
        print(f"{root}:1: No Python sources found")
        return 1
    total = 0
    for path in sources:
        for line, message in scan_file(path):
            print(f"{path.relative_to(root)}:{line}: {message}")
            total += 1
    status = "FAIL" if total else "PASS"
    print(f"{status}: {total} credential literal violation(s) in {len(sources)} files")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
