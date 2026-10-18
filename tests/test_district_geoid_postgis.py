"""Run migration 0014 against PostGIS; see docs/testing/postgis.md."""

import os
from uuid import uuid4

import pytest

pytest.importorskip("django", reason="Install siege-utilities[geodjango] to run PostGIS tests.")
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401
    from django.contrib.gis.geos import MultiPolygon, Polygon
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH; "
        "then follow docs/testing/postgis.md to run PostGIS tests.",
        allow_module_level=True,
    )

from django.conf import settings
from django.db import IntegrityError, OperationalError, connections, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.utils import ConnectionHandler

from siege_utilities.geo.django.models import (
    CongressionalDistrict,
    StateLegislativeLower,
    StateLegislativeUpper,
)

pytestmark = pytest.mark.postgis

POSTGIS_REMEDIATION = (
    "Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_NAME/USER/PASSWORD/HOST/PORT "
    "to a reachable PostGIS test database (CREATE EXTENSION postgis; "
    "grant CREATE on the database), then run python -m pytest "
    "tests/test_district_geoid_postgis.py -m postgis --no-cov -rs; "
    "see docs/testing/postgis.md."
)


@pytest.fixture
def district_postgis(django_db_blocker, request):
    """Create historical tables in a disposable schema without migrating public."""
    if os.environ.get("SIEGE_TEST_POSTGIS") != "1":
        pytest.skip(POSTGIS_REMEDIATION)
    database = settings.DATABASES["default"].copy()
    if database["ENGINE"] != "django.contrib.gis.db.backends.postgis":
        pytest.skip(
            "Use tests.django_project.settings with GDAL/GEOS installed. "
            + POSTGIS_REMEDIATION
        )
    database["OPTIONS"] = {**database.get("OPTIONS", {}), "connect_timeout": 3}
    local = ConnectionHandler({"default": database})["default"]
    original = connections["default"]
    schema = "district_geoid_test_" + uuid4().hex
    with django_db_blocker.unblock():
        try:
            try:
                local.ensure_connection()
            except OperationalError:
                pytest.skip("PostGIS test database is unreachable. " + POSTGIS_REMEDIATION)
            with local.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
                if cursor.fetchone() is None:
                    pytest.skip(
                        "Enable the postgis extension in the test database. "
                        + POSTGIS_REMEDIATION
                    )
                cursor.execute(f'CREATE SCHEMA "{schema}"')
            try:
                with local.cursor() as cursor:
                    cursor.execute(f'SET search_path TO "{schema}", public')
                connections["default"] = local
                loader = MigrationLoader(None)
                migration = loader.disk_migrations[
                    "siege_geo", getattr(request, "param", "0014_district_geoid_charclass")
                ]
                before = loader.project_state(migration.dependencies)
                with local.schema_editor() as editor:
                    for name in (
                        "State", "CongressionalDistrict",
                        "StateLegislativeUpper", "StateLegislativeLower",
                    ):
                        editor.create_model(before.apps.get_model("siege_geo", name))
                yield local, migration, before
            finally:
                connections["default"] = original
                with local.cursor() as cursor:
                    cursor.execute(f'DROP SCHEMA "{schema}" CASCADE')
        finally:
            local.close()


def _create_district(model, geoid, vintage_year=2024):
    return model.objects.create(
        geoid=geoid,
        vintage_year=vintage_year,
        name="District " + geoid,
        state_fips=geoid[:2],
        district_number=geoid[-model._meta.get_field("district_number").max_length:],
        geometry=MultiPolygon(Polygon(((0, 0), (1, 0), (1, 1), (0, 0))), srid=4326),
    )


