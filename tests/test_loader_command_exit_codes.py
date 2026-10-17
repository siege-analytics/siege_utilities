"""Loader commands report service failures to schedulers through CommandError."""

from contextlib import nullcontext
from functools import partial
from io import StringIO
from unittest.mock import patch

import pytest

pytest.importorskip("django")
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models as _gis_models  # noqa: F401
except (ImportError, RuntimeError, ImproperlyConfigured, OSError):
    pytest.skip("GeoDjango/GDAL not available", allow_module_level=True)

from django.core.management import call_command
from django.core.management.base import CommandError

from siege_utilities.geo.django.services.crosswalk_service import CrosswalkPopulationResult
from siege_utilities.geo.django.services.demographic_service import DemographicPopulationResult
from siege_utilities.geo.django.services.nces_service import NCESPopulationResult
from siege_utilities.geo.django.services.nlrb_service import NLRBPopulationResult
from siege_utilities.geo.django.services.population_service import PopulationResult
from siege_utilities.geo.django.services.timezone_service import TimezonePopulationResult
from siege_utilities.geo.django.services.urbanicity_service import ClassificationResult

pytestmark = pytest.mark.requires_gdal

COMMANDS = "siege_utilities.geo.django.management.commands"
SERVICES = "siege_utilities.geo.django.services"

LOADERS = {
    "populate_boundaries": (
        f"{COMMANDS}.populate_boundaries.BoundaryPopulationService",
        "populate",
        partial(PopulationResult, geography_type="county", year=2020, state_fips=None),
        {"year": 2020, "type": "county"},
        "Total:",
    ),
    "populate_demographics": (
        f"{COMMANDS}.populate_demographics.DemographicPopulationService",
        "populate",
        partial(
            DemographicPopulationResult, geography_type="county", year=2020,
            state_fips="06", dataset="acs5", variable_group="income",
        ),
        {"year": 2020, "type": "county", "state": "06", "variables": "income"},
        "Total:",
    ),
    "populate_crosswalks": (
        f"{COMMANDS}.populate_crosswalks.CrosswalkPopulationService",
        "populate",
        partial(
            CrosswalkPopulationResult, geography_type="tract", source_year=2010,
            target_year=2020, state_fips=None,
        ),
        {"source_year": 2010, "target_year": 2020, "type": "tract"},
        "Crosswalk population failed",
    ),
    "populate_timezones": (
        f"{SERVICES}.timezone_service.TimezonePopulationService",
        "populate_from_geojson",
        TimezonePopulationResult,
        {"file": "/nonexistent"},
        "Timezones:",
    ),
    "populate_nlrb_regions": (
        f"{SERVICES}.nlrb_service.NLRBPopulationService",
        "populate",
        NLRBPopulationResult,
        {},
        "NLRB regions:",
    ),
    "populate_nces": (
        f"{SERVICES}.nces_service.NCESPopulationService",
        "populate_locale_boundaries",
        partial(NCESPopulationResult, action="locale_boundaries", year=2023),
        {"year": 2023, "action": "locale_boundaries"},
        "Total:",
    ),
    "classify_urbanicity": (
        f"{COMMANDS}.classify_urbanicity.UrbanicityClassificationService",
        "classify",
        ClassificationResult,
        {"year": 2020},
        "Total processed:",
    ),
}


def make_result(command, *, created=0, updated=0, skipped=0, errors=()):
    factory = LOADERS[command][2]
    if command == "classify_urbanicity":
        return factory(
            classified=created + updated, skipped_no_population=skipped,
            errors=list(errors),
        )
    return factory(
        records_created=created, records_updated=updated, records_skipped=skipped,
        errors=list(errors),
    )


@pytest.fixture(params=LOADERS)
def loader(request):
    command = request.param
    target, method, _, options, summary = LOADERS[command]
    with patch(target, autospec=True) as service:
        yield command, getattr(service.return_value, method), options, summary


@pytest.mark.parametrize("created", [0, 2], ids=["total-failure", "partial-failure"])
def test_errors_raise_after_existing_output(loader, created):
    command, method, options, summary = loader
    method.return_value = make_result(command, created=created, errors=["download failed"])
    out, err = StringIO(), StringIO()

    with pytest.raises(CommandError, match="1 error"):
        call_command(command, stdout=out, stderr=err, **options)

    method.assert_called_once()
    assert summary in out.getvalue()
    assert "download failed" in out.getvalue() + err.getvalue()


