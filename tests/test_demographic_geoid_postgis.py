"""GEOID identity and legacy migration regressions for #1560 (test-postgis)."""

import os
from datetime import datetime, timezone

import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from siege_utilities.geo.django.managers import BoundaryQuerySet
from siege_utilities.geo.django.models import County, ZCTA
from siege_utilities.geo.django.models.demographics import DemographicSnapshot

pytestmark = [
    pytest.mark.postgis,
    pytest.mark.skipif(
        os.environ.get("SIEGE_TEST_POSTGIS") != "1",
        reason="Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* for live PostGIS tests.",
    ),
]


@pytest.fixture
def colliding_boundaries(db):
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    county = County.objects.create(
        pk=11, geoid="06037", state_fips="06", county_fips="037",
        vintage_year=2020, geometry=geometry,
    )
    County.objects.create(
        pk=6037, geoid="13001", state_fips="13", county_fips="001",
        vintage_year=2020, geometry=geometry,
    )
    zcta = ZCTA.objects.create(
        pk=12, geoid="06037", zcta5="06037", vintage_year=2020, geometry=geometry,
    )
    for boundary, population in ((county, 10_000_000), (zcta, 20_000)):
        DemographicSnapshot.objects.create(
            content_type=ContentType.objects.get_for_model(boundary),
            object_id=boundary.geoid, dataset="acs5", year=2022,
            total_population=population,
        )
    return county, zcta


def test_population_does_not_cross_geography(colliding_boundaries):
    """Runs unchanged on v4.0.0: equal GEOIDs must have distinct populations."""
    county, zcta = colliding_boundaries
    assert BoundaryQuerySet(County).filter(pk=county.pk).by_population(year=2022).get().population == 10_000_000
    assert BoundaryQuerySet(ZCTA).filter(pk=zcta.pk).by_population(year=2022).get().population == 20_000


def test_content_object_resolves_geoid_not_integer_pk(colliding_boundaries):
    """Runs unchanged on v4.0.0: County(pk=6037) is deliberately the wrong county."""
    for boundary in colliding_boundaries:
        snapshot = DemographicSnapshot.objects.get(
            content_type=ContentType.objects.get_for_model(boundary),
            object_id="06037", year=2022, dataset="acs5",
        )
        assert snapshot.content_object == boundary


def test_population_dataset_latest_year_and_reverse_helper(colliding_boundaries):
    county, zcta = colliding_boundaries
    content_type = ContentType.objects.get_for_model(county)
    DemographicSnapshot.objects.create(
        content_type=content_type, object_id=county.geoid, dataset="dec_pl",
        year=2022, total_population=900,
    )
    latest = DemographicSnapshot.objects.create(
        content_type=content_type, geoid=county.geoid, dataset="acs5",
        year=2023, total_population=11_000_000,
    )
    counties = County.objects.filter(pk=county.pk)
    assert counties.by_population(year=2022).get().population == 10_000_000
    assert counties.by_population(year=2022, dataset="dec_pl").get().population == 900
    assert counties.by_population().get().population == 11_000_000
    assert counties.by_population(year=1990).get().population is None
    assert County.objects.by_population().get(pk=county.pk).population == 11_000_000
    assert list(counties.snapshots(dataset="acs5", year=2023)) == [latest]
    assert counties.snapshots().count() == 3
    assert ZCTA.objects.snapshots().get().total_population == 20_000
    assert ZCTA.objects.filter(pk=zcta.pk).by_population(dataset="dec_pl").get().population is None


@pytest.mark.parametrize("series", [False, True], ids=["snapshot", "series"])
def test_geoid_create_shim_vintages_and_unique_constraint(colliding_boundaries, series):
    from siege_utilities.geo.django.models.demographics import DemographicTimeSeries

    county, _ = colliding_boundaries
    model = DemographicTimeSeries if series else DemographicSnapshot
    kwargs = dict(variable_code="B01001_001E", start_year=2020, end_year=2022,
                  years=[2020, 2022], values=[10, 20]) if series else dict(year=2021)
    with pytest.warns(DeprecationWarning, match="removed in v4.2.0"):
        row = model.objects.create(content_object=county, dataset="acs5", **kwargs)
    row.refresh_from_db()
    assert row.object_id == row.geoid == county.geoid
    assert row.get_boundary() == county
    with pytest.warns(DeprecationWarning, match="removed in v4.2.0"):
        assert row.content_object == county
    newer = County.objects.create(
        geoid=county.geoid, state_fips="06", county_fips="037",
        vintage_year=2024, geometry=county.geometry,
    )
    assert row.get_boundary() == newer
    assert row.get_boundary(vintage_year=2020) == county
    assert row.get_boundary(vintage_year=1990) is None
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(content_type=row.content_type, geoid=row.geoid, dataset="acs5", **kwargs)
    row.geoid = "99999"
    assert row.get_boundary() is None


