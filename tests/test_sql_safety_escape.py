"""Tests for dialect-specific SQL string literal escaping."""

import pytest

from siege_utilities.core.sql_safety import escape_sql_string_literal


class TestStandardDialect:
    def test_single_quotes_doubled(self):
        assert escape_sql_string_literal("it's") == "it''s"

    def test_backslash_unchanged(self):
        assert escape_sql_string_literal("C:\\path") == "C:\\path"

    @pytest.mark.parametrize("dialect", ["standard", "STANDARD"])
    def test_postgres_backslash_quote(self, dialect):
        assert escape_sql_string_literal(r"a\b'c", dialect=dialect) == r"a\b''c"

    def test_empty_string(self):
        assert escape_sql_string_literal("") == ""

    def test_nul_rejected(self):
        with pytest.raises(ValueError, match="NUL"):
            escape_sql_string_literal("ab\x00cd")

    def test_non_string_rejected(self):
        with pytest.raises(TypeError):
            escape_sql_string_literal(42)


@pytest.mark.parametrize("dialect", ["mysql", "spark", "hive", "databricks", "snowflake", "SpArK"])
class TestBackslashDialects:
    def test_backslash_doubled(self, dialect):
        assert escape_sql_string_literal("C:\\path", dialect=dialect) == "C:\\\\path"

    def test_single_quote_backslash_escaped(self, dialect):
        assert escape_sql_string_literal("it's", dialect=dialect) == "it\\'s"

    def test_combined(self, dialect):
        result = escape_sql_string_literal("a\\b'c", dialect=dialect)
        assert result == "a\\\\b\\'c"

    def test_nul_rejected(self, dialect):
        with pytest.raises(ValueError, match="NUL"):
            escape_sql_string_literal("\x00", dialect=dialect)

    def test_non_string_rejected(self, dialect):
        with pytest.raises(TypeError, match="expected str, got int"):
            escape_sql_string_literal(42, dialect=dialect)


class TestUnknownDialect:
    def test_raises(self):
        with pytest.raises(ValueError, match="unknown dialect"):
            escape_sql_string_literal("test", dialect="oracle")
