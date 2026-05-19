"""Tests for siege_utilities.trino.federation (SU#521 Shape B).

The OSS analog of the Databricks Lakehouse Federation helpers:
generates Trino ``CREATE VIEW`` statements that federate to a foreign
PostgreSQL source via Trino's ``postgresql`` connector.
"""

import pytest

from siege_utilities.trino import (
    build_trino_federation_view_sql,
    build_trino_schema_and_view_sync_sql,
    quote_ident,
)


def test_quote_ident_uses_double_quotes_not_backticks():
    # Trino dialect is ANSI; backticks are Databricks-only.
    assert quote_ident("persons") == '"persons"'
    assert "`" not in quote_ident("persons")


def test_quote_ident_doubles_internal_double_quotes():
    # Defense-in-depth — the validator rejects '"' in identifiers,
    # but the quoter still doubles them in case the validator is ever
    # relaxed.
    assert quote_ident('a"b') == '"a""b"'


def test_federation_view_default_source_table_uses_view_name():
    sql = build_trino_federation_view_sql(
        target_catalog="iceberg",
        target_schema="analytics",
        target_view="persons",
        postgres_catalog="postgresql",
        source_schema="public",
    )
    assert sql == (
        'CREATE OR REPLACE VIEW "iceberg"."analytics"."persons" AS\n'
        'SELECT * FROM "postgresql"."public"."persons";'
    )


def test_federation_view_explicit_source_table_name_used():
    sql = build_trino_federation_view_sql(
        target_catalog="iceberg",
        target_schema="analytics",
        target_view="people_view",
        postgres_catalog="postgresql",
        source_schema="public",
        source_table="persons",
    )
    assert '"iceberg"."analytics"."people_view"' in sql
    assert '"postgresql"."public"."persons"' in sql


def test_federation_view_rejects_target_catalog_injection():
    with pytest.raises(ValueError, match="target_catalog"):
        build_trino_federation_view_sql(
            target_catalog='evil";DROP TABLE x;--',
            target_schema="analytics",
            target_view="persons",
            postgres_catalog="postgresql",
            source_schema="public",
        )


def test_federation_view_rejects_source_table_injection():
    with pytest.raises(ValueError, match="source_table"):
        build_trino_federation_view_sql(
            target_catalog="iceberg",
            target_schema="analytics",
            target_view="persons",
            postgres_catalog="postgresql",
            source_schema="public",
            source_table='persons"; DROP TABLE persons; --',
        )


def test_federation_view_rejects_postgres_catalog_injection():
    with pytest.raises(ValueError, match="postgres_catalog"):
        build_trino_federation_view_sql(
            target_catalog="iceberg",
            target_schema="analytics",
            target_view="persons",
            postgres_catalog="postgresql\"--",
            source_schema="public",
        )


def test_schema_and_view_sync_emits_schema_then_views_in_order():
    statements = build_trino_schema_and_view_sync_sql(
        target_catalog="iceberg",
        target_schema="analytics",
        postgres_catalog="postgresql",
        source_schema="public",
        tables=["persons", "households", "addresses"],
    )
    assert len(statements) == 4
    assert statements[0] == (
        'CREATE SCHEMA IF NOT EXISTS "iceberg"."analytics";'
    )
    # Order preserved — each statement targets exactly its assigned table.
    assert '"persons"' in statements[1] and '"households"' not in statements[1]
    assert '"households"' in statements[2] and '"addresses"' not in statements[2]
    assert '"addresses"' in statements[3] and '"persons"' not in statements[3]


def test_schema_and_view_sync_empty_tables_yields_schema_only():
    statements = build_trino_schema_and_view_sync_sql(
        target_catalog="iceberg",
        target_schema="analytics",
        postgres_catalog="postgresql",
        source_schema="public",
        tables=[],
    )
    assert len(statements) == 1
    assert statements[0].startswith("CREATE SCHEMA IF NOT EXISTS")


def test_schema_and_view_sync_rejects_bad_table_name():
    with pytest.raises(ValueError):
        build_trino_schema_and_view_sync_sql(
            target_catalog="iceberg",
            target_schema="analytics",
            postgres_catalog="postgresql",
            source_schema="public",
            tables=["persons", 'evil"; DROP TABLE x; --'],
        )
