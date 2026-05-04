"""
PostgreSQL schema migration runner.

A minimal, dependency-light tool for applying versioned raw-SQL DDL
migrations to a PostgreSQL database. Domain-agnostic — consumers supply
their own DSN, migrations directory, and tracking-table location.

Does NOT compete with Django migrations. Its tracking table lives in a
consumer-configured schema, independent of ``django_migrations``. The
two systems can coexist on the same database so long as they manage
different schemas / tables.

Typical usage from a consumer project::

    from siege_utilities.schema import MigrationRunner

    runner = MigrationRunner(
        dsn=os.environ["DATABASE_URL"],
        migrations_dir="schema/migrations/",
        tracking_schema="myapp",
        tracking_table="_schema_migrations",
    )
    runner.apply_all()

See :class:`MigrationRunner` for the full API.
"""

from siege_utilities.schema.migration_runner import (
    AppliedMigration,
    MigrationFile,
    MigrationRunner,
    MigrationStatus,
    PendingMigration,
)

__all__ = [
    "MigrationRunner",
    "MigrationFile",
    "MigrationStatus",
    "AppliedMigration",
    "PendingMigration",
]
