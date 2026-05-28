"""Tests for siege_utilities.geo.census.catalog_populator."""

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.census.catalog_populator import (
    CensusCatalogPopulator,
    _subject_key,
)
from siege_utilities.geo.census.catalog import FamilyType


BASE_URL = "https://api.census.gov"


@pytest.fixture()
def mock_variables():
    return {
        "variables": {
            "NAME": {"label": "Geographic Area Name", "concept": "NAME"},
            "GEO_ID": {"label": "Geography", "concept": "GEO_ID"},
            "B19001_001E": {
                "label": "Estimate!!Total:",
                "concept": "HOUSEHOLD INCOME IN THE PAST 12 MONTHS",
                "group": "B19001",
            },
            "B19001_002E": {
                "label": "Estimate!!Total:!!Less than $10,000",
                "concept": "HOUSEHOLD INCOME IN THE PAST 12 MONTHS",
                "group": "B19001",
            },
            "B19001_001M": {
                "label": "Margin of Error!!Total:",
                "concept": "HOUSEHOLD INCOME IN THE PAST 12 MONTHS",
                "group": "B19001",
            },
            "B19001A_001E": {
                "label": "Estimate!!Total:",
                "concept": "HOUSEHOLD INCOME IN THE PAST 12 MONTHS (WHITE ALONE HOUSEHOLDER)",
                "group": "B19001A",
            },
            "B19001A_002E": {
                "label": "Estimate!!Total:!!Less than $10,000",
                "concept": "HOUSEHOLD INCOME IN THE PAST 12 MONTHS (WHITE ALONE HOUSEHOLDER)",
                "group": "B19001A",
            },
            "B19001B_001E": {
                "label": "Estimate!!Total:",
                "concept": "HOUSEHOLD INCOME IN THE PAST 12 MONTHS (BLACK OR AFRICAN AMERICAN ALONE HOUSEHOLDER)",
                "group": "B19001B",
            },
            "B19013_001E": {
                "label": "Estimate!!Median household income in the past 12 months",
                "concept": "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS",
                "group": "B19013",
            },
            "B01001_001E": {
                "label": "Estimate!!Total:",
                "concept": "SEX BY AGE",
                "group": "B01001",
            },
            "B01001_002E": {
                "label": "Estimate!!Total:!!Male",
                "concept": "SEX BY AGE",
                "group": "B01001",
            },
        }
    }


@pytest.fixture()
def mock_groups():
    return {
        "groups": [
            {
                "name": "B19001",
                "description": "Income--HOUSEHOLD INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)",
            },
            {
                "name": "B19001A",
                "description": "Income--HOUSEHOLD INCOME IN THE PAST 12 MONTHS (WHITE ALONE HOUSEHOLDER)",
            },
            {
                "name": "B19001B",
                "description": "Income--HOUSEHOLD INCOME IN THE PAST 12 MONTHS (BLACK ALONE HOUSEHOLDER)",
            },
            {
                "name": "B19013",
                "description": "Income--MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS",
            },
            {
                "name": "B01001",
                "description": "Age-Sex--SEX BY AGE",
            },
        ]
    }


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


class TestSubjectKey:
    def test_splits_on_dash_dash(self):
        assert _subject_key("Income--HOUSEHOLD INCOME") == "Income"

    def test_no_dash_returns_full(self):
        assert _subject_key("HOUSEHOLD INCOME") == "Household Income"

    def test_empty_string(self):
        assert _subject_key("") == ""


