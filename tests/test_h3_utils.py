"""
Tests for siege_utilities.geo.h3_utils — H3 hexagonal spatial index utilities.
"""

import importlib
import sys
from unittest import mock

import pandas as pd
import pytest

from siege_utilities.geo import h3_utils
from siege_utilities.geo.h3_utils import (
    H3_AVAILABLE,
    _H3_RESOLUTION_AREA_KM2,
)

# Marker: skip the full-h3 tests when the library is missing
requires_h3 = pytest.mark.skipif(not H3_AVAILABLE, reason="h3 not installed")


# ---------------------------------------------------------------------------
# Availability flag
# ---------------------------------------------------------------------------

class TestH3Available:
    """Verify the H3_AVAILABLE flag reflects actual import state."""

    def test_flag_is_bool(self):
        assert isinstance(H3_AVAILABLE, bool)

    def test_flag_matches_import(self):
        try:
            import h3  # noqa: F401
            assert H3_AVAILABLE is True
        except ImportError:
            assert H3_AVAILABLE is False


# ---------------------------------------------------------------------------
# Graceful degradation when h3 is NOT installed
# ---------------------------------------------------------------------------

class TestGracefulWithoutH3:
    """All public functions should raise ImportError cleanly when h3 is absent."""

    def _make_module_without_h3(self):
        """Re-import h3_utils with h3 mocked as missing."""
        # Temporarily block h3 import
        with mock.patch.dict(sys.modules, {"h3": None}):
            # Force re-import
            spec = importlib.util.find_spec("siege_utilities.geo.h3_utils")
            module = importlib.util.module_from_spec(spec)
            # Patch so import h3 raises ImportError
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

            def blocked_import(name, *args, **kwargs):
                if name == "h3":
                    raise ImportError("mocked")
                return original_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=blocked_import):
                spec.loader.exec_module(module)
        return module

    def test_functions_raise_importerror_when_h3_missing(self):
        mod = self._make_module_without_h3()
        assert mod.H3_AVAILABLE is False

        dummy_df = pd.DataFrame({"lat": [40.0], "lon": [-74.0]})

        with pytest.raises(ImportError, match="h3 is required"):
            mod.h3_index_points(dummy_df, "lat", "lon")

        with pytest.raises(ImportError, match="h3 is required"):
            mod.h3_index_polygon({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]})

        with pytest.raises(ImportError, match="h3 is required"):
            mod.h3_hex_to_boundary("8928308280fffff")

        with pytest.raises(ImportError, match="h3 is required"):
            mod.h3_resolution_for_area(1.0)


# ---------------------------------------------------------------------------
# h3_index_points
# ---------------------------------------------------------------------------

@requires_h3
class TestH3IndexPoints:

    def test_basic_indexing(self):
        df = pd.DataFrame({
            "lat": [40.7128, 34.0522, 41.8781],
            "lon": [-74.0060, -118.2437, -87.6298],
        })
        result = h3_utils.h3_index_points(df, "lat", "lon", resolution=8)

        assert isinstance(result, pd.Series)
        assert len(result) == 3
        assert result.name == "h3_index"
        # H3 hex IDs are 15-char hex strings (v4) or similar
        for hex_id in result:
            assert isinstance(hex_id, str)
            assert len(hex_id) > 0

    def test_different_resolutions(self):
        df = pd.DataFrame({"lat": [40.7128], "lon": [-74.0060]})
        r7 = h3_utils.h3_index_points(df, "lat", "lon", resolution=7).iloc[0]
        r8 = h3_utils.h3_index_points(df, "lat", "lon", resolution=8).iloc[0]
        r9 = h3_utils.h3_index_points(df, "lat", "lon", resolution=9).iloc[0]
        # Different resolutions should produce different hex IDs
        assert r7 != r8
        assert r8 != r9

    def test_invalid_resolution(self):
        df = pd.DataFrame({"lat": [40.0], "lon": [-74.0]})
        with pytest.raises(ValueError, match="resolution must be 0-15"):
            h3_utils.h3_index_points(df, "lat", "lon", resolution=16)
        with pytest.raises(ValueError, match="resolution must be 0-15"):
            h3_utils.h3_index_points(df, "lat", "lon", resolution=-1)

    def test_missing_column(self):
        df = pd.DataFrame({"latitude": [40.0], "longitude": [-74.0]})
        with pytest.raises(ValueError, match="not found"):
            h3_utils.h3_index_points(df, "lat", "lon")

    def test_preserves_index(self):
        df = pd.DataFrame(
            {"lat": [40.7, 34.0], "lon": [-74.0, -118.2]},
            index=[10, 20],
        )
        result = h3_utils.h3_index_points(df, "lat", "lon")
        assert list(result.index) == [10, 20]


# ---------------------------------------------------------------------------
# h3_index_polygon
# ---------------------------------------------------------------------------

