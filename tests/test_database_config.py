"""Tests for database configuration security fixes."""

import json

import pytest

from siege_utilities.config.databases import (
    _is_env_ref,
    _resolve_env_var,
    create_database_config,
    load_database_config,
    save_database_config,
)


class TestEnvVarHelpers:
    def test_is_env_ref_bare(self):
        assert _is_env_ref("$MY_VAR")

    def test_is_env_ref_braced(self):
        assert _is_env_ref("${MY_VAR}")

    def test_is_env_ref_literal(self):
        assert not _is_env_ref("plaintext_password")

    def test_resolve_env_var(self, monkeypatch):
        monkeypatch.setenv("TEST_PW", "s3cret")
        assert _resolve_env_var("$TEST_PW") == "s3cret"
        assert _resolve_env_var("${TEST_PW}") == "s3cret"

    def test_resolve_env_var_missing(self, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        with pytest.raises(EnvironmentError, match="NONEXISTENT_VAR"):
            _resolve_env_var("$NONEXISTENT_VAR")

    def test_resolve_literal_passthrough(self):
        assert _resolve_env_var("literal") == "literal"


class TestConnectionStringInjection:
    def test_special_chars_in_password(self):
        config = create_database_config(
            name="test",
            connection_type="postgres",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="p@ss:w/rd#?",
        )
        jdbc = config["jdbc_url"]
        assert "p@ss" not in jdbc
        assert "localhost" in jdbc

    def test_host_preserved_and_database_path_encoded(self):
        config = create_database_config(
            name="test",
            connection_type="postgres",
            host="db.example.com",
            port=5432,
            database="test db",
            username="user",
            password="pass",
        )
        assert config["jdbc_url"] == "jdbc:postgresql://db.example.com:5432/test%20db"

    @pytest.mark.parametrize("host", [
        "evil.example/x?socketFactory=org.example.Evil&socketFactoryArg=http://a/b#",
        "db.example.com:5432/other?sslmode=disable&",
        "user:pw@db.example.com",
        "db.example.com ; x",
    ])
    def test_injection_host_rejected(self, host):
        # A host is validated, not encoded, so URL-structural characters cannot
        # smuggle extra JDBC components (e.g. a socketFactory or a competing
        # sslmode) into the connection URL.
        with pytest.raises(ValueError):
            create_database_config(
                name="t", connection_type="postgres", host=host,
                port=5432, database="db", username="u", password="p",
            )


class TestPlaintextCredentialSave:
    def test_plaintext_password_replaced_with_env_ref(self, tmp_path):
        config = create_database_config(
            name="mydb",
            connection_type="postgres",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="secret123",
        )
        save_database_config(config, config_directory=str(tmp_path))

        saved_file = tmp_path / "database_mydb.json"
        saved = json.loads(saved_file.read_text())
        assert saved["password"] == "${DB_MYDB_PASSWORD}"
        assert "secret123" not in saved_file.read_text()

    def test_env_ref_password_preserved(self, tmp_path):
        config = create_database_config(
            name="mydb",
            connection_type="postgres",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="${MY_SECRET}",
        )
        save_database_config(config, config_directory=str(tmp_path))

        saved = json.loads((tmp_path / "database_mydb.json").read_text())
        assert saved["password"] == "${MY_SECRET}"

    def test_load_resolves_env_var(self, tmp_path, monkeypatch):
        config = create_database_config(
            name="mydb",
            connection_type="postgres",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="secret123",
        )
        save_database_config(config, config_directory=str(tmp_path))

        monkeypatch.setenv("DB_MYDB_PASSWORD", "resolved_secret")
        loaded = load_database_config("mydb", config_directory=str(tmp_path))
        assert loaded["password"] == "resolved_secret"
