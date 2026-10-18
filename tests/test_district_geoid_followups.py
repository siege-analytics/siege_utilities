"""#1522 post-merge regressions: CD session GEOIDs, ZZ __str__, command exit."""

import io
import re
from unittest import mock

import pytest

pytest.importorskip("django", reason="Install siege-utilities[geodjango] to run model tests.")
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip("Install GDAL/GEOS to run model tests.", allow_module_level=True)

from django.core.management import call_command
from django.core.management.base import CommandError

from siege_utilities.geo.django.models import CongressionalDistrict
from siege_utilities.geo.django.services.population_service import PopulationResult

# Real cdsession=112 GEOIDs from the electinfo TIGER warehouse: STATEFP + 112 + CD.
REAL_CD112 = ["0111201", "4811227", "0611253", "0211200"]


def _cd_pattern():
    (constraint,) = [c for c in CongressionalDistrict._meta.constraints if c.name == "cd_geoid_format"]
    return dict(constraint.condition.children)["geoid__regex"]


@pytest.mark.parametrize("raw", REAL_CD112)
def test_cd112_session_embedded_geoid_normalises_to_tiger_shape(raw):
    stored = CongressionalDistrict.normalize_geoid(raw, congress_number=112)
    assert stored == raw[:2] + raw[5:]
    assert re.fullmatch(_cd_pattern(), stored)
    assert CongressionalDistrict.parse_geoid(stored) == {
        "state_fips": raw[:2],
        "district_number": raw[5:],
    }


def test_cd_session_mismatch_is_rejected_not_truncated():
    with pytest.raises(ValueError):
        CongressionalDistrict.normalize_geoid("0111301", congress_number=112)


def test_cd_str_handles_unassigned_zz():
    cd = CongressionalDistrict(geoid="26ZZ", name="Michigan", state_fips="26", district_number="ZZ")
    assert str(cd) == "Michigan District ZZ (unassigned) (26ZZ)"


def test_populate_boundaries_reports_skipped_and_exits_nonzero_on_rejected_rows():
    result = PopulationResult(
        geography_type="cd", year=2020, state_fips=None,
        records_created=4, records_updated=0, records_skipped=1,
        errors=["GEOID 2601!: violates check constraint"],
    )
    out = io.StringIO()
    target = "siege_utilities.geo.django.management.commands.populate_boundaries.BoundaryPopulationService"
    with mock.patch(target, autospec=True) as service:
        service.return_value.populate.return_value = result
        with pytest.raises(CommandError):
            call_command("populate_boundaries", "--year", "2020", "--type", "cd", stdout=out)
    text = out.getvalue()
    assert "4 created" in text and "1 skipped" in text
    assert "cd: 4 created, 0 updated, 1 skipped, 1 errors" in text
    assert "Total: 4 created, 0 updated, 1 skipped" in text


@pytest.mark.parametrize("raw", REAL_CD112)
def test_cd112_raw_codes_are_admitted_and_parse_the_actual_district(raw):
    assert re.fullmatch(_cd_pattern(), raw)
    assert CongressionalDistrict.parse_geoid(raw) == {
        "state_fips": raw[:2], "district_number": raw[5:],
    }


@pytest.mark.parametrize("raw", ["0111301", "01112ZZ", "01112!1", "011120", "01112001", "0A11201"])
def test_cd_constraint_does_not_admit_unobserved_session_shapes(raw):
    assert re.fullmatch(_cd_pattern(), raw) is None


@pytest.mark.parametrize("raw", ["2601!", "26_1", "01112ZZ", "", "0111201\n"])
def test_cd_normalization_rejects_malformed_codes(raw):
    with pytest.raises(ValueError, match="Invalid congressional district GEOID"):
        CongressionalDistrict.normalize_geoid(raw, congress_number=112)


def test_cd_normalization_requires_known_congress_for_embedded_code():
    with pytest.raises(ValueError, match="expected Congress None"):
        CongressionalDistrict.normalize_geoid("0111201", congress_number=None)


@pytest.mark.parametrize("code,label", [
    ("00", "At-Large"), ("98", "At-Large"), ("01", "District 1"),
    ("A1", "District A1"), ("zz", "District zz (unassigned)"),
])
def test_cd_str_preserves_numeric_at_large_and_other_codes(code, label):
    cd = CongressionalDistrict(geoid="26" + code, name="Michigan", district_number=code)
    assert str(cd) == f"Michigan {label} (26{code})"


@pytest.mark.parametrize("skipped,errors", [(1, []), (0, ["download failed"])])
def test_populate_command_exits_one_for_skips_or_errors(skipped, errors):
    from siege_utilities.geo.django.management.commands.populate_boundaries import Command

    result = PopulationResult("cd", 2020, None, 4, 2, skipped, errors)
    out, err = io.StringIO(), io.StringIO()
    command = Command(stdout=out, stderr=err)
    command.requires_system_checks = []
    target = "siege_utilities.geo.django.management.commands.populate_boundaries.BoundaryPopulationService"
    with mock.patch(target, autospec=True) as service:
        service.return_value.populate.return_value = result
        with pytest.raises(SystemExit) as exit_status:
            command.run_from_argv(["manage.py", "populate_boundaries", "--year", "2020", "--type", "cd"])
    assert exit_status.value.code == 1
    assert f"Total: 4 created, 2 updated, {skipped} skipped" in out.getvalue()
    assert "Boundary population incomplete" in err.getvalue()


def test_populate_command_success_reports_all_counts():
    out = io.StringIO()
    target = "siege_utilities.geo.django.management.commands.populate_boundaries.BoundaryPopulationService"
    with mock.patch(target, autospec=True) as service:
        service.return_value.populate.return_value = PopulationResult("cd", 2020, None, 4, 2, 0, [])
        call_command("populate_boundaries", "--year", "2020", "--type", "cd", stdout=out)
    assert "cd: 4 created, 2 updated, 0 skipped, 0 errors" in out.getvalue()
    assert "Total: 4 created, 2 updated, 0 skipped" in out.getvalue()


def test_populate_command_totals_include_successful_and_partial_types():
    from siege_utilities.geo.django.management.commands.populate_boundaries import Command

    out = io.StringIO()
    target = "siege_utilities.geo.django.management.commands.populate_boundaries.BoundaryPopulationService"
    with mock.patch.object(Command, "GEOGRAPHY_TYPES", ["cd", "sldl"]), mock.patch(target, autospec=True) as service:
        service.return_value.populate.side_effect = [
            PopulationResult("cd", 2020, None, 4, 1, 2, ["invalid CD"]),
            PopulationResult("sldl", 2020, None, 3, 2, 0, []),
        ]
        with pytest.raises(CommandError, match="2 skipped, 1 errors"):
            call_command("populate_boundaries", "--year", "2020", "--type", "all", stdout=out)
    assert "cd: 4 created, 1 updated, 2 skipped, 1 errors" in out.getvalue()
    assert "sldl: 3 created, 2 updated, 0 skipped, 0 errors" in out.getvalue()
    assert "Total: 7 created, 3 updated, 2 skipped" in out.getvalue()
