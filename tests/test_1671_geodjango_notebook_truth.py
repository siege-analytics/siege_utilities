"""Documentation contract for the schematic GeoDjango workflow (#1671)."""

import ast
import importlib.util
import json
import re
from pathlib import Path

import nbformat
import pytest


REPO = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO / "notebooks/spatial/06_geodjango.ipynb"


@pytest.fixture(scope="module")
def notebook() -> nbformat.NotebookNode:
    document = nbformat.read(NOTEBOOK_PATH, as_version=4)
    nbformat.validate(document)
    return document


def test_unresolved_loader_is_not_advertised_as_a_runnable_recipe(
    notebook: nbformat.NotebookNode,
) -> None:
    markdown = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    loader_import = "from spatial_05_unified import build_unified_dataframe"
    assert loader_import in markdown, (
        "Reassess the loader contract if the import changes"
    )
    if importlib.util.find_spec("spatial_05_unified") is None:
        assert not re.search(
            r"\bcomplete\b|\bcopy[\s-]*paste(?:able)?\b",
            markdown,
            re.IGNORECASE,
        ), (
            "An unresolved loader import cannot be advertised as a "
            "complete/copy-pasteable recipe"
        )

    command_cell = next(
        cell.source for cell in notebook.cells if loader_import in cell.source
    ).lower()
    assert "schematic" in command_cell.splitlines()[0]
    assert "`spatial_05_unified`" in command_cell
    assert "spatial/05_multi_source_joins.ipynb" in command_cell
    assert "not an importable module" in command_cell
    assert "build or import a real loader" in command_cell
    assert "replace the placeholder import" in command_cell


def test_markdown_only_validation_is_not_workflow_execution(
    notebook: nbformat.NotebookNode,
) -> None:
    assert all(cell.cell_type == "markdown" for cell in notebook.cells)
    markdown = "\n".join(cell.source for cell in notebook.cells).lower()
    assert "no code cells" in markdown
    assert "does not exercise the loader, orm, or postgis" in markdown
    assert "tests/test_1671_geodjango_notebook_truth.py" in markdown


def test_notebooks_doc_drops_copy_paste_promise_for_schematics():
    doc = (REPO / "docs/NOTEBOOKS.md").read_text(encoding="utf-8")
    assert "copy-pasteable" not in doc.lower()
    assert "Full call-shape recipe" not in doc

def test_execution_groups_do_not_list_markdown_only_notebooks():
    tree = ast.parse((REPO / "tests/test_notebooks.py").read_text(encoding="utf-8"))
    groups = next(ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "NOTEBOOK_GROUPS")
    empty = [rel for rels in groups.values() for rel in rels
             if not any(c["cell_type"] == "code" for c in
                        json.loads((REPO / "notebooks" / rel).read_text(encoding="utf-8"))["cells"])]
    assert not empty, f"execution groups list markdown-only notebooks: {empty}"
