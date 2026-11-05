"""Regression coverage for NULL grouping/aggregation semantics (#1454)."""

from collections import Counter

import pandas as pd
import pytest

from siege_utilities.engines.dataframe_engine import (
    DuckDBEngine,
    PandasEngine,
    PostGISEngine,
    SparkEngine,
)


@pytest.fixture(params=["pandas", "duckdb", "postgis"])
def engine(request):
    if request.param == "pandas":
        yield PandasEngine()
    elif request.param == "duckdb":
        pytest.importorskip("duckdb")
        backend = DuckDBEngine()
        try:
            yield backend
        finally:
            backend._connection.close()
    else:
        pytest.importorskip("sqlalchemy")
        pytest.importorskip("geopandas")
        # Driver-side aggregation needs no connection; live SQL is tested below.
        yield PostGISEngine("postgresql://localhost/unused")


@pytest.fixture
def frame():
    return pd.DataFrame(
        {
            "key": [
                None,
                None,
                None,
                "empty",
                "empty",
                "partial",
                "partial",
                "partial",
                "partial",
                "full",
                "full",
                "zero",
                "zero",
            ],
            "value": [
                None,
                2.0,
                4.0,
                None,
                None,
                None,
                5.0,
                7.0,
                None,
                3.0,
                9.0,
                2.0,
                -2.0,
            ],
        }
    )


def _rows(df):
    """Compare multisets without depending on row order or null representation."""
    return Counter(
        tuple(None if pd.isna(value) else value for value in row)
        for row in df.itertuples(index=False, name=None)
    )


def _sql_result(frame, agg, keys=("key",)):
    pytest.importorskip("duckdb")
    sql_engine = DuckDBEngine()
    sql_fn = "avg" if agg == "mean" else agg
    group_cols = ", ".join(f'"{key}"' for key in keys)
    try:
        return sql_engine.query(
            f"SELECT {group_cols}, {sql_fn}(value) AS value "
            f"FROM input_frame GROUP BY {group_cols}",
            table="input_frame",
            df=frame,
        )
    finally:
        sql_engine._connection.close()


@pytest.mark.parametrize("agg", ["sum", "count", "mean", "avg", "min", "max"])
def test_null_key_group_matches_sql(engine, frame, agg):
    result = engine.groupby_agg(frame, ["key"], {"value": agg})
    null_group = result.loc[result["key"].isna()]
    assert len(null_group) == 1
    expected_null = {
        "sum": 6.0,
        "count": 2,
        "mean": 3.0,
        "avg": 3.0,
        "min": 2.0,
        "max": 4.0,
    }
    assert null_group["value"].iloc[0] == expected_null[agg]
    assert _rows(result) == _rows(_sql_result(frame, agg))


@pytest.mark.parametrize("dtype", ["float64", "Float64", "Int64"])
def test_all_null_sum_is_null(engine, frame, dtype):
    frame["value"] = frame["value"].astype(dtype)
    result = engine.groupby_agg(frame, ["key"], {"value": "sum"}).set_index("key")
    assert pd.isna(result.loc["empty", "value"])
    assert result.loc["partial", "value"] == 12
    assert result.loc["zero", "value"] == 0  # A real zero sum stays zero.


def test_mixed_aggregations_preserve_values_and_column_order(engine, frame):
    aggs = {
        "total": "sum",
        "counted": "count",
        "average": "mean",
        "minimum": "min",
        "maximum": "max",
        "other_total": "sum",
    }
    frame = frame[["key"]].assign(**{col: frame["value"] for col in aggs})
    result = engine.groupby_agg(frame, ["key"], aggs)
    assert list(result.columns) == ["key", *aggs]
    expected = pd.DataFrame(
        [
            [None, 6, 2, 3, 2, 4, 6],
            ["empty", None, 0, None, None, None, None],
            ["partial", 12, 2, 6, 5, 7, 12],
            ["full", 12, 2, 6, 3, 9, 12],
            ["zero", 0, 2, 0, -2, 2, 0],
        ],
        columns=["key", *aggs],
    )
    assert _rows(result) == _rows(expected)


def test_composite_null_keys_match_sql(engine):
    frame = pd.DataFrame(
        {
            "key": ["a", "a", None, None, None, "a"],
            "other": [None, None, "x", "x", None, "x"],
            "value": [1.0, 2.0, None, None, 5.0, 6.0],
        }
    )
    result = engine.groupby_agg(frame, ["key", "other"], {"value": "sum"})
    assert len(result) == 4
    assert _rows(result) == _rows(_sql_result(frame, "sum", ("key", "other")))


@pytest.mark.parametrize(
    "agg, expected",
    [
        ("first", [2, None, 5, 3, 2]),
        ("last", [4, None, 7, 9, -2]),
    ],
)
def test_first_last_skip_nulls_in_input_order(engine, frame, agg, expected):
    # This pins the pandas-family contract, not Spark's unordered first/last.
    result = engine.groupby_agg(frame, ["key"], {"value": agg})
    expected_frame = pd.DataFrame(
        {
            "key": [None, "empty", "partial", "full", "zero"],
            "value": expected,
        }
    )
    assert _rows(result) == _rows(expected_frame)


@pytest.mark.parametrize("agg", ["sum", "count", "mean", "min", "max"])
def test_spark_null_groups_agree_with_pandas(frame, agg, real_spark_session):
    # Explicit None values and schema ensure Spark receives SQL NULL, not NaN.
    records = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in frame.itertuples(index=False, name=None)
    ]
    sdf = real_spark_session.createDataFrame(records, "key string, value double")
    spark = SparkEngine(spark=real_spark_session)
    expected = spark.to_pandas(spark.groupby_agg(sdf, ["key"], {"value": agg}))
    result = PandasEngine().groupby_agg(frame, ["key"], {"value": agg})
    assert _rows(result) == _rows(expected)
