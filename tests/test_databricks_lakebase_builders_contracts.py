"""Root-import contracts for databricks lakebase/federation/secret builders."""

import pytest

from siege_utilities import build_foreign_table_sql
from siege_utilities import build_jdbc_url
from siege_utilities import build_lakebase_psql_command
from siege_utilities import build_pgpass_entry
from siege_utilities import build_schema_and_table_sync_sql
from siege_utilities import ensure_secret_scope
from siege_utilities.conf import settings


def test_build_jdbc_url_exact_and_default_port():
    assert build_jdbc_url("db.example.com", "mydb", 5432) == (
        "jdbc:postgresql://db.example.com:5432/mydb"
    )
    # Default port comes from settings.LAKEBASE_PORT.
    assert build_jdbc_url("db.example.com", "mydb") == (
        f"jdbc:postgresql://db.example.com:{settings.LAKEBASE_PORT}/mydb"
    )


def test_build_jdbc_url_rejects_injection():
    with pytest.raises(ValueError):
        build_jdbc_url("bad host; drop", "mydb", 5432)
    with pytest.raises(ValueError):
        build_jdbc_url("db.example.com", "bad;dbname", 5432)


def test_build_pgpass_entry_escapes_colon_and_backslash():
    # Plain entry.
    assert build_pgpass_entry("h", 5432, "d", "u", "pw") == "h:5432:d:u:pw"
    # A password containing ':' and '\\' must be escaped per .pgpass format
    # (':' -> '\\:', '\\' -> '\\\\') so it can't be misparsed as more fields.
    assert build_pgpass_entry("h", 5432, "d", "u", r"p:a\b") == (
        r"h:5432:d:u:p\:a\\b"
    )


def test_build_lakebase_psql_command_exact_and_defaults():
    expected = (
        "psql 'host=db.example.com user=usr dbname=mydb "
        "port=5432 sslmode=require'"
    )
    assert build_lakebase_psql_command(
        "db.example.com", "usr", "mydb", 5432, "require"
    ) == expected
    # Defaults pulled from settings.
    default_cmd = build_lakebase_psql_command("db.example.com", "usr", "mydb")
    assert (
        f"port={settings.LAKEBASE_PORT} sslmode={settings.LAKEBASE_SSLMODE}"
        in default_cmd
    )
    assert default_cmd.startswith("psql '")


def test_build_lakebase_psql_command_rejects_bad_fields():
    with pytest.raises(ValueError):
        build_lakebase_psql_command(
            "db.example.com", "usr", "mydb", sslmode="bogus"
        )
    with pytest.raises(ValueError):
        build_lakebase_psql_command("bad host", "usr", "mydb", 5432, "require")


def test_build_foreign_table_sql_exact_and_source_default():
    assert build_foreign_table_sql("cat", "sch", "tbl", "conn", "srcsch") == (
        "CREATE FOREIGN TABLE IF NOT EXISTS `cat`.`sch`.`tbl`\n"
        "USING CONNECTION `conn`\n"
        "OPTIONS (table 'srcsch.tbl');"
    )
    # Explicit source_table overrides the table-name default in the literal.
    assert build_foreign_table_sql(
        "cat", "sch", "tbl", "conn", "srcsch", source_table="othertbl"
    ) == (
        "CREATE FOREIGN TABLE IF NOT EXISTS `cat`.`sch`.`tbl`\n"
        "USING CONNECTION `conn`\n"
        "OPTIONS (table 'srcsch.othertbl');"
    )


def test_build_foreign_table_sql_rejects_bad_identifier():
    with pytest.raises(ValueError):
        build_foreign_table_sql("cat", "sch", "bad;tbl", "conn", "srcsch")


def test_build_schema_and_table_sync_sql_composes_schema_then_tables():
    stmts = build_schema_and_table_sync_sql(
        "cat", "sch", "conn", "srcsch", ["t1", "t2"]
    )
    assert stmts[0] == "CREATE SCHEMA IF NOT EXISTS `cat`.`sch`;"
    assert len(stmts) == 3
    # Each subsequent statement matches the single-table builder exactly.
    assert stmts[1] == build_foreign_table_sql(
        "cat", "sch", "t1", "conn", "srcsch", source_table="t1"
    )
    assert stmts[2] == build_foreign_table_sql(
        "cat", "sch", "t2", "conn", "srcsch", source_table="t2"
    )


class _FakeScope:
    def __init__(self, name):
        self.name = name


class _FakeSecrets:
    def __init__(self, existing):
        self._existing = existing
        self.created = []

    def list_scopes(self):
        return [_FakeScope(n) for n in self._existing]

    def create_scope(self, scope):
        self.created.append(scope)


class _FakeWorkspaceClient:
    def __init__(self, existing):
        self.secrets = _FakeSecrets(existing)


def test_ensure_secret_scope_reuses_existing_without_creating():
    client = _FakeWorkspaceClient(existing=["analytics"])

    assert ensure_secret_scope("analytics", client) == "analytics"
    assert client.secrets.created == []


def test_ensure_secret_scope_creates_when_absent():
    client = _FakeWorkspaceClient(existing=["other"])

    assert ensure_secret_scope("analytics", client) == "analytics"
    assert client.secrets.created == ["analytics"]
