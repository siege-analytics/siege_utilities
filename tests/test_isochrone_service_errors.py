"""Error-path coverage (SU-4b) for geo.django.services.isochrone_service."""
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
from siege_utilities.geo.django.services.isochrone_service import (
    IsochroneComputeService,
)


def test_geojson_to_multipolygon_raises_on_empty_features():
    with pytest.raises(ValueError) as exc_info:
        IsochroneComputeService._geojson_to_multipolygon({"features": []})
    assert "no features" in str(exc_info.value)
