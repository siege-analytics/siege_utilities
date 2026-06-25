"""Error-path coverage (SU-4b) for the populate_pl_demographics management command."""
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
from siege_utilities.geo.django.management.commands.populate_pl_demographics import Command


def test_handle_raises_command_error_on_invalid_state():
    # normalize_state_identifier raises ValueError -> wrapped as CommandError,
    # before any download or DB access.
    with pytest.raises(CommandError) as exc_info:
        Command().handle(
            state="NOTASTATEZZ", year=2020, geography="tract",
            tables=None, batch_size=500, update=False,
        )
    assert exc_info.value is not None


def test_resolve_model_returns_none_for_unknown_geography():
    # Drives the None branch that handle() converts into a CommandError.
    assert Command()._resolve_model("not_a_geography") is None
