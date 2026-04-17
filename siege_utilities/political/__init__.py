"""
siege_utilities.political — generic political-infrastructure primitives.

Provides the DDL-layer entities for things shared across political data
projects (LegiNation, socialwarehouse, electinfo, future clients):

- Seat — political identity that persists across redistricting cycles.
- OfficeTerm / CongressionalTerm — service periods.
- RedistrictingPlan / PlanDistrictAssignment — plan-scoped Seat→polygon mapping.
- StateElectionCalendar — per-state election dates per cycle.

Schema lives in a PostgreSQL schema named ``political`` — consumer
projects apply these migrations via
``siege_utilities.schema.MigrationRunner`` pointed at
``siege_utilities.political.schema_migrations_dir()`` BEFORE running
their own enterprise-specific migrations that FK into ``political.*``.

Django models that wrap these tables (for downstream ORM / API access)
live under ``siege_utilities/political/models/`` as ``managed = False``
Django models — per the project principle "ontology → DB → Django last."
"""

from pathlib import Path


def schema_migrations_dir() -> Path:
    """Return the path to the raw-SQL migrations directory for this module.

    Consumer projects hand this to ``siege_utilities.schema.MigrationRunner``
    so the political tables can be created / evolved alongside the
    consumer's own schema migrations.

    Typical consumer usage::

        from siege_utilities.schema import MigrationRunner
        from siege_utilities.political import schema_migrations_dir

        political_runner = MigrationRunner(
            dsn=DSN,
            migrations_dir=schema_migrations_dir(),
            tracking_schema="political",
            tracking_table="_schema_migrations",
        )
        political_runner.apply_all()

        # Then run the consumer's own migrations.
    """
    return Path(__file__).resolve().parent / "migrations"


from siege_utilities.political import readers  # noqa: F401

__all__ = ["schema_migrations_dir", "readers"]
