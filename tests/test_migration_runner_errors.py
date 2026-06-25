"""Error-path coverage (SU-4b) for siege_utilities.schema.migration_runner.

Forces the no-database ValueError guards:
- MigrationFile.from_path on a filename that doesn't match V<v>__<desc>.sql
- _validate_identifier on a non-identifier string and on an over-length name
"""

from pathlib import Path

import pytest

from siege_utilities.schema.migration_runner import (
    MigrationFile,
    _PG_IDENTIFIER_MAX_LEN,
    _validate_identifier,
)


@pytest.mark.parametrize(
    "bad_name",
    ["not_a_migration.sql", "0001__missing_v_prefix.sql", "V0001_single_underscore.sql", "readme.txt"],
)
def test_from_path_rejects_malformed_filename(bad_name):
    with pytest.raises(ValueError) as exc_info:
        MigrationFile.from_path(Path(bad_name))
    assert "does not match" in str(exc_info.value)


@pytest.mark.parametrize("bad_ident", ["has-dash", "1leading_digit", "has space", "drop;table", ""])
def test_validate_identifier_rejects_non_identifier(bad_ident):
    with pytest.raises(ValueError) as exc_info:
        _validate_identifier(bad_ident, "tracking_schema")
    assert "not a valid SQL identifier" in str(exc_info.value)


def test_validate_identifier_rejects_overlong_name():
    too_long = "a" * (_PG_IDENTIFIER_MAX_LEN + 1)
    with pytest.raises(ValueError) as exc_info:
        _validate_identifier(too_long, "tracking_table")
    assert "exceeds" in str(exc_info.value)


def test_validate_identifier_accepts_valid_name():
    # Sanity anchor: the guard does not reject a legitimate identifier.
    assert _validate_identifier("_schema_migrations", "tracking_table") is None
