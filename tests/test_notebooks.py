"""Headless notebook execution tests using papermill.

Notebooks are grouped by dependency so that tests skip gracefully
when external services (PostGIS, Spark, analytics credentials) are
not available.

Usage:
    # Pure Python notebooks only (always runnable)
    pytest tests/test_notebooks.py -k pure_python -v

    # Geo notebooks (requires GDAL)
    pytest tests/test_notebooks.py -k geo -v

    # All non-integration notebooks
    pytest tests/test_notebooks.py -v

    # Include analytics/credential notebooks
    pytest tests/test_notebooks.py -v -m ""
"""

import os
import tempfile
from pathlib import Path

import pytest

NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"

# ---------------------------------------------------------------------------
# Notebook dependency groups
# ---------------------------------------------------------------------------

PURE_PYTHON = [1, 2, 3, 6, 8, 11, 12, 17, 21, 22, 23, 24, 27]
GEO_NOTEBOOKS = [4, 5, 7, 25, 26]
DJANGO_NOTEBOOKS = [13, 15]
# Integration group: requires external services (credentials, Spark, network downloads)
ANALYTICS_NOTEBOOKS = [9, 14, 18]
SPARK_NOTEBOOKS = [16]
CREDENTIAL_NOTEBOOKS = [10]
EXTERNAL_DOWNLOAD_NOTEBOOKS = [19, 20]  # require NCES/external downloads


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notebook_path(nb_num: int) -> Path:
    """Resolve notebook number to file path."""
    for p in sorted(NOTEBOOKS_DIR.glob(f"{nb_num:02d}_*.ipynb")):
        return p
    pytest.skip(f"Notebook {nb_num:02d} not found")


def _run_notebook(nb_path: Path, timeout: int = 300):
    """Execute a notebook headlessly via papermill."""
    papermill = pytest.importorskip("papermill")
    with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False) as f:
        out_path = f.name
    try:
        papermill.execute_notebook(
            str(nb_path),
            out_path,
            kernel_name="python3",
            cwd=str(NOTEBOOKS_DIR),
            request_save_on_cell_execute=True,
        )
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def _run_and_get_outputs(nb_path: Path, timeout: int = 300) -> list:
    """Execute notebook and return cell outputs for validation."""
    papermill = pytest.importorskip("papermill")
    nbformat = pytest.importorskip("nbformat")
    with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False) as f:
        out_path = f.name
    try:
        papermill.execute_notebook(
            str(nb_path),
            out_path,
            kernel_name="python3",
            cwd=str(NOTEBOOKS_DIR),
            request_save_on_cell_execute=True,
        )
        nb = nbformat.read(out_path, as_version=4)
        outputs = []
        for cell in nb.cells:
            if cell.cell_type == "code" and cell.outputs:
                text = ""
                for out in cell.outputs:
                    if "text" in out:
                        text += out["text"]
                    elif "data" in out and "text/plain" in out["data"]:
                        text += out["data"]["text/plain"]
                outputs.append(text)
            elif cell.cell_type == "code":
                outputs.append("")
        return outputs
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


# ---------------------------------------------------------------------------
# Pure Python notebooks — always runnable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nb_num", PURE_PYTHON, ids=[f"NB{n:02d}" for n in PURE_PYTHON])
def test_pure_python_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# Geo notebooks — require GDAL
# ---------------------------------------------------------------------------

@pytest.mark.requires_gdal
@pytest.mark.parametrize("nb_num", GEO_NOTEBOOKS, ids=[f"NB{n:02d}" for n in GEO_NOTEBOOKS])
def test_geo_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# Django/PostGIS notebooks
# ---------------------------------------------------------------------------

@pytest.mark.requires_gdal
@pytest.mark.django_db
@pytest.mark.parametrize("nb_num", DJANGO_NOTEBOOKS, ids=[f"NB{n:02d}" for n in DJANGO_NOTEBOOKS])
def test_django_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# Analytics notebooks — require credentials (skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize(
    "nb_num", ANALYTICS_NOTEBOOKS,
    ids=[f"NB{n:02d}" for n in ANALYTICS_NOTEBOOKS],
)
def test_analytics_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# Spark notebooks
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_spark
@pytest.mark.parametrize("nb_num", SPARK_NOTEBOOKS, ids=[f"NB{n:02d}" for n in SPARK_NOTEBOOKS])
def test_spark_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# Credential notebooks (1Password, branding) — skipped by default
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize(
    "nb_num", CREDENTIAL_NOTEBOOKS,
    ids=[f"NB{n:02d}" for n in CREDENTIAL_NOTEBOOKS],
)
def test_credential_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# External download notebooks (require network access to NCES, etc.)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_gdal
@pytest.mark.parametrize(
    "nb_num", EXTERNAL_DOWNLOAD_NOTEBOOKS,
    ids=[f"NB{n:02d}" for n in EXTERNAL_DOWNLOAD_NOTEBOOKS],
)
def test_external_download_notebook(nb_num):
    _run_notebook(_notebook_path(nb_num))


# ---------------------------------------------------------------------------
# Output validation — verify notebooks produce correct results
# ---------------------------------------------------------------------------

class TestNotebookOutputValidation:
    """Verify that critical notebooks produce correct outputs, not just
    'doesn't crash'."""

    def test_nb08_sample_data_produces_dataframe(self):
        """NB08 generates synthetic data — verify it has expected columns."""
        outputs = _run_and_get_outputs(_notebook_path(8))
        all_text = "\n".join(outputs)
        # NB08 generates population data with specific columns
        assert "age" in all_text.lower() or "population" in all_text.lower(), \
            "NB08 should produce population/age data"

    def test_nb22_temporal_models_validate(self):
        """NB22 exercises validation — verify it catches invalid data."""
        outputs = _run_and_get_outputs(_notebook_path(22))
        all_text = "\n".join(outputs)
        assert "validation error" in all_text.lower() or "caught" in all_text.lower(), \
            "NB22 should demonstrate validation catching bad data"
        assert "119" in all_text, "NB22 should reference the 119th Congress"

    def test_nb23_redistricting_has_compactness(self):
        """NB23 shows compactness scores — verify they appear."""
        outputs = _run_and_get_outputs(_notebook_path(23))
        all_text = "\n".join(outputs)
        assert "polsby" in all_text.lower() or "reock" in all_text.lower(), \
            "NB23 should show compactness scores"

    def test_nb24_duckdb_produces_results(self):
        """NB24 runs DuckDB queries — verify results are non-empty."""
        try:
            import duckdb  # noqa: F401
        except ImportError:
            pytest.skip("DuckDB not installed")
        outputs = _run_and_get_outputs(_notebook_path(24))
        all_text = "\n".join(outputs)
        assert "engine" in all_text.lower(), "NB24 should reference engine names"
        # Should show actual aggregation results (numbers)
        assert any(c.isdigit() for c in all_text), "NB24 should produce numeric results"

    def test_nb27_moe_propagation(self):
        """NB27 demonstrates MOE — verify CV percentages appear."""
        outputs = _run_and_get_outputs(_notebook_path(27))
        all_text = "\n".join(outputs)
        assert "cv" in all_text.lower() or "margin" in all_text.lower() or "moe" in all_text.lower(), \
            "NB27 should demonstrate MOE/CV calculations"