@pytest.mark.parametrize(
    "model,old_name,valid,invalid",
    [
        (
            CongressionalDistrict, "cd_geoid_4_digits",
            ["2601", "2600", "26ZZ", "26zz", "26Zz"],
            ["260", "26001", "2AZZ", "261-", "26_1", "26!1"],
        ),
        (
            StateLegislativeUpper, "sldu_geoid_5_digits",
            ["06001", "0200A", "0200a", "09ZZZ", "09zZz", "501-1"],
            ["020A", "02000A", "0A00A", "020_A", "020!A"],
        ),
        (
            StateLegislativeLower, "sldl_geoid_5_digits",
            ["06001", "2701A", "2701B", "2701a", "09ZZZ", "09zZz", "501-1"],
            ["271A", "27001A", "2A01A", "2701!", "270_A"],
        ),
    ],
    ids=["cd", "sldu", "sldl"],
)
def test_district_migration_postgis_checks_and_unique(
    district_postgis, model, old_name, valid, invalid
):
    """Exercise real POSIX CHECKs, unique errors, validation, and reversal."""
    connection, migration, before = district_postgis
    seed = _create_district(model, valid[0])
    assert migration.atomic is False
    assert connection.get_autocommit() and not connection.in_atomic_block
    with connection.schema_editor(atomic=migration.atomic) as editor:
        migration.apply(before.clone(), editor)
    constraint_name = model._meta.constraints[0].name
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT conname, convalidated, pg_get_constraintdef(oid) "
            "FROM pg_constraint WHERE conrelid = %s::regclass "
            "AND conname IN (%s, %s)",
            [model._meta.db_table, old_name, constraint_name],
        )
        rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][:2] == (constraint_name, True)
    assert " ~ " in rows[0][2]
    assert model.objects.get(pk=seed.pk).geoid == valid[0]

    for geoid in valid[1:]:
        _create_district(model, geoid)
    for geoid in invalid:
        with pytest.raises(IntegrityError) as error, transaction.atomic():
            _create_district(model, geoid)
        assert error.value.__cause__.diag.constraint_name == constraint_name
    with pytest.raises(IntegrityError) as error, transaction.atomic():
        _create_district(model, valid[0])
    assert error.value.__cause__.diag.sqlstate == "23505"
    _create_district(model, valid[0], vintage_year=2025)
    assert model.objects.count() == len(valid) + 1

    # Reversal must fail validation while widened codes remain, then be retryable.
    with pytest.raises(IntegrityError, match=old_name):
        with connection.schema_editor(atomic=migration.atomic) as editor:
            migration.unapply(before.clone(), editor)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT convalidated FROM pg_constraint "
            "WHERE conrelid = %s::regclass AND conname = %s",
            [model._meta.db_table, old_name],
        )
        assert cursor.fetchone() == (False,)
    with pytest.raises(IntegrityError, match=old_name), transaction.atomic():
        _create_district(model, valid[-2], vintage_year=2026)
    with connection.cursor() as cursor:
        cursor.execute(
            f'DELETE FROM "{model._meta.db_table}" WHERE geoid <> %s', [valid[0]]
        )
    with connection.schema_editor(atomic=migration.atomic) as editor:
        migration.unapply(before.clone(), editor)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT conname, convalidated FROM pg_constraint "
            "WHERE conrelid = %s::regclass AND conname IN (%s, %s)",
            [model._meta.db_table, old_name, constraint_name],
        )
        assert cursor.fetchall() == [(old_name, True)]
    assert model.objects.count() == 2


@pytest.mark.parametrize("district_postgis", ["0017_cd112_geoid_format"], indirect=True)
def test_cd112_forward_migration_accepts_real_codes_and_reverses(district_postgis):
    connection, migration, before = district_postgis
    model = CongressionalDistrict
    raw_codes = ["0111201", "4811227", "0611253", "0211200"]
    _create_district(model, "26ZZ")
    with pytest.raises(IntegrityError, match="cd_geoid_format"), transaction.atomic():
        _create_district(model, raw_codes[0])

    assert not migration.atomic and connection.get_autocommit()
    with connection.schema_editor(atomic=False) as editor:
        migration.apply(before.clone(), editor)
    for geoid in raw_codes:
        _create_district(model, geoid)
    pattern = dict(model._meta.constraints[0].condition.children)["geoid__regex"]
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT count(*) FROM "siege_geo_congressionaldistrict" WHERE geoid !~ %s',
            [r"^\d{2}[0-9A-Za-z]{2}$"],
        )
        assert cursor.fetchone() == (4,)
        cursor.execute(
            'SELECT count(*) FROM "siege_geo_congressionaldistrict" WHERE geoid !~ %s', [pattern]
        )
        assert cursor.fetchone() == (0,)
        cursor.execute(
            "SELECT convalidated FROM pg_constraint WHERE conrelid = %s::regclass AND conname = %s",
            [model._meta.db_table, "cd_geoid_format"],
        )
        assert cursor.fetchone() == (True,)
    for invalid in ["0111301", "01112ZZ", "01112!1", "0A11201", "2601!", "01112001"]:
        with pytest.raises(IntegrityError, match="cd_geoid_format"), transaction.atomic():
            _create_district(model, invalid)

    with pytest.raises(IntegrityError, match="cd_geoid_format"):
        with connection.schema_editor(atomic=False) as editor:
            migration.unapply(before.clone(), editor)
    with connection.cursor() as cursor:
        cursor.execute(
            'DELETE FROM "siege_geo_congressionaldistrict" WHERE geoid = ANY(%s)', [raw_codes]
        )
    with connection.schema_editor(atomic=False) as editor:
        migration.unapply(before.clone(), editor)
    with pytest.raises(IntegrityError, match="cd_geoid_format"), transaction.atomic():
        _create_district(model, raw_codes[0])
    assert list(model.objects.values_list("geoid", flat=True)) == ["26ZZ"]


