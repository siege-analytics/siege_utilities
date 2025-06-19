# ================================================================
# FILE: test_string_utils.py
# ================================================================
"""
Tests for siege_utilities.core.string_utils module.
These tests thoroughly check the quote removal function for edge cases.
"""
import pytest
import siege_utilities


class TestStringUtils:
    """Test string utility functions."""

    @pytest.mark.parametrize("input_str,expected", [
        # Basic quote removal
        ('"hello world"', 'hello world'),
        ("'single quotes'", 'single quotes'),

        # With whitespace
        ('  "  spaced  "  ', 'spaced'),
        ('   "hello"   ', 'hello'),
        ("  'world'  ", 'world'),

        # No quotes
        ("no quotes", "no quotes"),
        ("  no quotes  ", "no quotes"),

        # Empty strings
        ('""', ''),
        ("''", ''),
        ("   ", ''),

        # Mismatched quotes
        ('"mismatched\'', '"mismatched\''),
        ('\'mismatched"', '\'mismatched"'),

        # Special cases from the original code
        (None, ''),
        ('', ''),
        ('\n', '\n'),

        # Nested quotes
        ('"nested "quotes" here"', 'nested "quotes" here'),
        ("'nested 'quotes' here'", "nested 'quotes' here"),
    ])
    def test_remove_wrapping_quotes_and_trim(self, input_str, expected):
        """Test quote removal and trimming function with various inputs."""
        result = siege_utilities.remove_wrapping_quotes_and_trim(input_str)
        assert result == expected

    def test_remove_wrapping_quotes_edge_cases(self):
        """Test edge cases that might break the function."""

        # Single character strings
        assert siege_utilities.remove_wrapping_quotes_and_trim('"') == '"'
        assert siege_utilities.remove_wrapping_quotes_and_trim("'") == "'"
        assert siege_utilities.remove_wrapping_quotes_and_trim('a') == 'a'

        # Two character strings - exactly at the boundary
        assert siege_utilities.remove_wrapping_quotes_and_trim('""') == ''
        assert siege_utilities.remove_wrapping_quotes_and_trim("''") == ''
