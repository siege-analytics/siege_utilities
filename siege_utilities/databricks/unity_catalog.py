"""Unity Catalog SQL helpers for foreign table registration."""

from typing import Iterable, List


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
    Build SQL for creating a Unity Catalog foreign table from a LakeBase source table.

    Note: syntax can vary by workspace/feature flag. Keep this as a composable
    helper and validate generated SQL in the target Databricks environment.
    """
    resolved_source = source_table or table
    fq_table = ".".join([quote_ident(catalog), quote_ident(schema), quote_ident(table)])
    source_ref = f"{source_schema}.{resolved_source}"
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
    """Build CREATE SCHEMA + CREATE FOREIGN TABLE statements for multiple tables."""
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
