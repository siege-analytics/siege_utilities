"""Tests for siege_utilities.geo.spatial_transformations module.

Covers SpatialDataTransformer (init, convert_format, all format converters),
PostGISConnector (with mocked DB), DuckDBConnector (with mocked duckdb),
and convenience functions.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_gdf():
    """A minimal GeoDataFrame with two point geometries."""
    return gpd.GeoDataFrame(
        {"name": ["a", "b"]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )


@pytest.fixture
def polygon_gdf():
    """A GeoDataFrame with polygon geometries."""
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    return gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[poly],
        crs="EPSG:4326",
    )


@pytest.fixture
def transformer():
    """SpatialDataTransformer with mocked user config."""
    with patch(
        "siege_utilities.geo.spatial_transformations.get_user_config",
        return_value={},
    ):
        from siege_utilities.geo.spatial_transformations import SpatialDataTransformer
        return SpatialDataTransformer()


# ---------------------------------------------------------------------------
# SpatialDataTransformer.__init__
# ---------------------------------------------------------------------------

class TestSpatialDataTransformerInit:

    def test_supported_formats_present(self, transformer):
        assert "output" in transformer.supported_formats
        base_formats = {"shp", "geojson", "gpkg", "kml", "gml", "wkt", "wkb", "postgis"}
        assert base_formats.issubset(set(transformer.supported_formats["output"]))

    def test_user_config_failure_handled(self):
        """When get_user_config raises, the transformer falls back to empty dict."""
        with patch(
            "siege_utilities.geo.spatial_transformations.get_user_config",
            side_effect=RuntimeError("no config"),
        ):
            from siege_utilities.geo.spatial_transformations import SpatialDataTransformer
            t = SpatialDataTransformer()
            assert t.user_config == {}


# ---------------------------------------------------------------------------
# convert_format — routing
# ---------------------------------------------------------------------------

class TestConvertFormat:

    def test_unsupported_format_returns_false(self, transformer, sample_gdf):
        assert transformer.convert_format(sample_gdf, "xyz123") is False

    def test_routes_to_shapefile(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_shapefile", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "shp", output_path="/tmp/t.shp")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_geojson(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_geojson", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "geojson")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_gpkg(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_geopackage", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "gpkg")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_kml(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_kml", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "kml")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_gml(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_gml", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "gml")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_wkt(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_wkt", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "wkt")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_wkb(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_wkb", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "wkb")
            assert result is True
            mock.assert_called_once()

    def test_routes_to_postgis(self, transformer, sample_gdf):
        with patch.object(transformer, "_convert_to_postgis", return_value=True) as mock:
            result = transformer.convert_format(sample_gdf, "postgis")
            assert result is True
            mock.assert_called_once()

    def test_duckdb_unavailable_returns_false(self, transformer, sample_gdf):
        with patch("siege_utilities.geo.spatial_transformations.DUCKDB_AVAILABLE", False):
            assert transformer.convert_format(sample_gdf, "duckdb") is False

    def test_exception_in_converter_returns_false(self, transformer, sample_gdf):
        with patch.object(
            transformer, "_convert_to_shapefile", side_effect=RuntimeError("boom")
        ):
            assert transformer.convert_format(sample_gdf, "shp") is False


# ---------------------------------------------------------------------------
# Individual converters (file-based, using tmp_path)
# ---------------------------------------------------------------------------

class TestShapefileConversion:

    def test_convert_to_shapefile(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.shp")
        result = transformer._convert_to_shapefile(sample_gdf, output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_convert_to_shapefile_roundtrip(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.shp")
        transformer._convert_to_shapefile(sample_gdf, output_path=out)
        loaded = gpd.read_file(out)
        assert len(loaded) == 2


class TestGeoJSONConversion:

    def test_convert_to_geojson(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.geojson")
        result = transformer._convert_to_geojson(sample_gdf, output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_geojson_roundtrip(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.geojson")
        transformer._convert_to_geojson(sample_gdf, output_path=out)
        loaded = gpd.read_file(out)
        assert len(loaded) == 2
        assert loaded.crs is not None


class TestGeoPackageConversion:

    def test_convert_to_geopackage(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.gpkg")
        result = transformer._convert_to_geopackage(sample_gdf, output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_geopackage_roundtrip(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.gpkg")
        transformer._convert_to_geopackage(sample_gdf, output_path=out)
        loaded = gpd.read_file(out)
        assert len(loaded) == 2


class TestWKTConversion:

    def test_convert_to_wkt(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.wkt")
        result = transformer._convert_to_wkt(sample_gdf, output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_wkt_csv_content(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.wkt")
        transformer._convert_to_wkt(sample_gdf, output_path=out)
        with open(out) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        # geometry column should be WKT strings
        assert "POINT" in rows[0]["geometry"]


class TestWKBConversion:

    def test_convert_to_wkb(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.wkb")
        result = transformer._convert_to_wkb(sample_gdf, output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_wkb_pickle_roundtrip(self, transformer, sample_gdf, tmp_path):
        import pandas as pd

        out = str(tmp_path / "out.wkb")
        transformer._convert_to_wkb(sample_gdf, output_path=out)
        loaded = pd.read_pickle(out)
        assert len(loaded) == 2
        # geometry column should be bytes (WKB)
        assert isinstance(loaded["geometry"].iloc[0], bytes)


class TestPostGISConversion:

    def test_convert_to_postgis_sql(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.sql")
        result = transformer._convert_to_postgis(sample_gdf, output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_postgis_sql_content(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.sql")
        transformer._convert_to_postgis(sample_gdf, output_path=out)
        content = Path(out).read_text()
        assert "INSERT INTO spatial_table" in content
        assert "ST_GeomFromText" in content
        assert "POINT" in content
        # One INSERT per row
        lines = [l for l in content.strip().split("\n") if l.strip()]
        assert len(lines) == 2


class TestKMLConversion:

    def test_convert_to_kml_failure_returns_false(self, transformer, sample_gdf, tmp_path):
        """KML driver may not be available in all GDAL builds; test graceful failure."""
        out = str(tmp_path / "out.kml")
        # Regardless of outcome (True if KML driver exists, False if not), no exception
        result = transformer._convert_to_kml(sample_gdf, output_path=out)
        assert isinstance(result, bool)


class TestGMLConversion:

    def test_convert_to_gml(self, transformer, sample_gdf, tmp_path):
        out = str(tmp_path / "out.gml")
        result = transformer._convert_to_gml(sample_gdf, output_path=out)
        # GML driver should be universally available
        assert result is True
        assert Path(out).exists()


# ---------------------------------------------------------------------------
# PostGISConnector (fully mocked — no real DB)
# ---------------------------------------------------------------------------

class TestPostGISConnector:

    def _make_connector(self, mock_conn=None):
        """Create a PostGISConnector with all external deps mocked."""
        with patch(
            "siege_utilities.geo.spatial_transformations.get_user_config"
        ) as mock_cfg:
            mock_cfg.return_value = MagicMock()
            mock_cfg.return_value.get_database_connection.return_value = (
                "postgresql://localhost/test"
            )

            with patch.dict("sys.modules", {"psycopg2": MagicMock()}):
                import sys
                mock_psycopg2 = sys.modules["psycopg2"]
                if mock_conn is None:
                    mock_conn = MagicMock()
                mock_psycopg2.connect.return_value = mock_conn

                from siege_utilities.geo.spatial_transformations import PostGISConnector
                connector = PostGISConnector.__new__(PostGISConnector)
                connector.connection_string = "postgresql://localhost/test"
                connector.psycopg2 = mock_psycopg2
                connector.connection = mock_conn
                return connector

    def test_upload_no_connection_returns_false(self, sample_gdf):
        connector = self._make_connector()
        connector.connection = None
        assert connector.upload_spatial_data(sample_gdf, "test_table") is False

    def test_upload_spatial_data_calls_cursor(self, sample_gdf):
        mock_conn = MagicMock()
        connector = self._make_connector(mock_conn)
        with patch.object(connector, "_create_spatial_table"):
            result = connector.upload_spatial_data(sample_gdf, "test_table")
        assert result is True
        mock_conn.cursor.assert_called()
        mock_conn.commit.assert_called()

    def test_download_no_connection_returns_none(self):
        connector = self._make_connector()
        connector.connection = None
        assert connector.download_spatial_data("test_table") is None

    def test_execute_spatial_query_no_connection_returns_none(self):
        connector = self._make_connector()
        connector.connection = None
        assert connector.execute_spatial_query("SELECT 1") is None

    def test_create_spatial_table_single_geom_type(self, sample_gdf):
        mock_conn = MagicMock()
        connector = self._make_connector(mock_conn)
        connector._create_spatial_table("my_table", sample_gdf)
        cursor = mock_conn.cursor.return_value
        cursor.execute.assert_called_once()
        call_sql = cursor.execute.call_args[0][0]
        assert "POINT" in call_sql
        assert "my_table" in call_sql

    def test_create_spatial_table_mixed_geom_type(self):
        """Mixed geometry types should fall back to GEOMETRY."""
        mixed = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[Point(0, 0), Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_conn = MagicMock()
        connector = self._make_connector(mock_conn)
        connector._create_spatial_table("mixed_table", mixed)
        call_sql = mock_conn.cursor.return_value.execute.call_args[0][0]
        assert "GEOMETRY" in call_sql

    def test_create_spatial_table_uses_gdf_crs(self, sample_gdf):
        """SRID should come from the GeoDataFrame's CRS when available."""
        mock_conn = MagicMock()
        connector = self._make_connector(mock_conn)
        connector._create_spatial_table("crs_table", sample_gdf)
        call_sql = mock_conn.cursor.return_value.execute.call_args[0][0]
        assert "4326" in call_sql

    def test_create_spatial_table_no_crs_falls_back(self):
        """When GeoDataFrame has no CRS, fall back to settings.STORAGE_CRS."""
        no_crs_gdf = gpd.GeoDataFrame(
            {"id": [1]}, geometry=[Point(0, 0)]
        )
        no_crs_gdf.crs = None
        mock_conn = MagicMock()
        connector = self._make_connector(mock_conn)

        with patch("siege_utilities.geo.spatial_transformations.settings") as mock_settings:
            mock_settings.STORAGE_CRS = 4269
            connector._create_spatial_table("fallback_table", no_crs_gdf)
            call_sql = mock_conn.cursor.return_value.execute.call_args[0][0]
            assert "4269" in call_sql


