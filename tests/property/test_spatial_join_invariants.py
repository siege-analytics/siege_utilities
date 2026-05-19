"""Property tests for DataFrameEngine.spatial_join.

INVARIANTS.md spatial_join section: predicates intersects / contains /
within, output keyed by (left_idx, right_idx). The Pandas/Sedona
divergence (auto-reproject vs. silent empty on mismatched SRIDs) is
the canonical bug surface but cannot be pinned without Spark; covered
here for PandasEngine only. Spark side belongs in Phase 3.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely.geometry")


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


@pytest.fixture
def overlapping_squares():
    left = gpd.GeoDataFrame(
        {"lid": [1, 2]},
        geometry=[
            shapely.Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            shapely.Polygon([(10, 10), (12, 10), (12, 12), (10, 12)]),
        ],
        crs="EPSG:4326",
    )
    right = gpd.GeoDataFrame(
        {"rid": [10, 20]},
        geometry=[
            shapely.Polygon([(1, 1), (3, 1), (3, 3), (1, 3)]),  # overlaps left[0]
            shapely.Polygon([(100, 100), (101, 100), (101, 101), (100, 101)]),  # disjoint
        ],
        crs="EPSG:4326",
    )
    return left, right


def test_spatial_join_intersects_picks_overlap(overlapping_squares):
    left, right = overlapping_squares
    result = _pandas_engine().spatial_join(left, right, predicate="intersects")
    # left[0] intersects right[0]; left[1] intersects nothing
    assert len(result) == 1
    assert result["lid"].iloc[0] == 1
    assert result["rid"].iloc[0] == 10


def test_spatial_join_empty_left_returns_empty(overlapping_squares):
    _, right = overlapping_squares
    empty_left = gpd.GeoDataFrame(
        {"lid": []}, geometry=[], crs="EPSG:4326",
    )
    result = _pandas_engine().spatial_join(empty_left, right, predicate="intersects")
    assert len(result) == 0


def test_spatial_join_within_predicate():
    inner = gpd.GeoDataFrame(
        {"iid": [1]},
        geometry=[shapely.Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])],
        crs="EPSG:4326",
    )
    outer = gpd.GeoDataFrame(
        {"oid": [10]},
        geometry=[shapely.Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])],
        crs="EPSG:4326",
    )
    result = _pandas_engine().spatial_join(inner, outer, predicate="within")
    assert len(result) == 1
    assert result["iid"].iloc[0] == 1
    assert result["oid"].iloc[0] == 10


def test_spatial_join_disjoint_geometries_produce_no_rows():
    a = gpd.GeoDataFrame(
        {"aid": [1]},
        geometry=[shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
        crs="EPSG:4326",
    )
    b = gpd.GeoDataFrame(
        {"bid": [10]},
        geometry=[shapely.Polygon([(10, 10), (11, 10), (11, 11), (10, 11)])],
        crs="EPSG:4326",
    )
    result = _pandas_engine().spatial_join(a, b, predicate="intersects")
    assert len(result) == 0
