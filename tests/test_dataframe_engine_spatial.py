"""Tests for spatial operations in the DataFrame engine abstraction."""

import tempfile

import pytest

try:
    import geopandas as gpd
    from shapely.geometry import Point, box

    HAS_GEO = True
except ImportError:
    HAS_GEO = False

pytestmark = [
    pytest.mark.requires_gdal,
    pytest.mark.skipif(not HAS_GEO, reason="GeoPandas/shapely not available"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_points():
    return gpd.GeoDataFrame(
        {"name": ["a", "b", "c"], "value": [1, 2, 3]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_polygons():
    return gpd.GeoDataFrame(
        {"zone": ["west", "east"]},
        geometry=[box(-1, -1, 0.5, 0.5), box(0.5, 0.5, 3, 3)],
        crs="EPSG:4326",
    )


@pytest.fixture
def tmp_geojson(sample_points):
    """Write sample points to a temp GeoJSON file."""
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False, mode="w") as f:
        f.write(sample_points.to_json())
        return f.name


# ---------------------------------------------------------------------------
# Pandas Engine
# ---------------------------------------------------------------------------

class TestPandasSpatial:

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        from siege_utilities.engines.dataframe_engine import PandasEngine
        self.engine = PandasEngine()

    def test_read_spatial(self, tmp_geojson):
        gdf = self.engine.read_spatial(tmp_geojson)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 3
        assert gdf.crs is not None

    def test_spatial_join_intersects(self, sample_points, sample_polygons):
        result = self.engine.spatial_join(sample_points, sample_polygons)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 1
        assert "zone" in result.columns

    def test_spatial_join_within(self, sample_points, sample_polygons):
        result = self.engine.spatial_join(
            sample_points, sample_polygons, predicate="within",
        )
        assert isinstance(result, gpd.GeoDataFrame)

    def test_buffer(self, sample_points):
        buffered = self.engine.buffer(sample_points, 0.5)
        assert isinstance(buffered, gpd.GeoDataFrame)
        # Buffered points should be polygons, not points
        assert buffered.geometry.iloc[0].geom_type == "Polygon"

    def test_distance_to_point(self, sample_points):
        distances = self.engine.distance(sample_points, Point(0, 0))
        assert len(distances) == 3
        assert distances.iloc[0] == pytest.approx(0.0)
        assert distances.iloc[1] > 0

    def test_distance_to_wkt(self, sample_points):
        distances = self.engine.distance(sample_points, "POINT(0 0)")
        assert len(distances) == 3
        assert distances.iloc[0] == pytest.approx(0.0)

    def test_distance_pairwise(self, sample_points):
        other = gpd.GeoDataFrame(
            geometry=[Point(0, 0), Point(0, 0), Point(0, 0)],
            crs="EPSG:4326",
        )
        distances = self.engine.distance(sample_points, other)
        assert len(distances) == 3

    def test_to_geodataframe_passthrough(self, sample_points):
        result = self.engine.to_geodataframe(sample_points)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 3

    def test_to_geodataframe_from_wkt(self):
        import pandas as pd
        df = pd.DataFrame({
            "name": ["a", "b"],
            "geometry": ["POINT(0 0)", "POINT(1 1)"],
        })
        gdf = self.engine.to_geodataframe(df)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_point_in_polygon(self, sample_points, sample_polygons):
        result = self.engine.point_in_polygon(sample_points, sample_polygons)
        assert isinstance(result, gpd.GeoDataFrame)
        assert "zone" in result.columns

    def test_dissolve(self, sample_polygons):
        # Add a grouping column
        polys = sample_polygons.copy()
        polys["region"] = ["R1", "R1"]
        result = self.engine.dissolve(polys, by="region")
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# DuckDB Engine
# ---------------------------------------------------------------------------

def _duckdb_available():
    try:
        import duckdb  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _duckdb_available(), reason="DuckDB not installed")
class TestDuckDBSpatial:

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        self.engine = DuckDBEngine()

    def test_spatial_join(self, sample_points, sample_polygons):
        result = self.engine.spatial_join(sample_points, sample_polygons)
        assert isinstance(result, gpd.GeoDataFrame)
        assert "zone" in result.columns

    def test_buffer(self, sample_points):
        buffered = self.engine.buffer(sample_points, 0.5)
        assert isinstance(buffered, gpd.GeoDataFrame)
        assert buffered.geometry.iloc[0].geom_type == "Polygon"

    def test_distance_to_point(self, sample_points):
        distances = self.engine.distance(sample_points, Point(0, 0))
        assert len(distances) == 3
        assert distances.iloc[0] == pytest.approx(0.0)

    def test_to_geodataframe_passthrough(self, sample_points):
        result = self.engine.to_geodataframe(sample_points)
        assert isinstance(result, gpd.GeoDataFrame)

    def test_to_geodataframe_from_wkt(self):
        import pandas as pd
        df = pd.DataFrame({
            "name": ["a", "b"],
            "geometry": ["POINT(0 0)", "POINT(1 1)"],
        })
        gdf = self.engine.to_geodataframe(df)
        assert isinstance(gdf, gpd.GeoDataFrame)

    def test_point_in_polygon(self, sample_points, sample_polygons):
        result = self.engine.point_in_polygon(sample_points, sample_polygons)
        assert isinstance(result, gpd.GeoDataFrame)


# ---------------------------------------------------------------------------
# Engine consistency: all engines agree on results
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _duckdb_available(), reason="DuckDB not installed")
class TestEngineConsistency:
    """Verify that Pandas and DuckDB produce equivalent spatial results."""

    def test_spatial_join_same_result(self, sample_points, sample_polygons):
        from siege_utilities.engines.dataframe_engine import PandasEngine, DuckDBEngine
        pd_result = PandasEngine().spatial_join(sample_points, sample_polygons)
        dk_result = DuckDBEngine().spatial_join(sample_points, sample_polygons)
        # Both should find the same point-polygon pairs
        assert len(pd_result) == len(dk_result)

    def test_buffer_same_area(self, sample_points):
        from siege_utilities.engines.dataframe_engine import PandasEngine, DuckDBEngine
        pd_result = PandasEngine().buffer(sample_points, 0.5)
        dk_result = DuckDBEngine().buffer(sample_points, 0.5)
        pd_area = pd_result.geometry.area.sum()
        dk_area = dk_result.geometry.area.sum()
        assert pd_area == pytest.approx(dk_area, rel=0.01)


# ---------------------------------------------------------------------------
# multi_assign: docstring contract enforcement (issue #473)
# ---------------------------------------------------------------------------

class TestMultiAssignLayerPrefix:
    """multi_assign must prefix polygon-side columns with the layer name.

    Without prefixing, two TIGER layers (each with ``geoid`` and ``name``)
    silently overwrite each other on the join. The docstring promises
    ``{layer_name}_geoid`` / ``{layer_name}_name``; this test enforces it.
    """

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        from siege_utilities.engines.dataframe_engine import PandasEngine
        self.engine = PandasEngine()

    @pytest.fixture
    def points5(self):
        return gpd.GeoDataFrame(
            {"id": [1, 2, 3, 4, 5]},
            geometry=[Point(x, x) for x in [0.1, 0.6, 1.1, 1.6, 2.1]],
            crs="EPSG:4326",
        )

    @pytest.fixture
    def tract_layer(self):
        return gpd.GeoDataFrame(
            {"geoid": ["T1", "T2"], "name": ["TractA", "TractB"], "pop": [100, 200]},
            geometry=[box(-1, -1, 1, 1), box(1, 1, 3, 3)],
            crs="EPSG:4326",
        )

    @pytest.fixture
    def cd_layer(self):
        return gpd.GeoDataFrame(
            {"geoid": ["C1", "C2"], "name": ["CD1", "CD2"]},
            geometry=[box(-1, -1, 1.5, 1.5), box(1.5, 1.5, 3, 3)],
            crs="EPSG:4326",
        )

    def test_layer_prefix_applied_to_polygon_columns(self, points5, tract_layer, cd_layer):
        result = self.engine.multi_assign(
            points5,
            {"tract": tract_layer, "cd": cd_layer},
        )
        cols = set(result.columns)
        for expected in ("tract_geoid", "tract_name", "tract_pop", "cd_geoid", "cd_name"):
            assert expected in cols, f"expected {expected!r} in output columns, got {sorted(cols)}"

    def test_bare_polygon_column_names_absent(self, points5, tract_layer, cd_layer):
        result = self.engine.multi_assign(
            points5,
            {"tract": tract_layer, "cd": cd_layer},
        )
        # Bare polygon-side names must NOT appear (otherwise the second
        # join silently overwrote the first).
        assert "geoid" not in result.columns
        assert "name" not in result.columns
        assert "pop" not in result.columns

    def test_point_columns_preserved(self, points5, tract_layer, cd_layer):
        result = self.engine.multi_assign(
            points5,
            {"tract": tract_layer, "cd": cd_layer},
        )
        # Point-side columns survive unchanged (no layer prefix).
        assert "id" in result.columns
