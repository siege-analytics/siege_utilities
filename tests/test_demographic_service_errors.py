"""Error-path coverage (SU-4b) for geo.django.services.demographic_service."""
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
from siege_utilities.geo.django.services.demographic_service import (
    DemographicPopulationService,
)


def test_get_content_type_raises_on_unknown_geography_type():
    with pytest.raises(ValueError) as exc_info:
        DemographicPopulationService()._get_content_type("not_a_geography")
    assert "Unknown geography type" in str(exc_info.value)
