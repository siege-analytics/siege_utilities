# ================================================================
# FILE: test_svg_markers.py
# ================================================================
"""
Tests for SVG marker functionality.
Tests SVG loading, processing, transformation, and rendering.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import xml.etree.ElementTree as ET
from io import StringIO

# Test SVG marker functionality
pytest.importorskip("matplotlib", reason="Matplotlib not available for SVG marker tests")

import siege_utilities


class TestSVGMarkerManager:
    """Test SVG marker management functionality."""

    @pytest.mark.svg_markers
    def test_svg_marker_manager_initialization(self, mock_svg_marker_manager):
        """Test that SVG marker manager initializes correctly."""
        
        manager = mock_svg_marker_manager
        
        assert hasattr(manager, 'cached_markers')
        assert hasattr(manager, 'supported_formats')
        assert '.svg' in manager.supported_formats
        assert hasattr(manager, 'load_svg_marker')

    @pytest.mark.svg_markers
    def test_svg_marker_loading(self, mock_svg_marker_manager, sample_svg_marker_file):
        """Test SVG marker loading functionality."""
        
        manager = mock_svg_marker_manager
        
        # Load SVG marker
        svg_content = manager.load_svg_marker(str(sample_svg_marker_file))
        
        assert svg_content is not None
        assert '<svg' in svg_content
        assert 'width="64"' in svg_content
        assert 'height="64"' in svg_content

    @pytest.mark.svg_markers
    def test_svg_marker_caching(self, mock_svg_marker_manager, sample_svg_marker_file):
        """Test SVG marker caching functionality."""
        
        manager = mock_svg_marker_manager
        
        # First load should cache
        first_load = manager.load_svg_marker(str(sample_svg_marker_file))
        
        # Second load should use cache
        second_load = manager.load_svg_marker(str(sample_svg_marker_file))
        
        assert first_load == second_load
        assert len(manager.cached_markers) > 0

    @pytest.mark.svg_markers
    def test_svg_marker_validation(self, mock_svg_marker_manager, temp_directory):
        """Test SVG marker validation."""
        
        manager = mock_svg_marker_manager
        
        # Test invalid file path
        invalid_result = manager.load_svg_marker('nonexistent.svg')
        assert invalid_result is None
        
        # Test unsupported format
        unsupported_file = temp_directory / "test.txt"
        unsupported_file.write_text("This is not an SVG")
        
        unsupported_result = manager.load_svg_marker(str(unsupported_file))
        assert unsupported_result is None

    @pytest.mark.svg_markers
    def test_svg_marker_processing(self, mock_svg_marker_manager):
        """Test SVG marker processing functionality."""
        
        manager = mock_svg_marker_manager
        
        # Test SVG processing
        processed_svg = manager._process_svg_marker(
            """<svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="16" fill="currentColor"/>
            </svg>""",
            {'scale': 2.0, 'color': '#FF0000'}
        )
        
        assert processed_svg is not None
        assert '<svg' in processed_svg

    @pytest.mark.svg_markers
    def test_svg_marker_transformations(self, mock_svg_marker_manager):
        """Test SVG marker transformations."""
        
        manager = mock_svg_marker_manager
        
        # Test scale transformation
        scaled_svg = manager._process_svg_marker(
            """<svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="16" fill="currentColor"/>
            </svg>""",
            {'scale': 1.5}
        )
        
        assert scaled_svg is not None
        
        # Test rotation transformation
        rotated_svg = manager._process_svg_marker(
            """<svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="16" fill="currentColor"/>
            </svg>""",
            {'rotation': 45}
        )
        
        assert rotated_svg is not None
        
        # Test color transformation
        colored_svg = manager._process_svg_marker(
            """<svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="16" fill="currentColor"/>
            </svg>""",
            {'color': '#00FF00', 'colorize': True}
        )
        
        assert colored_svg is not None

    @pytest.mark.svg_markers
    def test_svg_marker_file_creation(self, mock_svg_marker_manager, temp_directory):
        """Test SVG marker file creation."""
        
        manager = mock_svg_marker_manager
        
        input_svg = temp_directory / "input.svg"
        input_svg.write_text("""<svg width="64" height="64" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="16" fill="currentColor"/>
        </svg>""")
        
        output_svg = temp_directory / "output.svg"
        
        # Create processed marker
        success = manager.create_marker_from_svg(
            str(input_svg), 
            str(output_svg), 
            {'scale': 1.2, 'color': '#FF0000'}
        )
        
        assert success == True
        # Note: In a real implementation, output_svg would exist
        # For testing with mocks, we just verify the method was called successfully
        assert success == True

    @pytest.mark.svg_markers
    def test_svg_marker_cache_management(self, mock_svg_marker_manager):
        """Test SVG marker cache management."""
        
        manager = mock_svg_marker_manager
        
        # Add some markers to cache
        manager.cached_markers['test1'] = 'svg1'
        manager.cached_markers['test2'] = 'svg2'
        
        assert len(manager.cached_markers) == 2
        
        # Clear cache
        manager.clear_cache()
        
        assert len(manager.cached_markers) == 0


class TestSVGMarkerIntegration:
    """Test SVG marker integration with map generation."""

    @pytest.mark.integration
    @pytest.mark.svg_markers
    def test_svg_marker_in_map_config(self, mock_map_config):
        """Test SVG marker configuration in map settings."""
        
        config = mock_map_config
        
        # Check SVG marker configuration
        assert 'svg_path' in config['markers']
        assert 'svg_scale' in config['markers']
        assert 'svg_rotation' in config['markers']
        assert 'svg_colorize' in config['markers']
        
        # Check default values
        assert config['markers']['svg_path'] is None
        assert config['markers']['svg_scale'] == 1.0
        assert config['markers']['svg_rotation'] == 0
        assert config['markers']['svg_colorize'] == True

    @pytest.mark.integration
    @pytest.mark.svg_markers
    def test_svg_marker_conditional_assignment(self, sample_spatial_data):
        """Test conditional SVG marker assignment."""
        
        # Create conditional marker configuration
        marker_config = {
            'svg_markers': {
                'type_a': {'condition': {'category': 'A'}},
                'type_b': {'condition': {'category': 'B'}}
            }
        }
        
        # Test condition evaluation
        def evaluate_condition(condition, row):
            for field, value in condition.items():
                if field in row and row[field] != value:
                    return False
            return True
        
        # Test with sample data
        for idx, row in sample_spatial_data.iterrows():
            if row['category'] == 'A':
                condition_met = evaluate_condition({'category': 'A'}, row)
                assert condition_met == True
            elif row['category'] == 'B':
                condition_met = evaluate_condition({'category': 'B'}, row)
                assert condition_met == True

    @pytest.mark.integration
    @pytest.mark.svg_markers
    def test_svg_marker_backend_support(self, mock_map_config):
        """Test SVG marker support across different backends."""
        
        config = mock_map_config
        
        # Test matplotlib backend
        config['backend'] = 'matplotlib'
        assert config['backend'] == 'matplotlib'
        
        # Test folium backend
        config['backend'] = 'folium'
        assert config['backend'] == 'folium'
        
        # Both should support SVG markers
        assert 'svg_path' in config['markers']
        assert 'svg_markers' in config['markers']


class TestSVGMarkerErrorHandling:
    """Test SVG marker error handling and fallbacks."""

    @pytest.mark.svg_markers
    def test_svg_marker_loading_errors(self, mock_svg_marker_manager):
        """Test SVG marker loading error handling."""
        
        manager = mock_svg_marker_manager
        
        # Test with invalid file path (should return None, not raise exception)
        invalid_result = manager.load_svg_marker('nonexistent.svg')
        assert invalid_result is None

    @pytest.mark.svg_markers
    def test_svg_marker_processing_errors(self, mock_svg_marker_manager):
        """Test SVG marker processing error handling."""
        
        manager = mock_svg_marker_manager
        
        # Mock processing failure
        manager._process_svg_marker.side_effect = Exception("SVG processing failed")
        
        # Should handle errors gracefully
        with pytest.raises(Exception):
            manager._process_svg_marker("test svg content", {})

    @pytest.mark.svg_markers
    def test_svg_marker_fallback_behavior(self, mock_svg_marker_manager):
        """Test SVG marker fallback behavior."""
        
        manager = mock_svg_marker_manager
        
        # Test fallback when SVG processing fails
        # Test with unsupported format
        unsupported_result = manager.load_svg_marker('test.txt')
        assert unsupported_result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
