"""Headless notebook execution tests using papermill.

Notebooks are grouped by dependency (pure Python vs GDAL vs Django vs
Spark vs credentials) so tests skip gracefully when the group's
prerequisite is missing.

Discovery walks subdirectories under ``notebooks/`` — see the
``NOTEBOOK_GROUPS`` mapping below. The old flat ``{NN}_*.ipynb``
scheme was removed in #1161 (parent epic #1148): after the ELE-2456
migration, notebooks live in subdirectories and the previous
integer-number groups skipped every parametrized test at collection
time. See ``docs/PARSONS_NOTEBOOK_AUDIT.md``.

Usage:
    # Pure-Python group — always runnable, no system deps
    pytest tests/test_notebooks.py -k pure -v

    # Everything (respects env-required skip marks)
    pytest tests/test_notebooks.py -v

    # Include credential / integration notebooks
    pytest tests/test_notebooks.py -v -m ""

Adding a notebook: put it under the appropriate subdirectory and add
its path (relative to ``notebooks/``) to the matching group below. New
groups (e.g., ``advocacy`` for Parsons wrappers) go in
``NOTEBOOK_GROUPS`` with the mark set that captures its prereqs.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"


# ---------------------------------------------------------------------------
# Notebook discovery — subdirectory-path lists per dependency group
# ---------------------------------------------------------------------------
# Each entry is a path relative to ``notebooks/``. Group membership drives
# both discovery and the pytest marks applied to the parametrized test.
# Adding a notebook only requires listing its path here; the discovery
# helper resolves the absolute path at test time.

NOTEBOOK_GROUPS: dict[str, list[str]] = {
    # Pure Python — no system libs, no external services. Always runnable.
    "pure": [
        "foundations/01_configuration.ipynb",
        "foundations/02_profiles_branding.ipynb",
        "analytics/01_connectors.ipynb",
        "engines/01_multi_engine_dataframes.ipynb",
        "engines/04_statistics_primitives.ipynb",
        "reports/01_charts_and_pdf.ipynb",
    ],
    # Geo notebooks — require GDAL / GeoPandas / Shapely stack.
    "geo": [
        "spatial/01_boundaries.ipynb",
        "spatial/02_geocoding.ipynb",
        "spatial/03_choropleth_maps.ipynb",
        "spatial/04_redistricting.ipynb",
        "spatial/05_multi_source_joins.ipynb",
    ],
    # Django/PostGIS — require Django DB + GDAL.
    "django": [
        "spatial/06_geodjango.ipynb",
    ],
    # Analytics with credentials — external service tokens required.
    "analytics_integration": [
        "analytics/02_ga_end_to_end.ipynb",
    ],
    # Spark / distributed — require pyspark + JVM.
    "spark": [
        "engines/02_distributed_spark.ipynb",
    ],
    # Databricks — require databricks-sdk + connection profile.
    "databricks": [
        "engines/03_databricks_geo.ipynb",
    ],
    # Reports with heavy deps (PPTX, Google Slides, survey data).
    "reports_integration": [
        "reports/02_slides_pptx_and_google.ipynb",
        "reports/03_polling_survey_analysis.ipynb",
        "reports/04_survey_full_showcase.ipynb",
    ],
    # Advocacy — Parsons wrappers land here. Epic #1148 Phase 6.
    # Empty until N-4..N-9 tickets populate.
    "advocacy": [],
}


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _resolve(rel_path: str) -> Path:
    """Resolve a notebook path (relative to notebooks/) to absolute Path.

    Skips cleanly with an actionable message if the notebook is missing —
    treats missing files as an unshipped notebook, not a test failure. If
    a notebook was renamed / moved, update ``NOTEBOOK_GROUPS`` above.
    """
    p = NOTEBOOKS_DIR / rel_path
    if not p.is_file():
        pytest.skip(
            f"Notebook {rel_path!r} not found under {NOTEBOOKS_DIR}. "
            f"If renamed / moved / archived, update NOTEBOOK_GROUPS in this file."
        )
    return p


def _run_notebook(nb_path: Path, timeout: int = 300) -> None:
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
    """Execute a notebook and return code-cell outputs for validation."""
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


def _ids(group: str) -> list[str]:
    """Pytest IDs derived from the notebook's basename (without .ipynb)."""
    return [Path(p).stem for p in NOTEBOOK_GROUPS[group]]


# ---------------------------------------------------------------------------
# Pure Python — always runnable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["pure"], ids=_ids("pure"))
def test_pure_python_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Geo — require GDAL
# ---------------------------------------------------------------------------


@pytest.mark.requires_gdal
@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["geo"], ids=_ids("geo"))
def test_geo_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Django / PostGIS
# ---------------------------------------------------------------------------


@pytest.mark.requires_gdal
@pytest.mark.django_db
@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["django"], ids=_ids("django"))
def test_django_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Analytics integration — credentials required
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "nb_rel", NOTEBOOK_GROUPS["analytics_integration"],
    ids=_ids("analytics_integration"),
)
def test_analytics_integration_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Spark
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_spark
@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["spark"], ids=_ids("spark"))
def test_spark_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Databricks
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["databricks"], ids=_ids("databricks"))
def test_databricks_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Reports integration — PPTX / Google Slides / survey data
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "nb_rel", NOTEBOOK_GROUPS["reports_integration"],
    ids=_ids("reports_integration"),
)
def test_reports_integration_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Advocacy — Parsons wrappers (populated by N-4..N-9 under epic #1148)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["advocacy"], ids=_ids("advocacy"))
def test_advocacy_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


# ---------------------------------------------------------------------------
# Output validation — verify notebooks produce correct results, not just
# "doesn't crash." Every check names the current notebook path (not a
# legacy NB08 / NB22 / etc. integer ID).
# ---------------------------------------------------------------------------


class TestNotebookOutputValidation:
    """Semantic sanity on canonical notebook outputs.

    Each test resolves its notebook via ``_resolve`` so a rename or
    archive triggers a clean skip with an actionable message rather
    than a silent AttributeError. All checks reference the post-
    ELE-2456 subdirectory paths.
    """

    def test_multi_engine_dataframes_produces_engine_output(self) -> None:
        outputs = _run_and_get_outputs(_resolve("engines/01_multi_engine_dataframes.ipynb"))
        all_text = "\n".join(outputs)
        assert "engine" in all_text.lower(), \
            "engines/01_multi_engine_dataframes should reference engine names"
        assert any(c.isdigit() for c in all_text), \
            "engines/01_multi_engine_dataframes should produce numeric aggregation results"

    def test_statistics_primitives_show_moe_or_cv(self) -> None:
        outputs = _run_and_get_outputs(_resolve("engines/04_statistics_primitives.ipynb"))
        all_text = "\n".join(outputs)
        assert any(term in all_text.lower() for term in ("moe", "margin", "cv", "coefficient")), \
            "engines/04_statistics_primitives should demonstrate MOE/CV calculations"

    def test_redistricting_shows_compactness(self) -> None:
        outputs = _run_and_get_outputs(_resolve("spatial/04_redistricting.ipynb"))
        all_text = "\n".join(outputs)
        assert any(term in all_text.lower() for term in ("polsby", "reock", "compactness")), \
            "spatial/04_redistricting should show compactness scores"
