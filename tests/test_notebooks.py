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

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
NOTEBOOK_KERNEL_NAME = os.environ.get("NOTEBOOK_KERNEL_NAME", "python3")
_NOTEBOOK_ENV_KEYS = [
    "JUPYTER_PATH",
    "SIEGE_UTILITIES_CACHE_DIR",
    "SIEGE_CACHE",
    "SPARK_CACHE",
    "SIEGE_OUTPUT",
    "SIEGE_REPORTS",
    "SIEGE_CHARTS",
    "SIEGE_MAPS",
    "REPORT_OUTPUT_DIR",
]


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
        "foundations/entity_identification.ipynb",
        "foundations/file_operations_and_security.ipynb",
        "config/credential_management.ipynb",
        "git/repo_analysis.ipynb",
        "economic/economic_data_irs_bls.ipynb",
        "analytics/01_connectors.ipynb",
        "analytics/03_social_media_analytics.ipynb",
        "analytics/04_crm_pipeline.ipynb",
        "analytics/05_crm_sales_reports.ipynb",
        "engines/01_multi_engine_dataframes.ipynb",
        "engines/04_statistics_primitives.ipynb",
        "reports/01_charts_and_pdf.ipynb",
        "playground/00_public_api_contracts.ipynb",
    ],
    # Geo notebooks — require GDAL / GeoPandas / Shapely stack.
    "geo": [
        "spatial/01_boundaries.ipynb",
        "spatial/02_geocoding.ipynb",
        "spatial/03_choropleth_maps.ipynb",
        "spatial/04_redistricting.ipynb",
        "spatial/05_multi_source_joins.ipynb",
        "spatial/07_natural_language_to_geometry.ipynb",
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


def _set_kernel_pythonpath() -> str | None:
    old = os.environ.get("PYTHONPATH")
    # Keep the notebook kernel pointed at the checked-out repo without
    # inheriting developer-machine site-packages that can mask the CI venv.
    os.environ["PYTHONPATH"] = str(REPO_ROOT)
    return old


def _restore_pythonpath(old: str | None) -> None:
    if old is None:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = old


def _artifact_dir() -> Path:
    root = os.environ.get("NOTEBOOK_ARTIFACT_DIR")
    if root:
        path = Path(root)
    else:
        path = REPO_ROOT / ".notebook-artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_stem(nb_path: Path) -> str:
    return nb_path.relative_to(NOTEBOOKS_DIR).as_posix().replace("/", "__").replace(".ipynb", "")


def _cleanup_success_artifacts(artifacts: Path, *paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
    if artifacts.exists():
        try:
            next(artifacts.iterdir())
        except StopIteration:
            shutil.rmtree(artifacts, ignore_errors=True)


def _prepare_notebook_env(cwd: Path) -> dict[str, str | None]:
    old = {key: os.environ.get(key) for key in _NOTEBOOK_ENV_KEYS}
    cache = cwd / "cache"
    output = cwd / "output"
    paths = {
        "SIEGE_UTILITIES_CACHE_DIR": cache / "siege_utilities",
        "SIEGE_CACHE": cache / "siege",
        "SPARK_CACHE": cache / "spark",
        "SIEGE_OUTPUT": output,
        "SIEGE_REPORTS": output / "reports",
        "SIEGE_CHARTS": output / "charts",
        "SIEGE_MAPS": output / "maps",
        "REPORT_OUTPUT_DIR": output / "reports",
    }
    for key, path in paths.items():
        os.environ[key] = str(path)
    return old


def _restore_notebook_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@contextmanager
def _isolated_kernel(nb_path: Path, cwd: Path):
    """Expose a per-notebook kernelspec with kernel HOME under ``cwd``.

    Changing parent ``HOME`` before Papermill runs breaks Jupyter kernelspec
    discovery. Instead, copy the requested kernelspec into a temporary Jupyter
    data directory, add an ``env`` override for the spawned kernel process, and
    point ``JUPYTER_PATH`` at that temporary directory for this notebook only.
    """
    from jupyter_client.kernelspec import KernelSpecManager

    spec = KernelSpecManager().get_kernel_spec(NOTEBOOK_KERNEL_NAME)
    kernel_name = f"{NOTEBOOK_KERNEL_NAME}-isolated-{_artifact_stem(nb_path).replace('_', '-')}"
    kernels_dir = cwd / "jupyter" / "kernels" / kernel_name
    kernels_dir.mkdir(parents=True, exist_ok=True)

    kernel_home = cwd / "home"
    kernel_home.mkdir(parents=True, exist_ok=True)
    env = dict(spec.env or {})
    env["HOME"] = str(kernel_home)
    kernel_json = {
        "argv": spec.argv,
        "display_name": f"{spec.display_name} (isolated)",
        "language": spec.language,
        "metadata": spec.metadata,
        "env": env,
    }
    (kernels_dir / "kernel.json").write_text(json.dumps(kernel_json, indent=2), encoding="utf-8")

    old_jupyter_path = os.environ.get("JUPYTER_PATH")
    os.environ["JUPYTER_PATH"] = str(cwd / "jupyter")
    try:
        yield kernel_name
    finally:
        if old_jupyter_path is None:
            os.environ.pop("JUPYTER_PATH", None)
        else:
            os.environ["JUPYTER_PATH"] = old_jupyter_path


def _execute_with_nbclient(nb_path: Path, timeout: int, cwd: Path, kernel_name: str):
    """Execute with nbclient when papermill is unavailable.

    This keeps notebook execution tests honest in environments that have the
    Jupyter runtime but not papermill. Missing execution dependencies should be
    explicit failures in CI, not silent skips of the whole notebook suite.
    """
    import nbclient
    import nbformat

    nb = nbformat.read(nb_path, as_version=4)
    try:
        nbclient.NotebookClient(
            nb,
            timeout=timeout,
            kernel_name=kernel_name,
            resources={"metadata": {"path": str(cwd)}},
        ).execute()
        _cleanup_success_artifacts(_artifact_dir())
    except Exception:
        out_path = _artifact_dir() / f"{_artifact_stem(nb_path)}.failed.ipynb"
        nbformat.write(nb, out_path)
        raise
    return nb


def _execute_notebook(nb_path: Path, timeout: int = 300):
    """Execute a notebook headlessly from an isolated temp cwd."""
    old_pythonpath = _set_kernel_pythonpath()
    try:
        with tempfile.TemporaryDirectory() as cwd_str:
            cwd = Path(cwd_str)
            old_env = _prepare_notebook_env(cwd)
            stem = _artifact_stem(nb_path)
            artifacts = _artifact_dir()
            out_path = artifacts / f"{stem}.executed.ipynb"
            stdout_path = artifacts / f"{stem}.stdout.log"
            stderr_path = artifacts / f"{stem}.stderr.log"
            try:
                with _isolated_kernel(nb_path, cwd) as kernel_name:
                    try:
                        import papermill  # type: ignore[import-not-found]
                    except ImportError:
                        return _execute_with_nbclient(nb_path, timeout, cwd, kernel_name)

                    import nbformat

                    with stdout_path.open("w", encoding="utf-8") as stdout_file, \
                        stderr_path.open("w", encoding="utf-8") as stderr_file:
                        papermill.execute_notebook(
                            str(nb_path),
                            str(out_path),
                            kernel_name=kernel_name,
                            cwd=str(cwd),
                            request_save_on_cell_execute=True,
                            stdout_file=stdout_file,
                            stderr_file=stderr_file,
                            start_timeout=timeout,
                            execution_timeout=timeout,
                        )
                nb = nbformat.read(out_path, as_version=4)
                _cleanup_success_artifacts(artifacts, out_path, stdout_path, stderr_path)
                return nb
            finally:
                _restore_notebook_env(old_env)
    finally:
        _restore_pythonpath(old_pythonpath)


def _run_notebook(nb_path: Path, timeout: int = 300) -> None:
    """Execute a notebook headlessly."""
    _execute_notebook(nb_path, timeout)


def _run_and_get_outputs(nb_path: Path, timeout: int = 300) -> list:
    """Execute a notebook and return code-cell outputs for validation."""
    nb = _execute_notebook(nb_path, timeout)
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


def _ids(group: str) -> list[str]:
    """Pytest IDs derived from the notebook's basename (without .ipynb)."""
    return [Path(p).stem for p in NOTEBOOK_GROUPS[group]]


# ---------------------------------------------------------------------------
# Pure Python — always runnable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["pure"], ids=_ids("pure"))
def test_pure_python_notebook(nb_rel: str) -> None:
    _run_notebook(_resolve(nb_rel))


def test_pure_notebook_timeout_is_enforced(tmp_path, monkeypatch) -> None:
    """Synthetic hang fixture proves notebook timeout wiring is real."""
    import sys

    import nbformat
    from nbclient.exceptions import CellTimeoutError

    notebook_root = tmp_path / "notebooks"
    notebook_root.mkdir()
    nb_path = notebook_root / "timeout_probe.ipynb"
    nb = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("import time\ntime.sleep(5)\n")]
    )
    nbformat.write(nb, nb_path)

    kernel_name = "timeout-proof-kernel"
    kernel_dir = tmp_path / "jupyter" / "kernels" / kernel_name
    kernel_dir.mkdir(parents=True)
    (kernel_dir / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Timeout proof kernel",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )

    artifact_dir = tmp_path / "artifacts"
    monkeypatch.setenv("JUPYTER_PATH", str(tmp_path / "jupyter"))
    monkeypatch.setenv("NOTEBOOK_ARTIFACT_DIR", str(artifact_dir))
    monkeypatch.setattr(sys.modules[__name__], "NOTEBOOKS_DIR", notebook_root)
    monkeypatch.setattr(sys.modules[__name__], "NOTEBOOK_KERNEL_NAME", kernel_name)

    with pytest.raises(CellTimeoutError):
        _execute_notebook(nb_path, timeout=1)

    retained = artifact_dir / "timeout_probe.executed.ipynb"
    assert retained.exists(), "timeout failures should retain the executed notebook artifact"


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


@pytest.mark.integration
@pytest.mark.requires_gdal
@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["django"], ids=_ids("django"))
def test_django_notebook(nb_rel: str) -> None:
    # The current GeoDjango notebook is conceptual/docs-only. Do not let
    # pytest-django create a local Postgres database before notebook execution;
    # a future operational PostGIS notebook should add its own explicit fixture
    # or environment-gated integration test.
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
