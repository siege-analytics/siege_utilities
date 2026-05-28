"""Error-path tests for siege_utilities.schema.migration_runner (SU-4b)."""

import pytest

from siege_utilities.schema.migration_runner import (
    MigrationFile,
    _validate_identifier,
)


class TestValidateIdentifierErrors:
    """Error paths for _validate_identifier."""

    def test_empty_string_raises(self):
        """Empty identifier must raise ValueError."""
        with pytest.raises(ValueError, match="not a valid SQL identifier"):
            _validate_identifier("", "test_label")

    def test_starts_with_number_raises(self):
        """Identifier starting with number must raise ValueError."""
        with pytest.raises(ValueError, match="not a valid SQL identifier"):
            _validate_identifier("1table", "test_label")

    def test_special_characters_raises(self):
        """Identifier with special characters must raise ValueError."""
        with pytest.raises(ValueError, match="not a valid SQL identifier"):
            _validate_identifier("my-table", "test_label")

    def test_sql_injection_raises(self):
        """SQL injection attempt must raise ValueError."""
        with pytest.raises(ValueError, match="not a valid SQL identifier"):
            _validate_identifier("foo; DROP TABLE bar--", "test_label")

    def test_too_long_raises(self):
        """Identifier exceeding 63 bytes must raise ValueError."""
        long_name = "a" * 64
        with pytest.raises(ValueError, match="exceeds PostgreSQL"):
            _validate_identifier(long_name, "test_label")


class TestMigrationFileFromPathErrors:
    """Error paths for MigrationFile.from_path."""

    def test_invalid_filename_raises(self, tmp_path):
        """Non-conforming filename must raise ValueError."""
        bad_file = tmp_path / "not_a_migration.sql"
        bad_file.write_text("SELECT 1;")
        with pytest.raises(ValueError, match="does not match"):
            MigrationFile.from_path(bad_file)

    def test_missing_version_prefix_raises(self, tmp_path):
        """File without V prefix must raise ValueError."""
        bad_file = tmp_path / "001__init.sql"
        bad_file.write_text("SELECT 1;")
        with pytest.raises(ValueError, match="does not match"):
            MigrationFile.from_path(bad_file)


class TestMigrationFileFromPathHappyPath:
    """Sanity checks for MigrationFile.from_path."""

    def test_valid_filename_parses(self, tmp_path):
        """Correctly named migration file parses without error."""
        good_file = tmp_path / "V0001__create_tables.sql"
        good_file.write_text("CREATE TABLE test (id INT);")
        mf = MigrationFile.from_path(good_file)
        assert mf.version == "0001"
        assert mf.description == "create_tables"
        assert "CREATE TABLE" in mf.sql_text
