"""Tests for CensusCatalog.search() — full-text search across catalog levels."""

import pytest

from siege_utilities.geo.census.catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusSubject,
    CensusTable,
    CensusVariable,
    FamilyType,
    SearchLevel,
    SearchResult,
    _tokenize_query,
)


def _make_variable(code, label, concept, table_id):
    return CensusVariable(
        code=code, label=label, concept=concept, table_id=table_id,
    )


def _make_table(table_id, concept="", label="", variables=None, geo=None):
    return CensusTable(
        table_id=table_id,
        label=label or concept,
        concept=concept,
        variables=variables or [],
        geography_levels=geo or [],
    )


@pytest.fixture()
def search_catalog():
    cat = CensusCatalog()

    v_income_total = _make_variable("B19001_001E", "Estimate!!Total:", "HOUSEHOLD INCOME IN THE PAST 12 MONTHS", "B19001")
    v_income_bin = _make_variable("B19001_002E", "Estimate!!Total:!!Less than $10,000", "HOUSEHOLD INCOME IN THE PAST 12 MONTHS", "B19001")
    v_age_total = _make_variable("B01001_001E", "Estimate!!Total:", "SEX BY AGE", "B01001")
    v_age_male = _make_variable("B01001_002E", "Estimate!!Total:!!Male", "SEX BY AGE", "B01001")

    t_income = _make_table("B19001", "HOUSEHOLD INCOME IN THE PAST 12 MONTHS", variables=[v_income_total, v_income_bin])
    t_income_white = _make_table("B19001A", "HOUSEHOLD INCOME IN THE PAST 12 MONTHS (WHITE ALONE HOUSEHOLDER)")
    t_income_black = _make_table("B19001B", "HOUSEHOLD INCOME IN THE PAST 12 MONTHS (BLACK ALONE HOUSEHOLDER)")
    t_median = _make_table("B19013", "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS")
    t_age = _make_table("B01001", "SEX BY AGE", variables=[v_age_total, v_age_male])
    t_race = _make_table("B02001", "RACE")

    cat.add_tables([t_income, t_income_white, t_income_black, t_median, t_age, t_race])

    fam_race = CensusFamily(
        family_id="race:B19001",
        family_type=FamilyType.RACE_ITERATION,
        root_table_id="B19001",
        tables=[t_income, t_income_white, t_income_black],
        description="Race/ethnicity iterations of B19001",
    )
    cat.add_family(fam_race)

    sub_income = CensusSubject(subject_id="income", label="Income and Poverty")
    sub_age = CensusSubject(subject_id="age-sex", label="Age and Sex")
    cat.add_subject(sub_income)
    cat.add_subject(sub_age)

    ds = CensusCatalogDataset(
        dataset_id="acs5_2022",
        survey_type="acs_5yr",
        year=2022,
        subjects=[sub_income, sub_age],
        tables={"B19001": t_income, "B19013": t_median, "B01001": t_age},
    )
    cat.add_dataset(ds)

    return cat


class TestTokenizeQuery:
    def test_splits_and_uppercases(self):
        assert _tokenize_query("household income") == ["HOUSEHOLD", "INCOME"]

    def test_removes_stop_words(self):
        assert _tokenize_query("income in the past 12") == ["INCOME"]

    def test_empty_query(self):
        assert _tokenize_query("") == []


class TestSearchByTable:
    def test_finds_table_by_concept_keyword(self, search_catalog):
        results = search_catalog.search("household income", level=SearchLevel.TABLE)
        ids = [r.id for r in results]
        assert "B19001" in ids
        assert "B19013" in ids

    def test_finds_table_by_id(self, search_catalog):
        results = search_catalog.search("B19001", level=SearchLevel.TABLE)
        assert results[0].id == "B19001"

    def test_race_tables_match_income(self, search_catalog):
        results = search_catalog.search("income", level=SearchLevel.TABLE)
        ids = [r.id for r in results]
        assert "B19001A" in ids
        assert "B19001B" in ids

    def test_no_match_returns_empty(self, search_catalog):
        results = search_catalog.search("zzzyyyxxx", level=SearchLevel.TABLE)
        assert results == []


class TestSearchByFamily:
    def test_finds_race_family(self, search_catalog):
        results = search_catalog.search("race B19001", level=SearchLevel.FAMILY)
        assert len(results) >= 1
        assert results[0].id == "race:B19001"

    def test_finds_family_by_concept(self, search_catalog):
        results = search_catalog.search("income race", level=SearchLevel.FAMILY)
        assert len(results) >= 1


class TestSearchBySubject:
    def test_finds_income_subject(self, search_catalog):
        results = search_catalog.search("income", level=SearchLevel.SUBJECT)
        assert any(r.id == "income" for r in results)

    def test_finds_age_subject(self, search_catalog):
        results = search_catalog.search("age sex", level=SearchLevel.SUBJECT)
        assert any(r.id == "age-sex" for r in results)


class TestSearchByVariable:
    def test_finds_variable_by_label(self, search_catalog):
        results = search_catalog.search("Male", level=SearchLevel.VARIABLE)
        assert any(r.id == "B01001_002E" for r in results)

    def test_finds_variable_by_code(self, search_catalog):
        results = search_catalog.search("B19001_001E", level=SearchLevel.VARIABLE)
        assert results[0].id == "B19001_001E"


class TestSearchByDataset:
    def test_finds_dataset_by_year(self, search_catalog):
        results = search_catalog.search("2022", level=SearchLevel.DATASET)
        assert any(r.id == "acs5_2022" for r in results)

    def test_finds_dataset_by_type(self, search_catalog):
        results = search_catalog.search("acs_5yr", level=SearchLevel.DATASET)
        assert any(r.id == "acs5_2022" for r in results)


class TestSearchCrossLevel:
    def test_all_levels_searched_by_default(self, search_catalog):
        results = search_catalog.search("income")
        levels = {r.level for r in results}
        assert SearchLevel.TABLE in levels
        assert SearchLevel.SUBJECT in levels

    def test_results_ranked_by_score(self, search_catalog):
        results = search_catalog.search("household income")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_max_results_limits_output(self, search_catalog):
        results = search_catalog.search("income", max_results=2)
        assert len(results) <= 2

    def test_dataset_filter_narrows_tables(self, search_catalog):
        all_results = search_catalog.search("income", level=SearchLevel.TABLE)
        filtered = search_catalog.search("income", level=SearchLevel.TABLE, dataset="acs5_2022")
        # Dataset only has B19001 and B19013 for income, not B19001A/B
        filtered_ids = {r.id for r in filtered}
        assert "B19001A" not in filtered_ids
        assert "B19001" in filtered_ids


class TestSearchResult:
    def test_search_result_fields(self, search_catalog):
        results = search_catalog.search("B19001", level=SearchLevel.TABLE)
        r = results[0]
        assert r.level == SearchLevel.TABLE
        assert r.id == "B19001"
        assert r.score > 0
        assert isinstance(r.obj, CensusTable)
