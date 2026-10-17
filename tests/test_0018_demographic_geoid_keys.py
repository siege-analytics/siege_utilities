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
