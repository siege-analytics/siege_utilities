"""Snowflake connector must be usable on an installed SDK.

Consensus findings C13 + C14 (#1357):
- C13: the module imported `read_pandas` from snowflake.connector.pandas_tools,
  which does not exist; the ImportError disabled the whole connector
  (SNOWFLAKE_AVAILABLE=False) even though the SDK was installed, and
  download_dataframe called the nonexistent function.
- C14: account/user were required positionals, so the documented
  get_snowflake_connector(config_file=...) factory raised TypeError before
  loading the config.
"""
import json

import pytest

snowflake = pytest.importorskip(
    "snowflake.connector", reason="install snowflake-connector-python to exercise C13/C14"
)

from siege_utilities.analytics import snowflake_connector as sc


def test_connector_enabled_on_installed_sdk():
    # C13: the import no longer references a nonexistent symbol, so an
    # installed SDK yields an enabled connector.
    assert sc.SNOWFLAKE_AVAILABLE is True


def test_config_file_factory_does_not_raise_typeerror(tmp_path):
    cfg = tmp_path / "snowflake.json"
    cfg.write_text(json.dumps({"account": "acct123", "user": "svc_user"}))
    conn = sc.get_snowflake_connector(config_file=str(cfg))
    assert conn.account == "acct123"
    assert conn.user == "svc_user"
    assert conn.connection is None  # constructed, not connected


def test_missing_account_and_user_raises_valueerror():
    with pytest.raises(ValueError, match="requires"):
        sc.SnowflakeConnector()  # neither args nor config


def test_download_dataframe_uses_cursor_not_read_pandas():
    import pandas as pd

    conn = sc.SnowflakeConnector(account="a", user="u")

    class _Cursor:
        description = [("date",), ("n",)]
        def execute(self, *a, **k):
            return None
        def fetch_pandas_all(self):
            return pd.DataFrame({"date": ["2026-01-01"], "n": [5]})

    conn.connection = object()  # truthy so download_dataframe skips connect()
    conn.cursor = _Cursor()
    df = conn.download_dataframe("SELECT 1")
    assert list(df.columns) == ["date", "n"]
    assert len(df) == 1