class TestPopulatorBuildTables:
    def test_builds_correct_tables(self, mock_variables):
        pop = CensusCatalogPopulator(base_url=BASE_URL)
        tables = pop._build_tables(mock_variables["variables"])
        table_ids = {t.table_id for t in tables}

        assert "B19001" in table_ids
        assert "B19001A" in table_ids
        assert "B19001B" in table_ids
        assert "B19013" in table_ids
        assert "B01001" in table_ids
        assert "NAME" not in table_ids
        assert "GEO_ID" not in table_ids

    def test_excludes_moe_from_variables(self, mock_variables):
        pop = CensusCatalogPopulator(base_url=BASE_URL)
        tables = pop._build_tables(mock_variables["variables"])
        b19001 = next(t for t in tables if t.table_id == "B19001")
        codes = [v.code for v in b19001.variables]
        assert "B19001_001E" in codes
        assert "B19001_001M" not in codes

    def test_table_has_concept(self, mock_variables):
        pop = CensusCatalogPopulator(base_url=BASE_URL)
        tables = pop._build_tables(mock_variables["variables"])
        b19001 = next(t for t in tables if t.table_id == "B19001")
        assert "HOUSEHOLD INCOME" in b19001.concept


class TestPopulatorBuildSubjects:
    def test_builds_subjects_from_groups(self, mock_variables, mock_groups):
        pop = CensusCatalogPopulator(base_url=BASE_URL)
        tables = pop._build_tables(mock_variables["variables"])
        subjects = pop._build_subjects(mock_groups["groups"], tables)

        subject_ids = {s.subject_id for s in subjects}
        assert "income" in subject_ids
        assert "age-sex" in subject_ids

    def test_income_subject_has_tables(self, mock_variables, mock_groups):
        pop = CensusCatalogPopulator(base_url=BASE_URL)
        tables = pop._build_tables(mock_variables["variables"])
        subjects = pop._build_subjects(mock_groups["groups"], tables)

        income = next(s for s in subjects if s.subject_id == "income")
        table_ids = {t.table_id for t in income.tables}
        assert "B19001" in table_ids
        assert "B19013" in table_ids


class TestPopulatorIntegration:
    @patch("siege_utilities.geo.census.catalog_populator.requests.get")
    def test_populate_builds_full_catalog(self, mock_get, mock_variables, mock_groups):
        mock_get.side_effect = [
            _mock_response(mock_variables),
            _mock_response(mock_groups),
        ]

        pop = CensusCatalogPopulator(base_url=BASE_URL)
        catalog = pop.populate("acs5", 2022, survey_type="acs_5yr")

        assert len(catalog.tables) >= 5
        assert len(catalog.families) >= 1
        assert len(catalog.subjects) >= 2
        assert catalog.get_dataset("acs5_2022") is not None
        assert catalog.get_dataset("acs5_2022").year == 2022

    @patch("siege_utilities.geo.census.catalog_populator.requests.get")
    def test_populate_detects_race_families(self, mock_get, mock_variables, mock_groups):
        mock_get.side_effect = [
            _mock_response(mock_variables),
            _mock_response(mock_groups),
        ]

        pop = CensusCatalogPopulator(base_url=BASE_URL)
        catalog = pop.populate("acs5", 2022)

        race_families = [
            f for f in catalog.families.values()
            if f.family_type == FamilyType.RACE_ITERATION
        ]
        assert len(race_families) >= 1
        income_race = next(
            (f for f in race_families if f.root_table_id == "B19001"), None
        )
        assert income_race is not None
        assert "B19001A" in income_race.table_ids

    @patch("siege_utilities.geo.census.catalog_populator.requests.get")
    def test_populate_handles_api_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=404)

        pop = CensusCatalogPopulator(base_url=BASE_URL)
        with pytest.raises(Exception):
            pop.populate("acs5", 2022)

    @patch("siege_utilities.geo.census.catalog_populator.requests.get")
    def test_populate_calls_correct_urls(self, mock_get, mock_variables, mock_groups):
        mock_get.side_effect = [
            _mock_response(mock_variables),
            _mock_response(mock_groups),
        ]

        pop = CensusCatalogPopulator(base_url=BASE_URL)
        pop.populate("acs5", 2022)

        calls = mock_get.call_args_list
        assert len(calls) == 2
        assert "2022/acs/acs5/variables.json" in calls[0].args[0]
        assert "2022/acs/acs5/groups.json" in calls[1].args[0]
