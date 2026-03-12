"""Tests for siege_utilities.reporting.map_3d — 3D map rendering via pydeck."""

import importlib
import json
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Fixture: sample data
# ---------------------------------------------------------------------------

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import pydeck as pdk
    HAS_PYDECK = True
except ImportError:
    HAS_PYDECK = False

try:
    import geopandas as gpd
    from shapely.geometry import box
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

needs_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
needs_pydeck = pytest.mark.skipif(not HAS_PYDECK, reason="pydeck not installed")
needs_geopandas = pytest.mark.skipif(not HAS_GEOPANDAS, reason="geopandas not installed")


@pytest.fixture
def sample_df():
    """Small DataFrame with lat/lon/value columns."""
    return pd.DataFrame({
        "latitude": [38.9, 38.91, 38.92, 38.93, 38.94],
        "longitude": [-77.03, -77.04, -77.05, -77.06, -77.07],
        "value": [100, 200, 300, 400, 500],
    })


@pytest.fixture
def sample_gdf():
    """Small GeoDataFrame with polygon geometries and a value column."""
    polys = [
        box(-77.05, 38.90, -77.04, 38.91),
        box(-77.04, 38.91, -77.03, 38.92),
        box(-77.03, 38.92, -77.02, 38.93),
    ]
    return gpd.GeoDataFrame(
        {"value": [10, 20, 30], "name": ["a", "b", "c"]},
        geometry=polys,
        crs="EPSG:4326",
    )


# ===================================================================
# Availability flag tests
# ===================================================================


class TestPydeckAvailableFlag:
    """Ensure the PYDECK_AVAILABLE flag reflects the runtime environment."""

    def test_flag_matches_import(self):
        from siege_utilities.reporting.map_3d import PYDECK_AVAILABLE
        assert PYDECK_AVAILABLE is HAS_PYDECK

    def test_flag_exposed_via_reporting_package(self):
        from siege_utilities.reporting import PYDECK_AVAILABLE
        assert PYDECK_AVAILABLE is HAS_PYDECK

    def test_flag_false_when_pydeck_missing(self, monkeypatch):
        """Simulate pydeck not being installed by blocking its import."""
        import siege_utilities.reporting.map_3d as mod

        # Temporarily remove cached module and block the import
        monkeypatch.setitem(sys.modules, "pydeck", None)
        reloaded = importlib.reload(mod)
        assert reloaded.PYDECK_AVAILABLE is False

        # Restore
        monkeypatch.undo()
        importlib.reload(mod)


# ===================================================================
# Instantiation tests
# ===================================================================


class TestThreeDMapRendererInit:

    @needs_pydeck
    def test_default_init(self):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        assert renderer.mapbox_token is None
        assert "dark" in renderer.map_style

    @needs_pydeck
    def test_custom_style(self):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer(map_style="light")
        assert "light" in renderer.map_style

    @needs_pydeck
    def test_custom_mapbox_url(self):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        url = "mapbox://styles/custom/abc123"
        renderer = ThreeDMapRenderer(map_style=url)
        assert renderer.map_style == url

    @needs_pydeck
    def test_with_token(self):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer(mapbox_token="pk.test123")
        assert renderer.mapbox_token == "pk.test123"

    def test_raises_when_pydeck_missing(self, monkeypatch):
        """ThreeDMapRenderer should raise ImportError when pydeck is absent."""
        import siege_utilities.reporting.map_3d as mod
        monkeypatch.setitem(sys.modules, "pydeck", None)
        reloaded = importlib.reload(mod)
        with pytest.raises(ImportError, match="pydeck"):
            reloaded.ThreeDMapRenderer()
        monkeypatch.undo()
        importlib.reload(mod)


# ===================================================================
# Layer creation tests
# ===================================================================


@needs_pydeck
@needs_pandas
class TestHexagonLayer:

    def test_returns_deck(self, sample_df):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_hexagon_layer(sample_df)
        assert isinstance(deck, pdk.Deck)

    def test_custom_radius(self, sample_df):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_hexagon_layer(sample_df, radius=2000)
        assert isinstance(deck, pdk.Deck)

    def test_with_value_col(self, sample_df):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_hexagon_layer(sample_df, value_col="value")
        assert isinstance(deck, pdk.Deck)


