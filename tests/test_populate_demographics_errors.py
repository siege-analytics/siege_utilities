"""Error-path coverage (SU-4b) for the populate_demographics management command."""
import io
import logging
from unittest.mock import Mock

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
    pytest.skip("Install GDAL and configure GDAL_LIBRARY_PATH to run GeoDjango tests",
                allow_module_level=True)
from django.core.management.base import CommandError
from siege_utilities.geo.django.management.commands.populate_demographics import Command
from siege_utilities.geo.django.management.commands import populate_demographics
from siege_utilities.geo.django.services.demographic_service import (
    DemographicPopulationResult,
    DemographicPopulationService,
)

SECRET = 'sentinel-1402-private-value'


def test_normalize_state_raises_command_error_on_invalid_state():
    with pytest.raises(CommandError) as exc_info:
        Command()._normalize_state("NOTASTATEZZ")
    assert "Invalid state identifier" in str(exc_info.value)


@pytest.fixture(autouse=True)
def capture_diagnostics(caplog, monkeypatch):
    logger = logging.getLogger('census_credential_security_test')
    monkeypatch.setattr(logger, 'disabled', False)
    monkeypatch.setattr(logger, 'propagate', True)
    caplog.set_level(logging.DEBUG, logger=logger.name)
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(populate_demographics, 'logger', logger, raising=False)


@pytest.fixture
def demographic_service(monkeypatch):
    service = Mock(spec=DemographicPopulationService)
    service.populate.return_value = DemographicPopulationResult(
        geography_type='tract', year=2022, dataset='acs5', state_fips='06',
        variable_group='income', records_created=0, records_updated=0,
        records_skipped=0, errors=['Census request failed'],
    )
    factory = Mock(spec=DemographicPopulationService, return_value=service)
    monkeypatch.setattr(populate_demographics, 'DemographicPopulationService', factory)
    return factory


@pytest.mark.parametrize('option', [['--api-key', SECRET], ['--api-key=' + SECRET]])
def test_census_cli_key_rejected_without_echoing_secret(option, caplog):
    parser = populate_demographics.Command().create_parser('manage.py', 'populate_demographics')
    with pytest.raises(CommandError, match='CENSUS_API_KEY') as exc:
        parser.parse_args([
            '--year', '2022', '--type', 'tract', '--state', '06', '--variables', 'income',
        ] + option)
    assert SECRET not in str(exc.value)
    assert caplog.records
    assert SECRET not in caplog.text


def test_census_direct_legacy_key_rejected_without_echoing_secret(demographic_service, caplog):
    with pytest.raises(CommandError, match='CENSUS_API_KEY') as exc:
        populate_demographics.Command().handle(
            year=2022, type='tract', state='06', variables='income', api_key=SECRET,
        )
    demographic_service.assert_not_called()
    assert SECRET not in str(exc.value)
    assert caplog.records
    assert SECRET not in caplog.text


@pytest.mark.parametrize('api_key', [SECRET, None])
def test_census_env_key_reaches_service_on_failure(demographic_service, monkeypatch, caplog, api_key):
    monkeypatch.delenv('CENSUS_API_KEY', raising=False)
    if api_key is not None:
        monkeypatch.setenv('CENSUS_API_KEY', api_key)
    output = io.StringIO()
    populate_demographics.Command(stdout=output).handle(
        year=2022, type='tract', state='06', variables='income',
    )
    demographic_service.assert_called_once_with(api_key=api_key)
    assert 'Total errors: 1' in output.getvalue()
    assert 'Census request failed' in output.getvalue()
    assert SECRET not in output.getvalue()
    assert SECRET not in caplog.text