@pytest.mark.parametrize("skipped", [0, 3], ids=["empty", "only-skipped"])
def test_allow_partial_with_nothing_loaded_still_raises(loader, skipped):
    command, method, options, _ = loader
    method.return_value = make_result(command, skipped=skipped, errors=["load failed"])

    with pytest.raises(CommandError, match="1 error"):
        call_command(command, "--allow-partial", **options)


@pytest.mark.parametrize("counts", [{"created": 2}, {"updated": 2}], ids=["created", "updated"])
def test_allow_partial_with_loaded_records_returns_normally(loader, counts):
    command, method, options, summary = loader
    method.return_value = make_result(command, **counts, skipped=3, errors=["row failed"])
    out, err = StringIO(), StringIO()

    call_command(command, "--allow-partial", stdout=out, stderr=err, **options)

    method.assert_called_once()
    assert summary in out.getvalue()
    assert "row failed" in out.getvalue() + err.getvalue()


@pytest.mark.parametrize("created", [0, 2], ids=["empty", "loaded"])
def test_clean_success_returns_normally_with_unchanged_output(loader, created):
    command, method, options, _ = loader
    method.return_value = make_result(command, created=created)
    out, err = StringIO(), StringIO()
    call_command(command, stdout=out, stderr=err, **options)
    expected_output = out.getvalue()
    assert expected_output
    assert not err.getvalue()

    out, err = StringIO(), StringIO()
    call_command(command, "--allow-partial", stdout=out, stderr=err, **options)
    assert out.getvalue() == expected_output
    assert not err.getvalue()


def test_missing_timezone_file_raises_after_printing_details():
    out, err = StringIO(), StringIO()
    with pytest.raises(CommandError, match="1 error"):
        call_command("populate_timezones", file="/nonexistent", stdout=out, stderr=err)
    assert "Timezones: created=0, updated=0, skipped=0" in out.getvalue()
    assert "File not found: /nonexistent" in err.getvalue()


@pytest.mark.parametrize("command", ["populate_boundaries", "populate_demographics", "populate_nces"])
@pytest.mark.parametrize("allow_partial,loaded", [(False, 2), (True, 0), (True, 2)])
@pytest.mark.parametrize("failure_first", [True, False], ids=["failure-first", "failure-last"])
def test_multi_result_commands_finish_reporting_before_deciding_exit(
    command, allow_partial, loaded, failure_first,
):
    target, method, _, options, _ = LOADERS[command]
    options = dict(options)
    if command == "populate_boundaries":
        from siege_utilities.geo.django.management.commands.populate_boundaries import Command
        count = len(Command.GEOGRAPHY_TYPES)
        options.update(type="all", state="06")
    elif command == "populate_demographics":
        from siege_utilities.geo.django.management.commands.populate_demographics import Command
        count = len(Command.VARIABLE_GROUPS)
        options["variables"] = "all"
    else:
        count = 3
        options["action"] = "all"

    results = [make_result(command, updated=loaded) for _ in range(count)]
    results[0 if failure_first else -1] = make_result(command, errors=["source failed"])
    out, err = StringIO(), StringIO()
    expectation = nullcontext() if allow_partial and loaded else pytest.raises(CommandError, match="1 error")
    args = ["--allow-partial"] if allow_partial else []

    with patch(target, autospec=True) as service:
        if command == "populate_nces":
            methods = [
                service.return_value.populate_locale_boundaries,
                service.return_value.populate_school_locations,
                service.return_value.enrich_school_districts,
            ]
            for action_method, result in zip(methods, results):
                action_method.return_value = result
        else:
            getattr(service.return_value, method).side_effect = results

        with expectation:
            call_command(command, *args, stdout=out, stderr=err, **options)

        assert len(service.return_value.method_calls) == count
    assert "source failed" in out.getvalue() + err.getvalue()
    if command == "populate_nces":
        assert out.getvalue().count("Total:") == count
    else:
        assert f"Total: 0 created, {(count - 1) * loaded} updated" in out.getvalue()
        assert "Total errors: 1" in out.getvalue()
