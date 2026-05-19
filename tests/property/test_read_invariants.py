"""Round-trip property tests for read_csv / read_parquet.

INVARIANTS.md says read_parquet has no tolerance (parquet is
self-describing; divergences are bugs). read_csv has documented
tolerance for numeric dtype inference but the column set and row
contents must round-trip identically.

These tests write a Hypothesis-generated frame to disk via pandas,
read it back via each engine, and assert equivalence after a
to_pandas() normalisation.
"""

from __future__ import annotations

from collections import Counter

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


@st.composite
def simple_frame(draw, max_rows: int = 20):
    n = draw(st.integers(min_value=0, max_value=max_rows))
    ids = draw(st.lists(st.integers(min_value=0, max_value=1000), min_size=n, max_size=n))
    values = draw(st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=n, max_size=n,
    ))
    return pd.DataFrame({"id": ids, "value": values})


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def _duckdb_engine_or_skip():
    try:
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        return DuckDBEngine()
    except ImportError:
        pytest.skip("DuckDB not installed")


def _rows_as_counter(df) -> Counter:
    return Counter(
        (int(r.id), round(float(r.value), 6)) for r in df.itertuples()
    )


@given(df=simple_frame())
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_read_csv_pandas_round_trip(df, tmp_path):
    path = tmp_path / "rt.csv"
    df.to_csv(path, index=False)

    pandas_back = _pandas_engine().read_csv(str(path))
    assert _rows_as_counter(pandas_back) == _rows_as_counter(df)


@given(df=simple_frame())
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_read_parquet_pandas_round_trip(df, tmp_path):
    pytest.importorskip("pyarrow")
    path = tmp_path / "rt.parquet"
    df.to_parquet(path, index=False)

    pandas_back = _pandas_engine().read_parquet(str(path))
    assert _rows_as_counter(pandas_back) == _rows_as_counter(df)


@given(df=simple_frame())
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_read_csv_pandas_and_duckdb_agree(df, tmp_path):
    """The two engines must read the same CSV to the same row set
    after a to_pandas() normalisation. Sort order is not asserted."""
    path = tmp_path / "rt.csv"
    df.to_csv(path, index=False)

    pandas_engine = _pandas_engine()
    duckdb_engine = _duckdb_engine_or_skip()

    pandas_back = pandas_engine.read_csv(str(path))
    duckdb_back = duckdb_engine.to_pandas(duckdb_engine.read_csv(str(path)))
    assert _rows_as_counter(pandas_back) == _rows_as_counter(duckdb_back)


def test_read_csv_empty_file_returns_empty_frame(tmp_path):
    """A CSV with only a header must read back as a zero-row frame
    with the right column set, not raise."""
    path = tmp_path / "empty.csv"
    path.write_text("id,value\n")

    pandas_back = _pandas_engine().read_csv(str(path))
    assert len(pandas_back) == 0
    assert list(pandas_back.columns) == ["id", "value"]
