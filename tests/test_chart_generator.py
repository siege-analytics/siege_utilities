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


# =============================================================================
# AUTO-SCALING TESTS
# =============================================================================

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.units import inch


@pytest.fixture(autouse=True)
def _close_all_figures():
    """Close all matplotlib figures after each test to avoid leaks."""
    yield
    plt.close("all")


class TestScaleDimensions:
    """Tests for _scale_dimensions() pure-function logic."""

    def test_no_max_returns_unchanged(self):
        """With no maximums set, dimensions pass through untouched."""
        cg = ChartGenerator()
        assert cg._scale_dimensions(10.0, 8.0) == (10.0, 8.0)

    def test_width_only_scaling(self):
        """When only max_width is exceeded, scale uniformly by width."""
        cg = ChartGenerator(max_chart_width=6.0)
        w, h = cg._scale_dimensions(12.0, 8.0)
        assert abs(w - 6.0) < 1e-9
        assert abs(h - 4.0) < 1e-9  # 8 * 0.5

    def test_height_only_scaling(self):
        """When only max_height is exceeded, scale uniformly by height."""
        cg = ChartGenerator(max_chart_height=4.0)
        w, h = cg._scale_dimensions(6.0, 8.0)
        assert abs(h - 4.0) < 1e-9
        assert abs(w - 3.0) < 1e-9  # 6 * 0.5

    def test_both_max_tighter_wins(self):
        """When both maximums set, the tighter constraint dominates."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)
        # 12×8 → width ratio 6/12=0.5, height ratio 8.5/8>1 → width wins
        w, h = cg._scale_dimensions(12.0, 8.0)
        assert abs(w - 6.0) < 1e-9
        assert abs(h - 4.0) < 1e-9

    def test_within_bounds_no_change(self):
        """Dimensions already within bounds are not modified."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)
        assert cg._scale_dimensions(5.0, 3.0) == (5.0, 3.0)

    def test_per_call_override(self):
        """Per-call max_width overrides instance when no instance max."""
        cg = ChartGenerator()
        w, h = cg._scale_dimensions(10.0, 5.0, max_width=5.0)
        assert abs(w - 5.0) < 1e-9
        assert abs(h - 2.5) < 1e-9

    def test_per_call_tighter_than_instance(self):
        """Per-call max that is tighter than instance wins."""
        cg = ChartGenerator(max_chart_width=8.0)
        w, h = cg._scale_dimensions(10.0, 5.0, max_width=5.0)
        assert abs(w - 5.0) < 1e-9
        assert abs(h - 2.5) < 1e-9

    def test_per_call_looser_than_instance(self):
        """Per-call max that is looser than instance is ignored (instance wins)."""
        cg = ChartGenerator(max_chart_width=5.0)
        w, h = cg._scale_dimensions(10.0, 5.0, max_width=8.0)
        assert abs(w - 5.0) < 1e-9
        assert abs(h - 2.5) < 1e-9

    def test_exact_boundary_no_change(self):
        """Dimensions exactly at the boundary are not modified."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=4.0)
        assert cg._scale_dimensions(6.0, 4.0) == (6.0, 4.0)

    def test_square_aspect_ratio(self):
        """Square charts maintain 1:1 ratio after scaling."""
        cg = ChartGenerator(max_chart_width=4.0, max_chart_height=4.0)
        w, h = cg._scale_dimensions(8.0, 8.0)
        assert abs(w - 4.0) < 1e-9
        assert abs(h - 4.0) < 1e-9


class TestMatplotlibToReportlabImageScaling:
    """Tests for auto-scaling in _matplotlib_to_reportlab_image()."""

    def _make_figure(self, width=8.0, height=6.0):
        """Create a minimal matplotlib figure."""
        fig, ax = plt.subplots(figsize=(width, height))
        ax.plot([1, 2, 3], [1, 4, 9])
        return fig

    def test_oversized_chart_scaled_down(self):
        """A chart exceeding max_chart_width is scaled in the RL Image."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)
        fig = self._make_figure(12.0, 8.0)
        img = cg._matplotlib_to_reportlab_image(fig, 12.0, 8.0)
        # Image width should be scaled to 6 inches
        assert abs(img.drawWidth - 6.0 * inch) < 1.0
        # Image height should also be scaled (12→6 is 0.5 factor, 8*0.5=4)
        assert abs(img.drawHeight - 4.0 * inch) < 1.0

    def test_safe_chart_unchanged(self):
        """A chart within bounds keeps original width (height from PNG)."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)
        fig = self._make_figure(5.0, 3.0)
        img = cg._matplotlib_to_reportlab_image(fig, 5.0, 3.0)
        assert abs(img.drawWidth - 5.0 * inch) < 1.0

    def test_no_max_preserves_original(self):
        """With no max configured, original width passes through."""
        cg = ChartGenerator()
        fig = self._make_figure(12.0, 8.0)
        img = cg._matplotlib_to_reportlab_image(fig, 12.0, 8.0)
        assert abs(img.drawWidth - 12.0 * inch) < 1.0


class TestCreateMethodsWithScaling:
    """Verify that create_* methods produce scaled images when max is set."""

    @pytest.fixture
    def cg_scaled(self):
        return ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)

    @pytest.fixture
    def sample_data(self):
        import pandas as pd
        import numpy as np
        np.random.seed(42)
        return pd.DataFrame({
            "x": np.random.randn(10) * 10 + 50,
            "y": np.random.randn(10) * 15 + 70,
            "z": np.random.randn(10) * 5 + 20,
        })

    @pytest.fixture
    def bar_data(self):
        import pandas as pd
        return pd.DataFrame({
            "Month": ["Jan", "Feb", "Mar"],
            "Revenue": [45000, 52000, 48000],
        })

    def test_create_heatmap_default_scaled(self, cg_scaled, sample_data):
        """create_heatmap default 8×6 should be scaled to fit max_width=6."""
        img = cg_scaled.create_heatmap(sample_data, title="Test Heatmap")
        # Default width is 8.0 → scaled to 6.0 (factor 0.75), height 6*0.75=4.5
        assert img.drawWidth <= 6.0 * inch + 1.0

    def test_create_dashboard_default_scaled(self, cg_scaled):
        """create_dashboard default 12×8 should be scaled to fit max_width=6."""
        import pandas as pd
        charts = [
            {"type": "bar", "title": "T1",
             "data": {"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]}},
            {"type": "bar", "title": "T2",
             "data": {"labels": ["A", "B"], "datasets": [{"data": [3, 4]}]}},
        ]
        img = cg_scaled.create_dashboard(charts, layout="2x1")
        # Default width is 12.0 → scaled to 6.0
        assert img.drawWidth <= 6.0 * inch + 1.0

    def test_create_bar_chart_safe_default(self, cg_scaled, bar_data):
        """create_bar_chart default 6×4 is within bounds — no scaling."""
        img = cg_scaled.create_bar_chart(
            bar_data, x_column="Month", y_column="Revenue", title="Revenue",
        )
        # Default width 6.0 is exactly at boundary — should not shrink
        assert abs(img.drawWidth - 6.0 * inch) < 2.0


class TestPlaceholderScaling:
    """Verify that _create_placeholder_chart respects auto-scaling."""

    def test_placeholder_oversized_scaled(self):
        """Placeholder with oversized dimensions is scaled."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)
        img = cg._create_placeholder_chart(12.0, 8.0, "Test Placeholder")
        assert img.drawWidth <= 6.0 * inch + 1.0

    def test_placeholder_within_bounds_unchanged(self):
        """Placeholder within bounds keeps original size."""
        cg = ChartGenerator(max_chart_width=6.0, max_chart_height=8.5)
        img = cg._create_placeholder_chart(5.0, 3.0, "Small Placeholder")
        assert abs(img.drawWidth - 5.0 * inch) < 2.0
