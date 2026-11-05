"""Regression tests for Snowflake types, timestamp loading and session context (#1484).

Covers the pandas dtype mapping, ``write_pandas(use_logical_type=True)``, and
restoring the session database/schema after a per-call ``USE`` override.
The override statements themselves are unchanged pending #1421.
"""

import re
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


def _identifiers(sql):
    return [part.replace('""', '"') for part in re.findall(r'"((?:[^"]|"")*)"', sql)]


class SessionCursor:
    """A cursor that tracks Snowflake's current database and schema."""

    def __init__(self, database="CONFIGURED_DB", schema="CONFIGURED_SCHEMA", fail_on=None):
        self.database = database
        self.schema = schema
        self.fail_on = fail_on
        self.executed = []
        self._row = None

    def execute(self, sql, params=None):
        self.executed.append(sql)
        if self.fail_on and sql.startswith(self.fail_on):
            raise ValueError(f"forced failure on {self.fail_on}")
        if sql == "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()":
            self._row = (self.database, self.schema)
        elif sql.startswith("USE DATABASE"):
            self.database, = _identifiers(sql)
            self.schema = "PUBLIC"
        elif sql.startswith("USE SCHEMA"):
            names = _identifiers(sql)
            if len(names) == 2:
                self.database, self.schema = names
            else:
                self.schema, = names
        elif sql.startswith("SELECT COUNT(*)"):
            self._row = (3,)
        elif "INFORMATION_SCHEMA.TABLES" in sql:
            self._row = (10, 3)

    def fetchone(self):
        return self._row

    def fetchall(self):
        # Serves DESCRIBE TABLE (name, type, nullable) and SHOW TABLES (row[1] is the name).
        return [("amount", "EVENTS", "Y")]


@pytest.fixture
def session(connector, monkeypatch):
    calls = []

    def write_pandas(conn, df, table_name, *, auto_create_table=False, overwrite=False,
                     use_logical_type=None):
        calls.append({"table": table_name, "use_logical_type": use_logical_type})
        return True, 1, len(df), None

    monkeypatch.setattr(sc, "write_pandas", write_pandas, raising=False)
    connector.cursor = SessionCursor()
    return connector, connector.cursor, calls


def _frame():
    pd = pytest.importorskip("pandas")
    return pd.DataFrame({"amount": [1, 2], "at": pd.to_datetime(["2026-01-01", "2026-01-02"], utc=True)})


def _call(connector, method, **override):
    if method == "upload_dataframe":
        return connector.upload_dataframe(_frame(), "EVENTS", **override)
    if method == "get_table_info":
        return connector.get_table_info("EVENTS", **override)
    return connector.list_tables(**override)


METHODS = ["upload_dataframe", "get_table_info", "list_tables"]
OVERRIDES = [
    pytest.param({"database": "OTHER_DB"}, id="database"),
    pytest.param({"schema": "OTHER_SCHEMA"}, id="schema"),
    pytest.param({"database": "OTHER_DB", "schema": "OTHER_SCHEMA"}, id="both"),
]


@pytest.mark.parametrize("override", OVERRIDES)
@pytest.mark.parametrize("method", METHODS)
def test_override_runs_in_requested_context_then_restores(session, method, override):
    connector, cursor, _ = session

    _call(connector, method, **override)

    for name in override.values():
        assert any(sql.startswith("USE ") and f'"{name}"' in sql for sql in cursor.executed)
    assert (cursor.database, cursor.schema) == ("CONFIGURED_DB", "CONFIGURED_SCHEMA")


@pytest.mark.parametrize("method, fail_on", [
    ("upload_dataframe", "CREATE TABLE"),
    ("get_table_info", "DESCRIBE TABLE"),
    ("list_tables", "SHOW TABLES"),
])
def test_override_restores_context_when_the_call_fails(session, method, fail_on):
    connector, cursor, _ = session
    cursor.fail_on = fail_on

    with pytest.raises(RuntimeError):
        _call(connector, method, database="OTHER_DB", schema="OTHER_SCHEMA")

    assert (cursor.database, cursor.schema) == ("CONFIGURED_DB", "CONFIGURED_SCHEMA")


def test_restore_keeps_the_exact_stored_names(session):
    connector, cursor, _ = session
    cursor.database, cursor.schema = 'Mixed"Db', "lower schema"

    connector.list_tables(database="OTHER_DB")

    assert (cursor.database, cursor.schema) == ('Mixed"Db', "lower schema")
    assert cursor.executed[-2:] == [
        'USE DATABASE "Mixed""Db"',
        'USE SCHEMA "Mixed""Db"."lower schema"',
    ]


def test_failed_restore_raises(session):
    connector, cursor, _ = session
    cursor.fail_on = 'USE DATABASE "CONFIGURED_DB"'

    with pytest.raises(RuntimeError, match="restore the Snowflake session context"):
        connector.list_tables(database="OTHER_DB")


@pytest.mark.parametrize("method", METHODS)
def test_no_override_leaves_the_session_alone(session, method):
    connector, cursor, _ = session

    _call(connector, method)

    assert not any(
        sql.startswith("USE ") or sql == "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()"
        for sql in cursor.executed
    )


def test_upload_uses_parquet_logical_types(session):
    connector, _, calls = session

    connector.upload_dataframe(_frame(), "EVENTS")

    assert calls == [{"table": "EVENTS", "use_logical_type": True}]


@pytest.fixture
def old_sdk(connector, monkeypatch):
    calls = []

    def write_pandas(conn, df, table_name, auto_create_table=False, overwrite=False):
        calls.append(table_name)
        return True, 1, len(df), None

    monkeypatch.setattr(sc, "write_pandas", write_pandas, raising=False)
    connector.cursor = SessionCursor()
    return connector, connector.cursor, calls


def test_old_sdk_refuses_datetime_columns_before_any_statement(old_sdk):
    connector, cursor, calls = old_sdk

    with pytest.raises(RuntimeError, match="use_logical_type"):
        connector.upload_dataframe(_frame(), "EVENTS", database="OTHER_DB")

    assert calls == []
    assert cursor.executed == []


def test_old_sdk_uploads_frames_without_datetime_columns(old_sdk):
    pd = pytest.importorskip("pandas")
    connector, _, calls = old_sdk

    connector.upload_dataframe(pd.DataFrame({"amount": [1, 2]}), "EVENTS")

    assert calls == ["EVENTS"]
