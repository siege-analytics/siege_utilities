"""Regression tests for pandas type mapping (#1484, dtype-only scope).

The session-context-restore fix is deferred to ride with #1421 (identifier
quoting), so this file covers only the dtype mapping.
"""

from unittest.mock import Mock

import pytest

from siege_utilities.analytics import snowflake_connector as sc


@pytest.fixture
def connector(monkeypatch):
    monkeypatch.setattr(sc, "SNOWFLAKE_AVAILABLE", True)
    conn = sc.SnowflakeConnector(
        account="test_account", user="test_user",
        database="CONFIGURED_DB", schema="CONFIGURED_SCHEMA",
    )
    conn.connection = Mock()
    return conn


@pytest.mark.parametrize(
    "dtype, values, expected",
    [
        ("Int64", [1, None], "NUMBER(38,0)"),
        ("Float64", [1.5, None], "FLOAT"),
        ("boolean", [True, None], "BOOLEAN"),
        ("datetime64[ns]", ["2026-01-01", None], "TIMESTAMP_NTZ"),
        ("datetime64[ns, UTC]", ["2026-01-01", None], "TIMESTAMP_TZ"),
        ("datetime64[ns, America/Chicago]", ["2026-01-01", None], "TIMESTAMP_TZ"),
        ("int64", [1, 2], "NUMBER(38,0)"),
        ("float64", [1.5, 2.5], "FLOAT"),
        ("bool", [True, False], "BOOLEAN"),
        ("object", ["text", None], "VARCHAR(16777216)"),
    ],
)
def test_pandas_dtype_mapping(connector, dtype, values, expected):
    pd = pytest.importorskip("pandas")
    pandas_dtype = pd.array(values, dtype=dtype).dtype
    assert connector._map_pandas_to_snowflake_type(pandas_dtype) == expected
