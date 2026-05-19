"""Tests for siege_utilities.geo.s2_utils."""

from __future__ import annotations

import pandas as pd
import pytest

from siege_utilities.geo import s2_utils

pytestmark = pytest.mark.skipif(
    not s2_utils.S2_AVAILABLE, reason="s2sphere not installed"
)


# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

class TestLevelForArea:
    def test_us_state_area(self):
        # ~196,600 km² sits between S2 level 4 (~379k) and level 5 (~95k);
        # log-closest is level 4.
        assert s2_utils.s2_level_for_area(196_600.0) in (4, 5)

    def test_invalid_area_raises(self):
        with pytest.raises(ValueError, match="positive"):
            s2_utils.s2_level_for_area(0.0)
        with pytest.raises(ValueError, match="positive"):
            s2_utils.s2_level_for_area(-1.0)

    def test_returns_in_range(self):
        for km2 in (1e8, 1e4, 1.0, 1e-4, 1e-8):
            level = s2_utils.s2_level_for_area(km2)
            assert 0 <= level <= 30

    def test_monotonic(self):
        prev = s2_utils.S2_LEVEL_AREA_KM2[0]
        for level in range(1, 31):
            assert s2_utils.S2_LEVEL_AREA_KM2[level] < prev
            prev = s2_utils.S2_LEVEL_AREA_KM2[level]


class TestLevelForAdminLevel:
    def test_state_returns_low_level(self):
        # state ~196,600 km² → log-closest is level 4 (or 5)
        assert s2_utils.s2_level_for_admin_level("state") in (4, 5)

    def test_levels_are_monotonic(self):
        """Larger admin units → lower S2 levels."""
        levels = ["state", "county", "zcta", "tract", "block_group", "block"]
        s2_levels = [s2_utils.s2_level_for_admin_level(L) for L in levels]
        for i in range(len(s2_levels) - 1):
            assert s2_levels[i] <= s2_levels[i + 1]

    def test_aliases(self):
        assert s2_utils.s2_level_for_admin_level("zip") == \
            s2_utils.s2_level_for_admin_level("zcta")
        assert s2_utils.s2_level_for_admin_level("BG") == \
            s2_utils.s2_level_for_admin_level("block_group")

    def test_unknown_level_raises(self):
        with pytest.raises(ValueError, match="Unknown admin level"):
            s2_utils.s2_level_for_admin_level("metro")


# ---------------------------------------------------------------------------
# Point indexing
# ---------------------------------------------------------------------------

