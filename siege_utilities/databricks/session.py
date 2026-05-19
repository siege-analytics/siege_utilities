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

    Dispatches between the pyspark-DBUtils path (Databricks Connect /
    runtime) and the notebook-namespace path (classic Databricks
    notebooks) by inspecting the runtime environment rather than by
    try/except chain. Each context is content-distinguishable per
    writing-code:14: pyspark.dbutils availability is a module-import
    check; notebook context is an IPython global-namespace check.
    """
    if spark is None:
        spark = get_active_spark_session(create_if_missing=True)

    # Path 1: pyspark DBUtils (Databricks Connect or Databricks runtime).
    # ImportError is the deterministic distinguisher for "this Python
    # interpreter does not have pyspark.dbutils available."
    try:
        from pyspark.dbutils import DBUtils
        pyspark_dbutils_available = True
    except ImportError:
        pyspark_dbutils_available = False

    if pyspark_dbutils_available:
        return DBUtils(spark)

    # Path 2: notebook global namespace (classic Databricks notebooks).
    # IPython presence + 'dbutils' in user namespace is the deterministic
    # distinguisher. ImportError on IPython means "not a notebook
    # environment"; KeyError on user_ns means "IPython present but no
    # dbutils injected."
    try:
        from IPython import get_ipython
        ipython_available = True
    except ImportError:
        ipython_available = False

    if ipython_available:
        ipython = get_ipython()
        if ipython is not None and "dbutils" in ipython.user_ns:
            return ipython.user_ns["dbutils"]

    raise RuntimeError(
        "Could not resolve dbutils. Tried: (1) pyspark.dbutils.DBUtils "
        "(available: {}); (2) IPython notebook namespace (available: {}). "
        "Run from a Databricks notebook or a Python environment with "
        "pyspark.dbutils installed.".format(
            pyspark_dbutils_available, ipython_available
        )
    )
