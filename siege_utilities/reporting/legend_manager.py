"""
Legend management utilities for siege_utilities reporting system.
Provides comprehensive legend generation and management for charts, tables, and visualizations.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum

# Core plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

# ReportLab for PDF generation
try:
    from reportlab.platypus import Table, Paragraph, Spacer, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    Table = None
    TableStyle = None
    Paragraph = None
    Spacer = None
    colors = None
    inch = None
    getSampleStyleSheet = None

log = logging.getLogger(__name__)

class LegendPosition(Enum):
    """Enumeration of legend positions"""
    BEST = "best"
    OUTSIDE = "outside"
    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"

class ColorScheme(Enum):
    """Enumeration of color schemes for legends"""
    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    PURPLE = "purple"
    ORANGE = "orange"
    GRAY = "gray"

class LegendManager:
    """
    Comprehensive legend management system for charts, tables, and visualizations.
    Provides consistent legend generation across all siege_utilities components.
    """
    
    def __init__(self, branding_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the legend manager.
        
        Args:
            branding_config: Branding configuration for colors and styling
        """
        self.branding_config = branding_config or {}
        self._setup_default_colors()
        self._setup_legend_styles()
    
    def _setup_default_colors(self):
        """Setup default color schemes for legends."""
        self.color_schemes = {
            ColorScheme.BLUE: {
                'low': '#87CEEB',    # Light blue
                'high': '#1E3A5F',   # Dark blue
                'name': 'Blue Gradient'
            },
            ColorScheme.GREEN: {
                'low': '#C8E6C9',   # Light green
                'high': '#2E7D32',   # Dark green
                'name': 'Green Gradient'
            },
            ColorScheme.RED: {
                'low': '#FFCDD2',   # Light red
                'high': '#C62828',   # Dark red
                'name': 'Red Gradient'
            },
            ColorScheme.PURPLE: {
                'low': '#E1BEE7',   # Light purple
                'high': '#7B1FA2',   # Dark purple
                'name': 'Purple Gradient'
            },
            ColorScheme.ORANGE: {
                'low': '#FFE0B2',   # Light orange
                'high': '#F57C00',   # Dark orange
                'name': 'Orange Gradient'
            },
            ColorScheme.GRAY: {
                'low': '#F5F5F5',   # Light gray
                'high': '#424242',   # Dark gray
                'name': 'Gray Gradient'
            }
        }
    
    def _setup_legend_styles(self):
        """Setup default legend styling parameters."""
        self.legend_styles = {
            'frameon': True,
            'fancybox': True,
            'shadow': True,
            'framealpha': 0.9,
            'edgecolor': 'black',
            'facecolor': 'white',
            'fontsize': 9,
            'title_fontsize': 10
        }
    
    def get_color_for_intensity(self, intensity: float, color_scheme: ColorScheme = ColorScheme.BLUE) -> str:
        """
        Get color for a given intensity (0-1) using specified color scheme.
        
        Args:
            intensity: Intensity value between 0 and 1
            color_scheme: Color scheme to use
            
        Returns:
            Hex color string
        """
        if color_scheme not in self.color_schemes:
            color_scheme = ColorScheme.BLUE
        
        scheme = self.color_schemes[color_scheme]
        low_color = scheme['low']
        high_color = scheme['high']
        
        # Convert hex to RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        low_rgb = hex_to_rgb(low_color)
        high_rgb = hex_to_rgb(high_color)
        
        # Interpolate between low and high colors
        interpolated_rgb = tuple(
            int(low_rgb[i] + (high_rgb[i] - low_rgb[i]) * intensity)
            for i in range(3)
        )
        
        return rgb_to_hex(interpolated_rgb)
    
    def create_heatmap_legend_table(self, min_value: float, max_value: float, 
                                  value_name: str = "Value", 
                                  color_scheme: ColorScheme = ColorScheme.BLUE,
                                  levels: int = 5) -> Optional[Table]:
        """
        Create a heatmap legend table for ReportLab.
        
        Args:
            min_value: Minimum value in the data
            max_value: Maximum value in the data
            value_name: Name of the value being visualized
            color_scheme: Color scheme to use
            levels: Number of intensity levels (default 5)
            
        Returns:
            ReportLab Table object or None if ReportLab not available
        """
        if not REPORTLAB_AVAILABLE:
            log.warning("ReportLab not available for legend table generation")
            return None
        
        styles = getSampleStyleSheet()
        
        # Create legend data
        legend_data = [["Intensity", "Color", f"{value_name} Range"]]
        
        for i in range(levels):
            intensity = i / (levels - 1)  # 0 to 1
            value = min_value + (max_value - min_value) * intensity
            
            if i == 0:
                range_text = f"Low: {min_value:,.0f} - {int(value):,}"
            elif i == levels - 1:
                range_text = f"High: {int(value):,}+"
            else:
                prev_value = min_value + (max_value - min_value) * ((i-1) / (levels-1))
                range_text = f"{int(prev_value):,} - {int(value):,}"
            
            legend_data.append([f"{intensity*100:.0f}%", "█", range_text])
        
        # Create table
        legend_table = Table(legend_data, colWidths=[1*inch, 0.5*inch, 2*inch])
        
        # Create table style
        legend_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E7D32')),  # Header
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]
        
        # Add color backgrounds for legend
        for i in range(1, levels + 1):
            intensity = (i-1) / (levels-1)
            heat_color = self.get_color_for_intensity(intensity, color_scheme)
            legend_style.append(('BACKGROUND', (1,i), (1,i), colors.HexColor(heat_color)))
        
        legend_table.setStyle(TableStyle(legend_style))
        return legend_table
    
    def create_matplotlib_legend(self, ax, labels: List[str], title: str = "Legend",
                               position: LegendPosition = LegendPosition.BEST,
                               **kwargs) -> None:
        """
        Create a matplotlib legend with enhanced styling.
        
        Args:
            ax: Matplotlib axes object
            labels: List of legend labels
            title: Legend title
            position: Legend position
            **kwargs: Additional legend parameters
        """
        if not MATPLOTLIB_AVAILABLE:
            log.warning("Matplotlib not available for legend creation")
            return
        
        # Merge default styles with provided kwargs
        legend_kwargs = {**self.legend_styles, **kwargs}
        
        # Set position-specific parameters
        if position == LegendPosition.OUTSIDE:
            legend_kwargs.update({
                'bbox_to_anchor': (1.05, 1),
                'loc': 'upper left'
            })
        elif position == LegendPosition.BOTTOM:
            legend_kwargs.update({
                'bbox_to_anchor': (0.5, -0.15),
                'loc': 'upper center',
                'ncol': min(3, len(labels))
            })
        elif position == LegendPosition.TOP:
            legend_kwargs.update({
                'bbox_to_anchor': (0.5, 1.15),
                'loc': 'lower center',
                'ncol': min(3, len(labels))
            })
        elif position == LegendPosition.LEFT:
            legend_kwargs.update({
                'bbox_to_anchor': (0, 0, 0.5, 1),
                'loc': 'center right'
            })
        elif position == LegendPosition.RIGHT:
            legend_kwargs.update({
                'bbox_to_anchor': (1, 0, 0.5, 1),
                'loc': 'center left'
            })
        else:  # BEST or CENTER
            legend_kwargs['loc'] = position.value
        
        # Create legend
        legend = ax.legend(labels, title=title, **legend_kwargs)
        
        # Apply additional styling
        if legend:
            legend.get_frame().set_facecolor(legend_kwargs.get('facecolor', 'white'))
            legend.get_frame().set_alpha(legend_kwargs.get('framealpha', 0.9))
            legend.get_frame().set_edgecolor(legend_kwargs.get('edgecolor', 'black'))
    
    def create_legend_for_series(self, ax, series_data: Dict[str, Any], 
                                title: str = "Legend",
                                position: LegendPosition = LegendPosition.BEST) -> None:
        """
        Create a legend for multiple data series.
        
        Args:
            ax: Matplotlib axes object
            series_data: Dictionary mapping series names to their data/colors
            title: Legend title
            position: Legend position
        """
        if not MATPLOTLIB_AVAILABLE:
            return
        
        labels = list(series_data.keys())
        self.create_matplotlib_legend(ax, labels, title, position)
    
    def create_heatmap_legend_elements(self, min_value: float, max_value: float,
                                     color_scheme: ColorScheme = ColorScheme.BLUE,
                                     levels: int = 5) -> List[mpatches.Patch]:
        """
        Create matplotlib legend elements for heatmap visualization.
        
        Args:
            min_value: Minimum value in the data
            max_value: Maximum value in the data
            color_scheme: Color scheme to use
            levels: Number of intensity levels
            
        Returns:
            List of matplotlib Patch objects for legend
        """
        if not MATPLOTLIB_AVAILABLE:
            return []
        
        legend_elements = []
        
        for i in range(levels):
            intensity = i / (levels - 1)
            value = min_value + (max_value - min_value) * intensity
            color = self.get_color_for_intensity(intensity, color_scheme)
            
            if i == 0:
                label = f"Low: {min_value:,.0f} - {int(value):,}"
            elif i == levels - 1:
                label = f"High: {int(value):,}+"
            else:
                prev_value = min_value + (max_value - min_value) * ((i-1) / (levels-1))
                label = f"{int(prev_value):,} - {int(value):,}"
            
            legend_elements.append(mpatches.Patch(color=color, label=label))
        
        return legend_elements
    
    def add_heatmap_legend_to_plot(self, ax, min_value: float, max_value: float,
                                  color_scheme: ColorScheme = ColorScheme.BLUE,
                                  position: LegendPosition = LegendPosition.RIGHT,
                                  title: str = "Intensity") -> None:
        """
        Add a heatmap legend directly to a matplotlib plot.
        
        Args:
            ax: Matplotlib axes object
            min_value: Minimum value in the data
            max_value: Maximum value in the data
            color_scheme: Color scheme to use
            position: Legend position
            title: Legend title
        """
        if not MATPLOTLIB_AVAILABLE:
            return
        
        legend_elements = self.create_heatmap_legend_elements(
            min_value, max_value, color_scheme
        )
        
        if legend_elements:
            legend = ax.legend(handles=legend_elements, title=title, 
                             loc=position.value, **self.legend_styles)
            
            if legend:
                legend.get_frame().set_facecolor(self.legend_styles['facecolor'])
                legend.get_frame().set_alpha(self.legend_styles['framealpha'])
    
    def get_legend_position_for_chart_type(self, chart_type: str, 
                                          data_size: int) -> LegendPosition:
        """
        Get optimal legend position based on chart type and data size.
        
        Args:
            chart_type: Type of chart ('bar', 'line', 'pie', 'scatter', etc.)
            data_size: Number of data series or categories
            
        Returns:
            Recommended LegendPosition
        """
        if chart_type == 'pie':
            return LegendPosition.RIGHT if data_size <= 5 else LegendPosition.BOTTOM
        elif chart_type == 'bar':
            return LegendPosition.OUTSIDE if data_size > 3 else LegendPosition.BEST
        elif chart_type == 'line':
            return LegendPosition.BEST if data_size <= 3 else LegendPosition.OUTSIDE
        elif chart_type == 'scatter':
            return LegendPosition.BEST
        else:
            return LegendPosition.BEST
    
    def should_show_legend(self, chart_type: str, data_size: int, 
                          series_count: int = 1) -> bool:
        """
        Determine if a legend should be shown based on chart characteristics.
        
        Args:
            chart_type: Type of chart
            data_size: Number of data points
            series_count: Number of data series
            
        Returns:
            True if legend should be shown
        """
        if chart_type == 'pie':
            return True  # Pie charts always benefit from legends
        elif chart_type in ['bar', 'line']:
            return series_count > 1 or data_size > 5
        elif chart_type == 'scatter':
            return series_count > 1
        else:
            return series_count > 1

# Convenience functions for easy access
def create_heatmap_legend_table(min_value: float, max_value: float, 
                               value_name: str = "Value",
                               color_scheme: str = "blue") -> Optional[Table]:
    """
    Convenience function to create a heatmap legend table.
    
    Args:
        min_value: Minimum value in the data
        max_value: Maximum value in the data
        value_name: Name of the value being visualized
        color_scheme: Color scheme name ('blue', 'green', 'red', etc.)
        
    Returns:
        ReportLab Table object or None
    """
    manager = LegendManager()
    scheme = ColorScheme.BLUE
    try:
        scheme = ColorScheme(color_scheme.lower())
    except ValueError:
        log.warning(f"Unknown color scheme '{color_scheme}', using blue")
    
    return manager.create_heatmap_legend_table(min_value, max_value, value_name, scheme)

def get_optimal_legend_position(chart_type: str, data_size: int) -> str:
    """
    Convenience function to get optimal legend position.
    
    Args:
        chart_type: Type of chart
        data_size: Number of data series
        
    Returns:
        Legend position string
    """
    manager = LegendManager()
    return manager.get_legend_position_for_chart_type(chart_type, data_size).value
