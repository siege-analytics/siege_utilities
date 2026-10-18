"""
Packaging and PostgreSQL syntax checks for political migrations.
"""

from pathlib import Path

import pytest

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


def test_all_migration_filenames_parse_and_checksum():
    path = schema_migrations_dir()
    for f in path.glob("V*.sql"):
        m = MigrationFile.from_path(f)
        assert m.version
        assert m.description
        assert m.checksum
        assert m.sql_text


@pytest.mark.parametrize(
    "path",
    sorted(schema_migrations_dir().glob("V*.sql")),
    ids=lambda path: path.name,
)
def test_all_migrations_parse_as_postgresql(path: Path) -> None:
    pglast = pytest.importorskip("pglast")
    assert pglast.parse_sql(path.read_text(encoding="utf-8"))


def test_v0001_creates_political_schema():
    path = schema_migrations_dir() / "V0001__create_political_schema.sql"
    content = path.read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS political" in content
    assert "CREATE OR REPLACE FUNCTION political._touch_updated_at" in content


def test_next_term_delete_clears_only_forward_link() -> None:
    path = schema_migrations_dir() / "V0002__create_seats_and_office_terms.sql"
    sql = " ".join(path.read_text(encoding="utf-8").split())
    assert (
        "ADD CONSTRAINT fk_office_terms_next_same_seat "
        "FOREIGN KEY (next_term_id, seat_id) "
        "REFERENCES political.office_terms (id, seat_id) "
        "ON DELETE SET NULL (next_term_id);"
    ) in sql


def test_congressional_terms_allow_same_congress_successors() -> None:
    path = schema_migrations_dir() / "V0002__create_seats_and_office_terms.sql"
    sql = " ".join(path.read_text(encoding="utf-8").split())
    assert (
        "CREATE UNIQUE INDEX uq_congressional_terms_congress_seat "
        "ON political.congressional_terms "
        "(congress_number, seat_id, office_term_id);"
    ) in sql
