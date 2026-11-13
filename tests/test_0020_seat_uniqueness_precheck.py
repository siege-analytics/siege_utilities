"""DB-free contract for 0020's read-only duplicate-PRESIDENT precheck (#1623).

The live PostGIS behavior is in tests/test_0020_seat_uniqueness.py. These tests
pin the operation order, the no-op reverse, the alias and historical-model
plumbing, and the bounded message. The fakes have no write methods, so any
attempted delete/update/save fails the test.
"""

import importlib
from types import SimpleNamespace

import pytest

pytest.importorskip("django", reason="Install siege-utilities[geodjango] to run migration tests.")
from django.core.exceptions import ImproperlyConfigured  # noqa: E402
from django.db import migrations  # noqa: E402

# Importing the siege_geo migrations package loads GeoDjango, which needs GDAL.
try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH to run migration tests.",
        allow_module_level=True,
    )

MIGRATION = importlib.import_module("siege_utilities.geo.django.migrations.0020_seat_uniqueness")


class _ReadOnlyPresidents:
    """Fake queryset exposing only the read calls the precheck may use."""

    def __init__(self, log, pks):
        self._log = log
        self._pks = pks

    def filter(self, **lookups):
        self._log.append(("filter", lookups))
        return self

    def count(self):
        self._log.append(("count",))
        return len(self._pks)

    def order_by(self, *fields):
        self._log.append(("order_by", fields))
        return _ReadOnlyPresidents(self._log, sorted(self._pks))

    def values_list(self, *fields, flat=False):
        self._log.append(("values_list", fields, flat))
        return list(self._pks)


def _run_precheck(pks, alias="replica"):
    log = []

    class _Manager:
        def using(self, used_alias):
            log.append(("using", used_alias))
            return _ReadOnlyPresidents(log, list(pks))

    class _Apps:
        def get_model(self, app_label, model_name):
            log.append(("get_model", app_label, model_name))
            return SimpleNamespace(objects=_Manager())

    editor = SimpleNamespace(connection=SimpleNamespace(alias=alias))
    try:
        MIGRATION.reject_duplicate_presidents(_Apps(), editor)
    except RuntimeError as error:
        return log, error
    return log, None


def test_precheck_runs_before_any_constraint_change_and_reverses_as_noop():
    operations = MIGRATION.Migration.operations
    precheck = operations[0]
    assert isinstance(precheck, migrations.RunPython)
    assert precheck.code is MIGRATION.reject_duplicate_presidents
    assert precheck.reverse_code is migrations.RunPython.noop
    assert precheck.reversible
    # Routers see the same model_name as the Seat constraint operations.
    assert precheck.hints == {"model_name": "seat"}
    assert {op.model_name for op in operations[2:]} == {"seat"}
    assert [type(op).__name__ for op in operations[1:]] == [
        "AlterUniqueTogether", "AddConstraint", "AddConstraint", "AddConstraint",
    ]
    assert all(not isinstance(op, migrations.RunPython) for op in operations[1:])


def test_precheck_inspects_exactly_the_singleton_condition():
    singleton = MIGRATION.Migration.operations[-1].constraint
    assert singleton.name == MIGRATION.PRESIDENT_SINGLETON
    log, _ = _run_precheck([7])
    filters = [entry[1] for entry in log if entry[0] == "filter"]
    assert filters == [dict(singleton.condition.children)] == [{"office": "PRESIDENT"}]


@pytest.mark.parametrize("pks", [[], [42]], ids=["no-president", "one-president"])
def test_precheck_allows_zero_or_one_president(pks):
    log, error = _run_precheck(pks)
    assert error is None
    assert ("get_model", "siege_geo", "Seat") in log
    assert not any(entry[0] in {"order_by", "values_list"} for entry in log)


def test_precheck_rejects_duplicates_with_count_constraint_and_pks():
    log, error = _run_precheck([9, 3, 5], alias="replica")
    assert error is not None
    message = str(error)
    assert "constraint seat_president_singleton" in message
    assert "but 3 exist (database alias 'replica')" in message
    assert "Lowest primary keys, 3 of 3: 3, 5, 9. This migration changed no rows or constraints." in message
    assert "application/data owner" in message
    assert ("using", "replica") in log
    assert ("order_by", ("pk",)) in log
    assert ("values_list", ("pk",), True) in log


def test_precheck_rejection_sample_is_bounded_and_deterministic():
    limit = MIGRATION.DUPLICATE_SAMPLE_LIMIT
    pks = list(range(limit + 5, 0, -1))
    _, error = _run_precheck(pks)
    assert error is not None
    shown = ", ".join(str(pk) for pk in range(1, limit + 1))
    assert f"Lowest primary keys, {limit} of {limit + 5}: {shown}. This migration" in str(error)