class TestIndexPoints:
    def test_assigns_cell_per_row(self):
        df = pd.DataFrame({"lat": [33.5, 40.7], "lon": [-86.8, -74.0]})
        out = s2_utils.s2_index_points(df, "lat", "lon", level=10)
        assert len(out) == 2
        assert out.iloc[0] != out.iloc[1]
        assert all(isinstance(v, str) for v in out)  # default as_token=True

    def test_int_id_form(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        out = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False)
        # pandas may wrap integer cells as numpy.uint64; `int(...)` should
        # round-trip without loss.
        v = out.iloc[0]
        assert int(v) == v
        assert v > 0  # valid S2 cell IDs are non-zero

    def test_invalid_level_raises(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        with pytest.raises(ValueError, match="0-30"):
            s2_utils.s2_index_points(df, "lat", "lon", level=31)

    def test_missing_column_raises(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        with pytest.raises(ValueError, match="not found"):
            s2_utils.s2_index_points(df, "latitude", "lon")


# ---------------------------------------------------------------------------
# Polygon coverage
# ---------------------------------------------------------------------------

class TestIndexPolygon:
    @pytest.fixture
    def square(self):
        from shapely.geometry import box
        # ~1° square near Birmingham, AL
        return box(-87.0, 33.0, -86.0, 34.0)

    def test_single_level_returns_set(self, square):
        cells = s2_utils.s2_index_polygon(square, level=8, refine=False)
        assert isinstance(cells, set)
        assert len(cells) > 0

    def test_higher_level_more_cells(self, square):
        few = s2_utils.s2_index_polygon(square, level=8, refine=False)
        many = s2_utils.s2_index_polygon(square, level=10, refine=False)
        assert len(many) > len(few)

    def test_refine_filters_to_polygon(self):
        from shapely.geometry import Polygon
        # An L-shaped polygon: bbox covers a square but the polygon
        # excludes one corner.
        l_shape = Polygon([
            (0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2), (0, 0),
        ])
        bbox_only = s2_utils.s2_index_polygon(l_shape, level=10, refine=False)
        refined = s2_utils.s2_index_polygon(l_shape, level=10, refine=True)
        assert len(refined) < len(bbox_only), (
            "refine should drop cells in the excluded corner"
        )


class TestRegionCover:
    @pytest.fixture
    def bbox_polygon(self):
        from shapely.geometry import box
        # Roughly Alabama's bbox.
        return box(-88.5, 30.2, -84.9, 35.0)

    def test_max_cells_respected(self, bbox_polygon):
        cells = s2_utils.s2_region_cover(
            bbox_polygon, min_level=4, max_level=14, max_cells=20,
        )
        assert len(cells) <= 20
        assert len(cells) > 0

    def test_returns_int_ids(self, bbox_polygon):
        cells = s2_utils.s2_region_cover(bbox_polygon, max_cells=5)
        assert all(isinstance(c, int) for c in cells)

    def test_min_max_level_constrains_levels(self, bbox_polygon):
        import s2sphere
        cells = s2_utils.s2_region_cover(
            bbox_polygon, min_level=8, max_level=10, max_cells=100,
        )
        for cid in cells:
            level = s2sphere.CellId(cid).level()
            assert 8 <= level <= 10

    def test_max_cells_must_be_positive(self, bbox_polygon):
        with pytest.raises(ValueError, match="max_cells"):
            s2_utils.s2_region_cover(bbox_polygon, max_cells=0)

    def test_min_must_be_le_max(self, bbox_polygon):
        with pytest.raises(ValueError, match="min_level"):
            s2_utils.s2_region_cover(bbox_polygon, min_level=10, max_level=5)


class TestCellsToRanges:
    def test_each_range_is_pair(self):
        from shapely.geometry import box
        cells = s2_utils.s2_region_cover(
            box(-1, -1, 1, 1), max_cells=10,
        )
        ranges = s2_utils.s2_cells_to_ranges(cells)
        assert len(ranges) == len(cells)
        for lo, hi in ranges:
            assert isinstance(lo, int)
            assert isinstance(hi, int)
            assert lo <= hi


# ---------------------------------------------------------------------------
# Cell metadata
# ---------------------------------------------------------------------------

class TestCellToBoundary:
    def test_returns_four_points(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=10).iloc[0]
        boundary = s2_utils.s2_cell_to_boundary(cell)
        assert len(boundary) == 4
        for lat, lng in boundary:
            assert -90.0 <= lat <= 90.0
            assert -180.0 <= lng <= 180.0


class TestKring:
    def test_k0_returns_self(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        ring = s2_utils.s2_kring(cell, k=0)
        assert ring == [cell]

    def test_k1_includes_self_plus_neighbors(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        ring = s2_utils.s2_kring(cell, k=1)
        assert cell in ring
        assert len(ring) >= 5  # self + at least 4 neighbors (corners can dup)

    def test_negative_k_raises(self):
        with pytest.raises(ValueError, match="k must be"):
            s2_utils.s2_kring(0, k=-1)


class TestDistance:
    def test_self_distance_zero(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        assert s2_utils.s2_distance(cell, cell) == 0

    def test_neighbor_distance_one(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        ring = s2_utils.s2_kring(cell, k=1)
        # All cells in ring 1 are distance 0 (self) or 1
        non_self = [c for c in ring if c != cell]
        assert non_self
        for c in non_self:
            assert s2_utils.s2_distance(cell, c) == 1

    def test_level_mismatch_raises(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        a = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        b = s2_utils.s2_parent(a, 8)
        with pytest.raises(ValueError, match="level must match"):
            s2_utils.s2_distance(a, b)


class TestParentChildren:
    def test_parent_at_lower_level(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=12, as_token=False).iloc[0]
        parent = s2_utils.s2_parent(cell, level=8)
        # Check via s2sphere directly
        import s2sphere
        assert s2sphere.CellId(parent).level() == 8

    def test_parent_at_higher_level_raises(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=8, as_token=False).iloc[0]
        with pytest.raises(ValueError, match="target level"):
            s2_utils.s2_parent(cell, level=12)

    def test_children_returns_four(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        children = s2_utils.s2_children(cell)
        assert len(children) == 4

    def test_children_at_leaf_raises(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        leaf = s2_utils.s2_index_points(df, "lat", "lon", level=30, as_token=False).iloc[0]
        with pytest.raises(ValueError, match="leaf level"):
            s2_utils.s2_children(leaf)


class TestIDConversions:
    def test_token_round_trip(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        cell_int = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=False).iloc[0]
        token = s2_utils.s2_cell_id_to_token(cell_int)
        recovered = s2_utils.s2_token_to_cell_id(token)
        assert recovered == cell_int

    def test_uint64_passthrough(self):
        assert s2_utils.s2_cell_id_to_uint64(123456789) == 123456789

    def test_uint64_from_token(self):
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        token = s2_utils.s2_index_points(df, "lat", "lon", level=10, as_token=True).iloc[0]
        as_int = s2_utils.s2_cell_id_to_uint64(token)
        assert isinstance(as_int, int)

    def test_uint64_invalid_type_raises(self):
        # Things that have no sensible int conversion.
        with pytest.raises(TypeError):
            s2_utils.s2_cell_id_to_uint64(["not", "an", "id"])
        with pytest.raises(TypeError):
            s2_utils.s2_cell_id_to_uint64({"key": "value"})


class TestBboxToCells:
    def test_basic_bbox(self):
        cells = s2_utils.s2_bbox_to_cells(33.0, -87.0, 34.0, -86.0, max_cells=8)
        assert 0 < len(cells) <= 8

    def test_max_cells_zero_raises(self):
        with pytest.raises(ValueError, match="max_cells"):
            s2_utils.s2_bbox_to_cells(33.0, -87.0, 34.0, -86.0, max_cells=0)


# ---------------------------------------------------------------------------
# Spatial join
# ---------------------------------------------------------------------------

class TestSpatialJoin:
    def test_basic_join(self):
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            pytest.skip("geopandas / shapely not installed")
        # Two boxes side by side; two points, one in each box.
        gdf = gpd.GeoDataFrame({
            "name": ["west", "east"],
            "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)],
        })
        points = pd.DataFrame({
            "id": ["p1", "p2"],
            "lat": [0.5, 0.5],
            "lon": [0.5, 1.5],
        })
        joined = s2_utils.s2_spatial_join(points, gdf, "lat", "lon", level=12)
        assert len(joined) == 2
        assert set(joined["name"]) == {"west", "east"}

    def test_no_matches_returns_empty_with_schema(self):
        """Empty-match path keeps the polygon-attrs columns on the result
        (early-return at lines 415-419 of s2_utils — caught by CodeRabbit)."""
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            pytest.skip("geopandas / shapely not installed")
        gdf = gpd.GeoDataFrame({
            "name": ["far_away"],
            "geometry": [box(50, 50, 51, 51)],
        })
        points = pd.DataFrame({
            "id": ["p1"],
            "lat": [0.5],
            "lon": [0.5],  # not in any polygon
        })
        joined = s2_utils.s2_spatial_join(points, gdf, "lat", "lon", level=12)
        assert len(joined) == 0
        # Schema must still expose the polygon-attrs column even on empty.
        assert "name" in joined.columns

    def test_first_polygon_wins_on_overlap(self):
        """Two overlapping polygons — first one registered wins for shared cells."""
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            pytest.skip("geopandas / shapely not installed")
        # Two polygons that overlap; point lands inside both.
        gdf = gpd.GeoDataFrame({
            "name": ["first", "second"],
            "geometry": [box(0, 0, 1, 1), box(0.5, 0, 1.5, 1)],
        })
        points = pd.DataFrame({
            "id": ["p1"],
            "lat": [0.5],
            "lon": [0.7],  # inside both
        })
        joined = s2_utils.s2_spatial_join(points, gdf, "lat", "lon", level=12)
        assert len(joined) == 1
        assert joined["name"].iloc[0] == "first"


class TestCoercePolygonRejects:
    """_coerce_polygon must reject Points/LineStrings — duck-typing by
    .bounds + .contains was too permissive (CodeRabbit major)."""

    def test_point_rejected(self):
        try:
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("shapely not installed")
        with pytest.raises(TypeError, match="Polygon or MultiPolygon"):
            s2_utils.s2_index_polygon(Point(0, 0), level=10)

    def test_linestring_rejected(self):
        try:
            from shapely.geometry import LineString
        except ImportError:
            pytest.skip("shapely not installed")
        with pytest.raises(TypeError, match="Polygon or MultiPolygon"):
            s2_utils.s2_index_polygon(LineString([(0, 0), (1, 1)]), level=10)

    def test_geojson_point_rejected(self):
        with pytest.raises(TypeError, match="Polygon or MultiPolygon"):
            s2_utils.s2_index_polygon(
                {"type": "Point", "coordinates": [0, 0]}, level=10,
            )
