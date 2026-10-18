"""PostGIS data/schema migration regressions for #1560 and exact reversal."""

import os
from datetime import datetime, timezone

import pytest

if os.environ.get("SIEGE_TEST_POSTGIS") != "1":
    pytest.skip(
        "Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* for live PostGIS tests.",
        allow_module_level=True,
    )

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from siege_utilities.geo.django.models.demographics import DemographicSnapshot

pytestmark = pytest.mark.postgis


PREVIOUS = ("siege_geo", "0018_nlrbregion_geometry_nullable")
CURRENT = ("siege_geo", "0019_demographic_geoid_keys")


@pytest.fixture
def legacy_demographics(transactional_db, monkeypatch):
    """Exercise real migration DDL and data, restoring the leaf for other tests."""
    monkeypatch.delenv("SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE", raising=False)
    executor = MigrationExecutor(connection)
    executor.migrate([PREVIOUS])
    before = executor.loader.project_state([PREVIOUS]).apps
    try:
        yield before
    finally:
        with monkeypatch.context() as cleanup:
            cleanup.setenv("SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE", "1")
            MigrationExecutor(connection).migrate([CURRENT])
        ContentType.objects.clear_cache()


@pytest.mark.parametrize("name", ["DemographicSnapshot", "DemographicTimeSeries"])
def test_migration_keeps_geoid_with_coincident_boundary_pk(legacy_demographics, name):
    county = legacy_demographics.get_model("siege_geo", "County")
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    for pk, geoid in ((11, "06037"), (6037, "13001")):
        county.objects.create(
            pk=pk, geoid=geoid, state_fips=geoid[:2], county_fips=geoid[2:],
            vintage_year=2020, geometry=geometry,
        )
    ct = legacy_demographics.get_model("contenttypes", "ContentType").objects.get(
        app_label="siege_geo", model="county",
    )
    model = legacy_demographics.get_model("siege_geo", name)
    kwargs = dict(year=2022, total_population=10) if name == "DemographicSnapshot" else dict(
        variable_code="B01001_001E", start_year=2020, end_year=2022,
        years=[2020, 2022], values=[10, 20],
    )
    model.objects.create(content_type_id=ct.pk, object_id="06037", dataset="acs5", **kwargs)
    original = list(model.objects.values())

    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    assert list(after.get_model("siege_geo", name).objects.values()) == original
    assert not after.get_model("siege_geo", "DemographicKeyArchive").objects.exists()


@pytest.mark.parametrize("name", ["DemographicSnapshot", "DemographicTimeSeries"])
@pytest.mark.parametrize(
    "boundary_name, orphan, decoy_geoid",
    [("County", "09110", "50007"), ("ZCTA", "10004", "10005"), ("County", "0007", "06037")],
)
def test_migration_keeps_orphan_geoid_with_coincident_boundary_pk(
    legacy_demographics, name, boundary_name, orphan, decoy_geoid,
):
    boundary = legacy_demographics.get_model("siege_geo", boundary_name)
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    boundary.objects.create(
        pk=int(orphan), geoid=decoy_geoid, vintage_year=2020, geometry=geometry,
    )
    assert not boundary.objects.filter(geoid=orphan).exists()
    ct = legacy_demographics.get_model("contenttypes", "ContentType").objects.get(
        app_label="siege_geo", model=boundary_name.lower(),
    )
    model = legacy_demographics.get_model("siege_geo", name)
    kwargs = dict(year=2022, total_population=10) if name == "DemographicSnapshot" else dict(
        variable_code="B01001_001E", start_year=2020, end_year=2022,
        years=[2020, 2022], values=[10, 20],
    )
    row = model.objects.create(content_type_id=ct.pk, object_id=orphan, dataset="acs5", **kwargs)
    original = list(model.objects.values())

    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    migrated = after.get_model("siege_geo", name)
    assert migrated.objects.get(pk=row.pk).object_id == orphan
    assert not migrated.objects.filter(object_id=decoy_geoid).exists()
    assert list(migrated.objects.values()) == original
    assert not after.get_model("siege_geo", "DemographicKeyArchive").objects.exists()


