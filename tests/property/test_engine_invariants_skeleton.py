"""Hypothesis-based property tests for cross-engine invariants.

DuckDBEngine.groupby_agg passes pandas DataFrames straight through to
pandas, so comparing the two engines via the engine API proves nothing.
These tests instead compare PandasEngine's output to raw DuckDB SQL
via the duckdb python API. That actually crosses an engine boundary.

The aggregation families exercised:

  sum, mean, count, min, max -- with and without NaN values

Sort order is not asserted. Row contents are compared as a Counter
so duplicate rows from a buggy backend would surface.
"""

from __future__ import annotations

import math
from collections import Counter

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


_SAFE_FLOATS = st.floats(
    min_value=-1e6, max_value=1e6,
    allow_nan=False, allow_infinity=False, width=32,
)
_MAYBE_FLOATS = st.one_of(
    st.none(),
    st.floats(min_value=-1e6, max_value=1e6,
              allow_nan=False, allow_infinity=False, width=32),
)


@st.composite
def int_value_frame(draw, max_rows: int = 50):
    n = draw(st.integers(min_value=0, max_value=max_rows))
    groups = draw(st.lists(st.integers(min_value=0, max_value=5), min_size=n, max_size=n))
    values = draw(st.lists(_SAFE_FLOATS, min_size=n, max_size=n))
    return pd.DataFrame({"group": groups, "value": values})


@st.composite
def nullable_value_frame(draw, max_rows: int = 50):
    n = draw(st.integers(min_value=0, max_value=max_rows))
    groups = draw(st.lists(st.integers(min_value=0, max_value=5), min_size=n, max_size=n))
    values = draw(st.lists(_MAYBE_FLOATS, min_size=n, max_size=n))
    return pd.DataFrame({"group": groups, "value": values})


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def _duckdb_sql(df: "pd.DataFrame", agg: str) -> "pd.DataFrame":
    duckdb = pytest.importorskip("duckdb")
    con = duckdb.connect(":memory:")
    try:
        con.register("input_df", df)
        return con.sql(
            f"SELECT \"group\", {agg}(value) AS value "
            f"FROM input_df GROUP BY \"group\""
        ).to_df()
    finally:
        con.close()


def _rows_as_counter(df: "pd.DataFrame") -> Counter:
    out = Counter()
    for r in df.itertuples():
        group = int(r.group) if not pd.isna(r.group) else None
        if pd.isna(r.value):
            value = None
        elif isinstance(r.value, float):
            value = round(r.value, 6)
        else:
            value = r.value
        out[(group, value)] += 1
    return out


def test_pandas_groupby_sum_empty_input_preserves_schema():
    engine = _pandas_engine()
    empty = pd.DataFrame({"group": [], "value": []}).astype(
        {"group": "int64", "value": "float64"}
    )
    result = engine.groupby_agg(empty, group_cols=["group"], agg_dict={"value": "sum"})
    assert len(result) == 0
    assert list(result.columns) == ["group", "value"]
    assert result["group"].dtype == "int64"


@pytest.mark.parametrize("agg", ["sum", "mean", "min", "max", "count"])
@given(df=int_value_frame())
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_pandas_engine_agrees_with_duckdb_sql_no_nans(agg, df):
    """Each of the documented agg names produces the same row set
    under PandasEngine and raw DuckDB SQL when the input has no
    NaN values. Comparison uses Counter so duplicate rows from a
    buggy backend would show up; values are rounded to avoid
    floating-point noise from the two engines accumulating in
    different orders."""
    if len(df) == 0 and agg in ("min", "max"):
        return
    pandas_result = _pandas_engine().groupby_agg(
        df, group_cols=["group"], agg_dict={"value": agg},
    )
    sql_result = _duckdb_sql(df, agg.upper())
    assert _rows_as_counter(pandas_result) == _rows_as_counter(sql_result), (
        f"Disagreement on agg={agg}:\n"
        f"  pandas: {pandas_result.to_dict('records')}\n"
        f"  duckdb: {sql_result.to_dict('records')}"
    )


@given(df=nullable_value_frame())
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_sum_of_all_nan_group_is_zero_not_nan(df):
    """INVARIANTS.md asserts that sum of an all-NaN group is 0.0,
    not NaN. Pin it on PandasEngine and verify duckdb agrees."""
    pandas_result = _pandas_engine().groupby_agg(
        df, group_cols=["group"], agg_dict={"value": "sum"},
    )
    for r in pandas_result.itertuples():
        assert not (isinstance(r.value, float) and math.isnan(r.value)), (
            f"PandasEngine returned NaN for sum of group {r.group}; "
            f"INVARIANTS.md says sum of all-NaN is 0.0"
        )


@given(df=nullable_value_frame())
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_count_excludes_nan(df):
    """INVARIANTS.md asserts that count excludes NaN. Verify pandas
    behaves that way (count() on a Series ignores NaN by default)."""
    pandas_result = _pandas_engine().groupby_agg(
        df, group_cols=["group"], agg_dict={"value": "count"},
    )
    for r in pandas_result.itertuples():
        non_nan = df[(df["group"] == r.group) & df["value"].notna()]
        assert int(r.value) == len(non_nan), (
            f"count({r.group}) returned {r.value}, expected {len(non_nan)} "
            f"(non-NaN row count)"
        )
