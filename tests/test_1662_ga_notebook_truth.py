"""Exercise the committed offline GA demo and its credentialed recipe (#1662)."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import Mock, patch

import nbformat
import pandas as pd
import pytest


NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks/analytics/02_ga_end_to_end.ipynb"
GA_FACTORY = "siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account"


def _notebook():
    return nbformat.read(NOTEBOOK, as_version=4)


def _run_cells(*indices: int) -> dict:
    cells = _notebook().cells
    namespace: dict = {}
    for index in indices:
        assert cells[index].cell_type == "code"
        exec(compile(cells[index].source, f"{NOTEBOOK.name}:cell-{index}", "exec"), namespace)
    return namespace


def _live_recipe() -> str:
    recipes = [
        block
        for cell in _notebook().cells if cell.cell_type == "markdown"
        for block in re.findall(r"```python\n(.*?)```", cell.source, re.DOTALL)
        if ".get_ga4_data(" in block
    ]
    assert len(recipes) == 1, "Document one runnable, credentialed two-week GA recipe"
    return recipes[0]


def test_fixture_narrative_never_promises_live_or_current_results():
    notebook = _notebook()
    intro = notebook.cells[0].source.lower()
    assert "offline" in intro and "fixed-date" in intro
    assert "2026-04-17" in intro and "2026-04-23" in intro
    for index in (0, 1, 3, 5, 7, 9):
        text = notebook.cells[index].source.lower()
        assert "offline" in text or "fixture" in text, index
        assert not re.search(r"\b(live|current|last\s+7\s+days)\b", text), index


def test_inbound_references_describe_analytics_02_as_offline():
    # Notebooks and docs that link to analytics/02 must not advertise it as a
    # live, weekly, or full-pipeline GA digest: it is an offline fixed-date demo
    # (#1662). The credential table must not list it under a credential it never
    # uses.
    root = Path(__file__).resolve().parents[1]
    forbidden = re.compile(r"\bweekly\b|\blive\b|\bships\b|full ga pipeline")
    for rel in (
        "notebooks/analytics/01_connectors.ipynb",
        "notebooks/reports/01_charts_and_pdf.ipynb",
    ):
        notebook = nbformat.read(root / rel, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type != "markdown" or "analytics/02" not in cell.source:
                continue
            for line in cell.source.splitlines():
                if "analytics/02" in line:
                    assert not forbidden.search(line.lower()), (rel, line)
    doc = (root / "docs/NOTEBOOKS.md").read_text(encoding="utf-8")
    credential_rows = [
        line
        for line in doc.splitlines()
        if "GOOGLE_APPLICATION_CREDENTIALS" in line and "analytics/02" in line
    ]
    assert not credential_rows, credential_rows


@pytest.mark.parametrize("credentials_present", [False, True])
def test_fixture_ignores_credentials_and_labels_fixed_comparison(
    credentials_present, tmp_path, monkeypatch, capsys
):
    if credentials_present:
        credentials = tmp_path / "service-account.json"
        credentials.write_text('{"type": "service_account"}', encoding="utf-8")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credentials))
        monkeypatch.setenv("GA_PROPERTY_ID", "123456789")
    else:
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("GA_PROPERTY_ID", raising=False)
    with patch(GA_FACTORY, side_effect=AssertionError("Offline demo attempted authentication")) as factory:
        namespace = _run_cells(2, 4)
    factory.assert_not_called()
    assert namespace["daily"]["date"].min() == pd.Timestamp("2026-04-17")
    assert namespace["daily"]["date"].max() == pd.Timestamp("2026-04-23")
    assert namespace["totals"]["sessions_7d"] == 3353
    assert namespace["wow_pct"] == 11.8
    output = capsys.readouterr().out.lower()
    assert "offline" in output and "fixture" in output and "3000" in output


def test_pure_offline_cells_generate_a_labelled_pdf(monkeypatch):
    """Run every code cell in normal CI, without credentials or an API service."""
    PdfReader = pytest.importorskip("PyPDF2").PdfReader
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GA_PROPERTY_ID", raising=False)
    indices = [i for i, cell in enumerate(_notebook().cells) if cell.cell_type == "code"]
    with patch(GA_FACTORY, side_effect=AssertionError("Offline demo attempted authentication")):
        namespace = _run_cells(*indices)
    reader = PdfReader(namespace["pdf_path"])
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text().lower()
    assert "offline" in text and "fixed-date" in text and "fixture" in text
    assert "2026-04-17" in text and "2026-04-23" in text
    assert "3000" in text and "11.8%" in text
    assert not re.search(r"\b(live|current|last\s+7\s+days)\b", text)
    chart_title = namespace["ax"].get_title().lower()
    assert "offline" in chart_title and "2026-04-17" in chart_title
    assert "offline" in namespace["pdf_path"].name


def test_notebook_is_valid_and_executable_cells_have_no_ga_query():
    notebook = _notebook()
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None and not cell.outputs
            tree = ast.parse(cell.source)
            assert not any(
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get_ga4_data" for node in ast.walk(tree)
            )


@pytest.fixture
def live_connector(tmp_path, monkeypatch):
    credentials = tmp_path / "service-account.json"
    credentials.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credentials))
    monkeypatch.setenv("GA_PROPERTY_ID", "123456789")
    connector = Mock()
    with patch(GA_FACTORY, return_value=connector):
        yield connector


def _week(sessions: int = 10) -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["20261017"], "sessions": [str(sessions)],
        "screenPageViews": ["30"], "bounceRate": ["0.4"],
    })


def _run_live_recipe() -> dict:
    namespace: dict = {}
    exec(compile(_live_recipe(), f"{NOTEBOOK.name}:live-recipe", "exec"), namespace)
    return namespace


def test_documented_recipe_queries_both_weeks_and_uses_the_results(live_connector):
    live_connector.get_ga4_data.side_effect = [_week(20), _week(10)]
    namespace = _run_live_recipe()
    calls = live_connector.get_ga4_data.call_args_list
    assert len(calls) == 2
    assert [(c.kwargs["start_date"], c.kwargs["end_date"]) for c in calls] == [
        ("7daysAgo", "yesterday"), ("14daysAgo", "8daysAgo"),
    ]
    for call in calls:
        assert call.kwargs["property_id"] == "123456789"
        assert call.kwargs["metrics"] == ["sessions", "screenPageViews", "bounceRate"]
        assert call.kwargs["dimensions"] == ["date"]
    assert namespace["live_sessions_7d"] == 20
    assert namespace["live_wow_pct"] == 100.0
    assert namespace["live_daily"]["pageviews"].tolist() == [30]
    assert namespace["live_daily"]["bounce_rate"].tolist() == [0.4]


@pytest.mark.parametrize("week_index", [0, 1])
@pytest.mark.parametrize("failure", [
    "api_error", "none", "empty", "missing_column", "bad_date", "bad_number", "nan", "infinity",
])
def test_documented_recipe_rejects_failed_or_malformed_weeks(live_connector, week_index, failure):
    bad = _week()
    if failure == "api_error":
        bad = RuntimeError("synthetic GA outage")
    elif failure == "none":
        bad = None
    elif failure == "empty":
        bad = bad.iloc[:0]
    elif failure == "missing_column":
        bad = bad.drop(columns="sessions")
    elif failure == "bad_date":
        bad.loc[0, "date"] = "not-a-date"
    else:
        bad.loc[0, "sessions"] = {
            "bad_number": "not-a-number", "nan": float("nan"), "infinity": float("inf"),
        }[failure]
    weeks = [_week(), _week()]
    weeks[week_index] = bad
    live_connector.get_ga4_data.side_effect = weeks
    with pytest.raises((ValueError, RuntimeError)):
        _run_live_recipe()
    assert live_connector.get_ga4_data.call_count == week_index + 1


def test_documented_recipe_rejects_zero_prior_sessions(live_connector):
    live_connector.get_ga4_data.side_effect = [_week(), _week(0)]
    with pytest.raises(ValueError, match="prior.*zero"):
        _run_live_recipe()


def test_live_recipe_does_not_call_still_processing_days_complete():
    md = next(c.source for c in _notebook().cells if c.get("id") == "live-recipe")
    windows = re.findall(r"query_week\('(\w+)', '(\w+)'\)", md)
    assert windows
    text = re.sub(r"[*_`]", "", md.lower())
    if any(end in ("today", "yesterday") for _, end in windows):
        assert "complete days" not in text and "processing" in text, windows


def test_offline_ga_notebook_runs_in_pure_notebook_ci():
    from tests.test_notebooks import NOTEBOOK_GROUPS
    assert "analytics/02_ga_end_to_end.ipynb" in NOTEBOOK_GROUPS["pure"]
    assert "analytics/02_ga_end_to_end.ipynb" not in NOTEBOOK_GROUPS["analytics_integration"]
