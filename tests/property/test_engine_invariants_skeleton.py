"""Skeleton Hypothesis-based property tests for cross-engine invariants.

DuckDBEngine.groupby_agg currently dispatches to pandas when handed a
pandas DataFrame, so comparing the two engines via the engine API
proves nothing — both branches run the same pandas code. To actually
exercise a different backend, this skeleton drops down to raw DuckDB
SQL via the duckdb python API and compares the SQL result to the
pandas reference.

Phase 2 of #456 will scale this pattern across the operation matrix in
docs/engines/INVARIANTS.md and replace the raw-SQL probe with a proper
DuckDBEngine SQL path once that exists.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")
hyp_strategies = pytest.importorskip("hypothesis.strategies")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


_SAFE_INTS = st.integers(min_value=-1000, max_value=1000)


@st.composite
def simple_int_frame(draw, max_rows: int = 50):
    n = draw(st.integers(min_value=0, max_value=max_rows))
    groups = draw(st.lists(st.integers(min_value=0, max_value=5), min_size=n, max_size=n))
    values = draw(st.lists(_SAFE_INTS, min_size=n, max_size=n))
    return pd.DataFrame({"group": groups, "value": values})


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def test_pandas_groupby_sum_empty_input_returns_empty():
    engine = _pandas_engine()
    empty = pd.DataFrame({"group": [], "value": []}).astype(
        {"group": "int64", "value": "int64"}
    )
    result = engine.groupby_agg(empty, group_cols=["group"], agg_dict={"value": "sum"})
    assert len(result) == 0
    assert list(result.columns) == ["group", "value"]
    assert result["group"].dtype == "int64"
    assert result["value"].dtype == "int64"


@given(df=simple_int_frame())
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_pandas_engine_agrees_with_raw_duckdb_sql(df):
    """PandasEngine.groupby_agg sum agrees with the same query
    executed through raw DuckDB SQL on the identical input.

    This is the only place in the property suite that currently
    crosses a real engine boundary; phase 2 will broaden it.
    """
    duckdb = pytest.importorskip("duckdb")

    from collections import Counter

    pandas_result = _pandas_engine().groupby_agg(
        df, group_cols=["group"], agg_dict={"value": "sum"},
    )
    pandas_rows = Counter(
        (int(r.group), int(r.value)) for r in pandas_result.itertuples()
    )

    con = duckdb.connect(":memory:")
    try:
        con.register("input_df", df)
        sql_result = con.sql(
            "SELECT \"group\", SUM(value) AS value FROM input_df GROUP BY \"group\""
        ).to_df()
    finally:
        con.close()

    sql_rows = Counter(
        (int(r.group), int(r.value)) for r in sql_result.itertuples()
    )

    assert pandas_rows == sql_rows, (
        f"Pandas engine and DuckDB SQL disagree: "
        f"pandas-only={pandas_rows - sql_rows}, sql-only={sql_rows - pandas_rows}"
    )