@pytest.mark.parametrize("district_postgis", ["0017_cd112_geoid_format"], indirect=True)
@pytest.mark.parametrize("batch_size", [1, 100])
def test_cd_loader_normalizes_before_lookup_and_counts_rejections(
    district_postgis, monkeypatch, caplog, batch_size
):
    import logging

    import geopandas as gpd
    from shapely.geometry import Polygon as ShapelyPolygon

    from siege_utilities.geo.django.services.population_service import BoundaryPopulationService

    service = BoundaryPopulationService()
    raw_codes = ["0111201", "4811227", "0611253", "0211200", "0111302", "2601!", ""]
    frame = gpd.GeoDataFrame(
        {"GEOID": raw_codes, "NAME": raw_codes, "CDSESSN": ["112"] * len(raw_codes)},
        geometry=[ShapelyPolygon(((0, 0), (1, 0), (1, 1), (0, 0)))] * len(raw_codes),
        crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_download_boundaries", lambda *args: frame)
    with caplog.at_level(logging.WARNING):
        result = service.populate("cd", 2011, batch_size=batch_size)
    assert (result.records_created, result.records_skipped, result.total_processed) == (4, 3, 7)
    assert len(result.errors) == 3
    assert "0111302" in caplog.text and "2601!" in caplog.text and "Missing GEOID" in caplog.text
    assert set(CongressionalDistrict.objects.values_list("geoid", "district_number", "congress_number")) == {
        ("0101", "01", 112), ("4827", "27", 112), ("0653", "53", 112), ("0200", "00", 112),
    }
    # Both input forms must find the same identities, even during updates.
    frame = frame.iloc[:4].copy()
    frame["NAME"] = "Updated"
    updated = service.populate("cd", 2011, update_existing=True)
    assert (updated.records_created, updated.records_updated, updated.records_skipped) == (0, 4, 0)
    frame["GEOID"] = ["0101", "4827", "0653", "0200"]
    skipped = service.populate("cd", 2011)
    assert (skipped.records_created, skipped.records_skipped) == (0, 4)
    assert CongressionalDistrict.objects.filter(name="Updated").count() == 4


@pytest.mark.parametrize("district_postgis", ["0017_cd112_geoid_format"], indirect=True)
def test_cd_loader_counts_source_session_mismatch(district_postgis, monkeypatch, caplog):
    import logging

    import geopandas as gpd
    from shapely.geometry import Polygon as ShapelyPolygon

    from siege_utilities.geo.django.services.population_service import BoundaryPopulationService

    service = BoundaryPopulationService()
    frame = gpd.GeoDataFrame(
        {"geoid": ["0111201", "0211200"], "cdsessn": ["113", "112"]},
        geometry=[ShapelyPolygon(((0, 0), (1, 0), (1, 1), (0, 0)))] * 2, crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_download_boundaries", lambda *args: frame)
    with caplog.at_level(logging.WARNING):
        result = service.populate("cd", 2011)
    assert (result.records_created, result.records_skipped, result.total_processed) == (1, 1, 2)
    assert len(result.errors) == 1 and "CDSESSN 113" in result.errors[0]
    assert "0111201" in caplog.text
    assert list(CongressionalDistrict.objects.values_list("geoid", flat=True)) == ["0200"]
