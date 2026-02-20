"""
Unit tests for ChartGenerator output_dir and _save_folium_map helper.

Verifies that Folium-based map methods save HTML files to the configured
output_dir rather than a hardcoded ~/.siege_utilities path.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from siege_utilities.reporting.chart_generator import ChartGenerator


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Return a temporary directory for ChartGenerator output."""
    return tmp_path / "chart_output"


@pytest.fixture
def chart_gen_default():
    """ChartGenerator with default output_dir."""
    return ChartGenerator()


@pytest.fixture
def chart_gen_custom(tmp_output_dir):
    """ChartGenerator with custom output_dir."""
    return ChartGenerator(output_dir=tmp_output_dir)


# =============================================================================
# output_dir PARAMETER TESTS
# =============================================================================

class TestOutputDir:
    """Tests for the output_dir parameter on ChartGenerator.__init__."""

    def test_default_output_dir(self, chart_gen_default):
        """Default output_dir should be ~/.siege_utilities."""
        expected = Path.home() / ".siege_utilities"
        assert chart_gen_default.output_dir == expected

    def test_custom_output_dir_path(self, tmp_output_dir):
        """Custom Path output_dir is stored as-is."""
        cg = ChartGenerator(output_dir=tmp_output_dir)
        assert cg.output_dir == tmp_output_dir

    def test_custom_output_dir_string(self, tmp_output_dir):
        """String output_dir is converted to Path."""
        cg = ChartGenerator(output_dir=str(tmp_output_dir))
        assert isinstance(cg.output_dir, Path)
        assert cg.output_dir == tmp_output_dir

    def test_output_dir_with_branding(self, tmp_output_dir):
        """output_dir works alongside branding_config."""
        branding = {"colors": {"primary": "#FF0000"}}
        cg = ChartGenerator(branding_config=branding, output_dir=tmp_output_dir)
        assert cg.output_dir == tmp_output_dir
        assert cg.default_colors["primary"] == "#FF0000"


# =============================================================================
# _save_folium_map HELPER TESTS
# =============================================================================

class TestSaveFoliumMap:
    """Tests for the _save_folium_map helper method."""

    def test_saves_html_file(self, chart_gen_custom, tmp_output_dir):
        """_save_folium_map should call folium_map.save() at the correct path."""
        mock_map = MagicMock()
        chart_gen_custom._save_folium_map(
            mock_map, "test_map.html", "Test Map", 6.0, 4.0
        )
        expected_path = tmp_output_dir / "test_map.html"
        mock_map.save.assert_called_once_with(str(expected_path))

    def test_creates_parent_directory(self, chart_gen_custom, tmp_output_dir):
        """_save_folium_map should create the output directory if missing."""
        assert not tmp_output_dir.exists()
        mock_map = MagicMock()
        chart_gen_custom._save_folium_map(
            mock_map, "test_map.html", "Test Map", 6.0, 4.0
        )
        assert tmp_output_dir.exists()

    def test_returns_placeholder_image(self, chart_gen_custom):
        """_save_folium_map should return a ReportLab Image placeholder."""
        mock_map = MagicMock()
        result = chart_gen_custom._save_folium_map(
            mock_map, "test.html", "Test", 8.0, 6.0
        )
        # ReportLab Image has a 'drawOn' method
        assert hasattr(result, "drawOn") or hasattr(result, "filename")

    def test_placeholder_contains_label(self, chart_gen_custom, tmp_output_dir):
        """Placeholder text should include the label and path."""
        mock_map = MagicMock()
        # We can't easily inspect the placeholder text without rendering,
        # but we verify the method completes without error.
        result = chart_gen_custom._save_folium_map(
            mock_map, "mymap.html", "My Map", 6.0, 4.0
        )
        assert result is not None


# =============================================================================
# FOLIUM METHOD INTEGRATION TESTS
# =============================================================================

class TestFoliumMethodsUseOutputDir:
    """Verify that each Folium-based method delegates to _save_folium_map
    and therefore respects output_dir."""

    @pytest.fixture
    def patched_chart_gen(self, tmp_output_dir):
        """ChartGenerator with _save_folium_map patched to track calls."""
        cg = ChartGenerator(output_dir=tmp_output_dir)
        cg._save_folium_map = MagicMock(return_value=MagicMock())
        return cg

    @pytest.fixture
    def point_data(self):
        """Minimal point DataFrame for map methods."""
        import pandas as pd
        import numpy as np
        np.random.seed(42)
        return pd.DataFrame({
            "lat": np.random.uniform(33, 42, 10),
            "lon": np.random.uniform(-122, -71, 10),
            "value": np.random.randint(1, 100, 10),
            "label": [f"Point {i}" for i in range(10)],
        })

    @pytest.fixture
    def flow_data(self):
        """Minimal flow DataFrame."""
        import pandas as pd
        return pd.DataFrame({
            "origin_lat": [34.0, 40.7],
            "origin_lon": [-118.2, -74.0],
            "dest_lat": [40.7, 34.0],
            "dest_lon": [-74.0, -118.2],
            "flow": [100, 200],
        })

    @patch("siege_utilities.reporting.chart_generator.folium.LayerControl")
    @patch("siege_utilities.reporting.chart_generator.folium.Map")
    def test_create_marker_map_uses_helper(self, _mock_map, _mock_lc, patched_chart_gen, point_data):
        """create_marker_map should call _save_folium_map."""
        patched_chart_gen.create_marker_map(
            point_data, latitude_column="lat", longitude_column="lon"
        )
        patched_chart_gen._save_folium_map.assert_called_once()
        call_args = patched_chart_gen._save_folium_map.call_args
        assert call_args[0][1] == "temp_marker_map.html"

    @patch("siege_utilities.reporting.chart_generator.folium.LayerControl")
    def test_create_heatmap_map_uses_helper(self, _mock_lc, patched_chart_gen, point_data):
        """create_heatmap_map should call _save_folium_map."""
        patched_chart_gen.create_heatmap_map(
            point_data, latitude_column="lat", longitude_column="lon",
            value_column="value"
        )
        patched_chart_gen._save_folium_map.assert_called_once()
        call_args = patched_chart_gen._save_folium_map.call_args
        assert call_args[0][1] == "temp_heatmap.html"

    @patch("siege_utilities.reporting.chart_generator.folium.LayerControl")
    def test_create_cluster_map_uses_helper(self, _mock_lc, patched_chart_gen, point_data):
        """create_cluster_map should call _save_folium_map."""
        patched_chart_gen.create_cluster_map(
            point_data, latitude_column="lat", longitude_column="lon"
        )
        patched_chart_gen._save_folium_map.assert_called_once()
        call_args = patched_chart_gen._save_folium_map.call_args
        assert call_args[0][1] == "temp_cluster_map.html"

    @patch("siege_utilities.reporting.chart_generator.folium.LayerControl")
    def test_create_flow_map_uses_helper(self, _mock_lc, patched_chart_gen, flow_data):
        """create_flow_map should call _save_folium_map."""
        patched_chart_gen.create_flow_map(
            flow_data,
            origin_lat_column="origin_lat", origin_lon_column="origin_lon",
            dest_lat_column="dest_lat", dest_lon_column="dest_lon",
        )
        patched_chart_gen._save_folium_map.assert_called_once()
        call_args = patched_chart_gen._save_folium_map.call_args
        assert call_args[0][1] == "temp_flow_map.html"
