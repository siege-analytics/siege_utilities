"""Tests for siege_utilities.geo.census.catalog — Census table catalog data model."""

import pytest

from siege_utilities.geo.census.catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusSubject,
    CensusTable,
    CensusVariable,
    FamilyType,
    detect_race_iteration_families,
    detect_topical_families,
    parse_table_id,
)


# ── Fixtures ──


def _make_table(table_id, concept="", universe="", geo=None):
    return CensusTable(
        table_id=table_id,
        label=f"Label for {table_id}",
        concept=concept,
        universe=universe,
        geography_levels=geo or [],
    )


@pytest.fixture()
def income_tables():
    return [
        _make_table("B19001", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS"),
        _make_table("B19001A", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS (WHITE ALONE HOUSEHOLDER)"),
        _make_table("B19001B", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS (BLACK ALONE HOUSEHOLDER)"),
        _make_table("B19001C", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS (AIAN ALONE HOUSEHOLDER)"),
        _make_table("B19013", concept="MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS"),
        _make_table("B19025", concept="AGGREGATE HOUSEHOLD INCOME IN THE PAST 12 MONTHS"),
        _make_table("B19301", concept="PER CAPITA INCOME IN THE PAST 12 MONTHS"),
    ]


@pytest.fixture()
def mixed_tables():
    return [
        _make_table("B01001", concept="SEX BY AGE", geo=["state", "county", "tract"]),
        _make_table("B01002", concept="MEDIAN AGE BY SEX", geo=["state", "county", "tract"]),
        _make_table("B01003", concept="TOTAL POPULATION", geo=["state", "county", "tract", "block_group"]),
        _make_table("B02001", concept="RACE", geo=["state", "county", "tract"]),
        _make_table("B19001", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS", geo=["state", "county", "tract"]),
        _make_table("B19001A", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS (WHITE ALONE)", geo=["state", "county"]),
        _make_table("B19001B", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS (BLACK ALONE)", geo=["state", "county"]),
        _make_table("B19013", concept="MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS", geo=["state", "county", "tract"]),
    ]


# ── parse_table_id ──


class TestParseTableId:
    def test_standard_table(self):
        result = parse_table_id("B19001")
        assert result == {"prefix": "B", "number": "19001", "suffix": None}

    def test_race_suffix(self):
        result = parse_table_id("B19001A")
        assert result == {"prefix": "B", "number": "19001", "suffix": "A"}

    def test_c_prefix(self):
        result = parse_table_id("C17001")
        assert result == {"prefix": "C", "number": "17001", "suffix": None}

    def test_multi_char_prefix(self):
        result = parse_table_id("CP05001")
        assert result == {"prefix": "CP", "number": "05001", "suffix": None}
        result = parse_table_id("CP00005")
        assert result == {"prefix": "CP", "number": "00005", "suffix": None}

    def test_invalid_id(self):
        assert parse_table_id("not_a_table") is None
        assert parse_table_id("") is None
        assert parse_table_id("B1900") is None  # too few digits


# ── CensusVariable ──


class TestCensusVariable:
    def test_parse_estimate_code(self):
        result = CensusVariable.parse_code("B19001_001E")
        assert result == {"table_id": "B19001", "seq": "001", "stat_type": "E"}

    def test_parse_moe_code(self):
        result = CensusVariable.parse_code("B19001_001M")
        assert result == {"table_id": "B19001", "seq": "001", "stat_type": "M"}

    def test_parse_suffixed_table(self):
        result = CensusVariable.parse_code("B19001A_001E")
        assert result == {"table_id": "B19001A", "seq": "001", "stat_type": "E"}

    def test_parse_invalid_code(self):
        assert CensusVariable.parse_code("invalid") is None


# ── CensusTable properties ──


class TestCensusTable:
    def test_root_table_id_base(self):
        table = _make_table("B19001")
        assert table.root_table_id == "B19001"

    def test_root_table_id_suffixed(self):
        table = _make_table("B19001A")
        assert table.root_table_id == "B19001"

    def test_race_suffix_present(self):
        table = _make_table("B19001A")
        assert table.race_suffix == "A"

    def test_race_suffix_absent(self):
        table = _make_table("B19001")
        assert table.race_suffix is None


# ── Race iteration family detection ──


class TestRaceIterationFamilies:
    def test_detects_income_race_family(self, income_tables):
        families = detect_race_iteration_families(income_tables)
        assert len(families) == 1
        fam = families[0]
        assert fam.family_type == FamilyType.RACE_ITERATION
        assert fam.root_table_id == "B19001"
        assert "B19001" in fam.table_ids
        assert "B19001A" in fam.table_ids
        assert "B19001B" in fam.table_ids
        assert "B19001C" in fam.table_ids
        # Non-suffixed related tables should NOT be in the race family
        assert "B19013" not in fam.table_ids

    def test_no_suffixed_tables(self):
        tables = [_make_table("B01001"), _make_table("B02001")]
        families = detect_race_iteration_families(tables)
        assert families == []

    def test_base_table_included_when_present(self, income_tables):
        families = detect_race_iteration_families(income_tables)
        fam = families[0]
        assert fam.tables[0].table_id == "B19001"

    def test_family_id_format(self, income_tables):
        families = detect_race_iteration_families(income_tables)
        assert families[0].family_id == "race:B19001"


# ── Topical kinship family detection ──


class TestTopicalFamilies:
    def test_detects_income_topical_family(self, income_tables):
        families = detect_topical_families(income_tables)
        assert len(families) >= 1
        income_fam = next(
            (f for f in families if "B19001" in f.root_table_id), None
        )
        assert income_fam is not None
        assert income_fam.family_type == FamilyType.TOPICAL_KINSHIP

    def test_requires_shared_concept(self):
        tables = [
            _make_table("B19001", concept="HOUSEHOLD INCOME"),
            _make_table("B19050", concept="COMPLETELY UNRELATED"),
        ]
        families = detect_topical_families(tables)
        assert families == []

    def test_excludes_suffixed_tables(self, income_tables):
        families = detect_topical_families(income_tables)
        for fam in families:
            for table in fam.tables:
                parsed = parse_table_id(table.table_id)
                assert parsed["suffix"] is None

    def test_singleton_not_a_family(self):
        tables = [_make_table("B99001", concept="UNIQUE")]
        families = detect_topical_families(tables)
        assert families == []


# ── CensusCatalog ──


class TestCensusCatalog:
    def test_add_and_get_table(self):
        cat = CensusCatalog()
        table = _make_table("B19001")
        cat.add_table(table)
        assert cat.get_table("B19001") is table
        assert cat.get_table("NONEXISTENT") is None

    def test_add_tables_bulk(self):
        cat = CensusCatalog()
        tables = [_make_table("B01001"), _make_table("B02001")]
        cat.add_tables(tables)
        assert len(cat) == 2

    def test_tables_for_geography(self, mixed_tables):
        cat = CensusCatalog()
        cat.add_tables(mixed_tables)
        tract_tables = cat.tables_for_geography("tract")
        tract_ids = [t.table_id for t in tract_tables]
        assert "B01001" in tract_ids
        assert "B19013" in tract_ids
        # Suffixed tables with only state/county geo should not appear
        assert "B19001A" not in tract_ids

    def test_geography_for_table(self, mixed_tables):
        cat = CensusCatalog()
        cat.add_tables(mixed_tables)
        geo = cat.geography_for_table("B01003")
        assert "block_group" in geo
        assert cat.geography_for_table("NONEXISTENT") == []

    def test_build_families(self, mixed_tables):
        cat = CensusCatalog()
        cat.add_tables(mixed_tables)
        cat.build_families()
        assert len(cat.families) > 0
        race_families = [
            f for f in cat.families.values()
            if f.family_type == FamilyType.RACE_ITERATION
        ]
        assert len(race_families) == 1
        assert race_families[0].root_table_id == "B19001"

    def test_families_for_table(self, mixed_tables):
        cat = CensusCatalog()
        cat.add_tables(mixed_tables)
        cat.build_families()
        families = cat.families_for_table("B19001A")
        assert any(f.family_type == FamilyType.RACE_ITERATION for f in families)

    def test_add_subject(self):
        cat = CensusCatalog()
        subject = CensusSubject(
            subject_id="income",
            label="Income and Poverty",
        )
        cat.add_subject(subject)
        assert cat.get_subject("income") is subject

    def test_add_dataset(self):
        cat = CensusCatalog()
        dataset = CensusCatalogDataset(
            dataset_id="acs5_2022",
            survey_type="acs_5yr",
            year=2022,
        )
        cat.add_dataset(dataset)
        assert cat.get_dataset("acs5_2022") is dataset

    def test_repr(self, mixed_tables):
        cat = CensusCatalog()
        cat.add_tables(mixed_tables)
        cat.build_families()
        r = repr(cat)
        assert "CensusCatalog(" in r
        assert "tables=" in r
        assert "families=" in r


# ── CensusSubject ──


class TestCensusSubject:
    def test_all_tables_includes_family_and_loose(self):
        t1 = _make_table("B19001")
        t2 = _make_table("B19013")
        t3 = _make_table("B20001")  # loose table
        fam = CensusFamily(
            family_id="topic:B19001",
            family_type=FamilyType.TOPICAL_KINSHIP,
            root_table_id="B19001",
            tables=[t1, t2],
        )
        subject = CensusSubject(
            subject_id="income",
            label="Income",
            families=[fam],
            tables=[t3],
        )
        all_t = subject.all_tables
        assert len(all_t) == 3
        ids = [t.table_id for t in all_t]
        assert "B19001" in ids
        assert "B19013" in ids
        assert "B20001" in ids


# ── CensusFamily ──


class TestCensusFamily:
    def test_table_ids_property(self):
        t1 = _make_table("B19001")
        t2 = _make_table("B19001A")
        fam = CensusFamily(
            family_id="race:B19001",
            family_type=FamilyType.RACE_ITERATION,
            root_table_id="B19001",
            tables=[t1, t2],
        )
        assert fam.table_ids == ["B19001", "B19001A"]


# ── Error path tests ──


class TestParseTableIdInvalid:
    """parse_table_id with various invalid inputs."""

    def test_empty_string_returns_invalid(self):
        assert parse_table_id("") is None

    def test_too_short_returns_invalid(self):
        assert parse_table_id("B19") is None

    def test_no_digits_returns_invalid(self):
        assert parse_table_id("BABCDE") is None

    def test_lowercase_returns_invalid(self):
        assert parse_table_id("b19001") is None

    def test_digits_only_returns_invalid(self):
        assert parse_table_id("19001") is None

    def test_extra_trailing_chars_returns_invalid(self):
        assert parse_table_id("B19001AB") is None

    def test_special_chars_returns_invalid(self):
        assert parse_table_id("B19-01") is None


class TestCensusVariableParseCodeInvalid:
    """CensusVariable.parse_code with invalid variable codes."""

    def test_empty_string_returns_invalid(self):
        assert CensusVariable.parse_code("") is None

    def test_no_underscore_returns_invalid(self):
        assert CensusVariable.parse_code("B19001001E") is None

    def test_missing_sequence_returns_invalid(self):
        assert CensusVariable.parse_code("B19001_E") is None

    def test_bad_stat_type_returns_invalid(self):
        assert CensusVariable.parse_code("B19001_001X") is None

    def test_lowercase_returns_invalid(self):
        assert CensusVariable.parse_code("b19001_001e") is None


class TestSearchEmpty:
    """search() with queries that yield no results."""

    def test_empty_query_returns_empty(self):
        cat = CensusCatalog()
        cat.add_table(_make_table("B19001", concept="HOUSEHOLD INCOME"))
        results = cat.search("")
        assert results == []

    def test_stopwords_only_query_returns_empty(self):
        cat = CensusCatalog()
        cat.add_table(_make_table("B19001", concept="HOUSEHOLD INCOME"))
        results = cat.search("IN THE OF FOR")
        assert results == []

    def test_no_match_query_returns_empty(self):
        cat = CensusCatalog()
        cat.add_table(_make_table("B19001", concept="HOUSEHOLD INCOME"))
        results = cat.search("XYLOPHONE QUANTUM ZEBRA")
        assert results == []

    def test_search_empty_catalog_returns_empty(self):
        cat = CensusCatalog()
        results = cat.search("INCOME")
        assert results == []


class TestRaceIterationFamiliesEmpty:
    """detect_race_iteration_families with tables having no suffix."""

    def test_no_suffix_tables_returns_empty(self):
        tables = [
            _make_table("B01001", concept="SEX BY AGE"),
            _make_table("B02001", concept="RACE"),
            _make_table("B19001", concept="HOUSEHOLD INCOME"),
        ]
        families = detect_race_iteration_families(tables)
        assert families == []

    def test_empty_list_returns_empty(self):
        families = detect_race_iteration_families([])
        assert families == []

    def test_invalid_table_ids_skipped(self):
        tables = [
            CensusTable(table_id="bad", label="Bad", concept="Bad"),
            CensusTable(table_id="also_bad", label="Also bad", concept="Bad"),
        ]
        families = detect_race_iteration_families(tables)
        assert families == []


class TestTopicalFamiliesEdgeCases:
    """detect_topical_families edge cases."""

    def test_single_table_returns_empty(self):
        tables = [_make_table("B19001", concept="HOUSEHOLD INCOME")]
        families = detect_topical_families(tables)
        assert families == []

    def test_empty_list_returns_empty(self):
        families = detect_topical_families([])
        assert families == []

    def test_only_suffixed_tables_returns_empty(self):
        tables = [
            _make_table("B19001A", concept="HOUSEHOLD INCOME (WHITE)"),
            _make_table("B19001B", concept="HOUSEHOLD INCOME (BLACK)"),
        ]
        families = detect_topical_families(tables)
        assert families == []

    def test_unrelated_concepts_returns_empty(self):
        tables = [
            _make_table("B19001", concept="HOUSEHOLD INCOME"),
            _make_table("B19050", concept="COMPLETELY UNRELATED TOPIC"),
        ]
        families = detect_topical_families(tables)
        assert families == []


class TestCensusCatalogAddTableDuplicate:
    """CensusCatalog.add_table with a duplicate table ID overwrites."""

    def test_duplicate_table_id_overwrites(self):
        cat = CensusCatalog()
        table1 = _make_table("B19001", concept="ORIGINAL CONCEPT")
        table2 = _make_table("B19001", concept="UPDATED CONCEPT")
        cat.add_table(table1)
        cat.add_table(table2)
        assert len(cat) == 1
        assert cat.get_table("B19001").concept == "UPDATED CONCEPT"


class TestCensusTableInvalidId:
    """CensusTable properties with invalid table_id."""

    def test_root_table_id_invalid_returns_none(self):
        table = CensusTable(table_id="bad", label="Bad", concept="Bad")
        assert table.root_table_id is None

    def test_race_suffix_invalid_returns_none(self):
        table = CensusTable(table_id="bad", label="Bad", concept="Bad")
        assert table.race_suffix is None

    def test_parsed_id_invalid_returns_none(self):
        table = CensusTable(table_id="bad", label="Bad", concept="Bad")
        assert table.parsed_id is None
