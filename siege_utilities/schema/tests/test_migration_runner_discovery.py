"""
Tests for migration-file discovery, filename parsing, and checksum behavior.

These are pure-file tests; they don't touch PostgreSQL. DB-integration
tests live in ``test_migration_runner_integration.py`` and are gated on
an environment variable.
"""

import hashlib
from pathlib import Path

import pytest

from siege_utilities.schema.migration_runner import (
    MigrationFile,
    MigrationStatus,
    _validate_identifier,
)


def _write(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def test_migration_file_parses_valid_filename(tmp_path):
    path = _write(tmp_path, "V0001__create_agents.sql", "CREATE TABLE x(a INT);")
    m = MigrationFile.from_path(path)
    assert m.version == "0001"
    assert m.description == "create_agents"
    assert m.sql_text == "CREATE TABLE x(a INT);"
    expected_checksum = hashlib.sha256(b"CREATE TABLE x(a INT);").hexdigest()
    assert m.checksum == expected_checksum


def test_migration_file_rejects_invalid_filename(tmp_path):
    path = _write(tmp_path, "NOT_A_MIGRATION.sql", "")
    with pytest.raises(ValueError, match="does not match"):
        MigrationFile.from_path(path)


def test_migration_file_requires_double_underscore_separator(tmp_path):
    path = _write(tmp_path, "V0001_missing_separator.sql", "")
    with pytest.raises(ValueError, match="does not match"):
        MigrationFile.from_path(path)


def test_migration_file_checksum_is_sha256_of_utf8(tmp_path):
    body = "CREATE TABLE café (x INT);"
    path = _write(tmp_path, "V0001__utf8_name.sql", body)
    m = MigrationFile.from_path(path)
    assert m.checksum == hashlib.sha256(body.encode("utf-8")).hexdigest()


def test_migration_file_allows_any_version_string_that_sorts(tmp_path):
    """Version doesn't have to be numeric — any string that sorts works."""
    _write(tmp_path, "V2026-04-16-0001__thing.sql", "--")
    path = tmp_path / "V2026-04-16-0001__thing.sql"
    m = MigrationFile.from_path(path)
    assert m.version == "2026-04-16-0001"


def test_validate_identifier_accepts_valid_names():
    _validate_identifier("schema_name", "test")
    _validate_identifier("a1", "test")
    _validate_identifier("_leading_underscore", "test")
    _validate_identifier("UPPER", "test")


def test_validate_identifier_rejects_invalid():
    for bad in ["1leading_digit", "has-dash", "has space", "quotes\"x", "", "semi;"]:
        with pytest.raises(ValueError, match="not a valid SQL identifier"):
            _validate_identifier(bad, "test")


def test_validate_identifier_accepts_reserved_words():
    """Reserved SQL words match the identifier regex and pass validation.

    _validate_identifier is intentionally permissive about reserved words —
    _q() double-quotes all identifiers before interpolation, making reserved
    words safe to use as tracking schema/table names.
    """
    _validate_identifier("order", "test")
    _validate_identifier("table", "test")
    _validate_identifier("select", "test")


def test_migration_status_enum_values():
    assert MigrationStatus.APPLIED.value == "applied"
    assert MigrationStatus.PENDING.value == "pending"
