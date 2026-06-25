"""Error-path coverage (SU-4b) for the populate_nces management command."""
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
from siege_utilities.geo.django.management.commands.populate_nces import Command


def test_handle_rejects_unknown_action():
    with pytest.raises(CommandError) as exc_info:
        Command().handle(
            year=2020, action="bogus_action_zzz", state=None,
            update=False, batch_size=500, cache_dir=None,
        )
    assert "Unknown action" in str(exc_info.value)
