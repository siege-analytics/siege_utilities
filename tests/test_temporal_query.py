"""Tests for temporal and spatial query functions."""

from datetime import date

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from siege_utilities.geo.temporal.query import (
    temporal_filter,
    spatial_query,
    point_in_boundary,
)


@pytest.fixture
def boundaries_with_dates():
    """Boundaries with valid_from/valid_to columns."""
    return gpd.GeoDataFrame(
        {
            "geoid": ["A", "B", "C"],
            "valid_from": [
                date(2010, 1, 1), date(2020, 1, 1), None
            ],
            "valid_to": [
                date(2019, 12, 31), None, None
            ],
            "vintage_year": [2010, 2020, 2020],
        },
        geometry=[box(0, 0, 1, 1), box(0, 0, 1, 1), box(2, 2, 3, 3)],
        crs="EPSG:4326",
    )


@pytest.fixture
def boundaries_vintages_only():
    """Boundaries with only vintage_year (no valid_from/valid_to)."""
    return gpd.GeoDataFrame(
        {
            "geoid": ["X", "Y"],
            "vintage_year": [2010, 2020],
        },
        geometry=[box(0, 0, 1, 1), box(0, 0, 1, 1)],
        crs="EPSG:4326",
    )


@pytest.fixture
def simple_polygons():
    """Two non-overlapping square polygons."""
    return gpd.GeoDataFrame(
        {
            "name": ["box_a", "box_b"],
            "population": [1000, 2000],
        },
        geometry=[box(0, 0, 10, 10), box(20, 20, 30, 30)],
        crs="EPSG:4326",
    )


class TestTemporalFilter:
    def test_filter_by_valid_dates(self, boundaries_with_dates):
        # 2015 should match A (2010-2019) and C (no dates = always valid)
        result = temporal_filter(
            boundaries_with_dates, date(2015, 6, 1)
        )
        geoids = set(result["geoid"])
        assert "A" in geoids
        assert "C" in geoids

    def test_filter_after_transition(self, boundaries_with_dates):
        # 2022 should match B (2020-None) and C (None-None)
        result = temporal_filter(
            boundaries_with_dates, date(2022, 6, 1)
        )
        geoids = set(result["geoid"])
        assert "B" in geoids
        assert "C" in geoids
        assert "A" not in geoids

    def test_fallback_to_vintage_year(self, boundaries_vintages_only):
        result = temporal_filter(
            boundaries_vintages_only, date(2022, 6, 1)
        )
        assert len(result) == 1
        assert result.iloc[0]["vintage_year"] == 2020

    def test_fallback_before_all_vintages(self, boundaries_vintages_only):
        result = temporal_filter(
            boundaries_vintages_only, date(2005, 1, 1)
        )
        # Should fall back to earliest vintage
        assert len(result) == 1
        assert result.iloc[0]["vintage_year"] == 2010

    def test_no_temporal_columns(self):
        gdf = gpd.GeoDataFrame(
            {"geoid": ["A"]},
            geometry=[box(0, 0, 1, 1)],
            crs="EPSG:4326",
        )
        result = temporal_filter(gdf, date(2022, 1, 1))
        assert len(result) == 1


class TestSpatialQuery:
    def test_point_intersects_polygon(self, simple_polygons):
        pts = gpd.GeoDataFrame(
            {"id": [1]},
            geometry=[Point(5, 5)],
            crs="EPSG:4326",
        )
        result = spatial_query(simple_polygons, pts)
        assert len(result) == 1
        assert result.iloc[0]["name"] == "box_a"

    def test_point_outside_polygons(self, simple_polygons):
        pts = gpd.GeoDataFrame(
            {"id": [1]},
            geometry=[Point(50, 50)],
            crs="EPSG:4326",
        )
        result = spatial_query(simple_polygons, pts)
        assert len(result) == 0

    def test_multiple_points(self, simple_polygons):
        pts = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[Point(5, 5), Point(25, 25)],
            crs="EPSG:4326",
        )
        result = spatial_query(simple_polygons, pts)
        assert len(result) == 2


class TestPointInBoundary:
    def test_point_found(self, simple_polygons):
        result = point_in_boundary(simple_polygons, lon=5, lat=5)
        assert len(result) == 1
        assert result.iloc[0]["name"] == "box_a"

    def test_point_not_found(self, simple_polygons):
        result = point_in_boundary(simple_polygons, lon=50, lat=50)
        assert len(result) == 0

    def test_point_in_second_polygon(self, simple_polygons):
        result = point_in_boundary(simple_polygons, lon=25, lat=25)
        assert len(result) == 1
        assert result.iloc[0]["name"] == "box_b"