@pytest.mark.parametrize("removal", ["unresolvable", "duplicate", "both"])
def test_migration_rejects_quarantine_without_opt_in_atomically(legacy_demographics, removal):
    original = _legacy_rows(legacy_demographics)
    for name in original:
        model = legacy_demographics.get_model("siege_geo", name)
        if removal == "unresolvable":
            model.objects.filter(object_id="7").delete()
        elif removal == "duplicate":
            model.objects.filter(object_id__in=["missing", "88888"]).delete()
        original[name] = list(model.objects.order_by("pk").values())
    with pytest.raises(RuntimeError, match="SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE=1") as error:
        MigrationExecutor(connection).migrate([CURRENT])
    if removal != "duplicate":
        assert "unresolvable_key=1" in str(error.value)
    if removal != "unresolvable":
        assert "duplicate=1" in str(error.value)
    for name, expected in original.items():
        assert name in str(error.value)
        assert list(legacy_demographics.get_model("siege_geo", name).objects.order_by("pk").values()) == expected
    assert CURRENT not in MigrationExecutor(connection).loader.applied_migrations
    assert "siege_geo_demographickeyarchive" not in connection.introspection.table_names()


def test_migration_converts_without_opt_in_when_no_rows_removed(legacy_demographics):
    original = _legacy_rows(legacy_demographics)
    for name in original:
        model = legacy_demographics.get_model("siege_geo", name)
        model.objects.exclude(object_id__in=["13001", "7"]).delete()
        original[name] = list(model.objects.order_by("pk").values())
    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    for name, expected in original.items():
        for row in expected:
            if row["object_id"] == "7":
                row["object_id"] = "06037"
        migrated = after.get_model("siege_geo", name)
        assert list(migrated.objects.order_by("pk").values()) == expected
        assert migrated.objects.filter(object_id="13001").exists()
        assert not migrated.objects.filter(object_id="06001").exists()
    archive = after.get_model("siege_geo", "DemographicKeyArchive")
    assert list(archive.objects.values_list("reason", flat=True)) == ["converted_pk", "converted_pk"]
    assert all(row["object_id"] == "7" for row in archive.objects.values_list("original_data", flat=True))


def test_migration_noopt_clean_probe_preserves_native_rows_and_orphans(legacy_demographics, caplog):
    caplog.set_level("WARNING", logger="siege_utilities.geo.django.migrations.0019_demographic_geoid_keys")
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    fixtures = {
        "County": list(zip(
            (f"09{code}" for code in range(110, 200, 10)),
            ("50007", "50027", "50001", "50003", "50005", "50009", "50011", "50013", "50015"),
        )),
        "CongressionalDistrict": [("0808", "5002")],
        "ZCTA": [("00602", "02404"), ("00605", "02413"), ("10004", "10005")],
    }
    snapshots = legacy_demographics.get_model("siege_geo", "DemographicSnapshot")
    series = legacy_demographics.get_model("siege_geo", "DemographicTimeSeries")
    for name, keys in fixtures.items():
        boundary = legacy_demographics.get_model("siege_geo", name)
        ct = legacy_demographics.get_model("contenttypes", "ContentType").objects.get(
            app_label="siege_geo", model=name.lower(),
        )
        for orphan, geoid in keys:
            boundary.objects.create(pk=int(orphan), geoid=geoid, vintage_year=2020, geometry=geometry)
            snapshots.objects.create(
                content_type_id=ct.pk, object_id=geoid, dataset="acs5", year=2022, total_population=100,
            )
            # State-scoped imports coexist with native rows without duplicate keys.
            snapshots.objects.create(
                content_type_id=ct.pk, object_id=orphan, dataset=f"acs5_{orphan[:2]}", year=2022, total_population=10,
            )
            if orphan in {"09110", "10004"}:
                series.objects.create(
                    content_type_id=ct.pk, object_id=orphan, dataset=f"acs5_{orphan[:2]}",
                    variable_code="B01001_001E", start_year=2020, end_year=2022,
                    years=[2020, 2022], values=[10, 20],
                )
        assert not boundary.objects.filter(geoid__in=[orphan for orphan, _ in keys]).exists()
    original = {
        name: list(legacy_demographics.get_model("siege_geo", name).objects.order_by("pk").values())
        for name in ("DemographicSnapshot", "DemographicTimeSeries")
    }
    assert snapshots.objects.exclude(dataset="acs5").count() == 13
    assert series.objects.count() == 2

    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    for name, expected in original.items():
        assert list(after.get_model("siege_geo", name).objects.order_by("pk").values()) == expected
        assert f"{name} GEOID migration: converted=0 quarantined=0 deduplicated=0" in caplog.text
    assert not after.get_model("siege_geo", "DemographicKeyArchive").objects.exists()


