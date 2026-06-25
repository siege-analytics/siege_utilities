"""Error-path coverage (SU-4b) for geo.django.services.crosswalk_service.

Drives the real load-failure handler in CrosswalkPopulationService.populate()
(crosswalk_service.py ~168-183): when the crosswalk load raises one of
(OSError, ValueError, TypeError, ImportError, RuntimeError), populate() must
catch it and return a CrosswalkPopulationResult flagged unsuccessful rather
than propagating.

populate() is decorated @transaction.atomic, which needs a live database to
enter; the CI ``test`` job has no Postgres service. The transaction wrapper is
infrastructure, not the unit under test, so we no-op Atomic.__enter__/__exit__
for the duration of the test and force the load to fail. mutation-check:
deleting the try/except handler lets the ValueError escape populate() and this
test goes red.
"""
import django.db.transaction as _transaction
import pytest

# GeoDjango management commands/services imported below require libgdal at
# import time. Skip the whole module when GDAL is unavailable (the no-GDAL CI
# job, Databricks, Lambda) so collection does not hard-fail; these tests still
# run and count for SU-4b wherever GDAL is present.
try:
    from django.core.exceptions import ImproperlyConfigured
except ImportError:  # Django itself absent
    ImproperlyConfigured = ImportError
try:
    from django.contrib.gis.db import models as _gis_models  # noqa: F401
except (ImportError, RuntimeError, ImproperlyConfigured, OSError):
    pytest.skip("GeoDjango/GDAL not available", allow_module_level=True)

import siege_utilities.geo.crosswalk as crosswalk_pkg
from siege_utilities.geo.django.services.crosswalk_service import (
    CrosswalkPopulationService,
)


@pytest.fixture
def _no_db_transaction(monkeypatch):
    # @transaction.atomic would require a DB connection to enter; bypass the
    # transaction machinery so populate()'s body (the handler) is reachable.
    monkeypatch.setattr(_transaction.Atomic, "__enter__", lambda self: None)
    monkeypatch.setattr(_transaction.Atomic, "__exit__", lambda self, *exc: False)


def test_populate_returns_failed_result_when_load_raises(_no_db_transaction, monkeypatch):
    def boom(**kwargs):
        raise ValueError("crosswalk source unavailable")

    monkeypatch.setattr(crosswalk_pkg, "get_crosswalk", boom)

    result = CrosswalkPopulationService().populate(
        geography_type="tract", source_year=2010, target_year=2020,
    )

    # The handler caught the load failure and returned an unsuccessful result
    # instead of letting it propagate.
    assert result.success is False
    assert result.records_created == 0
    assert any("crosswalk source unavailable" in e for e in result.errors)
