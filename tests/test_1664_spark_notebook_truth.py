"""Keep the Spark notebook's schematic SQL and executable scope honest."""

import ast
import re
from pathlib import Path

import nbformat
import pytest

from tests.test_notebooks import _run_and_get_outputs

NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "notebooks/engines/02_distributed_spark.ipynb"
)


@pytest.fixture
def notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def test_notebooks_doc_drops_copy_paste_promise_for_engines_02():
    doc = (Path(__file__).resolve().parents[1] / "docs/NOTEBOOKS.md").read_text(encoding="utf-8")
    assert "copy-pasteable" not in doc


def test_notebooks_doc_marks_spatial_06_markdown_only():
    # spatial/06 has zero code cells, so NOTEBOOKS.md must not claim it runs an
    # import smoke cell (unlike engines/02, which does). Keep the doc truthful so
    # it also agrees with #1786's markdown-only description.
    doc = (Path(__file__).resolve().parents[1] / "docs/NOTEBOOKS.md").read_text(encoding="utf-8")
    spatial06 = [line for line in doc.splitlines() if "spatial/06" in line]
    assert spatial06, "NOTEBOOKS.md should mention spatial/06"
    assert all("import smoke cell executes" not in line for line in spatial06), (
        "NOTEBOOKS.md claims spatial/06 executes an import smoke cell, but it has "
        "zero code cells"
    )
    assert any(
        "markdown-only" in line.lower() or "no code cells" in line.lower()
        for line in spatial06
    ), "NOTEBOOKS.md should describe spatial/06 as markdown-only with no code cells"


def test_sedona_sql_is_labeled_schematic(
    notebook: nbformat.NotebookNode,
) -> None:
    markdown = {
        cell.id: cell.source
        for cell in notebook.cells
        if cell.cell_type == "markdown"
    }
    assert (
        "schematic" in markdown["s3"].lower()
    ), "Label the Sedona SQL schematic beside the example"
    assert (
        "schematic" in markdown["s4"].lower()
    ), "Section 4 must explain the schematic scope"
    assert "FROM donors d, precincts p" in markdown["s3"]
    assert "ST_Contains(p.geom, ST_Point(d.lon, d.lat))" in markdown["s3"]
    prose = "\n".join(markdown.values()).lower()
    assert not re.search(r"execut\w*\s+as[- ]is|this just works", prose)
    assert "import smoke test" in markdown["s4"].lower()
    assert "does not run spark or sedona computation" in markdown["s4"].lower()


@pytest.mark.parametrize(
    ("view", "columns"),
    [
        ("donors", ("donor_id", "amount", "lon", "lat")),
        ("precincts", ("precinct_id", "geom")),
    ],
)
def test_sedona_view_setup_is_documented(
    notebook: nbformat.NotebookNode, view: str, columns: tuple[str, ...]
) -> None:
    source = next(cell.source for cell in notebook.cells if cell.id == "s3")
    schema_row = next(
        (
            line
            for line in source.splitlines()
            if line.startswith(f"| `{view}` |")
        ),
        "",
    )
    assert schema_row, f"Document the required {view} view schema"
    for column in columns:
        assert f"`{column}`" in schema_row
    assert f'{view}_df.createOrReplaceTempView("{view}")' in source


def test_sedona_prerequisites_are_documented(
    notebook: nbformat.NotebookNode,
) -> None:
    source = next(cell.source for cell in notebook.cells if cell.id == "s3")
    for requirement in (
        "SparkSession",
        "JVM",
        "apache-sedona",
        "JAR",
        "classpath",
        "SedonaContext.create",
        "same session",
        "same CRS",
        "longitude",
        "latitude",
        "ST_GeomFromWKT",
    ):
        assert (
            requirement in source
        ), f"Document the Sedona prerequisite: {requirement}"
    assert "does not load data or create these views" in source


def test_notebook_is_valid(notebook: nbformat.NotebookNode) -> None:
    nbformat.validate(notebook)


def test_executable_cells_remain_an_import_smoke_test(
    notebook: nbformat.NotebookNode,
) -> None:
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code_cells
    for cell in code_cells:
        calls = [
            node
            for node in ast.walk(ast.parse(cell.source))
            if isinstance(node, ast.Call)
        ]
        assert all(
            isinstance(call.func, ast.Name) and call.func.id == "print"
            for call in calls
        ), (
            "The schematic notebook may print import results "
            "but must not start Spark or execute SQL"
        )


def test_spark_notebook_smoke_runs_without_a_cluster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep this unmarked so CI runs the changed Spark notebook even though
    # the main lane excludes tests/test_notebooks.py and integration tests.
    monkeypatch.setenv(
        "NOTEBOOK_ARTIFACT_DIR", str(tmp_path / "notebook-artifacts")
    )
    output = "\n".join(_run_and_get_outputs(NOTEBOOK, timeout=60))
    assert re.search(r"SparkEngine available\s*:\s*SparkEngine", output)
    assert "'spark'" in output
