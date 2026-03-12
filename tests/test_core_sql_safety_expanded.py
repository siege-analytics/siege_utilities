"""Expanded tests for siege_utilities.core.sql_safety module."""

import pytest
from siege_utilities.core.sql_safety import validate_sql_identifier


class TestValidateSqlIdentifier:
    """Tests for validate_sql_identifier."""

    def test_valid_identifier(self):
        assert validate_sql_identifier("electronic_silver") == "electronic_silver"

    def test_valid_with_numbers(self):
        assert validate_sql_identifier("table_123") == "table_123"

    def test_valid_underscore_start(self):
        assert validate_sql_identifier("_private") == "_private"

    def test_valid_single_letter(self):
        assert validate_sql_identifier("x") == "x"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_sql_identifier("")

    def test_sql_injection_raises(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("silver; DROP TABLE --")

    def test_spaces_raises(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("my table")

    def test_hyphen_raises(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("my-table")

    def test_starts_with_number_raises(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("123table")

    def test_special_chars_raise(self):
        for char in ["@", "#", "$", "%", "!", "'", '"', ";", "(", ")"]:
            with pytest.raises(ValueError):
                validate_sql_identifier(f"table{char}")

    def test_custom_label_in_error(self):
        with pytest.raises(ValueError, match="database"):
            validate_sql_identifier("bad name", label="database")

    def test_default_label(self):
        with pytest.raises(ValueError, match="identifier"):
            validate_sql_identifier("bad name")

    def test_valid_uppercase(self):
        assert validate_sql_identifier("MY_TABLE") == "MY_TABLE"

    def test_valid_mixed_case(self):
        assert validate_sql_identifier("MyTable") == "MyTable"