@requires_h3
class TestH3IndexPolygon:

    def _box_geojson(self):
        """Simple box polygon as GeoJSON dict."""
        return {
            "type": "Polygon",
            "coordinates": [[
                [-74.01, 40.70],
                [-73.99, 40.70],
                [-73.99, 40.72],
                [-74.01, 40.72],
                [-74.01, 40.70],
            ]],
        }

    def test_basic_polyfill(self):
        hexes = h3_utils.h3_index_polygon(self._box_geojson(), resolution=8)
        assert isinstance(hexes, set)
        assert len(hexes) > 0
        for hex_id in hexes:
            assert isinstance(hex_id, str)

    def test_higher_resolution_more_hexes(self):
        geojson = self._box_geojson()
        hexes_7 = h3_utils.h3_index_polygon(geojson, resolution=7)
        hexes_9 = h3_utils.h3_index_polygon(geojson, resolution=9)
        # Higher resolution = more hexes for same polygon
        assert len(hexes_9) > len(hexes_7)

    def test_shapely_geometry(self):
        """If shapely is available, accept a Shapely Polygon."""
        try:
            from shapely.geometry import box
        except ImportError:
            pytest.skip("shapely not installed")

        poly = box(-74.01, 40.70, -73.99, 40.72)
        hexes = h3_utils.h3_index_polygon(poly, resolution=8)
        assert isinstance(hexes, set)
        assert len(hexes) > 0

    def test_multipolygon(self):
        """Handle MultiPolygon geometries."""
        try:
            from shapely.geometry import MultiPolygon, box
        except ImportError:
            pytest.skip("shapely not installed")

        mp = MultiPolygon([
            box(-74.01, 40.70, -73.99, 40.72),
            box(-73.98, 40.73, -73.96, 40.75),
        ])
        hexes = h3_utils.h3_index_polygon(mp, resolution=8)
        assert isinstance(hexes, set)
        assert len(hexes) > 0

    def test_invalid_resolution(self):
        with pytest.raises(ValueError):
            h3_utils.h3_index_polygon(self._box_geojson(), resolution=20)

    def test_unsupported_geometry_type(self):
        with pytest.raises(TypeError, match="Unsupported geometry type"):
            h3_utils.h3_index_polygon({"type": "Point", "coordinates": [0, 0]})


# ---------------------------------------------------------------------------
# h3_spatial_join
# ---------------------------------------------------------------------------

@requires_h3
class TestH3SpatialJoin:

    def _make_test_data(self):
        """Create simple test points and polygons."""
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            pytest.skip("geopandas/shapely not installed")

        points_df = pd.DataFrame({
            "lat": [40.71, 40.74, 34.05],
            "lon": [-74.00, -73.97, -118.24],
            "name": ["NYC_Downtown", "NYC_Midtown", "LA"],
        })

        poly1 = box(-74.05, 40.68, -73.95, 40.76)  # NYC area
        poly2 = box(-118.30, 34.00, -118.20, 34.10)  # LA area

        polygons_gdf = gpd.GeoDataFrame(
            {"region": ["NYC", "LA"]},
            geometry=[poly1, poly2],
        )

        return points_df, polygons_gdf

    def test_end_to_end_join(self):
        points_df, polygons_gdf = self._make_test_data()
        result = h3_utils.h3_spatial_join(
            points_df, polygons_gdf, "lat", "lon", resolution=7,
        )

        assert isinstance(result, pd.DataFrame)
        # All 3 points should match (2 in NYC poly, 1 in LA poly)
        assert len(result) == 3
        assert "region" in result.columns
        assert "name" in result.columns
        # geometry column should NOT be in result
        assert "geometry" not in result.columns

    def test_unmatched_points_excluded(self):
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError:
            pytest.skip("geopandas/shapely not installed")

        # Point in Tokyo, polygon in NYC
        points_df = pd.DataFrame({
            "lat": [35.6762],
            "lon": [139.6503],
            "name": ["Tokyo"],
        })
        polygons_gdf = gpd.GeoDataFrame(
            {"region": ["NYC"]},
            geometry=[box(-74.05, 40.68, -73.95, 40.76)],
        )

        result = h3_utils.h3_spatial_join(
            points_df, polygons_gdf, "lat", "lon", resolution=8,
        )
        assert len(result) == 0

    def test_polygon_id_col(self):
        points_df, polygons_gdf = self._make_test_data()
        result = h3_utils.h3_spatial_join(
            points_df, polygons_gdf, "lat", "lon",
            resolution=7, polygon_id_col="region",
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# h3_hex_to_boundary
# ---------------------------------------------------------------------------

@requires_h3
class TestH3HexToBoundary:

    def test_returns_boundary_coordinates(self):
        import h3 as h3_lib
        # Get a valid hex ID first
        if hasattr(h3_lib, 'latlng_to_cell'):
            hex_id = h3_lib.latlng_to_cell(40.7128, -74.0060, 8)
        else:
            hex_id = h3_lib.geo_to_h3(40.7128, -74.0060, 8)

        boundary = h3_utils.h3_hex_to_boundary(hex_id)
        assert isinstance(boundary, list)
        # Hexagons have 6 vertices (boundary may or may not repeat first)
        assert len(boundary) >= 6
        # Each point is a (lat, lng) tuple
        for pt in boundary:
            assert len(pt) == 2


# ---------------------------------------------------------------------------
# h3_resolution_for_area
# ---------------------------------------------------------------------------

@requires_h3
class TestH3ResolutionForArea:

    def test_known_areas(self):
        # Resolution 8 ~ 0.737 km^2
        res = h3_utils.h3_resolution_for_area(0.7)
        assert res == 8

        # Resolution 5 ~ 252 km^2
        res = h3_utils.h3_resolution_for_area(250.0)
        assert res == 5

        # Resolution 0 ~ huge
        res = h3_utils.h3_resolution_for_area(5_000_000.0)
        assert res == 0

    def test_returns_int(self):
        res = h3_utils.h3_resolution_for_area(1.0)
        assert isinstance(res, int)
        assert 0 <= res <= 15

    def test_invalid_area_raises(self):
        with pytest.raises(ValueError, match="positive"):
            h3_utils.h3_resolution_for_area(0.0)
        with pytest.raises(ValueError, match="positive"):
            h3_utils.h3_resolution_for_area(-5.0)

    def test_very_small_area(self):
        res = h3_utils.h3_resolution_for_area(0.000001)
        assert res == 15

    def test_monotonic_resolution_table(self):
        """Area should decrease as resolution increases."""
        areas = [_H3_RESOLUTION_AREA_KM2[r] for r in range(16)]
        for i in range(len(areas) - 1):
            assert areas[i] > areas[i + 1]
