"""Regression tests for pandas type mapping and temporary session context (#1484)."""

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
    conn.cursor = RecordingCursor()
    conn.connection = Mock()
    conn.connection.cursor.return_value = conn.cursor
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


class RecordingCursor:
    """Keep session state, including USE DATABASE resetting the current schema."""

    def __init__(self):
        self.database = "ORIGINAL_DB"
        self.schema = "ORIGINAL_SCHEMA"
        self.executed = []
        self.operation_contexts = []
        self.last_sql = ""
        self.fail_sql = None

    def execute(self, sql, params=None):
        self.executed.append(sql)
        self.last_sql = sql
        if sql == self.fail_sql:
            raise ValueError("operation failed")
        if sql.startswith('USE DATABASE "'):
            self.database = sql[len('USE DATABASE "'):-1].replace('""', '"')
            self.schema = "PUBLIC"
        elif sql.startswith('USE SCHEMA "'):
            self.schema = sql[len('USE SCHEMA "'):-1].replace('""', '"')
        elif not sql.startswith("SELECT CURRENT_DATABASE()"):
            self.operation_contexts.append((self.database, self.schema))
        return self

    def fetchone(self):
        if self.last_sql == "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()":
            return self.database, self.schema
        if self.last_sql.startswith("SELECT COUNT(*)"):
            return (1,)
        return (128, 1)

    def fetchall(self):
        if self.last_sql == "SHOW TABLES":
            return [(None, "events")]
        return [("amount", "NUMBER(38,0)", "Y")]


@pytest.fixture(params=["upload_dataframe", "get_table_info", "list_tables"])
def operation(request, connector, monkeypatch):
    name = request.param

    def write_pandas(connection, df, table_name, **kwargs):
        connector.cursor.execute("WRITE PANDAS")
        return True, 1, len(df), None

    monkeypatch.setattr(sc, "write_pandas", write_pandas, raising=False)

    def call(**kwargs):
        if name == "upload_dataframe":
            pd = pytest.importorskip("pandas")
            connector.upload_dataframe(
                pd.DataFrame({"amount": pd.array([1, None], dtype="Int64")}),
                "events", **kwargs,
            )
        elif name == "get_table_info":
            result = connector.get_table_info("events", **kwargs)
            assert result["row_count"] == 1
            assert result["bytes"] == 128
        else:
            assert connector.list_tables(**kwargs) == ["events"]

    call.failing_sql = {
        "upload_dataframe": "WRITE PANDAS",
        "get_table_info": 'DESCRIBE TABLE "events"',
        "list_tables": "SHOW TABLES",
    }[name]
    return call


@pytest.mark.parametrize(
    "overrides, expected_context",
    [
        ({"database": "TARGET_DB", "schema": "TARGET_SCHEMA"}, ("TARGET_DB", "TARGET_SCHEMA")),
        ({"database": "TARGET_DB"}, ("TARGET_DB", "PUBLIC")),
        ({"schema": "TARGET_SCHEMA"}, ("ORIGINAL_DB", "TARGET_SCHEMA")),
    ],
)
@pytest.mark.parametrize("fails", [False, True], ids=["success", "failure"])
def test_operation_restores_session_context(connector, operation, overrides, expected_context, fails):
    cursor = connector.cursor
    if fails:
        cursor.fail_sql = operation.failing_sql
        with pytest.raises(RuntimeError, match="operation failed"):
            operation(**overrides)
    else:
        operation(**overrides)
        assert cursor.operation_contexts
        assert set(cursor.operation_contexts) == {expected_context}

    assert (cursor.database, cursor.schema) == ("ORIGINAL_DB", "ORIGINAL_SCHEMA")
    assert 'USE SCHEMA "ORIGINAL_SCHEMA"' in cursor.executed
    if "database" in overrides:
        assert cursor.executed[-2:] == [
            'USE DATABASE "ORIGINAL_DB"', 'USE SCHEMA "ORIGINAL_SCHEMA"',
        ]

    # A subsequent call with no overrides must see the original session.
    cursor.fail_sql = None
    cursor.operation_contexts.clear()
    operation()
    assert set(cursor.operation_contexts) == {("ORIGINAL_DB", "ORIGINAL_SCHEMA")}


def test_failed_schema_switch_restores_database_and_schema(connector, operation):
    connector.cursor.fail_sql = 'USE SCHEMA "TARGET_SCHEMA"'
    with pytest.raises(RuntimeError, match="operation failed"):
        operation(database="TARGET_DB", schema="TARGET_SCHEMA")
    assert (connector.cursor.database, connector.cursor.schema) == ("ORIGINAL_DB", "ORIGINAL_SCHEMA")


def test_invalid_schema_does_not_leak_database(connector, operation):
    with pytest.raises(RuntimeError):
        operation(database="TARGET_DB", schema="invalid;schema")
    assert (connector.cursor.database, connector.cursor.schema) == ("ORIGINAL_DB", "ORIGINAL_SCHEMA")


def test_restore_preserves_quoted_session_identifiers(connector, operation):
    connector.cursor.database = 'Original "Database"'
    connector.cursor.schema = 'Original "Schema"'
    operation(database="TARGET_DB", schema="TARGET_SCHEMA")
    assert (connector.cursor.database, connector.cursor.schema) == ('Original "Database"', 'Original "Schema"')


def test_no_override_does_not_switch_context(connector, operation):
    operation()
    assert not any(sql.startswith(("USE ", "SELECT CURRENT_DATABASE()")) for sql in connector.cursor.executed)


@pytest.mark.parametrize("original_database", [None, "ORIGINAL_DB"])
def test_unset_context_is_rejected_before_switching(connector, operation, original_database):
    connector.cursor.database = original_database
    connector.cursor.schema = None
    with pytest.raises(RuntimeError, match="current database and schema"):
        operation(database="TARGET_DB", schema="TARGET_SCHEMA")
    assert (connector.cursor.database, connector.cursor.schema) == (original_database, None)
    assert not any(sql.startswith("USE ") for sql in connector.cursor.executed)
