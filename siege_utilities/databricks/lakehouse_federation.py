"""SQL helpers for Databricks Lakehouse Federation foreign tables.

This module generates SQL of the form
``CREATE FOREIGN TABLE ... USING CONNECTION ...``, which is a
**Databricks-managed Unity Catalog only** feature (Lakehouse Federation).
It does NOT work against the open-source Unity Catalog implementation
(unitycatalog.io / ``unitycatalog/unitycatalog``). OSS UC has no
``CREATE CONNECTION`` / ``CREATE FOREIGN TABLE`` mechanism — federation
is handled at the compute layer (Trino, Spark) instead.

Previously named ``siege_utilities.databricks.unity_catalog``. Renamed
in SU#519 because the old name implied the helpers worked against any
Unity Catalog and burned consumers planning OSS UC bridges. The old
module path remains importable as a deprecation shim.

See ``unity_catalog.py`` (sibling) for the back-compat re-export and
SU#519 for the rename rationale.
"""

from typing import Iterable, List

from siege_utilities.core.sql_safety import (
    escape_sql_string_literal,
    validate_sql_identifier,
)


def quote_ident(value: str) -> str:
    """Quote an identifier with backticks for Databricks SQL."""
    return "`" + value.replace("`", "``") + "`"


def build_foreign_table_sql(
    catalog: str,
    schema: str,
    table: str,
    connection_name: str,
    source_schema: str,
    source_table: str | None = None,
) -> str:
    """
    Build SQL for creating a Databricks Lakehouse Federation foreign
    table from a LakeBase (or other UC-Federation-registered) source.

    Databricks Lakehouse Federation only. The generated
    ``CREATE FOREIGN TABLE ... USING CONNECTION`` syntax is not
    parseable by OSS unitycatalog.io. (SU#519)

    All identifier fields (catalog, schema, table, connection_name,
    source_schema, source_table) are validated against the Postgres
    identifier allow-list before interpolation. An earlier version
    interpolated source_schema and source_table directly into the SQL
    string without validation, producing an injection risk if either
    contained a single quote.

    Note: syntax can vary by Databricks workspace / feature flag. Keep
    this as a composable helper and validate generated SQL in the
    target Databricks environment.
    """
    resolved_source = source_table or table
    validate_sql_identifier(catalog, "catalog")
    validate_sql_identifier(schema, "schema")
    validate_sql_identifier(table, "table")
    validate_sql_identifier(connection_name, "connection_name")
    validate_sql_identifier(source_schema, "source_schema")
    validate_sql_identifier(resolved_source, "source_table")
    fq_table = ".".join([quote_ident(catalog), quote_ident(schema), quote_ident(table)])
    # source_ref goes inside a single-quoted SQL string literal. Even
    # though the identifier validator already rejects single quotes,
    # escape defensively in case a future relaxation allows them.
    source_ref = escape_sql_string_literal(f"{source_schema}.{resolved_source}")
    return (
        f"CREATE FOREIGN TABLE IF NOT EXISTS {fq_table}\n"
        f"USING CONNECTION {quote_ident(connection_name)}\n"
        f"OPTIONS (table '{source_ref}');"
    )


def build_schema_and_table_sync_sql(
    catalog: str,
    schema: str,
    connection_name: str,
    source_schema: str,
    tables: Iterable[str],
) -> List[str]:
    """Build CREATE SCHEMA + CREATE FOREIGN TABLE statements for multiple tables.

    Databricks Lakehouse Federation only — see module docstring.
    """
    statements: List[str] = [
        (
            "CREATE SCHEMA IF NOT EXISTS "
            + ".".join([quote_ident(catalog), quote_ident(schema)])
            + ";"
        )
    ]
    for table in tables:
        statements.append(
            build_foreign_table_sql(
                catalog=catalog,
                schema=schema,
                table=table,
                connection_name=connection_name,
                source_schema=source_schema,
                source_table=table,
            )
        )
    return statements
