"""
Tests for siege_utilities.core.sql_safety — SQL identifier validation.

Ensures SQL injection via database/table names is prevented.
Ported from pure-translation and expanded with additional edge cases.
"""

import pytest

from siege_utilities.core.sql_safety import validate_sql_identifier


class TestValidateIdentifier:
    """Test validate_sql_identifier with valid inputs."""

    def test_valid_simple_name(self):
        assert validate_sql_identifier("silver", "database") == "silver"

    def test_valid_underscored_name(self):
        assert validate_sql_identifier("electronic_silver", "database") == "electronic_silver"

    def test_valid_name_with_digits(self):
        assert validate_sql_identifier("sa11ai", "table") == "sa11ai"

    def test_valid_leading_underscore(self):
        assert validate_sql_identifier("_internal", "table") == "_internal"

    def test_valid_uppercase(self):
        assert validate_sql_identifier("GOLD", "database") == "GOLD"

    def test_valid_mixed_case(self):
        assert validate_sql_identifier("MyTable_v2", "table") == "MyTable_v2"

    def test_valid_single_char(self):
        assert validate_sql_identifier("x", "column") == "x"

    def test_valid_single_underscore(self):
        assert validate_sql_identifier("_", "column") == "_"

    def test_valid_long_name(self):
        long_name = "a" * 128
        assert validate_sql_identifier(long_name, "table") == long_name

    def test_returns_input_unchanged(self):
        """Verify the function returns the exact input string."""
        name = "electronic_bronze"
        result = validate_sql_identifier(name, "database")
        assert result is name  # same object, not just equal


class TestRejectsInvalidIdentifiers:
    """Test validate_sql_identifier rejects unsafe inputs."""

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_sql_identifier("", "database")

    def test_rejects_space(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("my database", "database")

    def test_rejects_semicolon_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("silver; DROP TABLE --", "database")

    def test_rejects_single_quotes(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("silver'", "database")

    def test_rejects_double_quotes(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier('silver"', "database")

    def test_rejects_dash(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("my-table", "table")

    def test_rejects_dot(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("db.table", "identifier")

    def test_rejects_leading_digit(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("1table", "table")

    def test_rejects_parentheses(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("db()", "database")

    def test_rejects_backtick(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("`table`", "table")

    def test_rejects_at_sign(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("@@global", "variable")

    def test_rejects_equals(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("name=value", "identifier")

    def test_rejects_newline(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("table\nname", "table")

    def test_rejects_tab(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("table\tname", "table")

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("table\x00name", "table")

    def test_rejects_slash(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("path/table", "table")

    def test_rejects_backslash(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("path\\table", "table")

    def test_rejects_comment_syntax(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("table -- comment", "table")

    def test_rejects_union_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL"):
            validate_sql_identifier("x UNION SELECT *", "table")


class TestErrorMessages:
    """Test that error messages are informative and include the label."""

    def test_label_in_empty_error(self):
        with pytest.raises(ValueError, match="SQL database"):
            validate_sql_identifier("", "database")

    def test_label_in_invalid_error(self):
        with pytest.raises(ValueError, match="SQL table"):
            validate_sql_identifier("bad name", "table")

    def test_default_label(self):
        with pytest.raises(ValueError, match="SQL identifier"):
            validate_sql_identifier("", )

    def test_invalid_name_shown_in_error(self):
        with pytest.raises(ValueError, match="bad-name"):
            validate_sql_identifier("bad-name", "table")

    def test_regex_pattern_shown_in_error(self):
        with pytest.raises(ValueError, match=r"\[a-zA-Z_\]"):
            validate_sql_identifier("bad-name", "table")


class TestAutoDiscovery:
    """Test that sql_safety is accessible via core package auto-discovery."""

    def test_importable_from_core(self):
        from siege_utilities.core import validate_sql_identifier as fn
        assert callable(fn)
        assert fn("test_table", "table") == "test_table"

    def test_in_core_all(self):
        import siege_utilities.core as core
        assert "validate_sql_identifier" in core.__all__
