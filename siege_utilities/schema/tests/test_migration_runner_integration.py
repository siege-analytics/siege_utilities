"""
PostgreSQL-integration tests for :class:`MigrationRunner`.

These tests are gated on ``SIEGE_UTILITIES_TEST_PG_DSN`` being set in the
environment. If unset, every test is skipped so the rest of the suite
can run in environments without a PostgreSQL available.

Each test uses an isolated tracking schema (randomized per run) so
concurrent runs don't collide, and drops the schema on teardown.
"""

from __future__ import annotations

import os
import secrets
import textwrap
from pathlib import Path

import pytest

try:
    import psycopg
    from psycopg import sql as psycopg_sql
except ImportError:
    psycopg = None  # type: ignore[assignment]
    psycopg_sql = None  # type: ignore[assignment]

from siege_utilities.schema.migration_runner import (
    MigrationRunner,
    MigrationStatus,
)


_DSN_ENV = "SIEGE_UTILITIES_TEST_PG_DSN"

pytestmark = pytest.mark.skipif(
    psycopg is None or not os.environ.get(_DSN_ENV),
    reason=f"requires psycopg and ${_DSN_ENV}",
)


@pytest.fixture
def pg_dsn() -> str:
    return os.environ[_DSN_ENV]


@pytest.fixture
def tracking_schema(pg_dsn: str):
    """
    Provide a randomized tracking schema name per test; drop it in teardown.
    """
    schema = f"sut_schema_{secrets.token_hex(6)}"
    yield schema
    with psycopg.connect(pg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                psycopg_sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    psycopg_sql.Identifier(schema)
                )
            )
        conn.commit()


@pytest.fixture
def migrations_dir(tmp_path: Path) -> Path:
    d = tmp_path / "migrations"
    d.mkdir()
    return d


def _write(d: Path, name: str, body: str) -> Path:
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


def _runner(pg_dsn: str, migrations_dir: Path, tracking_schema: str) -> MigrationRunner:
    return MigrationRunner(
        dsn=pg_dsn,
        migrations_dir=migrations_dir,
        tracking_schema=tracking_schema,
        tracking_table="_schema_migrations",
    )


def test_apply_all_on_empty_tracking_creates_tracking_then_applies(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__create_thing.sql", textwrap.dedent("""\
        CREATE SCHEMA IF NOT EXISTS sut_target;
        CREATE TABLE sut_target.thing (id INT PRIMARY KEY);
        """))
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)

    applied = runner.apply_all()

    assert [m.version for m in applied] == ["0001"]
    try:
        with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                psycopg_sql.SQL("SELECT version FROM {}.{} ORDER BY version").format(
                    psycopg_sql.Identifier(tracking_schema),
                    psycopg_sql.Identifier("_schema_migrations"),
                )
            )
            rows = [r[0] for r in cur.fetchall()]
            assert rows == ["0001"]
            cur.execute("SELECT to_regclass('sut_target.thing')")
            assert cur.fetchone()[0] == "sut_target.thing"
    finally:
        with psycopg.connect(pg_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS sut_target CASCADE")
            conn.commit()


def test_apply_all_is_idempotent_second_call_applies_nothing(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)

    runner.apply_all()
    second_pass = runner.apply_all()
    assert second_pass == []


def test_pending_migrations_listed_in_order(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0003__c.sql", "SELECT 1;")
    _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    _write(migrations_dir, "V0002__b.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)

    pending = runner.pending_migrations()
    assert [m.version for m in pending] == ["0001", "0002", "0003"]


def test_apply_up_to_stops_at_target(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    _write(migrations_dir, "V0002__b.sql", "SELECT 1;")
    _write(migrations_dir, "V0003__c.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)

    applied = runner.apply_up_to("0002")
    assert [m.version for m in applied] == ["0001", "0002"]
    pending_after = runner.pending_migrations()
    assert [m.version for m in pending_after] == ["0003"]


def test_apply_up_to_rejects_unknown_target(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)
    with pytest.raises(ValueError, match="not found"):
        runner.apply_up_to("0099")


def test_failed_migration_rolls_back_and_is_not_recorded(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__good.sql", "SELECT 1;")
    _write(migrations_dir, "V0002__bad.sql", "SELECT * FROM does_not_exist;")
    _write(migrations_dir, "V0003__should_not_run.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)

    with pytest.raises(psycopg.Error):
        runner.apply_all()

    applied = runner.applied_migrations()
    assert [m.version for m in applied] == ["0001"]  # bad one didn't commit, third never ran


def test_status_reports_applied_and_pending(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    _write(migrations_dir, "V0002__b.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)

    runner.apply_up_to("0001")

    status = dict(runner.status())
    assert status == {"0001": MigrationStatus.APPLIED, "0002": MigrationStatus.PENDING}


def test_verify_checksums_reports_edited_migration(
    pg_dsn, migrations_dir, tracking_schema
):
    path = _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)
    runner.apply_all()

    # Edit the migration file after it was applied. Should be detected.
    path.write_text("SELECT 2;", encoding="utf-8")

    drift = runner.verify_checksums()
    assert len(drift) == 1
    version, disk_checksum, tracked_checksum = drift[0]
    assert version == "0001"
    assert disk_checksum != tracked_checksum


def test_tracking_table_invalid_identifier_rejected(pg_dsn, migrations_dir):
    with pytest.raises(ValueError, match="not a valid SQL identifier"):
        MigrationRunner(
            dsn=pg_dsn,
            migrations_dir=migrations_dir,
            tracking_schema="has-dash",  # invalid
            tracking_table="x",
        )


def test_duplicate_version_rejected(
    pg_dsn, migrations_dir, tracking_schema
):
    _write(migrations_dir, "V0001__a.sql", "SELECT 1;")
    _write(migrations_dir, "V0001__duplicate.sql", "SELECT 1;")
    runner = _runner(pg_dsn, migrations_dir, tracking_schema)
    with pytest.raises(ValueError, match="duplicate migration versions"):
        runner.discover_migrations()
