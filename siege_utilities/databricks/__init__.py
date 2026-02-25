"""
Databricks and LakeBase utilities for siege_utilities.
"""

from .artifacts import build_databricks_run_url
from .auth import get_workspace_client
from .dataframe_bridge import (
    geopandas_to_spark,
    pandas_to_spark,
    spark_to_geopandas,
    spark_to_pandas,
)
from .lakebase import (
    build_jdbc_url,
    build_lakebase_psql_command,
    build_pgpass_entry,
    parse_conninfo,
)
from .secrets import (
    ensure_secret_scope,
    get_runtime_secret,
    put_secret,
    runtime_secret_exists,
)
from .session import get_active_spark_session, get_dbutils
from .unity_catalog import build_foreign_table_sql, build_schema_and_table_sync_sql

__all__ = [
    "build_databricks_run_url",
    "build_foreign_table_sql",
    "build_jdbc_url",
    "build_lakebase_psql_command",
    "build_pgpass_entry",
    "build_schema_and_table_sync_sql",
    "ensure_secret_scope",
    "geopandas_to_spark",
    "get_active_spark_session",
    "get_dbutils",
    "get_runtime_secret",
    "get_workspace_client",
    "pandas_to_spark",
    "parse_conninfo",
    "put_secret",
    "runtime_secret_exists",
    "spark_to_geopandas",
    "spark_to_pandas",
]
