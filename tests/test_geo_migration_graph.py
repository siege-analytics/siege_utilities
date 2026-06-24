"""Static consistency checks for the siege_geo Django migration graph.

Guards against the duplicate-``AddField`` bug class: a field added by two
different migrations applies cleanly to an already-migrated database but
crashes a fresh ``migrate`` with ``DuplicateColumn``, because the second
``AddField`` re-runs ``ALTER TABLE ... ADD COLUMN`` on a column the first
migration already created. Regression for the ``redistrictingplan.state``
field that was added by both 0005 and 0006.

Pure static analysis: imports the migration modules and inspects their
operation lists. No database and no ``migrate`` run is required, so this
executes in the standard test job without a PostGIS service.
"""
import importlib.util
import pathlib

import pytest

try:
    import django  # noqa: F401
    from django.db import migrations

    _HAS_DJANGO = True
except (ImportError, RuntimeError):
    _HAS_DJANGO = False

MIG_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "siege_utilities" / "geo" / "django" / "migrations"
)

pytestmark = pytest.mark.skipif(not _HAS_DJANGO, reason="Django not installed")


def _load_migration(path):
    spec = importlib.util.spec_from_file_location(f"siege_geo_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Migration


def _iter_field_ops(operations):
    """Yield ``(kind, model, field)`` for Add/RemoveField operations.

    Recurses into ``SeparateDatabaseAndState.state_operations`` so a field
    declared via a state-only operation still counts.
    """
    for op in operations:
        if isinstance(op, migrations.AddField):
            yield "add", op.model_name.lower(), op.name.lower()
        elif isinstance(op, migrations.RemoveField):
            yield "remove", op.model_name.lower(), op.name.lower()
        elif isinstance(op, migrations.SeparateDatabaseAndState):
            yield from _iter_field_ops(op.state_operations)


def test_no_duplicate_addfield_in_geo_migrations():
    """Every ``(model, field)`` is added at most once between removals."""
    paths = sorted(MIG_DIR.glob("0*.py"))
    assert paths, f"no migrations found under {MIG_DIR}"

    added_by = {}
    duplicates = []
    for path in paths:
        for kind, model, field in _iter_field_ops(_load_migration(path).operations):
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
