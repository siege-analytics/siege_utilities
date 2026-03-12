"""Tests for siege_utilities.core.string_utils module."""

import pytest
from siege_utilities.core.string_utils import (
    remove_wrapping_quotes_and_trim,
    clean_string,
    normalize_whitespace,
    snake_case,
    remove_non_alphanumeric,
)


class TestRemoveWrappingQuotesAndTrim:
    """Tests for remove_wrapping_quotes_and_trim."""

    def test_none_returns_empty(self):
        assert remove_wrapping_quotes_and_trim(None) == ""

    def test_empty_string_unchanged(self):
        assert remove_wrapping_quotes_and_trim("") == ""

    def test_newline_unchanged(self):
        assert remove_wrapping_quotes_and_trim("\n") == "\n"

    def test_double_quoted(self):
        assert remove_wrapping_quotes_and_trim('"hello"') == "hello"

    def test_single_quoted(self):
        assert remove_wrapping_quotes_and_trim("'hello'") == "hello"

    def test_mismatched_quotes_not_removed(self):
        assert remove_wrapping_quotes_and_trim("\"hello'") == "\"hello'"

    def test_whitespace_trimmed(self):
        assert remove_wrapping_quotes_and_trim("  hello  ") == "hello"

    def test_quoted_with_whitespace(self):
        assert remove_wrapping_quotes_and_trim('  "hello world"  ') == "hello world"

    def test_single_char_unchanged(self):
        assert remove_wrapping_quotes_and_trim("x") == "x"

    def test_just_quotes(self):
        assert remove_wrapping_quotes_and_trim('""') == ""

    def test_nested_quotes_only_outer_removed(self):
        result = remove_wrapping_quotes_and_trim('"\'hello\'"')
        assert result == "'hello'"


class TestCleanString:
    """Tests for clean_string."""

    def test_none_returns_empty(self):
        assert clean_string(None) == ""

    def test_empty_returns_empty(self):
        assert clean_string("") == ""

    def test_cleans_quotes_and_whitespace(self):
        assert clean_string('"  hello   world  "') == "hello world"

    def test_normalizes_whitespace(self):
        assert clean_string("hello    world") == "hello world"


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace."""

    def test_none_returns_empty(self):
        assert normalize_whitespace(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_whitespace("") == ""

    def test_multiple_spaces(self):
        assert normalize_whitespace("hello    world") == "hello world"

    def test_tabs_and_newlines(self):
        assert normalize_whitespace("hello\t\n\nworld") == "hello world"

    def test_leading_trailing_stripped(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_single_space_unchanged(self):
        assert normalize_whitespace("hello world") == "hello world"


class TestSnakeCase:
    """Tests for snake_case."""

    def test_empty_returns_empty(self):
        assert snake_case("") == ""

    def test_camel_case(self):
        assert snake_case("HelloWorld") == "hello_world"

    def test_hyphenated(self):
        assert snake_case("hello-world") == "hello_world"

    def test_spaced(self):
        assert snake_case("Hello World") == "hello_world"

    def test_already_snake_case(self):
        assert snake_case("hello_world") == "hello_world"

    def test_uppercase(self):
        assert snake_case("HELLO") == "hello"

    def test_mixed(self):
        assert snake_case("myVariableName") == "my_variable_name"


class TestRemoveNonAlphanumeric:
    """Tests for remove_non_alphanumeric."""

    def test_empty_returns_empty(self):
        assert remove_non_alphanumeric("") == ""

    def test_special_chars_removed(self):
        assert remove_non_alphanumeric("hello@world!") == "helloworld"

    def test_keeps_underscore_and_hyphen_by_default(self):
        assert remove_non_alphanumeric("test_value-123") == "test_value-123"

    def test_custom_keep_chars(self):
        assert remove_non_alphanumeric("hello@world.com", keep_chars="@.") == "hello@world.com"

    def test_none_input(self):
        assert remove_non_alphanumeric("") == ""

    def test_alphanumeric_only(self):
        assert remove_non_alphanumeric("abc123") == "abc123"
