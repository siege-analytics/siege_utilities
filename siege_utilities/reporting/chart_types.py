"""
Extensible chart type system for siege_utilities.
Provides base chart types and easy extension capabilities.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Type
from dataclasses import dataclass, field
import yaml
from abc import ABC, abstractmethod
import pandas as pd
import geopandas as gpd
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import seaborn as sns

log = logging.getLogger(__name__)

@dataclass
class ChartType:
    """Base chart type configuration."""
    
    name: str
    category: str  # 'geographic', 'statistical', 'temporal', 'comparative'
    description: str = ""
    
    # Required parameters
    required_parameters: List[str] = field(default_factory=list)
    
    # Optional parameters with defaults
    optional_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Chart properties
    supports_interactive: bool = False
    supports_3d: bool = False
    supports_animation: bool = False
    
    # Rendering options
    default_width: float = 10.0
    default_height: float = 8.0
    default_dpi: int = 300
    
    # Custom elements
    custom_options: Dict[str, Any] = field(default_factory=dict)
    
    # Chart functions
    create_function: Optional[Callable] = None
    validate_function: Optional[Callable] = None
    customize_function: Optional[Callable] = None

class ChartTypeRegistry:
    """
    Registry for chart types and their implementations.
    Provides easy extension and customization of chart types.
    """
    
    def __init__(self):
        """Initialize the chart type registry."""
        self.chart_types: Dict[str, ChartType] = {}
        self._register_default_chart_types()
    
    def _register_default_chart_types(self):
        """Register built-in default chart types."""
        
        # Geographic Chart Types
        self.register_chart_type(ChartType(
            name='bivariate_choropleth',
            category='geographic',
            description='Two-variable choropleth map showing relationships between variables',
            required_parameters=['data', 'location_column', 'value_column1', 'value_column2'],
            optional_parameters={
                'geodata': None,
                'title': '',
                'width': 12.0,
                'height': 10.0,
                'color_scheme': 'custom',
                'classification': 'natural_breaks',
                'bins': 5
            },
            supports_interactive=True,
            custom_options={
                'map_projection': 'mercator',
                'legend_position': 'right',
                'boundary_style': 'solid'
            }
        ))
        
        self.register_chart_type(ChartType(
            name='marker_map',
            category='geographic',
            description='Point-based map with customizable markers',
            required_parameters=['data', 'latitude_column', 'longitude_column'],
            optional_parameters={
                'value_column': None,
                'label_column': None,
                'title': '',
                'map_style': 'open-street-map',
                'zoom_level': 10
            },
            supports_interactive=True,
            custom_options={
                'marker_style': 'circle',
                'popup_content': True,
                'cluster_markers': False
            }
        ))
        
        self.register_chart_type(ChartType(
            name='3d_map',
            category='geographic',
            description='Three-dimensional elevation visualization',
            required_parameters=['data', 'latitude_column', 'longitude_column', 'elevation_column'],
            optional_parameters={
                'title': '',
                'view_angle': 45,
                'elevation_scale': 1.0
            },
            supports_3d=True,
            custom_options={
                'surface_type': 'triangulation',
                'color_map': 'terrain',
                'axis_labels': True
            }
        ))
        
        self.register_chart_type(ChartType(
            name='heatmap_map',
            category='geographic',
            description='Density and intensity heatmap',
            required_parameters=['data', 'latitude_column', 'longitude_column', 'value_column'],
            optional_parameters={
                'title': '',
                'grid_size': 50,
                'blur_radius': 0.5
            },
            supports_interactive=True,
            custom_options={
                'color_gradient': 'blue_to_red',
                'intensity_scale': 'logarithmic',
                'smoothing': True
            }
        ))
        
        self.register_chart_type(ChartType(
            name='cluster_map',
            category='geographic',
            description='Clustered point data visualization',
            required_parameters=['data', 'latitude_column', 'longitude_column'],
            optional_parameters={
                'cluster_column': None,
                'label_column': None,
                'title': '',
                'max_cluster_radius': 80
            },
            supports_interactive=True,
            custom_options={
                'cluster_algorithm': 'kmeans',
                'cluster_colors': True,
                'expand_on_click': True
            }
        ))
        
        self.register_chart_type(ChartType(
            name='flow_map',
            category='geographic',
            description='Movement and connection flow visualization',
            required_parameters=['data', 'origin_lat_column', 'origin_lon_column', 
                              'dest_lat_column', 'dest_lon_column'],
            optional_parameters={
                'flow_value_column': None,
                'title': ''
            },
            supports_interactive=True,
            custom_options={
                'flow_style': 'curved',
                'arrow_heads': True,
                'flow_colors': True
            }
        ))
        
        # Statistical Chart Types
        self.register_chart_type(ChartType(
            name='bar_chart',
            category='statistical',
            description='Bar chart for categorical data comparison',
            required_parameters=['data', 'x_column', 'y_column'],
            optional_parameters={
                'title': '',
                'orientation': 'vertical',
                'color': 'steelblue'
            },
            custom_options={
                'bar_width': 0.8,
                'error_bars': False,
                'stacked': False
            }
        ))
        
        self.register_chart_type(ChartType(
            name='line_chart',
            category='statistical',
            description='Line chart for trend visualization',
            required_parameters=['data', 'x_column', 'y_column'],
            optional_parameters={
                'title': '',
                'line_style': '-',
                'markers': False
            },
            custom_options={
                'smooth_lines': False,
                'confidence_interval': False,
                'multiple_lines': False
            }
        ))
        
        self.register_chart_type(ChartType(
            name='scatter_plot',
            category='statistical',
            description='Scatter plot for correlation analysis',
            required_parameters=['data', 'x_column', 'y_column'],
            optional_parameters={
                'title': '',
                'color_column': None,
                'size_column': None
            },
            custom_options={
                'trend_line': False,
                'regression': False,
                'density_contours': False
            }
        ))
        
        # Temporal Chart Types
        self.register_chart_type(ChartType(
            name='time_series',
            category='temporal',
            description='Time series visualization',
            required_parameters=['data', 'time_column', 'value_column'],
            optional_parameters={
                'title': '',
                'frequency': 'daily',
                'rolling_window': None
            },
            custom_options={
                'seasonal_decomposition': False,
                'forecast': False,
                'anomaly_detection': False
            }
        ))
        
        # Comparative Chart Types
        self.register_chart_type(ChartType(
            name='comparison_chart',
            category='comparative',
            description='Side-by-side comparison visualization',
            required_parameters=['data', 'comparison_column', 'value_column'],
            optional_parameters={
                'title': '',
                'chart_type': 'grouped_bar',
                'baseline': None
            },
            custom_options={
                'statistical_test': False,
                'effect_size': False,
                'confidence_intervals': True
            }
        ))
    
    def register_chart_type(self, chart_type: ChartType):
        """
        Register a new chart type.
        
        Args:
            chart_type: ChartType object to register
        """
        self.chart_types[chart_type.name] = chart_type
        log.info(f"Registered chart type: {chart_type.name}")
    
    def get_chart_type(self, chart_type_name: str) -> Optional[ChartType]:
        """
        Get a chart type by name.
        
        Args:
            chart_type_name: Name of the chart type
            
        Returns:
            ChartType object or None if not found
        """
        return self.chart_types.get(chart_type_name)
    
    def list_chart_types(self, category: Optional[str] = None) -> List[str]:
        """
        List available chart types.
        
        Args:
            category: Filter by category
            
        Returns:
            List of chart type names
        """
        if category:
            return [name for name, chart_type in self.chart_types.items() 
                   if chart_type.category == category]
        return list(self.chart_types.keys())
    
    def get_chart_categories(self) -> List[str]:
        """Get list of available chart categories."""
        categories = set(chart_type.category for chart_type in self.chart_types.values())
        return sorted(list(categories))
    
    def create_chart(self, chart_type_name: str, **kwargs) -> Optional[Figure]:
        """
        Create a chart using the specified chart type.
        
        Args:
            chart_type_name: Name of the chart type
            **kwargs: Chart parameters
            
        Returns:
            Matplotlib Figure object or None if creation fails
        """
        chart_type = self.get_chart_type(chart_type_name)
        if not chart_type:
            log.error(f"Chart type not found: {chart_type_name}")
            return None
        
        # Validate required parameters
        missing_params = [param for param in chart_type.required_parameters 
                         if param not in kwargs]
        if missing_params:
            log.error(f"Missing required parameters: {missing_params}")
            return None
        
        # Apply default values for optional parameters
        for param, default_value in chart_type.optional_parameters.items():
            if param not in kwargs:
                kwargs[param] = default_value
        
        # Create chart using the registered function
        if chart_type.create_function:
            try:
                return chart_type.create_function(**kwargs)
            except Exception as e:
                log.error(f"Failed to create chart {chart_type_name}: {e}")
                return None
        else:
            log.warning(f"No create function registered for chart type: {chart_type_name}")
            return None
    
    def add_chart_creator(self, chart_type_name: str, create_function: Callable):
        """
        Add or update the create function for a chart type.
        
        Args:
            chart_type_name: Name of the chart type
            create_function: Function to create the chart
        """
        chart_type = self.get_chart_type(chart_type_name)
        if chart_type:
            chart_type.create_function = create_function
            log.info(f"Updated create function for chart type: {chart_type_name}")
        else:
            log.warning(f"Chart type not found: {chart_type_name}")
    
    def validate_chart_parameters(self, chart_type_name: str, **kwargs) -> bool:
        """
        Validate parameters for a chart type.
        
        Args:
            chart_type_name: Name of the chart type
            **kwargs: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        chart_type = self.get_chart_type(chart_type_name)
        if not chart_type:
            return False
        
        # Check required parameters
        missing_params = [param for param in chart_type.required_parameters 
                         if param not in kwargs]
        if missing_params:
            log.warning(f"Missing required parameters: {missing_params}")
            return False
        
        # Run custom validation if available
        if chart_type.validate_function:
            try:
                return chart_type.validate_function(**kwargs)
            except Exception as e:
                log.error(f"Validation function failed: {e}")
                return False
        
        return True
    
    def get_chart_help(self, chart_type_name: str) -> Dict[str, Any]:
        """
        Get help information for a chart type.
        
        Args:
            chart_type_name: Name of the chart type
            
        Returns:
            Dictionary with help information
        """
        chart_type = self.get_chart_type(chart_type_name)
        if not chart_type:
            return {}
        
        return {
            'name': chart_type.name,
            'category': chart_type.category,
            'description': chart_type.description,
            'required_parameters': chart_type.required_parameters,
            'optional_parameters': chart_type.optional_parameters,
            'custom_options': chart_type.custom_options,
            'supports_interactive': chart_type.supports_interactive,
            'supports_3d': chart_type.supports_3d,
            'supports_animation': chart_type.supports_animation
        }
    
    def export_chart_type_config(self, chart_type_name: str, output_path: str):
        """
        Export chart type configuration to a file.
        
        Args:
            chart_type_name: Name of the chart type to export
            output_path: Path to export the configuration
        """
        chart_type = self.get_chart_type(chart_type_name)
        if not chart_type:
            log.warning(f"Chart type not found: {chart_type_name}")
            return
        
        try:
            # Convert to dict, excluding function references
            config_data = {
                'name': chart_type.name,
                'category': chart_type.category,
                'description': chart_type.description,
                'required_parameters': chart_type.required_parameters,
                'optional_parameters': chart_type.optional_parameters,
                'supports_interactive': chart_type.supports_interactive,
                'supports_3d': chart_type.supports_3d,
                'supports_animation': chart_type.supports_animation,
                'default_width': chart_type.default_width,
                'default_height': chart_type.default_height,
                'default_dpi': chart_type.default_dpi,
                'custom_options': chart_type.custom_options
            }
            
            with open(output_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            log.info(f"Exported chart type configuration to: {output_path}")
        except Exception as e:
            log.error(f"Failed to export chart type configuration: {e}")

# Global instance
chart_registry = ChartTypeRegistry()

def get_chart_registry() -> ChartTypeRegistry:
    """Get the global chart type registry."""
    return chart_registry

def register_chart_type(chart_type: ChartType):
    """Register a new chart type."""
    chart_registry.register_chart_type(chart_type)

def create_chart(chart_type_name: str, **kwargs) -> Optional[Figure]:
    """Create a chart using the specified chart type."""
    return chart_registry.create_chart(chart_type_name, **kwargs)