def test_plan_assignment_accepts_big_boundary_pk(colliding_boundaries):
    from siege_utilities.geo.django.models.redistricting import PlanDistrictAssignment, RedistrictingPlan
    from siege_utilities.geo.django.models import Seat, State

    county, _ = colliding_boundaries
    boundary = County.objects.create(
        pk=2**31 + 5, geoid="06001", state_fips="06", county_fips="001",
        vintage_year=2020, geometry=county.geometry,
    )
    plan = RedistrictingPlan.objects.create(
        plan_name="Big PK plan", state_fips="06", chamber="congress", cycle_year=2020,
        num_districts=1,
    )
    state = State.objects.create(geoid="06", state_fips="06", vintage_year=2020, geometry=county.geometry)
    seat = Seat.objects.create(state=state, office="US_HOUSE", district_label="01")
    assignment = PlanDistrictAssignment.objects.create(plan=plan, seat=seat, boundary=boundary)
    assignment.refresh_from_db()
    assert assignment.boundary_object_id == boundary.pk
    assert assignment.boundary == boundary


PREVIOUS = ("siege_geo", "0017_cd112_geoid_format")
CURRENT = ("siege_geo", "0018_demographic_geoid_keys")


@pytest.fixture
def legacy_demographics(transactional_db):
    """Exercise real migration DDL and data, restoring the leaf for other tests."""
    executor = MigrationExecutor(connection)
    executor.migrate([PREVIOUS])
    before = executor.loader.project_state([PREVIOUS]).apps
    try:
        yield before
    finally:
        MigrationExecutor(connection).migrate([CURRENT])
        ContentType.objects.clear_cache()


def _legacy_rows(apps, winner="pk_newest"):
    county_model = apps.get_model("siege_geo", "County")
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    for pk, geoid in ((7, "06037"), (13001, "06001"), (99999, "06005"), (8, "99999")):
        county_model.objects.create(
            pk=pk, geoid=geoid, state_fips=geoid[:2], county_fips=geoid[2:],
            vintage_year=2020, geometry=geometry,
        )
    ct = apps.get_model("contenttypes", "ContentType").objects.get(app_label="siege_geo", model="county")
    original = {}
    for name in ("DemographicSnapshot", "DemographicTimeSeries"):
        model = apps.get_model("siege_geo", name)
        kwargs = dict(year=2022, total_population=10, values={"test": 10}) if name == "DemographicSnapshot" else dict(
            variable_code="B01001_001E", start_year=2020, end_year=2022, years=[2020, 2022], values=[10, 20],
        )
        # A PK that has valid GEOID shape must also be detected (13001).
        # 99999 is ambiguous: both a GEOID and a different boundary's PK.
        for key in ("7", "06037", "13001", "missing", "99999", "88888"):
            row = model.objects.create(content_type_id=ct.pk, object_id=key, dataset="acs5", **kwargs)
            newest_key = "7" if winner == "pk_newest" else "06037"
            year = 2024 if key == newest_key and winner != "tie" else 2023
            model.objects.filter(pk=row.pk).update(
                updated_at=datetime(year, 1, 1, microsecond=123456, tzinfo=timezone.utc)
            )
        # The other dataset must survive independently.
        model.objects.create(content_type_id=ct.pk, object_id="06037", dataset="dec_pl", **kwargs)
        original[name] = list(model.objects.order_by("pk").values())
    return original


@pytest.mark.parametrize("winner", ["pk_newest", "geoid_newest", "tie"])
def test_migration_converts_quarantines_dedupes_and_reverses(legacy_demographics, caplog, winner):
    caplog.set_level("WARNING", logger="siege_utilities.geo.django.migrations.0018_demographic_geoid_keys")
    original = _legacy_rows(legacy_demographics, winner)
    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    archive = after.get_model("siege_geo", "DemographicKeyArchive")
    for name in original:
        model = after.get_model("siege_geo", name)
        rows = model.objects.filter(dataset="acs5")
        assert set(rows.values_list("object_id", flat=True)) == {"06037", "06001", "88888"}
        winning_key = "7" if winner == "pk_newest" else "06037"
        winning_row = next(row for row in original[name] if row["object_id"] == winning_key)
        assert rows.get(object_id="06037").pk == winning_row["id"]
        assert model.objects.filter(dataset="dec_pl").count() == 1
        assert archive.objects.filter(model_name=name).count() == (5 if winner == "pk_newest" else 4)
        assert archive.objects.filter(model_name=name, reason="ambiguous_pk_and_geoid").count() == 1
        assert archive.objects.filter(model_name=name, reason="unresolvable_key").count() == 1
        assert archive.objects.filter(model_name=name, reason="duplicate").count() == 1
        assert f"{name} GEOID migration: converted=2 quarantined=2 deduplicated=1" in caplog.text
        duplicate = rows.get(object_id="06037")
        duplicate.pk = None
        with pytest.raises(IntegrityError), transaction.atomic():
            duplicate.save(force_insert=True)

    MigrationExecutor(connection).migrate([PREVIOUS])
    for name, expected in original.items():
        restored = legacy_demographics.get_model("siege_geo", name)
        assert list(restored.objects.order_by("pk").values()) == expected


def test_migration_reverse_refuses_to_overwrite_newer_edits(legacy_demographics):
    _legacy_rows(legacy_demographics)
    MigrationExecutor(connection).migrate([CURRENT])
    row = DemographicSnapshot.objects.get(object_id="06001", dataset="acs5")
    old_values = row.values
    DemographicSnapshot.objects.filter(pk=row.pk).update(values={"new": 42})
    try:
        with pytest.raises(RuntimeError, match="row changed after GEOID migration"):
            MigrationExecutor(connection).migrate([PREVIOUS])
        assert DemographicSnapshot.objects.get(pk=row.pk).values == {"new": 42}
    finally:
        DemographicSnapshot.objects.filter(pk=row.pk).update(values=old_values)
