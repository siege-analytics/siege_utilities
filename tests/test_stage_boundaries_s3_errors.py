"""Error-path coverage (SU-4b) for the stage_boundaries_s3 management command."""
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
from django.core.management.base import CommandError
import siege_utilities.geo.django.management.commands.stage_boundaries_s3 as stage


def test_handle_raises_when_boto3_missing(monkeypatch):
    # Force the dependency guard regardless of whether boto3 is installed.
    monkeypatch.setattr(stage, "boto3", None)
    with pytest.raises(CommandError) as exc_info:
        stage.Command().handle()
    assert "boto3 is required" in str(exc_info.value)
