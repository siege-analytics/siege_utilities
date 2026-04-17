"""
Sanity tests for siege_utilities.political migration packaging.
"""

from pathlib import Path

from siege_utilities.political import schema_migrations_dir
from siege_utilities.schema.migration_runner import MigrationFile


def test_schema_migrations_dir_returns_existing_path():
    path = schema_migrations_dir()
    assert isinstance(path, Path)
    assert path.exists()
    assert path.is_dir()


def test_schema_migrations_dir_has_expected_files():
    path = schema_migrations_dir()
    files = sorted(path.glob("V*.sql"))
    versions = [MigrationFile.from_path(f).version for f in files]
    # Every migration filename parses and versions are unique.
    assert versions == sorted(set(versions))
    # We shipped at least V0001-V0004 in this series.
    assert "0001" in versions
    assert len(versions) >= 4


def test_all_migrations_parse_and_checksum():
    path = schema_migrations_dir()
    for f in path.glob("V*.sql"):
        m = MigrationFile.from_path(f)
        assert m.version
        assert m.description
        assert m.checksum
        assert m.sql_text


def test_v0001_creates_political_schema():
    path = schema_migrations_dir() / "V0001__create_political_schema.sql"
    content = path.read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS political" in content
    assert "CREATE OR REPLACE FUNCTION political._touch_updated_at" in content
