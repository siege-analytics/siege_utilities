"""Tests for SQL string literal escaping, including MySQL backslash handling."""

import pytest

from siege_utilities.core.sql_safety import escape_sql_string_literal


class TestStandardDialect:
    def test_single_quotes_doubled(self):
        assert escape_sql_string_literal("it's") == "it''s"

    def test_backslash_unchanged(self):
        assert escape_sql_string_literal("C:\\path") == "C:\\path"

    def test_empty_string(self):
        assert escape_sql_string_literal("") == ""

    def test_nul_rejected(self):
        with pytest.raises(ValueError, match="NUL"):
            escape_sql_string_literal("ab\x00cd")

    def test_non_string_rejected(self):
        with pytest.raises(TypeError):
            escape_sql_string_literal(42)


class TestMySQLDialect:
    def test_backslash_doubled(self):
        assert escape_sql_string_literal("C:\\path", dialect="mysql") == "C:\\\\path"

    def test_single_quote_backslash_escaped(self):
        assert escape_sql_string_literal("it's", dialect="mysql") == "it\\'s"

    def test_combined(self):
        result = escape_sql_string_literal("a\\b'c", dialect="mysql")
        assert result == "a\\\\b\\'c"

    def test_nul_rejected(self):
        with pytest.raises(ValueError, match="NUL"):
            escape_sql_string_literal("\x00", dialect="mysql")


class TestUnknownDialect:
    def test_raises(self):
        with pytest.raises(ValueError, match="unknown dialect"):
            escape_sql_string_literal("test", dialect="oracle")
