"""Contract for prepare_dataframe_for_export across scalar column types.

Regression for the defect where the function applied isnan() to every
non-string scalar column. isnan only accepts FLOAT/DOUBLE, so a boolean,
date, or timestamp column raised an AnalysisException. Uses the real_spark_
session fixture, which skips cleanly when pyspark is unavailable.
"""

from datetime import date, datetime

from siege_utilities import prepare_dataframe_for_export


def test_handles_bool_date_timestamp_and_numeric_columns(real_spark_session):
    from pyspark.sql import Row

    df = real_spark_session.createDataFrame([
        Row(flag=True, d=date(2020, 1, 1), ts=datetime(2020, 1, 1, 12, 0),
            n=5, x=1.5, s="hi"),
    ])
    # Must not raise AnalysisException on the boolean/date/timestamp columns.
    prepared = prepare_dataframe_for_export(df)
    rows = prepared.collect()
    assert len(rows) == 1
    row = rows[0].asDict()
    # Every column is rendered as a string.
    assert row["flag"] == "true"
    assert row["d"] == "2020-01-01"
    assert row["n"] == "5"
    assert row["x"] == "1.5"
    assert row["s"] == "hi"


def test_float_nan_and_null_become_empty_string(real_spark_session):
    from pyspark.sql import Row

    df = real_spark_session.createDataFrame([
        Row(v=float("nan"), b=False),
        Row(v=None, b=True),
        Row(v=2.5, b=False),
    ])
    prepared = prepare_dataframe_for_export(df)
    values = [r["v"] for r in prepared.orderBy("b").collect()]
    # NaN and null float values render as empty strings; real values cast.
    assert "" in values
    assert "2.5" in values
