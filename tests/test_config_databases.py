"""Error-path tests for siege_utilities.config.databases (SU-4b)."""

import json

import pytest

from siege_utilities.config.databases import (
    load_database_config,
    get_spark_database_options,
    list_database_configs,
)


class TestLoadDatabaseConfigErrors:
    """Error paths for load_database_config."""

    def test_missing_file_returns_none(self, tmp_path):
        """Nonexistent config file returns None."""
        result = load_database_config("nonexistent_db", config_directory=str(tmp_path))
        assert result is None

    def test_corrupt_json_returns_none(self, tmp_path):
        """Malformed JSON config file returns None."""
        bad_file = tmp_path / "database_corrupt.json"
        bad_file.write_text("{invalid json content!!!")
        result = load_database_config("corrupt", config_directory=str(tmp_path))
        assert result is None

    def test_valid_json_loads_successfully(self, tmp_path):
        """Valid JSON config file loads correctly."""
        config = {"name": "test_db", "connection_type": "postgres",
                  "host": "localhost", "port": 5432, "database": "testdb",
                  "username": "user", "password": "pass",
                  "jdbc_url": "jdbc:postgresql://localhost:5432/testdb",
                  "jdbc_driver": "org.postgresql.Driver",
                  "connection_params": {}, "spark_options": {}}
        config_file = tmp_path / "database_test_db.json"
        config_file.write_text(json.dumps(config))
        result = load_database_config("test_db", config_directory=str(tmp_path))
        assert result is not None
        assert result["name"] == "test_db"


class TestGetSparkDatabaseOptionsErrors:
    """Error paths for get_spark_database_options."""

    def test_missing_config_returns_none(self, tmp_path):
        """Missing database config returns None for Spark options."""
        result = get_spark_database_options("nonexistent", config_directory=str(tmp_path))
        assert result is None


class TestListDatabaseConfigsErrors:
    """Error paths for list_database_configs."""

    def test_nonexistent_directory_returns_empty(self, tmp_path):
        """Nonexistent config directory returns empty list."""
        bogus = tmp_path / "no_such_dir"
        result = list_database_configs(config_directory=str(bogus))
        assert result == []

    def test_corrupt_file_skipped(self, tmp_path):
        """Corrupt config files are skipped without raising."""
        bad_file = tmp_path / "database_bad.json"
        bad_file.write_text("not valid json!!!")
        result = list_database_configs(config_directory=str(tmp_path))
        assert result == []
