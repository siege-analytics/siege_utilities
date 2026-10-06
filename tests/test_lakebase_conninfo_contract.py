"""Contract tests for parse_conninfo (siege_utilities.databricks.lakebase).

parse_conninfo is a pure-Python PostgreSQL conninfo parser (shlex-based, no
Databricks runtime dependency) that the per-symbol coverage scanner flagged as
an untested root symbol. These tests pin its documented behaviour. Ref #1199.
"""

from siege_utilities import parse_conninfo


class TestParseConninfo:
    def test_standard_conninfo_parses_all_pairs(self):
        parsed = parse_conninfo(
            "host=example.com user=alice dbname=mydb port=5432 "
            "sslmode=require"
        )
        assert parsed == {
            "host": "example.com",
            "user": "alice",
            "dbname": "mydb",
            "port": "5432",
            "sslmode": "require",
        }

    def test_quoted_value_with_spaces_is_preserved(self):
        # shlex tokenisation keeps a quoted value containing spaces intact.
        parsed = parse_conninfo("host=h password='se cret'")
        assert parsed == {"host": "h", "password": "se cret"}

    def test_value_containing_equals_splits_on_first_only(self):
        # split("=", 1): only the first '=' separates key from value.
        parsed = parse_conninfo("key=a=b=c")
        assert parsed == {"key": "a=b=c"}

    def test_tokens_without_equals_are_skipped(self):
        parsed = parse_conninfo("host=h bareword user=u")
        assert parsed == {"host": "h", "user": "u"}

    def test_empty_string_returns_empty_dict(self):
        assert parse_conninfo("") == {}
