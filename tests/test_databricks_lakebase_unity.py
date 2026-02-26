"""Tests for LakeBase/Unity helpers."""

from siege_utilities.databricks.artifacts import build_databricks_run_url
from siege_utilities.databricks.lakebase import (
    build_jdbc_url,
    build_lakebase_psql_command,
    build_pgpass_entry,
    parse_conninfo,
)
from siege_utilities.databricks.unity_catalog import (
    build_foreign_table_sql,
    build_schema_and_table_sync_sql,
)


def test_parse_conninfo_and_lakebase_builders():
    """LakeBase helpers should parse/build connection artifacts."""
    parsed = parse_conninfo(
        "host=db.example.net user=alice dbname=analytics port=5432 sslmode=require"
    )
    assert parsed["host"] == "db.example.net"
    assert parsed["user"] == "alice"
    assert parsed["dbname"] == "analytics"

    cmd = build_lakebase_psql_command(
        host="db.example.net",
        user="alice",
        dbname="analytics",
    )
    assert 'host=db.example.net user=alice dbname=analytics' in cmd

    pgpass = build_pgpass_entry(
        host="db.example.net",
        port=5432,
        dbname="analytics",
        user="alice",
        password="secret",
    )
    assert pgpass == "db.example.net:5432:analytics:alice:secret"

    jdbc = build_jdbc_url("db.example.net", "analytics", port=5432)
    assert jdbc == "jdbc:postgresql://db.example.net:5432/analytics"


def test_unity_sql_helpers():
    """Unity SQL helpers should generate schema + foreign table SQL."""
    foreign_sql = build_foreign_table_sql(
        catalog="main",
        schema="ext",
        table="zip",
        connection_name="lakebase_conn",
        source_schema="census_reference",
    )
    assert "CREATE FOREIGN TABLE IF NOT EXISTS `main`.`ext`.`zip`" in foreign_sql
    assert "USING CONNECTION `lakebase_conn`" in foreign_sql
    assert "OPTIONS (table 'census_reference.zip')" in foreign_sql

    statements = build_schema_and_table_sync_sql(
        catalog="main",
        schema="ext",
        connection_name="lakebase_conn",
        source_schema="census_reference",
        tables=["zip", "tract"],
    )
    assert len(statements) == 3
    assert statements[0].startswith("CREATE SCHEMA IF NOT EXISTS")


def test_build_databricks_run_url():
    """Run URL helper should generate stable links."""
    url = build_databricks_run_url(
        host="https://adb-123.azuredatabricks.net/",
        workspace_id="3912175703892324",
        run_id="123456789",
    )
    assert url == "https://adb-123.azuredatabricks.net/jobs/runs/123456789?o=3912175703892324"
