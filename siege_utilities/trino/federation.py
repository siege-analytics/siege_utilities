"""Trino SQL helpers for federating to a foreign RDBMS via Trino connectors.

This is the OSS analog of
:mod:`siege_utilities.databricks.lakehouse_federation` for the open-source
unitycatalog.io (and any other catalog Trino can write a VIEW into).

OSS Unity Catalog does NOT support live query federation natively
(no ``CREATE FOREIGN TABLE``/``USING CONNECTION`` syntax — that is
Databricks-specific). The OSS path is to configure Trino with the
``postgresql`` connector (catalog config file), then expose the
foreign table under a stable name in a different Trino catalog via
``CREATE OR REPLACE VIEW``. Readers query the view; Trino does the
federation transparently.

This module generates the view-creation SQL. Catalog configuration
(the ``etc/catalog/*.properties`` files Trino reads at startup) is
out of scope — that is operator territory.

See SU#521 (umbrella) and SU#519 (root context).
"""

from typing import Iterable, List

from siege_utilities.core.sql_safety import validate_sql_identifier


def quote_ident(value: str) -> str:
    """Quote an identifier in Trino dialect.

    Trino uses ANSI double quotes for identifiers (not backticks like
    Databricks). Internal double-quote characters are escaped by
    doubling. The identifier itself is also run through the SU
    identifier allow-list before quoting, so the double-quote
    doubling is defense-in-depth.
    """
    return '"' + value.replace('"', '""') + '"'


def _join_fq(parts: Iterable[str]) -> str:
    return ".".join(quote_ident(p) for p in parts)


def build_trino_federation_view_sql(
    target_catalog: str,
    target_schema: str,
    target_view: str,
    postgres_catalog: str,
    source_schema: str,
    source_table: str | None = None,
) -> str:
    """Build SQL for a Trino federation view over a PostgreSQL source.

    Generates a ``CREATE OR REPLACE VIEW`` statement in
    ``target_catalog.target_schema.target_view`` that selects every
    column from the PostgreSQL table ``postgres_catalog.source_schema.source_table``
    via Trino's ``postgresql`` connector.

    All identifier fields are validated against the SU identifier
    allow-list before interpolation. The output is double-quoted in
    Trino's ANSI dialect (not backticks).

    Args:
        target_catalog: Trino catalog the view lives in (e.g. ``"iceberg"``
            for an OSS UC-backed Iceberg catalog).
        target_schema: Schema within the target catalog (e.g. ``"analytics"``).
        target_view: View name (e.g. ``"persons"``).
        postgres_catalog: Trino catalog alias for the PostgreSQL connector
            (whatever the operator named the ``etc/catalog/postgresql.properties``
            file, sans extension).
        source_schema: PostgreSQL schema (e.g. ``"public"``).
        source_table: PostgreSQL table name. Defaults to ``target_view``
            when omitted, which is the common case (same name on both
            sides).

    Returns:
        A single SQL statement ending in ``;``.

    Example:
        >>> build_trino_federation_view_sql(
        ...     target_catalog="iceberg",
        ...     target_schema="analytics",
        ...     target_view="persons",
        ...     postgres_catalog="postgresql",
        ...     source_schema="public",
        ... )
        'CREATE OR REPLACE VIEW "iceberg"."analytics"."persons" AS\\nSELECT * FROM "postgresql"."public"."persons";'
    """
    resolved_source = source_table or target_view
    validate_sql_identifier(target_catalog, "target_catalog")
    validate_sql_identifier(target_schema, "target_schema")
    validate_sql_identifier(target_view, "target_view")
    validate_sql_identifier(postgres_catalog, "postgres_catalog")
    validate_sql_identifier(source_schema, "source_schema")
    validate_sql_identifier(resolved_source, "source_table")
    target_fq = _join_fq([target_catalog, target_schema, target_view])
    source_fq = _join_fq([postgres_catalog, source_schema, resolved_source])
    return (
        f"CREATE OR REPLACE VIEW {target_fq} AS\n"
        f"SELECT * FROM {source_fq};"
    )


def build_trino_schema_and_view_sync_sql(
    target_catalog: str,
    target_schema: str,
    postgres_catalog: str,
    source_schema: str,
    tables: Iterable[str],
) -> List[str]:
    """Build ``CREATE SCHEMA`` + per-table ``CREATE VIEW`` statements.

    Convenience for syncing many PostgreSQL tables into a Trino catalog
    in one pass. The schema statement uses ``IF NOT EXISTS`` so the
    list is safe to re-run. Each view statement is ``CREATE OR REPLACE``
    so re-runs after upstream column additions stay correct.

    Args:
        target_catalog: Trino catalog the schema + views live in.
        target_schema: Schema within ``target_catalog``.
        postgres_catalog: Trino PostgreSQL connector alias.
        source_schema: PostgreSQL schema containing ``tables``.
        tables: Iterable of PostgreSQL table names. Same names are
            used for the Trino views.

    Returns:
        List of SQL statements: one ``CREATE SCHEMA`` followed by one
        ``CREATE OR REPLACE VIEW`` per table, in the order given.
    """
    statements: List[str] = [
        "CREATE SCHEMA IF NOT EXISTS "
        + _join_fq([target_catalog, target_schema])
        + ";"
    ]
    for table in tables:
        statements.append(
            build_trino_federation_view_sql(
                target_catalog=target_catalog,
                target_schema=target_schema,
                target_view=table,
                postgres_catalog=postgres_catalog,
                source_schema=source_schema,
                source_table=table,
            )
        )
    return statements
