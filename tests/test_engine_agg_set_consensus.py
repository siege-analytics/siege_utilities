"""Behavioral coverage for the advertised shared aggregation set.

Consensus finding C17 (#1359): `_SUPPORTED_AGG_NAMES` advertises `stddev`
and `variance`, but the pandas-family engines passed those spellings
straight to `DataFrame.agg`, which only knows `std` and `var`. A caller
asking for an advertised aggregation got `AttributeError` instead of a
result. These tests run the entire advertised set on each pandas-family
engine and assert the numeric result, so a revert of the spelling map
turns them red.
"""
import importlib.util
import math

import pandas as pd
import pytest

from siege_utilities.engines.dataframe_engine import (
    DuckDBEngine,
    PandasEngine,
    _SUPPORTED_AGG_NAMES,
    _normalise_pandas_aggs,
)

# DuckDB is an optional `performance` extra; the geo-without-GDAL CI job runs
# this file without it. Skip the DuckDB parameter when the package is absent
# rather than fail at construction; Pandas coverage is retained unconditionally.
_HAVE_DUCKDB = importlib.util.find_spec("duckdb") is not None
_ENGINE_PARAMS = [
    pytest.param(PandasEngine, id="pandas"),
    pytest.param(
        DuckDBEngine,
        id="duckdb",
        marks=pytest.mark.skipif(
            not _HAVE_DUCKDB,
            reason="install duckdb (the 'performance' extra) to exercise DuckDBEngine",
        ),
    ),
]


def _sample_frame():
    # Two groups, each with enough rows for a defined sample std/var.
    return pd.DataFrame(
        {
            "g": ["a", "a", "a", "b", "b", "b"],
            "v": [1.0, 3.0, 5.0, 10.0, 14.0, 18.0],
        }
    )


def test_normalise_maps_sql_spellings_to_pandas():
    out = _normalise_pandas_aggs(
        {"a": "avg", "b": "stddev", "c": "variance", "d": "sum"}
    )
    assert out == {"a": "mean", "b": "std", "c": "var", "d": "sum"}


@pytest.mark.parametrize("engine_cls", _ENGINE_PARAMS)
def test_full_supported_agg_set_runs(engine_cls):
    """Every advertised aggregation must execute without AttributeError."""
    engine = engine_cls()
    df = _sample_frame()
    for agg in sorted(_SUPPORTED_AGG_NAMES):
        result = engine.groupby_agg(df, group_cols=["g"], agg_dict={"v": agg})
        assert "v" in result.columns, f"{agg} dropped the aggregated column"
        assert len(result) == 2, f"{agg} did not produce one row per group"


@pytest.mark.parametrize("engine_cls", _ENGINE_PARAMS)
def test_stddev_and_variance_match_pandas(engine_cls):
    """stddev/variance must compute the real statistic, not raise."""
    engine = engine_cls()
    df = _sample_frame()
    expected_std = df.groupby("g")["v"].std()  # ddof=1
    expected_var = df.groupby("g")["v"].var()

    got_std = engine.groupby_agg(df, group_cols=["g"], agg_dict={"v": "stddev"})
    got_var = engine.groupby_agg(df, group_cols=["g"], agg_dict={"v": "variance"})

    got_std = got_std.set_index("g")["v"]
    got_var = got_var.set_index("g")["v"]
    for grp in ("a", "b"):
        assert math.isclose(got_std[grp], expected_std[grp], rel_tol=1e-9)
        assert math.isclose(got_var[grp], expected_var[grp], rel_tol=1e-9)


def test_postgis_driver_side_agg_set():
    """PostGIS groupby_agg is driver-side pandas; same spelling contract."""
    try:
        from siege_utilities.engines.dataframe_engine import PostGISEngine
    except ImportError as exc:  # pragma: no cover - import guard
        pytest.skip(f"install sqlalchemy to exercise PostGISEngine: {exc}")
    try:
        engine = PostGISEngine("postgresql://u:p@localhost:5432/none")
    except ImportError as exc:
        pytest.skip(f"install sqlalchemy+psycopg to exercise PostGISEngine: {exc}")
    df = _sample_frame()
    out = engine.groupby_agg(df, group_cols=["g"], agg_dict={"v": "variance"})
    assert math.isclose(
        out.set_index("g")["v"]["a"],
        df.groupby("g")["v"].var()["a"],
        rel_tol=1e-9,
    )


def test_unknown_agg_still_raises_valueerror():
    """The validator error path must survive the spelling-map change."""
    engine = PandasEngine()
    with pytest.raises(ValueError, match="unsupported aggregation"):
        engine.groupby_agg(_sample_frame(), group_cols=["g"], agg_dict={"v": "median"})
