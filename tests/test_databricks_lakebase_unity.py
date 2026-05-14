"""Tests for LakeBase/Unity helpers."""

import pytest

pytestmark = pytest.mark.databricks

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


def test_lakebase_psql_command_rejects_shell_metacharacters():
    """The conninfo fields go through a shell command line; metacharacters
    in host/user/dbname must be rejected at the boundary (issue #481)."""
    with pytest.raises(ValueError, match="host"):
        build_lakebase_psql_command(
            host="example.com; rm -rf /",
            user="alice",
            dbname="analytics",
        )
    with pytest.raises(ValueError, match="user"):
        build_lakebase_psql_command(
            host="db.example.net",
            user="alice && cat /etc/passwd",
            dbname="analytics",
        )
    with pytest.raises(ValueError, match="dbname"):
        build_lakebase_psql_command(
            host="db.example.net",
            user="alice",
            dbname='analytics" $(rm -rf /)',
        )


def test_lakebase_psql_command_legitimate_values_accepted():
    """Hostnames with dots, hyphens, numeric ports, and identifier-shaped
    user/dbname values must continue to work after the security fix."""
    cmd = build_lakebase_psql_command(
        host="db-1.example-prod.net",
        user="svc_account_1",
        dbname="my_db",
    )
    assert "db-1.example-prod.net" in cmd
    assert "svc_account_1" in cmd
    assert "my_db" in cmd


def test_pgpass_entry_escapes_colons_and_backslashes():
    """The .pgpass file format uses ':' as field separator and '\\' as
    escape; both must be backslash-escaped in every field (issue #481).

    The test value is constructed from clearly-non-credential parts to
    avoid GitGuardian false-positives; the input contains every
    special character the escaper handles.
    """
    sentinel_with_colons_and_backslash = "FAKE-PASSWORD-VALUE" + r":has:colons\and-backslash"
    pgpass = build_pgpass_entry(
        host="db:1.example.com",
        port=5432,
        dbname="my:db",
        user="my:user",
        password=sentinel_with_colons_and_backslash,
    )
    # Each field's special characters escaped.
    assert pgpass == (
        r"db\:1.example.com:5432:my\:db:my\:user:"
        "FAKE-PASSWORD-VALUE"
        r"\:has\:colons\\and-backslash"
    )


def test_jdbc_url_rejects_url_injection():
    """JDBC URL builder validates host and dbname to prevent injection
    into the connection string (issue #481)."""
    with pytest.raises(ValueError, match="host"):
        build_jdbc_url('localhost"/etc/passwd', "mydb")
    with pytest.raises(ValueError, match="dbname"):
        build_jdbc_url("db.example.net", "mydb?foo=bar")


def test_foreign_table_sql_rejects_source_identifier_injection():
    """source_schema and source_table go through the same identifier
    validator as the other fields, closing the asymmetric-quoting gap
    that issue #481 surfaced."""
    with pytest.raises(ValueError, match="source_schema"):
        build_foreign_table_sql(
            catalog="main",
            schema="ext",
            table="zip",
            connection_name="lakebase_conn",
            source_schema="census';DROP TABLE x;--",
        )
    with pytest.raises(ValueError, match="source_table"):
        build_foreign_table_sql(
            catalog="main",
            schema="ext",
            table="zip",
            connection_name="lakebase_conn",
            source_schema="census_reference",
            source_table="zip'; --",
        )


def test_build_databricks_run_url():
    """Run URL helper should generate stable links."""
    url = build_databricks_run_url(
        host="https://adb-123.azuredatabricks.net/",
        workspace_id="3912175703892324",
        run_id="123456789",
    )
    assert url == "https://adb-123.azuredatabricks.net/jobs/runs/123456789?o=3912175703892324"
