"""Exercise real CHECK failures and savepoints without a PostGIS server.

The test model stores geometry as text. All queries, inserts, updates,
constraints, and transactions use Django's real SQLite backend; only the
download and model selection are replaced. No spatial SQL is exercised.
"""

import logging

import pytest

gpd = pytest.importorskip("geopandas", reason="Install siege-utilities[geo] to run loader tests.")
pytest.importorskip("django", reason="Install siege-utilities[geodjango] to run loader tests.")
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH to run loader tests.",
        allow_module_level=True,
    )

from django.db import connections, models
from django.db.utils import ConnectionHandler
from django.test.utils import CaptureQueriesContext, isolate_apps
from shapely.geometry import Polygon

from siege_utilities.geo.django.models import StateLegislativeLower
from siege_utilities.geo.django.services.population_service import BoundaryPopulationService


@pytest.fixture
def boundary_table(django_db_blocker):
    original = connections["default"]
    local = ConnectionHandler({
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
    })["default"]
    with isolate_apps(), django_db_blocker.unblock():
        class Boundary(models.Model):
            geoid = models.CharField(max_length=5)
            vintage_year = models.PositiveSmallIntegerField()
            name = models.CharField(max_length=255)
            geometry = models.TextField()
            state_fips = models.CharField(max_length=2)
            district_number = models.CharField(max_length=3)
            area_land = models.BigIntegerField(null=True)
            area_water = models.BigIntegerField(null=True)

            parse_geoid = staticmethod(StateLegislativeLower.parse_geoid)

            class Meta:
                app_label = "population_tests"
                unique_together = [("geoid", "vintage_year")]
                constraints = [
                    *StateLegislativeLower._meta.constraints,
                    models.CheckConstraint(
                        condition=models.Q(area_land__gte=0), name="nonnegative_land"
                    ),
                ]

        connections["default"] = local
        try:
            with local.schema_editor() as editor:
                editor.create_model(Boundary)
            yield Boundary
        finally:
            local.close()
            connections["default"] = original


@pytest.fixture
def service(boundary_table, monkeypatch):
    service = BoundaryPopulationService()
    monkeypatch.setattr(service, "_get_model", lambda geography_type: boundary_table)
    return service


def _supply_rows(service, monkeypatch, geoids, land=None):
    frame = gpd.GeoDataFrame(
        {
            "GEOID": geoids,
            "NAME": ["District " + geoid for geoid in geoids],
            "ALAND": land if land is not None else [1] * len(geoids),
            "AWATER": [0] * len(geoids),
        },
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])] * len(geoids),
        crs="EPSG:4326",
    )
    monkeypatch.setattr(service, "_download_boundaries", lambda *args: frame)


@pytest.mark.parametrize("batch_size", [2, 100], ids=["full-batch", "final-batch"])
def test_populate_keeps_valid_rows_after_check_failure(
    service, boundary_table, monkeypatch, caplog, batch_size
):
    """A malformed GEOID raises IntegrityError, without losing earlier/later rows."""
    _supply_rows(service, monkeypatch, ["27001", "27002", "27003", "27!04", "27005"])
    with caplog.at_level(logging.WARNING):
        result = service.populate("sldl", 2024, "27", batch_size=batch_size)

    assert list(boundary_table.objects.order_by("geoid").values_list("geoid", flat=True)) == [
        "27001", "27002", "27003", "27005",
    ]
    assert (result.records_created, result.records_skipped, result.total_processed) == (4, 1, 5)
    assert not result.success
    assert len(result.errors) == 1
    assert "27!04" in result.errors[0]
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "27!04" in caplog.text


def test_populate_reports_each_invalid_row(service, boundary_table, monkeypatch, caplog):
    """Both GEOID and land-area CHECK constraints raise real IntegrityError."""
    _supply_rows(service, monkeypatch, ["27!01", "27002", "27003"], [1, -1, 1])
    with caplog.at_level(logging.WARNING):
        result = service.populate("sldl", 2024, "27")

    assert list(boundary_table.objects.values_list("geoid", flat=True)) == ["27003"]
    assert (result.records_created, result.records_skipped) == (1, 2)
    assert len(result.errors) == len(caplog.records) == 2
    assert "27!01" in caplog.text and "27002" in caplog.text
    assert all(record.levelno == logging.WARNING for record in caplog.records)


def test_populate_reports_duplicate_in_batch(service, boundary_table, monkeypatch, caplog):
    """A UNIQUE IntegrityError is reported rather than counted as a created row."""
    _supply_rows(service, monkeypatch, ["27001", "27001", "27002"])
    with caplog.at_level(logging.WARNING):
        result = service.populate("sldl", 2024, "27")

    assert boundary_table.objects.count() == 2
    assert (result.records_created, result.records_skipped) == (2, 1)
    assert len(result.errors) == len(caplog.records) == 1
    assert "27001" in caplog.text


def test_populate_keeps_valid_rows_after_update_check_failure(
    service, boundary_table, monkeypatch, caplog
):
    """An UPDATE IntegrityError must roll back before the next row's query."""
    _supply_rows(service, monkeypatch, ["27001"])
    service.populate("sldl", 2024, "27")
    # Exclude the seed call's summary from the update assertion.
    caplog.clear()
    _supply_rows(service, monkeypatch, ["27001", "27002"], [-1, 2])
    with caplog.at_level(logging.WARNING):
        result = service.populate("sldl", 2024, "27", update_existing=True)

    assert boundary_table.objects.get(geoid="27001").area_land == 1
    assert boundary_table.objects.get(geoid="27002").area_land == 2
    assert (result.records_created, result.records_updated, result.records_skipped) == (1, 0, 1)
    assert len(result.errors) == len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "27001" in caplog.text


def test_populate_healthy_rows_use_bulk_insert(service, boundary_table, monkeypatch):
    _supply_rows(service, monkeypatch, ["27001", "27002", "27003"])
    with CaptureQueriesContext(connections["default"]) as queries:
        result = service.populate("sldl", 2024, "27")

    assert boundary_table.objects.count() == result.records_created == 3
    assert result.success and result.records_skipped == 0
    assert len([query for query in queries if query["sql"].startswith("INSERT")]) == 1
