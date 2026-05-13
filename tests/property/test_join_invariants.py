"""Cross-engine property tests for DataFrameEngine.join.

Exercises all four `how` values (inner / left / right / outer)
against raw DuckDB SQL with the same JOIN semantics. Sort order is
not asserted; multiset comparison via Counter.
"""

from __future__ import annotations

from collections import Counter

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


@st.composite
def joinable_frames(draw, max_rows: int = 20):
    """Build a left/right pair sharing a `key` column."""
    left_n = draw(st.integers(min_value=0, max_value=max_rows))
    right_n = draw(st.integers(min_value=0, max_value=max_rows))
    left_keys = draw(st.lists(st.integers(min_value=0, max_value=8), min_size=left_n, max_size=left_n))
    right_keys = draw(st.lists(st.integers(min_value=0, max_value=8), min_size=right_n, max_size=right_n))
    left_vals = draw(st.lists(st.integers(min_value=-30, max_value=30), min_size=left_n, max_size=left_n))
    right_vals = draw(st.lists(st.integers(min_value=-30, max_value=30), min_size=right_n, max_size=right_n))
    left = pd.DataFrame({"key": left_keys, "left_value": left_vals})
    right = pd.DataFrame({"key": right_keys, "right_value": right_vals})
    return left, right


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def _duckdb_join(left, right, how: str) -> "pd.DataFrame":
    duckdb = pytest.importorskip("duckdb")
    sql_join = {
        "inner": "INNER JOIN",
        "left": "LEFT JOIN",
        "right": "RIGHT JOIN",
        "outer": "FULL OUTER JOIN",
    }[how]
    con = duckdb.connect(":memory:")
    try:
        con.register("L", left)
        con.register("R", right)
        # Use COALESCE on the join key to mirror pandas' behaviour: when
        # the key is absent on a side (left/right/outer), pandas keeps
        # it as the value from the present side. SQL's natural USING
        # gives the same result via the consolidated key.
        return con.sql(
            f"SELECT COALESCE(L.key, R.key) AS key, "
            f"L.left_value AS left_value, "
            f"R.right_value AS right_value "
            f"FROM L {sql_join} R ON L.key = R.key"
        ).to_df()
    finally:
        con.close()


def _rows_as_counter(df) -> Counter:
    def _cell(v):
        if pd.isna(v):
            return None
        return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return Counter(
        (_cell(r.key), _cell(r.left_value), _cell(r.right_value))
        for r in df.itertuples()
    )


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
def test_join_empty_inputs_return_empty(how):
    empty_left = pd.DataFrame({"key": [], "left_value": []}).astype(
        {"key": "int64", "left_value": "int64"}
    )
    empty_right = pd.DataFrame({"key": [], "right_value": []}).astype(
        {"key": "int64", "right_value": "int64"}
    )
    result = _pandas_engine().join(empty_left, empty_right, on="key", how=how)
    assert len(result) == 0
    assert set(result.columns) == {"key", "left_value", "right_value"}


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
@given(frames=joinable_frames())
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_join_agrees_with_duckdb(how, frames):
    """For each how value, pandas merge and DuckDB JOIN produce the
    same multiset of rows."""
    left, right = frames
    pandas_result = _pandas_engine().join(left, right, on="key", how=how)
    sql_result = _duckdb_join(left, right, how)
    assert _rows_as_counter(pandas_result) == _rows_as_counter(sql_result), (
        f"how={how} pandas != duckdb:\n"
        f"  left=\n{left}\n  right=\n{right}\n"
        f"  pandas=\n{pandas_result}\n  duckdb=\n{sql_result}"
    )
