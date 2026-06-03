"""Tests for boundary provider engine abstraction (#988).

Tests the from_geodataframe() engine method and the engine= parameter
on boundary providers. Uses synthetic GeoDataFrames to avoid network calls.
"""

import pytest
import numpy as np
import pandas as pd


@pytest.fixture
def sample_gdf():
    """Create a minimal GeoDataFrame for testing engine conversion."""
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box

    return gpd.GeoDataFrame(
        {"name": ["A", "B", "C"], "pop": [100, 200, 300]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
        crs="EPSG:4326",
    )


# ---------------------------------------------------------------------------
# DataFrameEngine.from_geodataframe — base class (default = passthrough)
# ---------------------------------------------------------------------------

class TestFromGeoDataFrameBase:

    def test_base_returns_gdf_unchanged(self, sample_gdf):
        gpd = pytest.importorskip("geopandas")
        from siege_utilities.engines.dataframe_engine import PandasEngine

        engine = PandasEngine()
        result = engine.from_geodataframe(sample_gdf)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 3
        assert list(result.columns) == list(sample_gdf.columns)


# ---------------------------------------------------------------------------
# DuckDBEngine.from_geodataframe
# ---------------------------------------------------------------------------

class TestDuckDBFromGeoDataFrame:

    @pytest.fixture(autouse=True)
    def _skip_without_duckdb(self):
        pytest.importorskip("duckdb")

    def test_returns_pandas_dataframe(self, sample_gdf):
        from siege_utilities.engines.dataframe_engine import DuckDBEngine

        engine = DuckDBEngine()
        result = engine.from_geodataframe(sample_gdf)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_preserves_attribute_columns(self, sample_gdf):
        from siege_utilities.engines.dataframe_engine import DuckDBEngine

        engine = DuckDBEngine()
        result = engine.from_geodataframe(sample_gdf)
        assert "name" in result.columns
        assert "pop" in result.columns

    def test_has_geometry_column(self, sample_gdf):
        from siege_utilities.engines.dataframe_engine import DuckDBEngine

        engine = DuckDBEngine()
        result = engine.from_geodataframe(sample_gdf)
        assert "geometry" in result.columns

    def test_no_wkb_helper_column(self, sample_gdf):
        from siege_utilities.engines.dataframe_engine import DuckDBEngine

        engine = DuckDBEngine()
        result = engine.from_geodataframe(sample_gdf)
        assert "_geom_wkb" not in result.columns

    def test_empty_gdf(self):
        gpd = pytest.importorskip("geopandas")
        from siege_utilities.engines.dataframe_engine import DuckDBEngine

        empty_gdf = gpd.GeoDataFrame(
            {"name": pd.Series(dtype=str)},
            geometry=gpd.GeoSeries([], crs="EPSG:4326"),
        )
        engine = DuckDBEngine()
        result = engine.from_geodataframe(empty_gdf)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# BoundaryProvider._maybe_convert
# ---------------------------------------------------------------------------

class TestMaybeConvert:

    def test_none_engine_returns_gdf(self, sample_gdf):
        gpd = pytest.importorskip("geopandas")
        from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider

        provider = CensusTIGERProvider()
        result = provider._maybe_convert(sample_gdf, engine=None)
        assert isinstance(result, gpd.GeoDataFrame)
        assert result is sample_gdf

    def test_with_engine_converts(self, sample_gdf):
        pytest.importorskip("duckdb")
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider

        engine = DuckDBEngine()
        provider = CensusTIGERProvider()
        result = provider._maybe_convert(sample_gdf, engine=engine)
        assert isinstance(result, pd.DataFrame)
        assert "name" in result.columns


# ---------------------------------------------------------------------------
# CensusTIGERProvider with engine (mocked fetch)
# ---------------------------------------------------------------------------

class TestCensusTIGERWithEngine:

    @pytest.fixture(autouse=True)
    def _mock_spatial_data_module(self):
        """Inject a mock spatial_data module so CensusTIGERProvider's local
        import resolves without bs4/requests/etc."""
        import sys
        from unittest.mock import MagicMock
        key = "siege_utilities.geo.spatial_data"
        already = key in sys.modules
        if not already:
            sys.modules[key] = MagicMock()
        yield
        if not already:
            del sys.modules[key]

    def test_engine_param_passes_through(self, sample_gdf):
        pytest.importorskip("duckdb")
        from unittest.mock import patch, MagicMock
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.geodataframe = sample_gdf

        engine = DuckDBEngine()
        provider = CensusTIGERProvider()

        with patch(
            "siege_utilities.geo.spatial_data.CensusDataSource"
        ) as MockDS:
            MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result
            result = provider.get_boundary("county", "06", engine=engine)

        assert isinstance(result, pd.DataFrame)
        assert "name" in result.columns
        assert len(result) == 3

    def test_no_engine_returns_gdf(self, sample_gdf):
        gpd = pytest.importorskip("geopandas")
        from unittest.mock import patch, MagicMock
        from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.geodataframe = sample_gdf

        provider = CensusTIGERProvider()

        with patch(
            "siege_utilities.geo.spatial_data.CensusDataSource"
        ) as MockDS:
            MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result
            result = provider.get_boundary("county", "06")

        assert isinstance(result, gpd.GeoDataFrame)

    def test_fetch_failure_still_raises(self, sample_gdf):
        pytest.importorskip("duckdb")
        from unittest.mock import patch, MagicMock
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        from siege_utilities.geo.providers.boundary_providers import (
            CensusTIGERProvider,
            BoundaryFetchError,
        )

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_stage = "download"
        mock_result.message = "HTTP 404"

        engine = DuckDBEngine()
        provider = CensusTIGERProvider()

        with patch(
            "siege_utilities.geo.spatial_data.CensusDataSource"
        ) as MockDS:
            MockDS.return_value.fetch_geographic_boundaries.return_value = mock_result
            with pytest.raises(BoundaryFetchError, match="HTTP 404"):
                provider.get_boundary("county", "06", engine=engine)


# ---------------------------------------------------------------------------
# Roundtrip: from_geodataframe → to_geodataframe
# ---------------------------------------------------------------------------

class TestRoundtrip:

    def test_duckdb_roundtrip_preserves_data(self, sample_gdf):
        pytest.importorskip("duckdb")
        gpd = pytest.importorskip("geopandas")
        from siege_utilities.engines.dataframe_engine import DuckDBEngine

        engine = DuckDBEngine()
        duckdb_df = engine.from_geodataframe(sample_gdf)
        roundtrip = engine.to_geodataframe(duckdb_df, geometry_col="geometry")

        assert isinstance(roundtrip, gpd.GeoDataFrame)
        assert len(roundtrip) == 3
        assert list(roundtrip["name"]) == ["A", "B", "C"]
        assert list(roundtrip["pop"]) == [100, 200, 300]
