"""Unit tests for Databricks/LakeBase helper utilities."""

from siege_utilities.databricks.artifacts import build_databricks_run_url
from siege_utilities.databricks.lakebase import (
    build_jdbc_url,
    build_lakebase_psql_command,
    build_pgpass_entry,
    parse_conninfo,
)
from siege_utilities.databricks.unity_catalog import build_foreign_table_sql, quote_ident


def test_parse_conninfo_basic() -> None:
    conninfo = (
        "host=instance.database.azuredatabricks.net "
        "user=dheerajchand dbname=databricks_postgres port=5432 sslmode=require"
    )
    parsed = parse_conninfo(conninfo)
    assert parsed["host"] == "instance.database.azuredatabricks.net"
    assert parsed["user"] == "dheerajchand"
    assert parsed["dbname"] == "databricks_postgres"
    assert parsed["port"] == "5432"
    assert parsed["sslmode"] == "require"


def test_build_lakebase_psql_command() -> None:
    cmd = build_lakebase_psql_command(
        host="instance.database.azuredatabricks.net",
        user="dheerajchand",
        dbname="databricks_postgres",
    )
    assert cmd.startswith('psql "host=instance.database.azuredatabricks.net')
    assert "user=dheerajchand" in cmd
    assert "dbname=databricks_postgres" in cmd
    assert "port=5432" in cmd


def test_build_pgpass_entry() -> None:
    entry = build_pgpass_entry(
        host="instance.database.azuredatabricks.net",
        port=5432,
        dbname="databricks_postgres",
        user="dheerajchand",
        password="secret",
    )
    assert (
        entry
        == "instance.database.azuredatabricks.net:5432:databricks_postgres:dheerajchand:secret"
    )


def test_build_jdbc_url() -> None:
    assert (
        build_jdbc_url("instance.database.azuredatabricks.net", "databricks_postgres")
        == "jdbc:postgresql://instance.database.azuredatabricks.net:5432/databricks_postgres"
    )


def test_build_databricks_run_url() -> None:
    url = build_databricks_run_url(
        workspace_host="https://adb-3912175703892324.4.azuredatabricks.net",
        workspace_id=3912175703892324,
        run_id=727532632329590,
    )
    assert (
        url
        == "https://adb-3912175703892324.4.azuredatabricks.net/jobs/runs/727532632329590?o=3912175703892324"
    )


def test_quote_ident_escapes_backticks() -> None:
    assert quote_ident("my`table") == "`my``table`"


def test_build_foreign_table_sql() -> None:
    sql = build_foreign_table_sql(
        catalog="business",
        schema="census_reference",
        table="census_2024_tract",
        connection_name="lakebase_postgis",
        source_schema="census_reference",
    )
    assert "CREATE FOREIGN TABLE IF NOT EXISTS `business`.`census_reference`.`census_2024_tract`" in sql
    assert "USING CONNECTION `lakebase_postgis`" in sql
    assert "OPTIONS (table 'census_reference.census_2024_tract');" in sql
