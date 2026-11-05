"""analytics/01 notebook: GA4 window in the property timezone, Snowflake JSON config (#1661, PR #1780).

The GA4 Data API interprets report dates in the property's timezone, so the
notebook must pick "the previous two complete weeks" in that zone, not on the
host clock. The Snowflake connector reads its config with ``json.load``, so the
config the notebook documents must load through the real connector; earlier
tests mocked the factory and never exercised it.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest


NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks/analytics/01_connectors.ipynb"


def _cells():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def _run_cells(*indices: int) -> dict:
    cells = _cells()
    namespace: dict = {}
    for index in indices:
        assert cells[index]["cell_type"] == "code", index
        exec(compile("".join(cells[index]["source"]), f"{NOTEBOOK.name}:cell-{index}", "exec"), namespace)
    return namespace


def _ga_env(tmp_path, monkeypatch, zone):
    creds = tmp_path / "service-account.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    monkeypatch.setenv("GA_PROPERTY_ID", "123456789")
    monkeypatch.delenv("SNOWFLAKE_CONFIG_FILE", raising=False)
    if zone is None:
        monkeypatch.delenv("GA_PROPERTY_TIMEZONE", raising=False)
    else:
        monkeypatch.setenv("GA_PROPERTY_TIMEZONE", zone)


def _clock(instant_utc: str):
    """Patch the host clock: date.today() is the host (UTC) date of the instant."""
    instant = datetime.fromisoformat(instant_utc).replace(tzinfo=timezone.utc)

    class HostDate(date):
        @classmethod
        def today(cls):
            return instant.date()

    class HostDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            moment = instant if tz is None else instant.astimezone(tz)
            return cls.fromtimestamp(moment.timestamp(), tz=moment.tzinfo)

    return patch("datetime.date", HostDate), patch("datetime.datetime", HostDatetime)


@pytest.mark.parametrize("instant, zone, start, end", [
    # Monday 03:00 UTC is still Sunday evening in Los Angeles: the property's
    # current week began 2026-10-05, so the window ends 2026-10-04.
    ("2026-10-12T03:00:00", "America/Los_Angeles", "2026-09-21", "2026-10-04"),
    # Sunday noon UTC is already Monday in Kiritimati (UTC+14).
    ("2026-10-11T12:00:00", "Pacific/Kiritimati", "2026-09-28", "2026-10-11"),
    # Control: the property zone agrees with the host date.
    ("2026-10-14T12:00:00", "UTC", "2026-09-28", "2026-10-11"),
])
def test_ga_window_uses_property_timezone_not_host_date(tmp_path, monkeypatch, instant, zone, start, end):
    _ga_env(tmp_path, monkeypatch, zone)
    ga = Mock()
    ga.get_ga4_data.return_value = pd.DataFrame({"date": ["20261001"], "sessions": [1]})
    date_patch, datetime_patch = _clock(instant)
    with patch("siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account",
               return_value=ga), date_patch, datetime_patch:
        _run_cells(2, 4)

    kwargs = ga.get_ga4_data.call_args.kwargs
    assert (kwargs["start_date"], kwargs["end_date"]) == (start, end)


@pytest.mark.parametrize("zone", [None, "Mars/Olympus_Mons"])
def test_ga_path_requires_a_valid_property_timezone(tmp_path, monkeypatch, zone):
    _ga_env(tmp_path, monkeypatch, zone)
    ga = Mock()
    with patch("siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account",
               return_value=ga):
        with pytest.raises(ValueError, match="GA_PROPERTY_TIMEZONE"):
            _run_cells(2, 4)
    ga.get_ga4_data.assert_not_called()


def _documented_snowflake_config() -> dict:
    """The JSON example the notebook's Snowflake section documents."""
    section = next(
        "".join(cell["source"]) for cell in _cells()
        if cell["cell_type"] == "markdown" and "## 3. Snowflake" in "".join(cell["source"])
    )
    match = re.search(r"```json\n(.*?)```", section, re.S)
    assert match, "the Snowflake section must show the JSON config the connector reads"
    return json.loads(match.group(1))


def test_documented_snowflake_config_loads_through_the_real_connector(tmp_path, monkeypatch):
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    documented = _documented_snowflake_config()
    config = tmp_path / "snowflake.json"
    config.write_text(json.dumps(documented), encoding="utf-8")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setenv("SNOWFLAKE_CONFIG_FILE", str(config))
    rows = [("2026-10-05", 5), ("2026-10-06", 6)]
    # Only the network calls are replaced; get_snowflake_connector and
    # _load_config are the real ones.
    with patch.object(SnowflakeConnector, "execute_ddl", autospec=True) as ddl, \
            patch.object(SnowflakeConnector, "execute_query", autospec=True, return_value=rows) as query:
        ns = _run_cells(2, 4, 6)

    connector = query.call_args.args[0]
    assert isinstance(connector, SnowflakeConnector)
    for key in ("account", "user", "warehouse", "database", "schema", "role"):
        assert getattr(connector, key) == documented[key], key
    ddl.assert_called_once_with(connector, "ALTER SESSION SET WEEK_START = 1")
    assert list(ns["snowflake_daily"]["sessions"]) == [5, 6]


def test_notebook_no_longer_documents_a_yaml_snowflake_config():
    text = NOTEBOOK.read_text(encoding="utf-8")
    assert "a YAML config" not in text
    assert "snowflake.yaml" not in text
