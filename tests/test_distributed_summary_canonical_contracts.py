"""Canonical root-import contracts for distributed summary helpers."""

import sys
import types
from unittest.mock import Mock

import pytest

from siege_utilities.distributed import prepare_summary_dataframe
from siege_utilities.distributed import tabulate_null_vs_not_null


class ColumnExpr:
    def __init__(self, text):
        self.text = text

    def isNull(self):
        return ColumnExpr(f"isNull({self.text})")

    def isNotNull(self):
        return ColumnExpr(f"isNotNull({self.text})")

    def otherwise(self, value):
        return ColumnExpr(f"otherwise({self.text},{value})")

    def alias(self, name):
        return (self.text, name)


class GroupedFrame:
    def __init__(self):
        self.agg_args = None
        self.result = Mock()

    def agg(self, *args):
        self.agg_args = args
        return self.result


class NullFrame:
    def __init__(self):
        self.grouped = GroupedFrame()
        self.group_by_column = None

    def groupBy(self, column_name):
        self.group_by_column = column_name
        return self.grouped


def test_tabulate_null_vs_not_null_builds_counts_and_shows(monkeypatch):
    from siege_utilities.distributed import spark_utils

    frame = NullFrame()

    monkeypatch.setattr(
        spark_utils,
        "col",
        lambda name: ColumnExpr(name),
        raising=False,
    )
    monkeypatch.setattr(
        spark_utils,
        "when",
        lambda condition, value: ColumnExpr(f"when({condition.text},{value})"),
        raising=False,
    )
    monkeypatch.setattr(
        spark_utils,
        "sum",
        lambda expression: ColumnExpr(f"sum({expression.text})"),
        raising=False,
    )

    result = tabulate_null_vs_not_null(frame, "email")

    assert result is frame.grouped.result
    assert frame.group_by_column == "email"
    assert frame.grouped.agg_args == (
        ("sum(otherwise(when(isNull(email),1),0))", "email_null_count"),
        (
            "sum(otherwise(when(isNotNull(email),1),0))",
            "email_not_null_count",
        ),
    )
    frame.grouped.result.show.assert_called_once_with(truncate=False)


def test_prepare_summary_dataframe_requires_active_spark_session(monkeypatch):
    pyspark = types.ModuleType("pyspark")
    pyspark_sql = types.ModuleType("pyspark.sql")
    pyspark_types = types.ModuleType("pyspark.sql.types")

    class StructType(list):
        pass

    class StructField:
        def __init__(self, name, data_type, nullable):
            self.name = name
            self.data_type = data_type
            self.nullable = nullable

    class StringType:
        pass

    class SparkSession:
        @staticmethod
        def getActiveSession():
            return None

    pyspark_types.StructType = StructType
    pyspark_types.StructField = StructField
    pyspark_types.StringType = StringType
    pyspark_sql.SparkSession = SparkSession
    monkeypatch.setitem(sys.modules, "pyspark", pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", pyspark_sql)
    monkeypatch.setitem(sys.modules, "pyspark.sql.types", pyspark_types)

    with pytest.raises(RuntimeError, match="No active Spark session"):
        prepare_summary_dataframe([("rows", 3)], ["metric", "value"])
