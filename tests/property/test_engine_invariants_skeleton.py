"""Skeleton Hypothesis-based property tests for cross-engine invariants.

Demonstrates the pattern that Phase 2 of Sprint E (#456) will scale
out across the full operation matrix from docs/engines/INVARIANTS.md.
Two concrete invariants are pinned here so the testing approach is
verifiable today; the rest is a follow-up.

The pattern:

    1. Hypothesis strategy generates a valid input frame.
    2. Run the operation through every available engine.
    3. Convert each engine's output back to pandas (the canonical
       reference) and assert equivalence under documented tolerances.

Engines whose deps aren't installed are skipped per-test via
``pytest.importorskip`` — CI matrices that don't ship DuckDB / Spark
won't fail; they just exercise fewer backends.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")
hyp_strategies = pytest.importorskip("hypothesis.strategies")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


# ---------------------------------------------------------------------------
# Hypothesis strategies — minimal set for the skeleton
# ---------------------------------------------------------------------------

# Small range so the test runs fast and Hypothesis can shrink effectively.
_SAFE_INTS = st.integers(min_value=-1000, max_value=1000)
_SAFE_FLOATS = st.floats(
    min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False,
)


@st.composite
def simple_int_frame(draw, max_rows: int = 50):
    """Generate a small DataFrame with two int columns named ``group`` and ``value``.

    Group keys are bounded so the property tests actually exercise
    multi-row groups rather than degenerating into one-row-per-group.
    """
    n = draw(st.integers(min_value=0, max_value=max_rows))
    groups = draw(st.lists(st.integers(min_value=0, max_value=5), min_size=n, max_size=n))
    values = draw(st.lists(_SAFE_INTS, min_size=n, max_size=n))
    return pd.DataFrame({"group": groups, "value": values})


# ---------------------------------------------------------------------------
# Engine probes — return None if the engine isn't available
# ---------------------------------------------------------------------------

def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def _duckdb_engine():
    """Construct DuckDBEngine or return None if DuckDB isn't installed."""
    try:
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        return DuckDBEngine()
    except ImportError:
        return None


# Spark + PostGIS are heavier to spin up. Phase 2 will add probes that
# share a single fixture-scoped session; for the skeleton we exercise
# pandas + DuckDB which run reliably in CI without external services.

_AVAILABLE_ENGINES = [
    ("pandas", _pandas_engine),
    ("duckdb", _duckdb_engine),
]


# ---------------------------------------------------------------------------
# Invariant 1: empty input → empty output, schema preserved
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("engine_name,engine_factory", _AVAILABLE_ENGINES)
def test_groupby_agg_empty_input_returns_empty(engine_name, engine_factory):
    """INVARIANTS.md Universal #1: empty input → empty output, never raise."""
    engine = engine_factory()
    if engine is None:
        pytest.skip(f"{engine_name} engine not available")

    empty = pd.DataFrame({"group": [], "value": []}).astype(
        {"group": "int64", "value": "int64"}
    )
    result = engine.groupby_agg(empty, group_cols=["group"], agg_dict={"value": "sum"})

    # Convert back to pandas — engines that return a native handle (e.g.
    # DuckDBPyRelation) materialize via to_pandas in Phase 2 strategies.
    if not isinstance(result, pd.DataFrame):
        result = result.to_pandas() if hasattr(result, "to_pandas") else pd.DataFrame(result)

    assert len(result) == 0


# ---------------------------------------------------------------------------
# Invariant 2: groupby_agg sum is set-equal across engines (sort-tolerant)
# ---------------------------------------------------------------------------

@given(df=simple_int_frame())
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_groupby_sum_agrees_across_engines(df):
    """INVARIANTS.md groupby_agg: sum is identical (as a set of rows)
    across every available backend. Phase 2 will broaden this to all
    agg names and add float / NaN / count variants."""
    expected_engine = _pandas_engine()
    expected = expected_engine.groupby_agg(
        df, group_cols=["group"], agg_dict={"value": "sum"},
    )
    expected_set = frozenset(
        (int(r.group), int(r.value)) for r in expected.itertuples()
    )

    for engine_name, factory in _AVAILABLE_ENGINES:
        if engine_name == "pandas":
            continue
        engine = factory()
        if engine is None:
            continue
        got = engine.groupby_agg(df, group_cols=["group"], agg_dict={"value": "sum"})
        if not isinstance(got, pd.DataFrame):
            got = got.to_pandas() if hasattr(got, "to_pandas") else pd.DataFrame(got)
        got_set = frozenset(
            (int(r.group), int(r.value)) for r in got.itertuples()
        )
        assert got_set == expected_set, (
            f"{engine_name} disagrees with pandas: "
            f"{got_set - expected_set} extra, {expected_set - got_set} missing"
        )
