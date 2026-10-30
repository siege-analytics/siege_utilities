"""Contract checks for the runnable analytics/01 connector demonstration (#1661).

Execute the actual committed notebook cells, not a reimplementation of them.
No credentials or network services are used: connector factories are patched.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest


NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks/analytics/01_connectors.ipynb"


def _run_cells(*indices: int) -> dict:
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    namespace: dict = {}
    for index in indices:
        source = "".join(cells[index]["source"])
        assert cells[index]["cell_type"] == "code", index
        exec(compile(source, f"{NOTEBOOK.name}:cell-{index}", "exec"), namespace)
    return namespace


@pytest.mark.parametrize("today, start, end", [
    ("2026-10-12", "2026-09-28", "2026-10-11"),
    ("2026-10-14", "2026-09-28", "2026-10-11"),
    ("2026-10-18", "2026-09-28", "2026-10-11"),
    ("2026-01-01", "2025-12-15", "2025-12-28"),
])
def test_credentialed_branches_query_both_sources_and_derive_daily(tmp_path, monkeypatch, today, start, end):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return date.fromisoformat(today)

    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    config = tmp_path / "snowflake.yaml"
    config.write_text("account: example", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.setenv("GA_PROPERTY_ID", "123456789")
    monkeypatch.setenv("SNOWFLAKE_CONFIG_FILE", str(config))
    ga = Mock()
    ga.get_ga4_data.return_value = pd.DataFrame({"date": ["20260401", "20260402"], "sessions": [10, 20]})
    sf = Mock()
    sf.execute_query.return_value = [("2026-04-01", 900), ("2026-04-02", 800)]
    with patch("siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account", return_value=ga), patch(
        "siege_utilities.analytics.snowflake_connector.get_snowflake_connector", return_value=sf
    ), patch("datetime.date", FixedDate):
        ns = _run_cells(2, 4, 6, 8)
    ga.get_ga4_data.assert_called_once()
    assert ga.get_ga4_data.call_args.kwargs["property_id"] == "123456789"
    assert ga.get_ga4_data.call_args.kwargs["start_date"] == start
    assert ga.get_ga4_data.call_args.kwargs["end_date"] == end
    sf.execute_ddl.assert_called_once_with("ALTER SESSION SET WEEK_START = 1")
    sf.execute_query.assert_called_once()
    query = sf.execute_query.call_args.args[0]
    assert "SUM(sessions)" in query
    assert "date >= DATEADD(week, -2, DATE_TRUNC('week', CURRENT_DATE))" in query
    assert "date < DATE_TRUNC('week', CURRENT_DATE)" in query
    assert list(ns["daily"]["sessions"]) == [10, 20], "summary must use the live GA result, not a fixture"
    assert list(ns["snowflake_daily"]["sessions"]) == [900, 800]
    assert ns["summary"]["weekly_sessions"].sum() == 30


def test_snowflake_only_result_drives_summary(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    config = tmp_path / "snowflake.yaml"
    config.write_text("account: example", encoding="utf-8")
    monkeypatch.setenv("SNOWFLAKE_CONFIG_FILE", str(config))
    sf = Mock()
    sf.execute_query.return_value = [("2026-04-01", 71), ("2026-04-02", 73)]
    with patch("siege_utilities.analytics.snowflake_connector.get_snowflake_connector", return_value=sf):
        ns = _run_cells(2, 4, 6, 8)
    sf.execute_query.assert_called_once()
    assert list(ns["daily"]["sessions"]) == [71, 73]
    assert ns["summary"]["weekly_sessions"].sum() == 144


def test_no_credentials_is_explicitly_offline_fixture(monkeypatch, capsys):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GA_PROPERTY_ID", raising=False)
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    ns = _run_cells(2, 4, 6, 8)
    assert "illustrative offline fixture" in capsys.readouterr().out.lower()
    assert ns["data_source"] == "illustrative offline fixture"
    assert ns["summary"]["weekly_sessions"].sum() == sum(ns["daily"]["sessions"])
    assert ns["daily"].groupby("week")["date"].nunique().tolist() == [7, 7]
    assert ns["summary"].index.strftime("%Y-%m-%d").tolist() == ["2026-03-30", "2026-04-06"]


def test_live_query_error_does_not_silently_fall_back(tmp_path, monkeypatch):
    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.setenv("GA_PROPERTY_ID", "123456789")
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    ga = Mock()
    ga.get_ga4_data.side_effect = RuntimeError("synthetic GA outage")
    with patch("siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account", return_value=ga):
        with pytest.raises(RuntimeError, match="synthetic GA outage"):
            _run_cells(2, 4, 6, 8)
    ga.get_ga4_data.assert_called_once()


def test_credential_file_without_property_is_not_fake_live_result(tmp_path, monkeypatch):
    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.delenv("GA_PROPERTY_ID", raising=False)
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    with pytest.raises(ValueError, match="GA_PROPERTY_ID"):
        _run_cells(2, 4)


@pytest.mark.parametrize("rows", [[], [("2026-10-05", 100), ("2026-10-06", None)], [("2026-10-05", 100), (None, 9)]])
def test_null_sessions_fail(tmp_path, monkeypatch, rows):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    config = tmp_path / "snowflake.yaml"
    config.write_text("account: example", encoding="utf-8")
    monkeypatch.setenv("SNOWFLAKE_CONFIG_FILE", str(config))
    sf = Mock()
    sf.execute_query.return_value = rows
    with patch("siege_utilities.analytics.snowflake_connector.get_snowflake_connector", return_value=sf):
        with pytest.raises(ValueError):
            _run_cells(2, 4, 6, 8)


def test_flat_live_traffic_reports_no_wow_change(tmp_path, monkeypatch):
    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.setenv("GA_PROPERTY_ID", "1")
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    # Whatever window the notebook requests, return flat traffic for it.
    def flat(**kwargs):
        iso = lambda v: len(v) == 10 and v[4] == "-"
        # Relative GA keywords: pretend today is Wed 2026-10-14.
        start = pd.Timestamp(kwargs["start_date"]) if iso(kwargs["start_date"]) else pd.Timestamp("2026-10-07")
        end = pd.Timestamp(kwargs["end_date"]) if iso(kwargs["end_date"]) else pd.Timestamp("2026-10-13")
        days = pd.date_range(start, end).strftime("%Y%m%d")
        return pd.DataFrame({"date": list(days), "sessions": [100.0] * len(days)})
    ga = Mock()
    ga.get_ga4_data.side_effect = flat
    with patch("siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account", return_value=ga):
        ns = _run_cells(2, 4, 6, 8)
    wow = ns["summary"]["WoW change %"].dropna()
    assert (wow == 0).all(), ns["summary"]


@pytest.mark.parametrize("columns", [None, ["date", "sessions"]])
def test_empty_ga_result_fails(tmp_path, monkeypatch, columns):
    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.setenv("GA_PROPERTY_ID", "1")
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    ga = Mock()
    ga.get_ga4_data.return_value = pd.DataFrame(columns=columns)
    with patch("siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account", return_value=ga):
        with pytest.raises(ValueError, match="GA4 live query has no dated sessions"):
            _run_cells(2, 4, 6, 8)


@pytest.mark.parametrize("sessions", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_sessions_fail(tmp_path, monkeypatch, sessions):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    config = tmp_path / "snowflake.yaml"
    config.write_text("account: example", encoding="utf-8")
    monkeypatch.setenv("SNOWFLAKE_CONFIG_FILE", str(config))
    sf = Mock()
    sf.execute_query.return_value = [("2026-10-05", 100), ("2026-10-06", sessions)]
    with patch("siege_utilities.analytics.snowflake_connector.get_snowflake_connector", return_value=sf):
        with pytest.raises(ValueError, match="null or non-finite sessions"):
            _run_cells(2, 4, 6, 8)


def test_zero_sessions_are_valid(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    config = tmp_path / "snowflake.yaml"
    config.write_text("account: example", encoding="utf-8")
    monkeypatch.setenv("SNOWFLAKE_CONFIG_FILE", str(config))
    sf = Mock()
    sf.execute_query.return_value = [(day, 0) for day in pd.date_range("2026-09-28", periods=14)]
    with patch("siege_utilities.analytics.snowflake_connector.get_snowflake_connector", return_value=sf):
        ns = _run_cells(2, 4, 6, 8)
    assert ns["daily"]["sessions"].tolist() == [0] * 14
    assert ns["summary"]["weekly_sessions"].tolist() == [0, 0]
    assert ns["summary"]["WoW change %"].isna().all()


def test_sparse_live_weeks_withhold_wow(tmp_path, monkeypatch):
    # One observed day per week is not a complete week; a confident
    # "+100.0% WoW" from such a sparse response is wrong. The summary must
    # withhold the percentage and show the day counts instead.
    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.setenv("GA_PROPERTY_ID", "1")
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    ga = Mock()
    ga.get_ga4_data.return_value = pd.DataFrame(
        {"date": ["20260928", "20261005"], "sessions": [100, 200]}
    )
    with patch(
        "siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account",
        return_value=ga,
    ):
        ns = _run_cells(2, 4, 6, 8)
    summary = ns["summary"]
    assert not (pd.to_numeric(summary["WoW change %"], errors="coerce") == 100.0).any(), summary
    assert (pd.to_numeric(summary["WoW change %"], errors="coerce").isna()).all(), summary
    assert summary["observed_days"].tolist() == [1, 1]
    assert summary["weekly_sessions"].tolist() == [100, 200]
