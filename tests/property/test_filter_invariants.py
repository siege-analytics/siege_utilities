"""Cross-engine property tests for DataFrameEngine.filter.

Currently exercises PandasEngine against raw DuckDB SQL since
DuckDBEngine.filter passes pandas DataFrames straight through to
pandas. SparkEngine / PostGISEngine probes belong in a Spark-marked
follow-up because they need fixture-scoped session setup.
"""

from __future__ import annotations

from collections import Counter

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


@st.composite
def filterable_frame(draw, max_rows: int = 40):
    n = draw(st.integers(min_value=0, max_value=max_rows))
    group = draw(st.lists(st.integers(min_value=0, max_value=4), min_size=n, max_size=n))
    value = draw(st.lists(st.integers(min_value=-50, max_value=50), min_size=n, max_size=n))
    return pd.DataFrame({"group": group, "value": value})


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def _duckdb_filter_sql(df, sql_predicate: str) -> "pd.DataFrame":
    duckdb = pytest.importorskip("duckdb")
    con = duckdb.connect(":memory:")
    try:
        con.register("input_df", df)
        return con.sql(
            f"SELECT * FROM input_df WHERE {sql_predicate}"
        ).to_df()
    finally:
        con.close()


def _rows_as_counter(df) -> Counter:
    return Counter((int(r.group), int(r.value)) for r in df.itertuples())


def test_filter_empty_input_returns_empty_with_schema():
    empty = pd.DataFrame({"group": [], "value": []}).astype(
        {"group": "int64", "value": "int64"}
    )
    result = _pandas_engine().filter(empty, empty["value"] > 0)
    assert len(result) == 0
    assert list(result.columns) == ["group", "value"]


@given(df=filterable_frame())
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_filter_value_gt_zero_agrees_with_duckdb(df):
    pandas_result = _pandas_engine().filter(df, df["value"] > 0)
    sql_result = _duckdb_filter_sql(df, "value > 0")
    assert _rows_as_counter(pandas_result) == _rows_as_counter(sql_result)


@given(df=filterable_frame())
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_filter_group_eq_zero_agrees_with_duckdb(df):
    pandas_result = _pandas_engine().filter(df, df["group"] == 0)
    sql_result = _duckdb_filter_sql(df, "\"group\" = 0")
    assert _rows_as_counter(pandas_result) == _rows_as_counter(sql_result)


def test_filter_resets_index():
    """The PandasEngine docs imply ordered, contiguous integer index
    on output (`.reset_index(drop=True)` in the impl). Pin it."""
    df = pd.DataFrame({"group": [0, 1, 2, 3, 4], "value": [10, 20, 30, 40, 50]})
    result = _pandas_engine().filter(df, df["value"] > 25)
    assert list(result.index) == list(range(len(result)))
