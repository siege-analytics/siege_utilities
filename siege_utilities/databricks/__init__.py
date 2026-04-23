"""
Databricks and LakeBase utilities for siege_utilities.

**Why this package is a sibling to `distributed/`, not a child.**

`distributed/` holds vendor-agnostic PySpark + HDFS utilities that work on any
Spark cluster (EMR, Dataproc, self-hosted). `databricks/` holds Databricks-only
SDK features (Unity Catalog, LakeBase, workspace auth, secrets, DBFS, job-run
URL construction for Asset Bundles) that only make sense inside a Databricks
workspace.

The split is **load-bearing** because Azure Databricks lacks Apache Sedona and
the C-library stack that GeoPandas / Shapely / Fiona need. ``dataframe_bridge.py``
is the workaround — Spark ↔ pandas and Spark ↔ GeoPandas bridges that let
geospatial work happen in environments where the usual stack is not installable.

Don't merge these modules. A future reader "DRY"-ing them together will
re-create a problem we already solved.

See also: `docs/INTENT.md` (D4), `docs/adr/` (architecture decisions).
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
