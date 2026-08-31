"""Static consistency checks for the siege_geo Django migration graph.

Guards against the duplicate-``AddField`` bug class: a field added by two
different migrations applies cleanly to an already-migrated database but
crashes a fresh ``migrate`` with ``DuplicateColumn``, because the second
``AddField`` re-runs ``ALTER TABLE ... ADD COLUMN`` on a column the first
migration already created. Regression for the ``redistrictingplan.state``
field that was added by both 0005 and 0006.

Pure static analysis: parses migration files with :mod:`ast` and inspects
operation constructor calls. No migration module imports, database, GDAL, or
``migrate`` run is required, so this executes in no-GDAL CI jobs.
"""
from __future__ import annotations

import ast
import pathlib
from collections.abc import Iterable, Iterator

MIG_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "siege_utilities" / "geo" / "django" / "migrations"
)


def _call_name(node: ast.AST) -> str:
    """Return the unqualified function/constructor name for an AST call."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _literal_keyword(call: ast.Call, keyword_name: str) -> str | None:
    """Return a string literal keyword value from a migration operation call."""
    for keyword in call.keywords:
        if keyword.arg != keyword_name:
            continue
        value = keyword.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
    return None


def _operation_list_from_migration(path: pathlib.Path) -> list[ast.AST]:
    """Return the literal ``Migration.operations`` list without importing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "Migration":
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "operations"
                        for target in stmt.targets)
                and isinstance(stmt.value, ast.List)
            ):
                return list(stmt.value.elts)
    return []


def _iter_operation_calls(operations: Iterable[ast.AST]) -> Iterator[ast.Call]:
    """Yield migration operation calls, recursing into state-only wrappers."""
    for op in operations:
        if not isinstance(op, ast.Call):
            continue
        yield op
        if _call_name(op.func) != "SeparateDatabaseAndState":
            continue
        for keyword in op.keywords:
            if keyword.arg == "state_operations" and isinstance(keyword.value, ast.List):
                yield from _iter_operation_calls(keyword.value.elts)


def _iter_field_ops(path: pathlib.Path) -> Iterator[tuple[str, str, str]]:
    """Yield ``(kind, model, field)`` for Add/RemoveField operations.

    Recurses into ``SeparateDatabaseAndState.state_operations`` so a field
    declared via a state-only operation still counts.
    """
    for op in _iter_operation_calls(_operation_list_from_migration(path)):
        kind = _call_name(op.func)
        if kind not in {"AddField", "RemoveField"}:
            continue
        model = _literal_keyword(op, "model_name")
        field = _literal_keyword(op, "name")
        assert model and field, (
            f"{path.name}: migrations.{kind} must use literal model_name/name "
            "keywords for static duplicate-field analysis"
        )
        yield ("add" if kind == "AddField" else "remove", model.lower(), field.lower())


def test_no_duplicate_addfield_in_geo_migrations():
    """Every ``(model, field)`` is added at most once between removals."""
    paths = sorted(MIG_DIR.glob("0*.py"))
    assert paths, f"no migrations found under {MIG_DIR}"

    added_by = {}
    duplicates = []
    for path in paths:
        for kind, model, field in _iter_field_ops(path):
            key = (model, field)
            if kind == "add":
                if key in added_by:
                    duplicates.append((key, added_by[key], path.name))
                else:
                    added_by[key] = path.name
            else:  # remove
                added_by.pop(key, None)

    assert not duplicates, "duplicate AddField across migrations: " + "; ".join(
        f"{model}.{field} in both {first} and {second}"
        for (model, field), first, second in duplicates
    )
