"""Contract checks for the runnable analytics/01 connector demonstration (#1661).

Execute the actual committed notebook cells, not a reimplementation of them.
No credentials or network services are used: connector factories are patched.
"""

from __future__ import annotations

import json
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


def test_credentialed_branches_query_both_sources_and_derive_daily(tmp_path, monkeypatch):
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
    ):
        ns = _run_cells(2, 4, 6, 8)
    ga.get_ga4_data.assert_called_once()
    assert ga.get_ga4_data.call_args.kwargs["property_id"] == "123456789"
    assert ga.get_ga4_data.call_args.kwargs["start_date"] == "7daysAgo"
    assert ga.get_ga4_data.call_args.kwargs["end_date"] == "yesterday"
    sf.execute_query.assert_called_once()
    query = sf.execute_query.call_args.args[0]
    assert "SUM(sessions)" in query and "date < CURRENT_DATE" in query
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
