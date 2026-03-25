"""Tests for siege_utilities.files.formats module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from siege_utilities.files.formats import (
    SpatialFormat,
    TabularFormat,
    save_spatial,
    save_tabular,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_gdf():
    return gpd.GeoDataFrame(
        {"name": ["a", "b"], "value": [1, 2]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_df():
    return pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})


# ---------------------------------------------------------------------------
# SpatialFormat / TabularFormat enums
# ---------------------------------------------------------------------------

class TestEnums:

    def test_spatial_format_values(self):
        assert SpatialFormat.GEOPARQUET.value == "geoparquet"
        assert SpatialFormat.TOPOJSON.value == "topojson"
        assert SpatialFormat.CSV.value == "csv"

    def test_tabular_format_values(self):
        assert TabularFormat.PARQUET.value == "parquet"
        assert TabularFormat.EXCEL.value == "excel"

    def test_string_enum(self):
        assert str(SpatialFormat.GPKG) == "SpatialFormat.GPKG"
        assert SpatialFormat("geojson") is SpatialFormat.GEOJSON


# ---------------------------------------------------------------------------
# save_spatial
# ---------------------------------------------------------------------------

class TestSaveSpatial:

    def test_geoparquet_roundtrip(self, sample_gdf, tmp_path):
        out = tmp_path / "data.parquet"
        result = save_spatial(sample_gdf, out, SpatialFormat.GEOPARQUET)
        assert result == out
        assert out.exists()
        loaded = gpd.read_parquet(out)
        assert len(loaded) == 2
        assert loaded.crs is not None

    def test_parquet_drops_geometry(self, sample_gdf, tmp_path):
        out = tmp_path / "data.parquet"
        save_spatial(sample_gdf, out, SpatialFormat.PARQUET)
        loaded = pd.read_parquet(out)
        assert "geometry" not in loaded.columns
        assert "name" in loaded.columns

    def test_gpkg_roundtrip(self, sample_gdf, tmp_path):
        out = tmp_path / "data.gpkg"
        save_spatial(sample_gdf, out, SpatialFormat.GPKG)
        loaded = gpd.read_file(out)
        assert len(loaded) == 2

    def test_geojson_roundtrip(self, sample_gdf, tmp_path):
        out = tmp_path / "data.geojson"
        save_spatial(sample_gdf, out, SpatialFormat.GEOJSON)
        loaded = gpd.read_file(out)
        assert len(loaded) == 2

    def test_csv_includes_wkt_geometry(self, sample_gdf, tmp_path):
        out = tmp_path / "data.csv"
        save_spatial(sample_gdf, out, SpatialFormat.CSV)
        loaded = pd.read_csv(out)
        assert "geometry" in loaded.columns
        assert "POINT" in loaded["geometry"].iloc[0]

    def test_shapefile_roundtrip(self, sample_gdf, tmp_path):
        out = tmp_path / "data.shp"
        save_spatial(sample_gdf, out, SpatialFormat.SHAPEFILE)
        loaded = gpd.read_file(out)
        assert len(loaded) == 2

    def test_topojson_missing_library(self, sample_gdf, tmp_path):
        out = tmp_path / "data.topojson"
        with patch.dict("sys.modules", {"topojson": None}):
            with pytest.raises(ImportError, match="topojson"):
                save_spatial(sample_gdf, out, SpatialFormat.TOPOJSON)

    def test_topojson_with_mock(self, sample_gdf, tmp_path):
        out = tmp_path / "data.topojson"
        mock_tp = MagicMock()
        mock_topo = MagicMock()
        mock_topo.to_json.return_value = '{"type":"Topology"}'
        mock_tp.Topology.return_value = mock_topo

        with patch.dict("sys.modules", {"topojson": mock_tp}):
            save_spatial(sample_gdf, out, SpatialFormat.TOPOJSON)

        assert out.exists()
        assert "Topology" in out.read_text()

    def test_creates_parent_dirs(self, sample_gdf, tmp_path):
        out = tmp_path / "sub" / "dir" / "data.geojson"
        save_spatial(sample_gdf, out, SpatialFormat.GEOJSON)
        assert out.exists()

    def test_default_format_is_geoparquet(self, sample_gdf, tmp_path):
        out = tmp_path / "default.parquet"
        save_spatial(sample_gdf, out)
        loaded = gpd.read_parquet(out)
        assert len(loaded) == 2


# ---------------------------------------------------------------------------
# save_tabular
# ---------------------------------------------------------------------------

class TestSaveTabular:

    def test_parquet_roundtrip(self, sample_df, tmp_path):
        out = tmp_path / "data.parquet"
        result = save_tabular(sample_df, out, TabularFormat.PARQUET)
        assert result == out
        loaded = pd.read_parquet(out)
        assert list(loaded.columns) == ["x", "y"]
        assert len(loaded) == 3

    def test_csv_roundtrip(self, sample_df, tmp_path):
        out = tmp_path / "data.csv"
        save_tabular(sample_df, out, TabularFormat.CSV)
        loaded = pd.read_csv(out)
        assert len(loaded) == 3

    def test_excel_roundtrip(self, sample_df, tmp_path):
        out = tmp_path / "data.xlsx"
        save_tabular(sample_df, out, TabularFormat.EXCEL)
        loaded = pd.read_excel(out)
        assert len(loaded) == 3

    def test_json_roundtrip(self, sample_df, tmp_path):
        out = tmp_path / "data.json"
        save_tabular(sample_df, out, TabularFormat.JSON)
        loaded = pd.read_json(out)
        assert len(loaded) == 3

    def test_creates_parent_dirs(self, sample_df, tmp_path):
        out = tmp_path / "nested" / "dir" / "data.csv"
        save_tabular(sample_df, out, TabularFormat.CSV)
        assert out.exists()

    def test_default_format_is_parquet(self, sample_df, tmp_path):
        out = tmp_path / "default.parquet"
        save_tabular(sample_df, out)
        loaded = pd.read_parquet(out)
        assert len(loaded) == 3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:

    def test_invalid_spatial_format(self, sample_gdf, tmp_path):
        out = tmp_path / "data.xyz"
        with pytest.raises(ValueError, match="Unsupported spatial"):
            # Force an invalid enum value through
            save_spatial(sample_gdf, out, "not_a_format")

    def test_invalid_tabular_format(self, sample_df, tmp_path):
        out = tmp_path / "data.xyz"
        with pytest.raises(ValueError, match="Unsupported tabular"):
            save_tabular(sample_df, out, "not_a_format")


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

class TestExports:

    def test_all_exports(self):
        from siege_utilities.files.formats import __all__
        expected = {"SpatialFormat", "TabularFormat", "save_spatial", "save_tabular"}
        assert expected == set(__all__)

    def test_importable_from_files_package(self):
        from siege_utilities.files import SpatialFormat, save_spatial
        assert SpatialFormat.GEOPARQUET.value == "geoparquet"
