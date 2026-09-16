"""Canonical root-import contract for boolean pivot summaries."""

import sys
import types

from siege_utilities.distributed import pivot_summary_table_for_bools


class Expr:
    def __init__(self, text):
        self.text = text

    def otherwise(self, value):
        return Expr(f"otherwise({self.text},{value})")

    def alias(self, name):
        return (self.text, name)


class Functions(types.ModuleType):
    def col(self, name):
        return Expr(name)

    def when(self, condition, value):
        return Expr(f"when({condition.text},{value})")

    def sum(self, expression):
        return Expr(f"sum({expression.text})")


class AggFrame:
    def __init__(self, row):
        self.row = row

    def collect(self):
        return [self.row]


class SourceFrame:
    def __init__(self):
        self.agg_args = None

    def count(self):
        return 4

    def agg(self, *args):
        self.agg_args = args
        return AggFrame({"is_active": 3, "is_valid": 1})


class CreatedFrame:
    pass


class Spark:
    def __init__(self):
        self.rows = None
        self.created_frame = CreatedFrame()

    def createDataFrame(self, rows):
        self.rows = rows
        return self.created_frame


def test_pivot_summary_table_for_bools_builds_count_percent_total(monkeypatch):
    pyspark = types.ModuleType("pyspark")
    pyspark_sql = types.ModuleType("pyspark.sql")
    functions = Functions("pyspark.sql.functions")
    monkeypatch.setitem(sys.modules, "pyspark", pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", pyspark_sql)
    monkeypatch.setitem(sys.modules, "pyspark.sql.functions", functions)
    frame = SourceFrame()
    spark = Spark()

    result = pivot_summary_table_for_bools(
        frame,
        ["is_active", "is_valid"],
        spark,
    )

    assert result is spark.created_frame
    assert frame.agg_args == (
        ("sum(otherwise(when(is_active,1),0))", "is_active"),
        ("sum(otherwise(when(is_valid,1),0))", "is_valid"),
    )
    assert spark.rows == [
        {"Metric": "Count", "is_active": 3.0, "is_valid": 1.0},
        {"Metric": "Percentage (%)", "is_active": 75.0, "is_valid": 25.0},
        {"Metric": "Total", "is_active": 4.0, "is_valid": 4.0},
    ]