def test_migration_geoid_only_probe_keeps_all_10059_rows(legacy_demographics, caplog):
    caplog.set_level("WARNING", logger="siege_utilities.geo.django.migrations.0019_demographic_geoid_keys")
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    state_codes = (
        "01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 "
        "28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 "
        "54 55 56 60 66 69 72 78"
    ).split()
    fixtures = {
        "State": [(pk, geoid) for pk, geoid in enumerate(state_codes, 1)],
        "County": [(11, "06037"), (12, "48201"), (6037, "13001")],
        "ZCTA": [(pk, f"{pk + 600:05d}") for pk in range(1, 10001)],
    }
    snapshots = legacy_demographics.get_model("siege_geo", "DemographicSnapshot")
    for name, keys in fixtures.items():
        boundary = legacy_demographics.get_model("siege_geo", name)
        boundary.objects.bulk_create([
            boundary(pk=pk, geoid=geoid, vintage_year=2020, geometry=geometry)
            for pk, geoid in keys
        ], batch_size=1000)
        ct = legacy_demographics.get_model("contenttypes", "ContentType").objects.get(
            app_label="siege_geo", model=name.lower(),
        )
        snapshots.objects.bulk_create([
            snapshots(content_type_id=ct.pk, object_id=geoid, dataset="acs5", year=2022)
            for _, geoid in keys
        ], batch_size=1000)
    original = list(snapshots.objects.order_by("pk").values())

    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    assert snapshots.objects.count() == 10059
    assert list(snapshots.objects.order_by("pk").values()) == original
    assert not after.get_model("siege_geo", "DemographicKeyArchive").objects.exists()
    assert "DemographicSnapshot GEOID migration: converted=0 quarantined=0 deduplicated=0" in caplog.text


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
        # 13001 is GEOID-shaped, so its coincident PK must not rewrite it.
        # 99999 stays GEOID-native despite also matching a different boundary PK.
        # 88888 is also a preserved orphan, with no loaded GEOID or PK match.
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
def test_migration_converts_quarantines_dedupes_and_reverses(legacy_demographics, caplog, winner, monkeypatch):
    monkeypatch.setenv("SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE", "1")
    caplog.set_level("WARNING", logger="siege_utilities.geo.django.migrations.0019_demographic_geoid_keys")
    original = _legacy_rows(legacy_demographics, winner)
    executor = MigrationExecutor(connection)
    executor.migrate([CURRENT])
    after = executor.loader.project_state([CURRENT]).apps
    archive = after.get_model("siege_geo", "DemographicKeyArchive")
    for name in original:
        model = after.get_model("siege_geo", name)
        rows = model.objects.filter(dataset="acs5")
        assert set(rows.values_list("object_id", flat=True)) == {"06037", "13001", "99999", "88888"}
        winning_key = "7" if winner == "pk_newest" else "06037"
        winning_row = next(row for row in original[name] if row["object_id"] == winning_key)
        assert rows.get(object_id="06037").pk == winning_row["id"]
        assert model.objects.filter(dataset="dec_pl").count() == 1
        assert archive.objects.filter(model_name=name).count() == (3 if winner == "pk_newest" else 2)
        assert archive.objects.filter(model_name=name, reason="ambiguous_pk_and_geoid").count() == 0
        assert archive.objects.filter(model_name=name, reason="unresolvable_key").count() == 1
        assert archive.objects.filter(model_name=name, reason="converted_pk").count() == (1 if winner == "pk_newest" else 0)
        assert archive.objects.filter(model_name=name, reason="duplicate").count() == 1
        assert not archive.objects.filter(model_name=name, original_data__object_id__in=["13001", "88888"]).exists()
        assert f"{name} GEOID migration: converted=1 quarantined=1 deduplicated=1" in caplog.text
        duplicate = rows.get(object_id="06037")
        duplicate.pk = None
        with pytest.raises(IntegrityError), transaction.atomic():
            duplicate.save(force_insert=True)

    MigrationExecutor(connection).migrate([PREVIOUS])
    for name, expected in original.items():
        restored = legacy_demographics.get_model("siege_geo", name)
        assert list(restored.objects.order_by("pk").values()) == expected


def test_migration_reverse_refuses_to_overwrite_newer_edits(legacy_demographics, monkeypatch):
    monkeypatch.setenv("SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE", "1")
    _legacy_rows(legacy_demographics)
    MigrationExecutor(connection).migrate([CURRENT])
    row = DemographicSnapshot.objects.get(object_id="06037", dataset="acs5")
    old_values = row.values
    DemographicSnapshot.objects.filter(pk=row.pk).update(values={"new": 42})
    try:
        with pytest.raises(RuntimeError, match="row changed after GEOID migration"):
            MigrationExecutor(connection).migrate([PREVIOUS])
        assert DemographicSnapshot.objects.get(pk=row.pk).values == {"new": 42}
    finally:
        DemographicSnapshot.objects.filter(pk=row.pk).update(values=old_values)
