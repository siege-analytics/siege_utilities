#!/usr/bin/env python3
"""Reject unreviewed exception swallowing in siege_utilities (#1532).

BROAD: bare/Exception/BaseException handlers unless the body ends in a raise
and nothing in the handler's own scope returns, breaks, continues or yields.
A raise reached on only some paths does not exempt a broad handler, because
its other paths can still swallow the error (#1971).
DEFAULT: in a data function, pass/continue, success-shaped returns, or
empty-frame assignments. Data functions declare a non-None return or have
an unannotated non-None return. Success shapes include tuples, strings,
Unknown dictionaries, and default/placeholder/fallback/missing factories.
LOGONLY: handlers consisting only of logging calls, including void functions.
DEFAULT and LOGONLY do not apply to a handler that raises on any path.
Nested definitions cannot supply a handler's raise. Finally cleanup,
__del__, and callbacks registered with signal.signal are exempt.

Allow-list keys bind the path, qualified owner, rule and handler AST digest.
Changed handlers require review; stale entries and empty justifications fail.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def walk_body(nodes):
    """Walk statements without descending into a separate execution scope."""
    for node in nodes:
        if isinstance(node, SCOPES):
            continue
        yield node
        yield from walk_body(ast.iter_child_nodes(node))


def names(node):
    """Extract exception names, including tuples and qualified builtins."""
    if node is None:
        return {"<bare>"}
    if isinstance(node, ast.Tuple):
        return set().union(*(names(item) for item in node.elts))
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    return set()


def empty_value(node):
    """Recognize the success-shaped fallback expressions in the guard contract."""
    if node is None:
        return True
    if isinstance(node, ast.Constant):
        return (
            node.value is None
            or (type(node.value) in (int, float) and node.value == 0)
            or (isinstance(node.value, str) and node.value.lower() == "unknown")
        )
    if isinstance(node, ast.Dict):
        return not node.keys or any(
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and value.value.lower() == "unknown"
            for value in node.values
        )
    if isinstance(node, ast.List):
        return not node.elts
    if isinstance(node, ast.Tuple):
        return all(empty_value(value) for value in node.elts)
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.Call) and any(
        name == "str"
        or any(part in name.lower() for part in ("placeholder", "_default", "fallback", "_resolve_missing"))
        for name in names(node.func)
    ):
        return True
    if isinstance(node, ast.Call) and names(node.func) & {"DataFrame", "GeoDataFrame"}:
        # Explicit columns/dtype/CRS do not populate a frame. Recognize empty
        # data as well as the zero-argument spelling, without guessing whether
        # an arbitrary input expression or a supplied index/geometry is empty.
        def empty_data(value):
            return (
                (isinstance(value, ast.Constant) and value.value is None)
                or (isinstance(value, (ast.List, ast.Tuple)) and not value.elts)
                or (isinstance(value, ast.Dict) and not value.keys)
            )

        if node.args and (len(node.args) != 1 or not empty_data(node.args[0])):
            return False
        for keyword in node.keywords:
            if keyword.arg in {"data", "index", "geometry"}:
                if not empty_data(keyword.value):
                    return False
            elif keyword.arg not in {"columns", "dtype", "crs", "copy"}:
                return False
        return True
    return False


def data_function(function):
    """Recognize declared data functions and infer unannotated return values."""
    if function is None:
        return False
    if function.returns is None:
        return any(
            isinstance(node, ast.Return) and non_none_value(node.value)
            for node in walk_body(function.body)
        )
    annotation = function.returns
    if isinstance(annotation, ast.Constant):
        return annotation.value not in (None, "None", "NoneType")
    return ast.unparse(annotation) not in {"None", "NoneType", "type(None)"}


def non_none_value(node):
    return node is not None and not (
        isinstance(node, ast.Constant) and node.value is None
    )


def default_handler(handler, function):
    """Find fallback statements even when accompanied by logging or branches."""
    if not data_function(function):
        return False
    for node in walk_body(handler.body):
        if isinstance(node, (ast.Pass, ast.Continue)):
            return True
        if isinstance(node, ast.Return) and (
            empty_value(node.value)
            or (function.returns is None and non_none_value(node.value))
        ):
            return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and (
            isinstance(node.value, ast.Call)
            and names(node.value.func) & {"DataFrame", "GeoDataFrame"}
            and empty_value(node.value)
        ):
            return True
    return False


ESCAPES = (ast.Return, ast.Break, ast.Continue, ast.Yield, ast.YieldFrom)


def definition_time_expressions(node):
    """Expressions a nested definition evaluates in the enclosing scope.

    Decorators, argument defaults, argument and return annotations, and class
    bases and keywords run when the ``def``, ``lambda`` or ``class`` statement
    runs, so a ``yield`` there runs in the enclosing handler. The definition's
    body runs later, in its own scope, and is not included.
    """
    if isinstance(node, ast.ClassDef):
        return [*node.decorator_list, *node.bases, *(keyword.value for keyword in node.keywords)]
    args = node.args
    expressions = [*getattr(node, "decorator_list", []), *args.defaults]
    expressions += [default for default in args.kw_defaults if default is not None]
    parameters = [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]
    expressions += [
        parameter.annotation
        for parameter in parameters
        if parameter is not None and getattr(parameter, "annotation", None) is not None
    ]
    if getattr(node, "returns", None) is not None:
        expressions.append(node.returns)
    return expressions


def escape_nodes(nodes):
    """Walk a handler's own scope for an escape, as it runs.

    Like ``walk_body`` this does not enter the body of a nested function,
    class or lambda, but it does visit the definition-time expressions of
    those definitions, which run in the handler's scope.
    """
    for node in nodes:
        if isinstance(node, SCOPES):
            yield from escape_nodes(definition_time_expressions(node))
            continue
        yield node
        yield from escape_nodes(ast.iter_child_nodes(node))


def unconditional_reraise(body):
    """True when a handler body always ends by raising and has no other exit.

    The last statement must be a ``raise``, and nothing in the handler's own
    scope may return, break, continue or yield, including inside if, for,
    while, try, with and finally blocks: any of those could leave the handler,
    or hand control back, without raising. Nested function, class and lambda
    bodies are separate scopes and do not count, but their decorators,
    defaults, annotations, bases and keywords run in the handler and do.
    """
    if not body or not isinstance(body[-1], ast.Raise):
        return False
    return not any(isinstance(node, ESCAPES) for node in escape_nodes(body))


def log_only(handler):
    """Logging alone cannot communicate failure to a caller, even without data."""
    levels = {"debug", "info", "warning", "warn", "error", "exception", "critical", "fatal", "log"}
    return all(
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and any(
            name in levels or name.startswith("log_")
            for name in names(stmt.value.func)
        )
        for stmt in handler.body
    )


def canonical_ast(node):
    """Serialize semantic AST fields consistently across Python 3.11–3.14.

    ast.dump changed its empty-field rendering in newer Python releases.
    Ignore absent/empty optional fields (including new type_params), while
    preserving node types and all populated fields so handler edits still
    invalidate the reviewed allowance.
    """
    if isinstance(node, ast.AST):
        return (
            type(node).__name__,
            tuple(
                (name, canonical_ast(value))
                for name, value in sorted(ast.iter_fields(node))
                if value is not None and value != []
            ),
        )
    if isinstance(node, list):
        return tuple(canonical_ast(value) for value in node)
    return node


class SourceRootNotFound(FileNotFoundError):
    """The scan root has no ``siege_utilities/`` directory to check."""


def scan(root):
    """Return keyed violations, without importing any scanned library modules.

    Raises SourceRootNotFound when ``root/siege_utilities`` is not a
    directory, so that a missing or mistyped root fails instead of scanning
    nothing and reporting a clean tree. This is the one root check for this
    guard and for ``check_broad_except.py``; the message is the one
    ``check_broad_except.py`` printed before it delegated here.
    """
    source = root / "siege_utilities"
    if not source.is_dir():
        raise SourceRootNotFound(f"ERROR: source root not found: {source}")
    found = []
    for path in sorted(source.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        # Resolve actual registered callbacks, not arbitrary names containing signal.
        signals = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and len(node.args) >= 2
                and ast.unparse(node.func) in {"signal.signal", "signal"}
            ):
                signals.update(names(node.args[1]))

        occurrences = {}
        for handler in ast.walk(tree):
            if not isinstance(handler, ast.ExceptHandler):
                continue
            owner = []
            function = None
            cleanup = False
            child = handler
            while child in parents:
                parent = parents[child]
                if isinstance(
                    parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    owner.append(parent.name)
                    if function is None and not isinstance(parent, ast.ClassDef):
                        function = parent
                if function is None and isinstance(parent, (ast.Try, ast.TryStar)):
                    cleanup |= child in parent.finalbody
                child = parent
            if cleanup or (
                function and (function.name == "__del__" or function.name in signals)
            ):
                continue
            raises = any(isinstance(node, ast.Raise) for node in walk_body(handler.body))
            rules = []
            if names(handler.type) & {"<bare>", "Exception", "BaseException"} and not (
                unconditional_reraise(handler.body)
            ):
                rules.append("BROAD")
            if not raises and default_handler(handler, function):
                rules.append("DEFAULT")
            if not raises and log_only(handler):
                rules.append("LOGONLY")
            digest = hashlib.sha256(repr(canonical_ast(handler)).encode()).hexdigest()[
                :16
            ]
            qualified = ".".join(reversed(owner)) or "<module>"
            for rule in rules:
                key = f"{relative}::{qualified}::{rule}::{digest}"
                occurrences[key] = occurrences.get(key, 0) + 1
                found.append(
                    {
                        "key": f"{key}::{occurrences[key]}",
                        "location": f"{relative}:{handler.lineno}",
                        "rule": rule,
                    }
                )
    return found


ALLOWLIST_ERROR = "Every allow-list entry must have a nonempty justification"


def load_allowlist(root, allowlist=None):
    """Read the allow-list and reject any entry without a nonempty justification.

    The single loader for this guard and for ``check_broad_except.py``.
    Raises ValueError (including json.JSONDecodeError) for an invalid file.
    """
    path = allowlist or root / "scripts/exception_contracts_allowlist.json"
    allow = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(allow, dict) or any(
        not isinstance(reason, str) or not reason.strip() for reason in allow.values()
    ):
        raise ValueError(ALLOWLIST_ERROR)
    return allow


def main(argv=None):
    """Check the tree against reviewed exceptions and print zero-unlisted proof."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--allowlist", type=Path)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    try:
        allow = load_allowlist(args.root, args.allowlist)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        found = scan(args.root)
    except SourceRootNotFound as exc:
        print(exc, file=sys.stderr)
        return 1
    unlisted = [item for item in found if item["key"] not in allow]
    stale = sorted(set(allow) - {item["key"] for item in found})
    print(
        f"handlers flagged: {len(found)}; unlisted: {len(unlisted)}; stale allow-list: {len(stale)}"
    )
    if args.list:
        for item in unlisted:
            print(f"  {item['location']} {item['key']}")
        for key in stale:
            print(f"  STALE {key}")
    return int(bool(unlisted or stale))


if __name__ == "__main__":
    raise SystemExit(main())