@needs_pydeck
@needs_pandas
class TestColumnLayer:

    def test_returns_deck(self, sample_df):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_column_layer(sample_df, value_col="value")
        assert isinstance(deck, pdk.Deck)

    def test_custom_color(self, sample_df):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_column_layer(
            sample_df, value_col="value", color=[0, 128, 255, 180]
        )
        assert isinstance(deck, pdk.Deck)


@needs_pydeck
@needs_geopandas
class TestChoropleth3D:

    def test_returns_deck(self, sample_gdf):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_choropleth_3d(sample_gdf, value_col="value")
        assert isinstance(deck, pdk.Deck)

    def test_custom_elevation_scale(self, sample_gdf):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_choropleth_3d(
            sample_gdf, value_col="value", elevation_scale=50
        )
        assert isinstance(deck, pdk.Deck)


# ===================================================================
# Output tests
# ===================================================================


@needs_pydeck
@needs_pandas
class TestRenderToHtml:

    def test_produces_html_file(self, sample_df, tmp_path):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_hexagon_layer(sample_df)
        out = renderer.render_to_html(deck, tmp_path / "map.html")
        assert out.exists()
        assert out.suffix == ".html"
        content = out.read_text()
        assert "<html" in content.lower() or "<!doctype" in content.lower()

    def test_creates_parent_dirs(self, sample_df, tmp_path):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_hexagon_layer(sample_df)
        nested = tmp_path / "sub" / "dir" / "map.html"
        out = renderer.render_to_html(deck, nested)
        assert out.exists()


@needs_pydeck
@needs_pandas
class TestRenderInNotebook:

    def test_returns_deck(self, sample_df):
        from siege_utilities.reporting.map_3d import ThreeDMapRenderer
        renderer = ThreeDMapRenderer()
        deck = renderer.create_hexagon_layer(sample_df)
        result = renderer.render_in_notebook(deck)
        assert result is deck


# ===================================================================
# Convenience function tests
# ===================================================================


@needs_pydeck
@needs_pandas
class TestConvenienceFunctions:

    def test_create_3d_hexbin(self, sample_df):
        from siege_utilities.reporting.map_3d import create_3d_hexbin
        deck = create_3d_hexbin(sample_df)
        assert isinstance(deck, pdk.Deck)

    def test_create_3d_columns(self, sample_df):
        from siege_utilities.reporting.map_3d import create_3d_columns
        deck = create_3d_columns(sample_df, value_col="value")
        assert isinstance(deck, pdk.Deck)

    def test_hexbin_via_reporting_package(self, sample_df):
        from siege_utilities.reporting import create_3d_hexbin
        deck = create_3d_hexbin(sample_df)
        assert isinstance(deck, pdk.Deck)

    def test_columns_via_reporting_package(self, sample_df):
        from siege_utilities.reporting import create_3d_columns
        deck = create_3d_columns(sample_df, value_col="value")
        assert isinstance(deck, pdk.Deck)


# ===================================================================
# Graceful degradation
# ===================================================================


class TestGracefulDegradation:
    """Verify that convenience functions fail gracefully without pydeck."""

    def test_create_3d_hexbin_raises(self, monkeypatch):
        import siege_utilities.reporting.map_3d as mod
        monkeypatch.setitem(sys.modules, "pydeck", None)
        reloaded = importlib.reload(mod)
        with pytest.raises(ImportError, match="pydeck"):
            reloaded.create_3d_hexbin(None)
        monkeypatch.undo()
        importlib.reload(mod)

    def test_create_3d_columns_raises(self, monkeypatch):
        import siege_utilities.reporting.map_3d as mod
        monkeypatch.setitem(sys.modules, "pydeck", None)
        reloaded = importlib.reload(mod)
        with pytest.raises(ImportError, match="pydeck"):
            reloaded.create_3d_columns(None, value_col="v")
        monkeypatch.undo()
        importlib.reload(mod)
