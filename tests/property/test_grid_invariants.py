"""Determinism property tests for index_points / index_polygon.

INVARIANTS.md says index_points is deterministic across backends:
one cell ID per row, same value for the same (lat, lon, grid,
resolution) tuple. index_polygon may produce zero / one / many cell
IDs per row, but the cell set for a given polygon at a given
resolution must be deterministic.

These tests don't compare engine to engine yet -- the
DataFrameEngine.index_points implementation round-trips through
pandas, so single-engine determinism is what's pinned. Engine
divergence comes in Phase 3 once SparkEngine has a native override.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


_LAT = st.floats(min_value=-85.0, max_value=85.0, allow_nan=False, allow_infinity=False)
_LON = st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False)


@st.composite
def points_frame(draw, max_rows: int = 30):
    n = draw(st.integers(min_value=1, max_value=max_rows))
    lats = draw(st.lists(_LAT, min_size=n, max_size=n))
    lons = draw(st.lists(_LON, min_size=n, max_size=n))
    return pd.DataFrame({"lat": lats, "lon": lons})


@given(df=points_frame())
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_h3_index_points_deterministic(df):
    pytest.importorskip("h3")
    from siege_utilities.geo.grids import index_points

    first = index_points(df, "lat", "lon", resolution=8)
    second = index_points(df, "lat", "lon", resolution=8)
    assert list(first) == list(second), (
        "h3 index_points must be deterministic for the same (lat,lon,resolution)"
    )


@given(df=points_frame())
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_s2_index_points_deterministic(df):
    pytest.importorskip("s2sphere")
    from siege_utilities.geo.grids import index_points

    first = index_points(df, "lat", "lon", level=12)
    second = index_points(df, "lat", "lon", level=12)
    assert list(first) == list(second), (
        "s2 index_points must be deterministic for the same (lat,lon,level)"
    )


def test_h3_index_points_one_cell_per_row():
    pytest.importorskip("h3")
    from siege_utilities.geo.grids import index_points

    df = pd.DataFrame({
        "lat": [37.7749, 40.7128, 51.5074],
        "lon": [-122.4194, -74.0060, -0.1278],
    })
    result = index_points(df, "lat", "lon", resolution=8)
    assert len(result) == len(df), "exactly one cell ID per row"
    assert result.notna().all(), "no row maps to no cell"


def test_h3_resolution_changes_cell_id():
    """Different resolutions produce different cell IDs for the same
    point. Pin the property the docs imply when they say resolution
    is part of the (point, grid, resolution) key."""
    pytest.importorskip("h3")
    from siege_utilities.geo.grids import index_points

    df = pd.DataFrame({"lat": [37.7749], "lon": [-122.4194]})
    res_6 = index_points(df, "lat", "lon", resolution=6)
    res_9 = index_points(df, "lat", "lon", resolution=9)
    assert res_6.iloc[0] != res_9.iloc[0]


def test_index_polygon_is_deterministic():
    pytest.importorskip("h3")
    shapely = pytest.importorskip("shapely.geometry")
    from siege_utilities.geo.grids import index_polygon

    # A 1-degree square; covers a stable cell set at any given resolution.
    poly = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    first = list(index_polygon(poly, grid="h3", resolution=6))
    second = list(index_polygon(poly, grid="h3", resolution=6))
    assert first == second
    assert len(first) > 0, "a 1-deg square at h3 res 6 must cover at least one cell"
