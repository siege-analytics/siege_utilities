"""Keep the CRM pipeline notebook's deduplication claims true (#1416)."""

from pathlib import Path

import nbformat


NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "analytics" / "04_crm_pipeline.ipynb"


def _run_dedup_cells() -> dict:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    cells = {cell.id: cell for cell in notebook.cells}
    namespace = {"display": lambda *args, **kwargs: None}
    for cell_id in ("e80eb60a", "5321b34a"):
        exec(compile(cells[cell_id].source, f"{NOTEBOOK.name}:{cell_id}", "exec"), namespace)
    return namespace


def test_notebook_merges_only_identifier_corroborated_contacts() -> None:
    namespace = _run_dedup_cells()

    assert sorted(namespace["merged"]["normalized_name"].unique()) == ["ada lovelace"]
    assert sorted(namespace["candidates"]["normalized_name"].unique()) == ["grace hopper"]
    grace = namespace["merge_table"].query("normalized_name == 'grace hopper'")
    assert grace["canonical_id"].nunique() == 2
    assert grace["name_candidate_id"].nunique() == 1
    # No email conflict between them, so both are review candidates.
    assert grace["match_confidence"].eq(0.75).all()
    ada = namespace["merge_table"].query("normalized_name == 'ada lovelace'")
    assert ada["match_confidence"].eq(1.0).all()


def test_notebook_markdown_describes_review_gated_name_matches() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    section = next(cell.source for cell in notebook.cells if cell.id == "04541929")

    assert "never merged" in section
    assert "name_candidate_id" in section
    assert "from normalized names." not in section
