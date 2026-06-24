"""Tests for siege_utilities.geo.census.catalog_docs."""


from siege_utilities.geo.census.catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusSubject,
    CensusTable,
    CensusVariable,
    FamilyType,
)
from siege_utilities.geo.census.catalog_docs import (
    generate_catalog_docs,
    generate_catalog_markdown,
)


def _make_catalog():
    cat = CensusCatalog()

    v1 = CensusVariable(code="B19001_001E", label="Estimate!!Total:", concept="HOUSEHOLD INCOME", table_id="B19001")
    v2 = CensusVariable(code="B19001_002E", label="Estimate!!Total:!!Less than $10,000", concept="HOUSEHOLD INCOME", table_id="B19001")

    t_income = CensusTable(table_id="B19001", label="HOUSEHOLD INCOME", concept="HOUSEHOLD INCOME IN THE PAST 12 MONTHS", variables=[v1, v2], geography_levels=["state", "county", "tract"])
    t_income_white = CensusTable(table_id="B19001A", label="HOUSEHOLD INCOME (WHITE)", concept="HOUSEHOLD INCOME (WHITE ALONE)", geography_levels=["state", "county"])
    t_age = CensusTable(table_id="B01001", label="SEX BY AGE", concept="SEX BY AGE", geography_levels=["state", "county", "tract"])
    t_orphan = CensusTable(table_id="B99001", label="OTHER", concept="SOME OTHER TABLE")

    cat.add_tables([t_income, t_income_white, t_age, t_orphan])

    fam = CensusFamily(
        family_id="race:B19001",
        family_type=FamilyType.RACE_ITERATION,
        root_table_id="B19001",
        tables=[t_income, t_income_white],
        description="Race iterations of B19001",
    )
    cat.add_family(fam)

    sub = CensusSubject(subject_id="income", label="Income", tables=[t_income])
    cat.add_subject(sub)

    ds = CensusCatalogDataset(
        dataset_id="acs5_2022", survey_type="acs_5yr", year=2022,
        subjects=[sub], tables={"B19001": t_income, "B01001": t_age},
    )
    cat.add_dataset(ds)

    return cat


class TestGenerateMarkdown:
    def test_includes_title(self):
        cat = _make_catalog()
        md = generate_catalog_markdown(cat, title="Test Catalog")
        assert "# Test Catalog" in md

    def test_includes_subject(self):
        cat = _make_catalog()
        md = generate_catalog_markdown(cat)
        assert "### Income" in md

    def test_includes_race_family(self):
        cat = _make_catalog()
        md = generate_catalog_markdown(cat)
        assert "Race Iteration Families" in md
        assert "B19001" in md
        assert "B19001A" in md

    def test_includes_dataset(self):
        cat = _make_catalog()
        md = generate_catalog_markdown(cat)
        assert "acs5_2022" in md

    def test_includes_orphan_tables(self):
        cat = _make_catalog()
        md = generate_catalog_markdown(cat)
        assert "B99001" in md
        assert "Other Tables" in md

    def test_table_links(self):
        cat = _make_catalog()
        md = generate_catalog_markdown(cat)
        assert "tables/B19001.md" in md


class TestGenerateDocs:
    def test_creates_index(self, tmp_path):
        cat = _make_catalog()
        written = generate_catalog_docs(cat, tmp_path)
        assert (tmp_path / "index.md").exists()
        assert tmp_path / "index.md" in written

    def test_creates_table_pages(self, tmp_path):
        cat = _make_catalog()
        written = generate_catalog_docs(cat, tmp_path)
        assert (tmp_path / "tables" / "B19001.md").exists()
        assert (tmp_path / "tables" / "B01001.md").exists()
        assert (tmp_path / "tables" / "B19001.md") in written

    def test_table_page_has_variables(self, tmp_path):
        cat = _make_catalog()
        generate_catalog_docs(cat, tmp_path)
        content = (tmp_path / "tables" / "B19001.md").read_text()
        assert "B19001_001E" in content
        assert "B19001_002E" in content

    def test_table_page_has_geography(self, tmp_path):
        cat = _make_catalog()
        generate_catalog_docs(cat, tmp_path)
        content = (tmp_path / "tables" / "B19001.md").read_text()
        assert "tract" in content

    def test_table_page_has_family_membership(self, tmp_path):
        cat = _make_catalog()
        generate_catalog_docs(cat, tmp_path)
        content = (tmp_path / "tables" / "B19001.md").read_text()
        assert "race:B19001" in content

    def test_table_page_has_dataset(self, tmp_path):
        cat = _make_catalog()
        generate_catalog_docs(cat, tmp_path)
        content = (tmp_path / "tables" / "B19001.md").read_text()
        assert "acs5_2022" in content

    def test_table_page_has_back_link(self, tmp_path):
        cat = _make_catalog()
        generate_catalog_docs(cat, tmp_path)
        content = (tmp_path / "tables" / "B19001.md").read_text()
        assert "index.md" in content

    def test_returns_all_written_paths(self, tmp_path):
        cat = _make_catalog()
        written = generate_catalog_docs(cat, tmp_path)
        # 1 index + 4 table pages
        assert len(written) == 5

    def test_empty_catalog(self, tmp_path):
        cat = CensusCatalog()
        written = generate_catalog_docs(cat, tmp_path)
        assert len(written) == 1  # just the index
        content = (tmp_path / "index.md").read_text()
        assert "Census Table Catalog" in content