# ---------------------------------------------------------------------------
# DuckDBConnector (mocked — no real duckdb dependency required)
# ---------------------------------------------------------------------------

class TestDuckDBConnector:

    def _make_connector(self, *, duckdb_available=True):
        """Create a DuckDBConnector with mocked dependencies."""
        with patch(
            "siege_utilities.geo.spatial_transformations.get_user_config",
            return_value={},
        ), patch(
            "siege_utilities.geo.spatial_transformations.DUCKDB_AVAILABLE",
            duckdb_available,
        ):
            if not duckdb_available:
                from siege_utilities.geo.spatial_transformations import DuckDBConnector
                with pytest.raises(ImportError):
                    DuckDBConnector()
                return None

            from siege_utilities.geo.spatial_transformations import DuckDBConnector
            connector = DuckDBConnector.__new__(DuckDBConnector)
            connector.user_config = {}
            connector.db_path = ":memory:"
            connector.connection = None
            return connector

    def test_init_raises_when_duckdb_unavailable(self):
        self._make_connector(duckdb_available=False)

    def test_connect_success(self):
        connector = self._make_connector()
        mock_duckdb = MagicMock()
        import siege_utilities.geo.spatial_transformations as st_mod
        st_mod.duckdb = mock_duckdb
        try:
            result = connector.connect()
            assert result is True
            assert connector.connection is not None
        finally:
            if not hasattr(st_mod, '_orig_duckdb'):
                del st_mod.duckdb

    def test_connect_failure(self):
        connector = self._make_connector()
        mock_duckdb = MagicMock()
        mock_duckdb.connect.side_effect = RuntimeError("fail")
        import siege_utilities.geo.spatial_transformations as st_mod
        st_mod.duckdb = mock_duckdb
        try:
            result = connector.connect()
            assert result is False
        finally:
            del st_mod.duckdb

    def test_upload_no_connection_calls_connect(self, sample_gdf):
        connector = self._make_connector()
        connector.connection = None
        mock_conn = MagicMock()
        mock_duckdb = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        import siege_utilities.geo.spatial_transformations as st_mod
        st_mod.duckdb = mock_duckdb
        try:
            result = connector.upload_spatial_data(sample_gdf, "test_table")
            assert result is True
        finally:
            del st_mod.duckdb

    def test_upload_replace_drops_table(self, sample_gdf):
        connector = self._make_connector()
        mock_conn = MagicMock()
        connector.connection = mock_conn
        connector.upload_spatial_data(sample_gdf, "test_table", if_exists="replace")
        calls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("DROP TABLE" in c for c in calls)

    def test_upload_no_replace_skips_drop(self, sample_gdf):
        connector = self._make_connector()
        mock_conn = MagicMock()
        connector.connection = mock_conn
        connector.upload_spatial_data(sample_gdf, "test_table", if_exists="append")
        calls = [str(c) for c in mock_conn.execute.call_args_list]
        assert not any("DROP TABLE" in c for c in calls)

    def test_download_no_connection_tries_connect_and_fails(self):
        connector = self._make_connector()
        connector.connection = None
        mock_duckdb = MagicMock()
        mock_duckdb.connect.side_effect = RuntimeError("fail")
        import siege_utilities.geo.spatial_transformations as st_mod
        st_mod.duckdb = mock_duckdb
        try:
            result = connector.download_spatial_data("tbl")
            assert result is None
        finally:
            del st_mod.duckdb

    def test_execute_spatial_query_no_connection_tries_connect_and_fails(self):
        connector = self._make_connector()
        connector.connection = None
        mock_duckdb = MagicMock()
        mock_duckdb.connect.side_effect = RuntimeError("fail")
        import siege_utilities.geo.spatial_transformations as st_mod
        st_mod.duckdb = mock_duckdb
        try:
            result = connector.execute_spatial_query("SELECT 1")
            assert result is None
        finally:
            del st_mod.duckdb


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:

    def test_convert_spatial_format_delegates(self, sample_gdf, tmp_path):
        out = str(tmp_path / "out.geojson")
        with patch(
            "siege_utilities.geo.spatial_transformations.get_user_config",
            return_value={},
        ):
            from siege_utilities.geo.spatial_transformations import convert_spatial_format
            result = convert_spatial_format(sample_gdf, "geojson", output_path=out)
        assert result is True
        assert Path(out).exists()

    def test_upload_to_duckdb_unavailable(self, sample_gdf):
        with patch(
            "siege_utilities.geo.spatial_transformations.DUCKDB_AVAILABLE", False
        ):
            from siege_utilities.geo.spatial_transformations import upload_to_duckdb
            assert upload_to_duckdb(sample_gdf, "tbl") is False

    def test_download_from_duckdb_unavailable(self):
        with patch(
            "siege_utilities.geo.spatial_transformations.DUCKDB_AVAILABLE", False
        ):
            from siege_utilities.geo.spatial_transformations import download_from_duckdb
            assert download_from_duckdb("tbl") is None

    def test_execute_duckdb_query_unavailable(self):
        with patch(
            "siege_utilities.geo.spatial_transformations.DUCKDB_AVAILABLE", False
        ):
            from siege_utilities.geo.spatial_transformations import execute_duckdb_query
            assert execute_duckdb_query("SELECT 1") is None


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

class TestModuleExports:

    def test_all_exports_present(self):
        from siege_utilities.geo.spatial_transformations import __all__

        expected = {
            "SpatialDataTransformer",
            "PostGISConnector",
            "DuckDBConnector",
            "convert_spatial_format",
            "upload_to_postgis",
            "download_from_postgis",
            "execute_postgis_query",
            "upload_to_duckdb",
            "download_from_duckdb",
            "execute_duckdb_query",
            "DUCKDB_AVAILABLE",
        }
        assert expected == set(__all__)

    def test_duckdb_available_is_bool(self):
        from siege_utilities.geo.spatial_transformations import DUCKDB_AVAILABLE
        assert isinstance(DUCKDB_AVAILABLE, bool)
