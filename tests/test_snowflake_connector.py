"""Tests for siege_utilities.analytics.snowflake_connector.

Mock tests run on every CI build. The ``requires_api_key``-marked
smoke test at the bottom hits Snowflake for real and is skipped
unless ``~/.siege-test-credentials.yaml`` has a ``snowflake:``
section.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock tests
# ---------------------------------------------------------------------------

@pytest.fixture
def _patch_snowflake(monkeypatch):
    """Stand in for snowflake.connector at module level so __init__ doesn't
    raise ImportError on machines without snowflake-connector-python installed.
    Returns the mock module so tests can assert on connect() calls.
    """
    from siege_utilities.analytics import snowflake_connector as mod

    fake = MagicMock()
    monkeypatch.setattr(mod, "SNOWFLAKE_AVAILABLE", True)
    monkeypatch.setattr(mod, "snowflake", fake, raising=False)
    # write_pandas is referenced directly; patch the symbol the module imports.
    monkeypatch.setattr(mod, "write_pandas", MagicMock(return_value=(True, 1, 5, None)), raising=False)
    return fake


def test_init_rejects_when_snowflake_not_installed(monkeypatch):
    """The constructor must raise ImportError, not silently produce a
    half-built object that fails later with a confusing AttributeError."""
    from siege_utilities.analytics import snowflake_connector as mod

    monkeypatch.setattr(mod, "SNOWFLAKE_AVAILABLE", False)
    with pytest.raises(ImportError, match="snowflake-connector-python"):
        mod.SnowflakeConnector(account="x", user="y")


def test_init_records_connection_params(_patch_snowflake):
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    c = SnowflakeConnector(
        account="acc", user="u", password="p",
        warehouse="WH", database="DB", schema="SCH", role="R",
    )
    assert (c.account, c.user, c.warehouse, c.database, c.schema, c.role) == (
        "acc", "u", "WH", "DB", "SCH", "R"
    )
    # connection is lazy
    assert c.connection is None


def test_load_config_overlays_json_values(tmp_path, _patch_snowflake):
    """A config file value must override the constructor None defaults
    but not stomp explicitly-passed values."""
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"warehouse": "FROM_FILE", "database": "FROM_FILE_DB"}))

    c = SnowflakeConnector(account="acc", user="u", password="p", config_file=cfg)
    assert c.warehouse == "FROM_FILE"
    assert c.database == "FROM_FILE_DB"


def test_load_config_missing_file_raises(_patch_snowflake, tmp_path):
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    with pytest.raises(FileNotFoundError):
        SnowflakeConnector(
            account="a", user="u", password="p",
            config_file=tmp_path / "does_not_exist.json",
        )


def test_connect_passes_only_non_none_params(_patch_snowflake):
    """``snowflake.connector.connect`` should never see warehouse=None /
    database=None -- those are best omitted so Snowflake falls back to
    user defaults instead of erroring on empty values."""
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    c = SnowflakeConnector(account="acc", user="u", password="p", warehouse=None)
    assert c.connect() is True

    _patch_snowflake.connector.connect.assert_called_once()
    kwargs = _patch_snowflake.connector.connect.call_args.kwargs
    assert "warehouse" not in kwargs
    assert kwargs["account"] == "acc"
    assert kwargs["password"] == "p"


def test_execute_query_returns_none_on_driver_error(_patch_snowflake):
    """Driver-side failures must be translated to ``None``, not propagate
    a raw snowflake.connector exception -- callers expect Optional[list]."""
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    c = SnowflakeConnector(account="acc", user="u", password="p")
    cursor = MagicMock()
    cursor.execute.side_effect = RuntimeError("boom")
    c.connection = MagicMock()
    c.cursor = cursor

    assert c.execute_query("SELECT 1") is None


def test_upload_dataframe_validates_table_identifier(_patch_snowflake):
    """Bad identifiers must fail before any cursor.execute or
    write_pandas call. validate_sql_identifier guards this path."""
    pd = pytest.importorskip("pandas")
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    c = SnowflakeConnector(account="acc", user="u", password="p")
    c.connection = MagicMock()
    c.cursor = MagicMock()

    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError):
        c.upload_dataframe(df, table_name="bad; DROP TABLE users;--")


def test_context_manager_connects_and_disconnects(_patch_snowflake):
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    with SnowflakeConnector(account="a", user="u", password="p") as c:
        assert c.connection is not None
    # disconnect closes both cursor and connection
    c.connection.close.assert_called_once()


# ---------------------------------------------------------------------------
# Live API smoke (skipped without credentials)
# ---------------------------------------------------------------------------

@pytest.mark.requires_api_key
def test_snowflake_live_connect_disconnect(api_credentials):
    pytest.importorskip("snowflake.connector")
    from siege_utilities.analytics.snowflake_connector import SnowflakeConnector

    creds = api_credentials.get("snowflake")
    if not creds:
        pytest.skip("no 'snowflake:' section in credentials file")

    c = SnowflakeConnector(**{k: creds.get(k) for k in (
        "account", "user", "password", "warehouse", "database", "schema", "role"
    )})
    assert c.connect() is True
    try:
        result = c.execute_query("SELECT CURRENT_VERSION()")
        assert result and len(result) == 1
    finally:
        c.disconnect()
