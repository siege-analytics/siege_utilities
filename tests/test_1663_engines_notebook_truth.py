"""Keep the engines tutorial's parity claim aligned with its query cells (#1663)."""

from pathlib import Path
import re

import nbformat
import pytest


NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "notebooks/engines/01_multi_engine_dataframes.ipynb"
)


@pytest.fixture(scope="module")
def notebook() -> nbformat.NotebookNode:
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(nb)
    return nb


def test_teaching_claims_result_parity_with_different_queries(notebook: nbformat.NotebookNode) -> None:
    opening = " ".join(notebook.cells[0].source.lower().split())
    teaching = " ".join(
        " ".join(cell.source.lower().split())
        for cell in notebook.cells
        if cell.cell_type == "markdown"
    )
    for claim in (
        "swap the engine constructor",
        "the rest of the code is unchanged",
        "without rewriting the analysis layer",
        "identical query code",
        "same query code",
        "same ranking query",
    ):
        assert claim not in teaching, f"Unsupported query-code parity claim: {claim}"

    assert "result parity" in opening
    assert "different query implementations" in opening


def test_separate_engine_queries_keep_the_result_comparison(notebook: nbformat.NotebookNode) -> None:
    code = {cell.id: cell.source for cell in notebook.cells if cell.cell_type == "code"}
    pandas_query = code["c2"]
    duckdb_query = code["c3"]
    comparison = code["c4"]

    assert "get_engine(Engine.PANDAS)" in pandas_query
    for operation in (".groupby_agg(", ".rename(", ".sort_values("):
        assert operation in pandas_query
    assert "get_engine(Engine.DUCKDB)" in duckdb_query
    for operation in ("duckdb_engine.query(", "FROM read_parquet(", "GROUP BY", "ORDER BY"):
        assert operation in duckdb_query

    assert "pd.testing.assert_frame_equal(" in comparison
    assert "pandas_result[['committee_id', 'total_receipts']]" in comparison
    assert "duckdb_result[['committee_id', 'total_receipts']]" in comparison


def test_synthetic_data_description_matches_generator(notebook):
    cells = {c.id: c.source for c in notebook.cells}
    counties = re.search(r"'county_fips':.*?rng\.choice\(\[([^\]]*)\]", cells["c1"]).group(1).split(",")
    assert f"{len(counties)} TX counties" in cells["s1"], cells["s1"]
