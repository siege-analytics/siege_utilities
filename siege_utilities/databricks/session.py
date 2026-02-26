"""Databricks runtime session helpers."""

from typing import Any, Optional


def get_active_spark_session(create_if_missing: bool = False, app_name: str = "siege_utilities_databricks") -> Any:
    """
    Get active Spark session from Databricks or PySpark runtime.

    Args:
        create_if_missing: If True, create a Spark session when none is active.
        app_name: App name used when creating a new session.
    """
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise ImportError("PySpark not available. Install with: pip install pyspark") from exc

    spark = SparkSession.getActiveSession()
    if spark is not None:
        return spark

    if not create_if_missing:
        raise RuntimeError(
            "No active Spark session found. Set create_if_missing=True to build one."
        )

    return SparkSession.builder.appName(app_name).getOrCreate()


def get_dbutils(spark: Optional[Any] = None) -> Any:
    """
    Get a Databricks DBUtils handle.

    Tries pyspark DBUtils first, then notebook global namespace fallback.
    """
    if spark is None:
        spark = get_active_spark_session(create_if_missing=True)

    try:
        from pyspark.dbutils import DBUtils

        return DBUtils(spark)
    except Exception:
        pass

    try:
        from IPython import get_ipython

        ipython = get_ipython()
        if ipython and "dbutils" in ipython.user_ns:
            return ipython.user_ns["dbutils"]
    except Exception:
        pass

    raise RuntimeError("Could not resolve dbutils from Spark or notebook runtime.")
