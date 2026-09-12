"""Error-path coverage (SU-4b) for geo.django.services.population_service."""
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
from siege_utilities.geo.django.services.population_service import (
    BoundaryPopulationService,
)


def test_download_boundaries_raises_on_unknown_geography_type():
    with pytest.raises(ValueError) as exc_info:
        BoundaryPopulationService()._download_boundaries("not_a_geography", 2020)
    assert "Unknown geography type" in str(exc_info.value)
