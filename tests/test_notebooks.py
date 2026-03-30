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

PURE_PYTHON = [1, 2, 3, 6, 8, 11, 12, 17, 21]
GEO_NOTEBOOKS = [4, 5, 7]
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
