"""Live PostGIS regressions for 0020's read-only duplicate-PRESIDENT precheck (#1623)."""

import importlib
import os

import pytest

if os.environ.get("SIEGE_TEST_POSTGIS") != "1":
    pytest.skip(
        "Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* for live PostGIS tests.",
        allow_module_level=True,
    )

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext

pytestmark = pytest.mark.postgis

MIGRATION = importlib.import_module("siege_utilities.geo.django.migrations.0020_seat_uniqueness")
PREVIOUS = ("siege_geo", "0019_demographic_geoid_keys")
CURRENT = ("siege_geo", "0020_seat_uniqueness")
NEW_CONSTRAINTS = {
    "seat_identity_with_senate_class",
    "seat_identity_without_senate_class",
    "seat_president_singleton",
}
OLD_KEY = ["district_label", "office", "state_id"]


@pytest.fixture
def legacy_seats(transactional_db):
    """Run the real 0020 path from historical 0019 state; restore the leaf after."""
    executor = MigrationExecutor(connection)
    leaf = executor.loader.graph.leaf_nodes("siege_geo")
    executor.migrate([PREVIOUS])
    before = executor.loader.project_state([PREVIOUS]).apps
    try:
        yield before
    finally:
        # Test-database cleanup only, so later tests get the leaf schema back.
        before.get_model("siege_geo", "Seat").objects.filter(office="PRESIDENT").delete()
        MigrationExecutor(connection).migrate(leaf)


def _state(apps):
    return apps.get_model("siege_geo", "State").objects.create(
        geoid="48", name="Texas", vintage_year=2020, state_fips="48",
        geometry=MultiPolygon(Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)))),
    )


def _seat_constraints(seat):
    with connection.cursor() as cursor:
        found = connection.introspection.get_constraints(cursor, seat._meta.db_table)
    old_key = any(
        info["unique"] and not info["primary_key"] and name not in NEW_CONSTRAINTS
        and sorted(info["columns"]) == OLD_KEY
        for name, info in found.items()
    )
    return set(found) & NEW_CONSTRAINTS, old_key


def _rows(seat):
    return list(seat.objects.order_by("pk").values())


def test_duplicate_presidents_rejected_before_constraint_changes(legacy_seats):
    seat = legacy_seats.get_model("siege_geo", "Seat")
    state = _state(legacy_seats)
    presidents = [
        seat.objects.create(office="PRESIDENT"),
        seat.objects.create(office="PRESIDENT", state=state, district_label="national"),
        seat.objects.create(office="PRESIDENT", senate_class=1),
    ]
    seat.objects.create(office="US_SENATE", state=state, senate_class=1)
    original = _rows(seat)

    # PostgreSQL rolls DDL back with the failed migration, so the end state
    # alone cannot show ordering: assert no DDL was issued before the raise.
    with CaptureQueriesContext(connection) as queries, pytest.raises(RuntimeError) as error:
        MigrationExecutor(connection).migrate([CURRENT])

    ddl = [
        query["sql"] for query in queries.captured_queries
        if query["sql"].lstrip().upper().startswith(("ALTER", "CREATE", "DROP"))
    ]
    assert ddl == []
    shown = ", ".join(str(row.pk) for row in sorted(presidents, key=lambda row: row.pk))
    message = str(error.value)
    assert "constraint seat_president_singleton" in message
    assert "but 3 exist (database alias 'default')" in message
    assert f"Lowest primary keys, 3 of 3: {shown}. This migration changed no rows or constraints." in message
    assert _rows(seat) == original
    assert CURRENT not in MigrationExecutor(connection).loader.applied_migrations
    assert _seat_constraints(seat) == (set(), True)


def test_duplicate_president_rejection_lists_bounded_lowest_pks(legacy_seats):
    seat = legacy_seats.get_model("siege_geo", "Seat")
    limit = MIGRATION.DUPLICATE_SAMPLE_LIMIT
    pks = [seat.objects.create(office="PRESIDENT").pk for _ in range(limit + 5)]
    original = _rows(seat)

    with pytest.raises(RuntimeError) as error:
        MigrationExecutor(connection).migrate([CURRENT])

    shown = ", ".join(str(pk) for pk in sorted(pks)[:limit])
    assert f"Lowest primary keys, {limit} of {limit + 5}: {shown}. This migration" in str(error.value)
    assert _rows(seat) == original
    assert _seat_constraints(seat) == (set(), True)


@pytest.mark.parametrize("president_count", [0, 1])
def test_zero_or_one_president_migrates_and_enforces_identity(legacy_seats, president_count):
    seat = legacy_seats.get_model("siege_geo", "Seat")
    state = _state(legacy_seats)
    for _ in range(president_count):
        seat.objects.create(office="PRESIDENT")
    seat.objects.create(office="US_SENATE", state=state, senate_class=1)
    seat.objects.create(office="US_SENATE", state=state, district_label="at-large")
    seat.objects.create(office="US_HOUSE", state=state, district_label="12")
    original = _rows(seat)

    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps.get_model("siege_geo", "Seat")
    assert _rows(after) == original
    assert _seat_constraints(after) == (NEW_CONSTRAINTS, False)

    # Senate class 2 now coexists; duplicate identities and a second PRESIDENT do not.
    after.objects.create(office="US_SENATE", state_id=state.pk, senate_class=2)
    duplicates = [
        dict(office="US_SENATE", state_id=state.pk, senate_class=1),
        dict(office="US_SENATE", state_id=state.pk, district_label="at-large"),
        dict(office="US_HOUSE", state_id=state.pk, district_label="12"),
    ]
    if president_count == 0:
        after.objects.create(office="PRESIDENT")
    duplicates.append(dict(office="PRESIDENT"))
    for fields in duplicates:
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                after.objects.create(**fields)
    assert after.objects.filter(office="PRESIDENT").count() == 1


def test_reverse_restores_old_key_without_touching_rows(legacy_seats):
    seat = legacy_seats.get_model("siege_geo", "Seat")
    state = _state(legacy_seats)
    seat.objects.create(office="PRESIDENT")
    seat.objects.create(office="US_HOUSE", state=state, district_label="12")
    original = _rows(seat)
    MigrationExecutor(connection).migrate([CURRENT])

    MigrationExecutor(connection).migrate([PREVIOUS])

    assert _rows(seat) == original
    assert _seat_constraints(seat) == (set(), True)
