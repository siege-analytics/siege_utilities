"""
PostgreSQL schema migration runner.

Applies numbered raw-SQL migration files in order, tracking applied
versions in a consumer-configured tracking table. Each migration is
applied inside its own transaction together with the tracking-table
insert, so a failed migration leaves no partial state behind.

Conventions:

- Migration files live in a single directory.
- Filenames match ``V<version>__<description>.sql`` — the version
  string is the primary key (any string that sorts correctly works;
  zero-padded numerics like ``0001`` are recommended).
- Tracking schema and table are consumer-configured so multiple
  projects can share a database without colliding.
- The runner uses psycopg (v3). Callers supply a standard PostgreSQL
  DSN string.

The runner does NOT support down-migrations. Schema rollback is out of
scope — recovery is a restore-from-backup or a forward-only corrective
migration. Consumers who need rollbacks should reach for a heavier tool.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]


log = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_FILENAME_RE = re.compile(r"^V(?P<version>[^_]+)__(?P<description>.+)\.sql$")


class MigrationStatus(enum.Enum):
    """Result of inspecting the tracking table against on-disk migrations."""

    APPLIED = "applied"
    PENDING = "pending"


@dataclasses.dataclass(frozen=True)
class MigrationFile:
    """A migration file on disk."""

    version: str
    description: str
    path: Path
    sql_text: str
    checksum: str

    @classmethod
    def from_path(cls, path: Path) -> MigrationFile:
        """Parse ``V<version>__<description>.sql`` and load its SQL body."""
        match = _FILENAME_RE.match(path.name)
        if not match:
            raise ValueError(
                f"migration filename {path.name!r} does not match V<version>__<description>.sql"
            )
        sql_text = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql_text.encode("utf-8")).hexdigest()
        return cls(
            version=match.group("version"),
            description=match.group("description"),
            path=path,
            sql_text=sql_text,
            checksum=checksum,
        )


@dataclasses.dataclass(frozen=True)
class AppliedMigration:
    version: str
    description: str
    checksum: str
    applied_at: datetime


@dataclasses.dataclass(frozen=True)
class PendingMigration:
    version: str
    description: str
    checksum: str
    path: Path


class MigrationRunner:
    """
    Apply versioned SQL migrations to a PostgreSQL database.

    Args:
        dsn: Standard PostgreSQL DSN string (``postgresql://user:pass@host:port/db``).
        migrations_dir: Path to the directory containing ``V*__*.sql`` files.
        tracking_schema: Schema where the tracking table lives. Must be a
            valid SQL identifier. Typically consumer-specific (e.g.,
            ``"myapp"``). The schema is created if it doesn't exist.
        tracking_table: Name of the tracking table. Must be a valid SQL
            identifier. Defaults to ``"_schema_migrations"``.

    Raises:
        RuntimeError: if psycopg is not installed.
        ValueError: if tracking_schema or tracking_table is not a valid
            SQL identifier.
    """

    def __init__(
        self,
        *,
        dsn: str,
        migrations_dir: str | Path,
        tracking_schema: str,
        tracking_table: str = "_schema_migrations",
    ) -> None:
        if psycopg is None:
            raise RuntimeError(
                "psycopg is required for MigrationRunner. "
                "Install it (e.g., `pip install 'psycopg[binary]'`)."
            )
        _validate_identifier(tracking_schema, "tracking_schema")
        _validate_identifier(tracking_table, "tracking_table")
        self._dsn = dsn
        self._migrations_dir = Path(migrations_dir)
        self._tracking_schema = tracking_schema
        self._tracking_table = tracking_table

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def discover_migrations(self) -> list[MigrationFile]:
        """
        Read all migration files from ``migrations_dir``, sorted by version.

        Returns a list in lexical version order. Raises ``FileNotFoundError``
        if the directory is missing; returns ``[]`` if it's empty.
        """
        if not self._migrations_dir.exists():
            raise FileNotFoundError(self._migrations_dir)
        files = sorted(
            (
                MigrationFile.from_path(p)
                for p in self._migrations_dir.iterdir()
                if p.is_file() and p.name.startswith("V") and p.suffix == ".sql"
            ),
            key=lambda m: m.version,
        )
        versions = [m.version for m in files]
        if len(versions) != len(set(versions)):
            raise ValueError(f"duplicate migration versions in {self._migrations_dir}: {versions}")
        return files

    def applied_migrations(self) -> list[AppliedMigration]:
        """
        Return rows from the tracking table, oldest first.

        If the tracking table doesn't exist yet, returns an empty list.
        """
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                if not self._tracking_table_exists(cur):
                    return []
                cur.execute(
                    self._q(
                        "SELECT version, description, checksum, applied_at "
                        "FROM {schema}.{table} "
                        "ORDER BY applied_at ASC, version ASC"
                    )
                )
                rows = cur.fetchall()
        return [
            AppliedMigration(
                version=row[0],
                description=row[1],
                checksum=row[2],
                applied_at=row[3],
            )
            for row in rows
        ]

    def status(self) -> list[tuple[str, MigrationStatus]]:
        """
        Return ``(version, status)`` for every discovered-or-applied migration.

        Includes applied migrations that are no longer on disk (orphans),
        which typically indicate a concerning drift between the DB and the
        code.
        """
        on_disk = {m.version: m for m in self.discover_migrations()}
        applied = {m.version: m for m in self.applied_migrations()}
        all_versions = sorted(set(on_disk) | set(applied))
        result: list[tuple[str, MigrationStatus]] = []
        for version in all_versions:
            if version in applied:
                result.append((version, MigrationStatus.APPLIED))
            else:
                result.append((version, MigrationStatus.PENDING))
        return result

    def pending_migrations(self) -> list[PendingMigration]:
        """Return migrations on disk that are not in the tracking table."""
        applied_versions = {m.version for m in self.applied_migrations()}
        pending = [
            PendingMigration(
                version=m.version,
                description=m.description,
                checksum=m.checksum,
                path=m.path,
            )
            for m in self.discover_migrations()
            if m.version not in applied_versions
        ]
        return pending

    def verify_checksums(self) -> list[tuple[str, str, str]]:
        """
        Compare on-disk checksum vs tracking-table checksum for every applied migration.

        Returns a list of ``(version, disk_checksum, tracked_checksum)`` for
        any migrations whose on-disk content has drifted from what was
        originally applied. Empty list = healthy. A non-empty result is a
        warning that migration files have been edited after application —
        a correctness hazard.
        """
        on_disk = {m.version: m for m in self.discover_migrations()}
        drift: list[tuple[str, str, str]] = []
        for applied in self.applied_migrations():
            disk = on_disk.get(applied.version)
            if disk is None:
                continue  # orphan — reported separately via status()
            if disk.checksum != applied.checksum:
                drift.append((applied.version, disk.checksum, applied.checksum))
        return drift

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_all(self) -> list[PendingMigration]:
        """
        Apply every pending migration in version order.

        Returns the list of migrations that were applied during this call.
        """
        applied: list[PendingMigration] = []
        pending = self.pending_migrations()
        if not pending:
            log.info("schema runner: no pending migrations")
            return []

        self._ensure_tracking_table()

        for migration in pending:
            self._apply_one(migration)
            applied.append(migration)
            log.info("schema runner: applied %s (%s)", migration.version, migration.description)
        return applied

    def apply_up_to(self, target_version: str) -> list[PendingMigration]:
        """
        Apply pending migrations in order, stopping once ``target_version`` is applied.

        Raises ``ValueError`` if ``target_version`` is not on disk.
        """
        on_disk_versions = [m.version for m in self.discover_migrations()]
        if target_version not in on_disk_versions:
            raise ValueError(f"target_version {target_version!r} not found in migrations dir")

        self._ensure_tracking_table()

        applied: list[PendingMigration] = []
        for migration in self.pending_migrations():
            self._apply_one(migration)
            applied.append(migration)
            log.info("schema runner: applied %s (%s)", migration.version, migration.description)
            if migration.version == target_version:
                break
        return applied

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply_one(self, migration: PendingMigration) -> None:
        """Apply a single migration + record it in the tracking table in one transaction."""
        sql_text = migration.path.read_text(encoding="utf-8")
        with psycopg.connect(self._dsn) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(sql_text)
                    cur.execute(
                        self._q(
                            "INSERT INTO {schema}.{table} "
                            "(version, description, checksum, applied_at) "
                            "VALUES (%s, %s, %s, %s)"
                        ),
                        (
                            migration.version,
                            migration.description,
                            migration.checksum,
                            datetime.now(timezone.utc),
                        ),
                    )

    def _ensure_tracking_table(self) -> None:
        """Create the tracking schema + table if they don't exist."""
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(self._q("CREATE SCHEMA IF NOT EXISTS {schema}"))
                cur.execute(
                    self._q(
                        "CREATE TABLE IF NOT EXISTS {schema}.{table} ("
                        "version TEXT PRIMARY KEY, "
                        "description TEXT NOT NULL, "
                        "checksum TEXT NOT NULL, "
                        "applied_at TIMESTAMPTZ NOT NULL"
                        ")"
                    )
                )
            conn.commit()

    def _tracking_table_exists(self, cur) -> bool:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (self._tracking_schema, self._tracking_table),
        )
        return cur.fetchone() is not None

    def _q(self, template: str) -> str:
        """
        Interpolate validated schema / table identifiers into a SQL template.

        Uses ``.format(...)`` safely because the identifiers are validated
        by :func:`_validate_identifier` at construction time — the
        interpolation cannot introduce SQL injection.
        """
        return template.format(schema=self._tracking_schema, table=self._tracking_table)


def _validate_identifier(name: str, label: str) -> None:
    """Reject non-identifier strings so they can't be interpolated unsafely."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"{label}={name!r} is not a valid SQL identifier "
            "(must match [a-zA-Z_][a-zA-Z0-9_]*)"
        )
