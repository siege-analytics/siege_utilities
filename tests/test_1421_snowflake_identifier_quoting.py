"""Regression coverage for #1421 using connector SQL and a mocked client."""

from pathlib import Path
from unittest.mock import MagicMock, call

import pandas as pd
import pytest

from siege_utilities.analytics import snowflake_connector as sc


@pytest.fixture
def connector(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(sc, "SNOWFLAKE_AVAILABLE", True)
    monkeypatch.setattr(sc, "snowflake", client, raising=False)
    monkeypatch.setattr(
        sc, "write_pandas", MagicMock(return_value=(True, 1, 1, None)), raising=False
    )
    conn = sc.SnowflakeConnector(
        account="test_account", user="test_user", database="analytics", schema="public"
    )
    conn.connect()
    conn.cursor.fetchall.return_value = [("AMOUNT", "NUMBER", "Y")]
    conn.cursor.fetchone.side_effect = [(1,), (8, 1)]
    return conn


def test_lowercase_database_resolves_against_uppercase_object(connector):
    """The ticket's analytics database must address ANALYTICS.PUBLIC.EVENTS."""
    result = connector.get_table_info("events", database="analytics", schema="public")

    connector.cursor.execute.assert_has_calls([
        call("USE DATABASE ANALYTICS"),
        call("USE SCHEMA PUBLIC"),
        call("DESCRIBE TABLE ANALYTICS.PUBLIC.EVENTS"),
        call("SELECT COUNT(*) FROM ANALYTICS.PUBLIC.EVENTS"),
    ])
    assert connector.cursor.execute.call_args.args[1] == ("EVENTS",)
    assert result["row_count"] == 1
    assert result["bytes"] == 8


@pytest.mark.parametrize("use_defaults", [True, False])
def test_mixed_case_and_special_names_keep_individual_quotes(connector, use_defaults):
    connector.schema = "My Schema"
    kwargs = {} if use_defaults else {"database": "analytics", "schema": "My Schema"}

    connector.get_table_info("weirdName", **kwargs)

    connector.cursor.execute.assert_any_call(
        'DESCRIBE TABLE ANALYTICS."My Schema"."weirdName"'
    )
    connector.cursor.execute.assert_any_call(
        'SELECT COUNT(*) FROM ANALYTICS."My Schema"."weirdName"'
    )
    assert connector.cursor.execute.call_args.args[1] == ("weirdName",)


@pytest.mark.parametrize("method", ["upload_dataframe", "list_tables", "get_table_info"])
@pytest.mark.parametrize(
    ("database", "schema", "expected_database", "expected_schema"),
    [
        ("analytics", "public", "ANALYTICS", "PUBLIC"),
        ("Analytics", "My Schema", '"Analytics"', '"My Schema"'),
        ("analytics-prod", "public", '"analytics-prod"', "PUBLIC"),
    ],
)
def test_context_selection_uses_same_rule(
    connector, method, database, schema, expected_database, expected_schema
):
    args = {
        "upload_dataframe": (pd.DataFrame({"amount": [1]}), "events"),
        "list_tables": (),
        "get_table_info": ("events",),
    }[method]
    getattr(connector, method)(*args, database=database, schema=schema)

    connector.cursor.execute.assert_any_call(f"USE DATABASE {expected_database}")
    connector.cursor.execute.assert_any_call(f"USE SCHEMA {expected_schema}")


@pytest.mark.parametrize("auto_create", [True, False])
def test_upload_normalizes_plain_table_and_columns_without_changing_input(connector, auto_create):
    frame = pd.DataFrame({"amount": [1], "EVENT_ID": [2]})

    connector.upload_dataframe(frame, "events", auto_create_table=auto_create, overwrite=True)

    if auto_create:
        connector.cursor.execute.assert_any_call("DROP TABLE IF EXISTS EVENTS")
        connector.cursor.execute.assert_any_call(
            "CREATE TABLE IF NOT EXISTS EVENTS (AMOUNT NUMBER(38,0), EVENT_ID NUMBER(38,0))"
        )
    upload = sc.write_pandas.call_args
    assert upload.args[2] == "EVENTS"
    assert list(upload.args[1].columns) == ["AMOUNT", "EVENT_ID"]
    assert upload.kwargs["quote_identifiers"] is False
    assert list(frame.columns) == ["amount", "EVENT_ID"]
    assert upload.args[1].iloc[0].tolist() == [1, 2]


@pytest.mark.parametrize("table", ["events", "weirdName"])
def test_upload_mixed_columns_match_ddl_and_preserve_input(connector, table):
    frame = pd.DataFrame({"amount": [1], "eventId": [2], "Event Name": ["launch"]})

    connector.upload_dataframe(frame, table)

    sql_table = "EVENTS" if table == "events" else '"weirdName"'
    connector.cursor.execute.assert_any_call(
        f'CREATE TABLE IF NOT EXISTS {sql_table} '
        '(AMOUNT NUMBER(38,0), "eventId" NUMBER(38,0), "Event Name" VARCHAR(16777216))'
    )
    upload = sc.write_pandas.call_args
    assert upload.args[2] == ("EVENTS" if table == "events" else table)
    assert list(upload.args[1].columns) == ["AMOUNT", "eventId", "Event Name"]
    assert upload.kwargs["quote_identifiers"] is True
    assert list(frame.columns) == ["amount", "eventId", "Event Name"]


@pytest.mark.parametrize(
    ("name", "sql_name", "stored_name"),
    [
        ("EVENTS", "EVENTS", "EVENTS"),
        ("event$1", "EVENT$1", "EVENT$1"),
        ("event-log", '"event-log"', "event-log"),
        ('event"name', '"event""name"', 'event"name'),
        ("event.name", '"event.name"', "event.name"),
        ("123events", '"123events"', "123events"),
        ("événements", '"événements"', "événements"),
        ('"events"', '"events"', "events"),
        ("select", '"select"', "select"),
        ("CURRENT_DATE", '"CURRENT_DATE"', "CURRENT_DATE"),
    ],
)
def test_table_names_are_escaped_as_one_identifier(connector, name, sql_name, stored_name):
    connector.get_table_info(name)

    connector.cursor.execute.assert_any_call(f"DESCRIBE TABLE ANALYTICS.PUBLIC.{sql_name}")
    assert connector.cursor.execute.call_args.args[1] == (stored_name,)


@pytest.mark.parametrize("name", ["", "bad; DROP TABLE users;--", "bad\x00name", "bad\nname"])
def test_invalid_table_name_fails_before_sql_or_upload(connector, name):
    with pytest.raises(ValueError):
        connector.upload_dataframe(pd.DataFrame({"amount": [1]}), name, overwrite=True)

    connector.cursor.execute.assert_not_called()
    sc.write_pandas.assert_not_called()


def test_column_collision_after_folding_fails_before_overwrite(connector):
    with pytest.raises(ValueError, match="duplicate"):
        connector.upload_dataframe(pd.DataFrame({"amount": [1], "AMOUNT": [2]}), "events", overwrite=True)

    connector.cursor.execute.assert_not_called()
    sc.write_pandas.assert_not_called()


def test_connection_context_uses_same_identifier_rule(connector):
    connector.warehouse = "compute_wh"
    connector.role = "reportReader"
    connector.schema = "My Schema"
    connector.connect()

    params = sc.snowflake.connector.connect.call_args.kwargs
    assert params["database"] == "ANALYTICS"
    assert params["schema"] == '"My Schema"'
    assert params["warehouse"] == "COMPUTE_WH"
    assert params["role"] == '"reportReader"'


@pytest.mark.parametrize(
    ("table", "columns", "expected_table", "expected_columns"),
    [
        ("events", ["amount", "event_id"], "EVENTS", "AMOUNT,EVENT_ID"),
        ("events", ["amount", "eventId"], '"EVENTS"', '"AMOUNT","eventId"'),
        ('event"name', ["amount", 'event"Id'], '"event""name"', '"AMOUNT","event""Id"'),
        ('"events"', ['"amount"'], '"events"', '"amount"'),
    ],
)
def test_real_writer_builds_copy_for_matching_objects(
    connector, monkeypatch, table, columns, expected_table, expected_columns
):
    """Exercise SDK COPY generation against a fake connection, without Snowflake."""
    pandas_tools = pytest.importorskip("snowflake.connector.pandas_tools")
    # SQL generation is under test; keep serialization independent of local
    # Arrow filesystem plugins. The SDK removes this staged file afterward.
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, **kwargs: Path(path).touch())
    monkeypatch.setattr(sc, "write_pandas", pandas_tools.write_pandas)
    connector.connection._session_parameters = {}
    connector.cursor.execute.return_value = connector.cursor
    connector.cursor.fetchall.return_value = [("chunk.parquet", "LOADED", 1, 1)]
    frame = pd.DataFrame([[1] * len(columns)], columns=columns)

    connector.upload_dataframe(frame, table, auto_create_table=False)

    copy_call = next(
        item for item in connector.cursor.execute.call_args_list
        if item.args[0].startswith("COPY INTO")
    )
    assert copy_call.kwargs["params"][0] == expected_table
    assert f"({expected_columns})" in copy_call.args[0]
    assert list(frame.columns) == columns
