"""Error-path tests for siege_utilities.political.readers (SU-4b)."""

import pytest

from siege_utilities.political.readers import _quote_ident


class TestQuoteIdentErrors:
    """Error paths for _quote_ident — unsafe identifier rejection."""

    def test_empty_string_raises(self):
        """Empty identifier must raise ValueError."""
        with pytest.raises(ValueError, match="unsafe identifier"):
            _quote_ident("")

    def test_dot_in_name_raises(self):
        """Dotted name (schema.table) must raise ValueError."""
        with pytest.raises(ValueError, match="unsafe identifier"):
            _quote_ident("schema.table")

    def test_space_in_name_raises(self):
        """Name with spaces must raise ValueError."""
        with pytest.raises(ValueError, match="unsafe identifier"):
            _quote_ident("my table")

    def test_semicolon_injection_raises(self):
        """SQL injection attempt with semicolon must raise ValueError."""
        with pytest.raises(ValueError, match="unsafe identifier"):
            _quote_ident("users; DROP TABLE--")

    def test_double_quote_raises(self):
        """Double-quote in name must raise ValueError."""
        with pytest.raises(ValueError, match="unsafe identifier"):
            _quote_ident('table"name')

    def test_hyphen_raises(self):
        """Hyphenated name must raise ValueError."""
        with pytest.raises(ValueError, match="unsafe identifier"):
            _quote_ident("my-table")


class TestQuoteIdentHappyPath:
    """Sanity checks for _quote_ident."""

    def test_simple_name(self):
        """Simple alphanumeric name is quoted."""
        assert _quote_ident("seats") == '"seats"'

    def test_underscore_allowed(self):
        """Underscored name is valid."""
        assert _quote_ident("election_results") == '"election_results"'

    def test_numeric_suffix(self):
        """Name with numbers is valid."""
        assert _quote_ident("table2024") == '"table2024"'
