"""
Chart generation utilities for siege_utilities reporting system.
Supports multiple chart types, maps, and data sources including pandas and Spark DataFrames.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import io
import base64

# Core plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    sns = None

# Interactive plotting
try:
    import plotly.graph_objects as go
    import plotly.express as px
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None

# Geographic plotting
try:
    import folium
    from folium import plugins
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    folium = None

# Geographic data processing
try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    gpd = None

# Data processing
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None

from reportlab.platypus import Image, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet

# Legend management will be added later
# from .legend_manager import LegendManager, LegendPosition, ColorScheme

from .engines import (
    BaseChartEngine,
    BarChartMixin,
    MapChartMixin,
    StatsChartMixin,
    CompositeChartMixin,
)

log = logging.getLogger(__name__)

class ChartGenerator(BaseChartEngine, BarChartMixin, MapChartMixin, StatsChartMixin, CompositeChartMixin):
    """
    Generates charts and visualizations for reports using matplotlib, seaborn, plotly, and folium.
    Supports pandas DataFrames, Spark DataFrames, and various data sources.

    All chart methods are provided by engine mixins:

    - **BaseChartEngine** — ``__init__``, scaling, placeholder, save/convert helpers
    - **BarChartMixin** — bar, line, pie, proportional text bar charts
    - **MapChartMixin** — choropleth, marker, 3D, heatmap-map, cluster, flow, bivariate maps
    - **StatsChartMixin** — statistical heatmap, scatter plot, text heatmap
    - **CompositeChartMixin** — convergence diagram, dashboard, summary charts, subplots
    """
    pass


# Standalone function wrappers for functional access
def create_bar_chart(data: Union['pd.DataFrame', Dict[str, Any]],
                    x_column: Optional[str] = None,
                    y_column: Optional[str] = None,
                    title: str = "",
                    width: int = 800,
                    height: int = 600,
                    **kwargs) -> Optional[Dict[str, Any]]:
    """
    Standalone function to create a bar chart.

    Args:
        data: DataFrame or data dictionary
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title
        width: Chart width in pixels
        height: Chart height in pixels
        **kwargs: Additional chart parameters

    Returns:
        Chart configuration dictionary or None if error
    """
    generator = ChartGenerator()
    return generator.create_bar_chart(
        data, x_column, y_column, title, width, height, **kwargs
    )


def create_line_chart(data: Union['pd.DataFrame', Dict[str, Any]],
                     x_column: Optional[str] = None,
                     y_column: Optional[str] = None,
                     title: str = "",
                     width: int = 800,
                     height: int = 600,
                     **kwargs) -> Optional[Dict[str, Any]]:
    """
    Standalone function to create a line chart.

    Args:
        data: DataFrame or data dictionary
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title
        width: Chart width in pixels
        height: Chart height in pixels
        **kwargs: Additional chart parameters

    Returns:
        Chart configuration dictionary or None if error
    """
    generator = ChartGenerator()
    return generator.create_line_chart(
        data, x_column, y_column, title, width, height, **kwargs
    )


def create_scatter_plot(data: Union['pd.DataFrame', Dict[str, Any]],
                       x_column: Optional[str] = None,
                       y_column: Optional[str] = None,
                       title: str = "",
                       width: int = 800,
                       height: int = 600,
                       **kwargs) -> Optional[Dict[str, Any]]:
    """
    Standalone function to create a scatter plot.

    Args:
        data: DataFrame or data dictionary
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title
        width: Chart width in pixels
        height: Chart height in pixels
        **kwargs: Additional chart parameters

    Returns:
        Chart configuration dictionary or None if error
    """
    generator = ChartGenerator()
    return generator.create_scatter_plot(
        data, x_column, y_column, title, width, height, **kwargs
    )


def create_pie_chart(data: Union['pd.DataFrame', Dict[str, Any]],
                    label_column: Optional[str] = None,
                    value_column: Optional[str] = None,
                    title: str = "",
                    width: int = 800,
                    height: int = 600,
                    **kwargs) -> Optional[Dict[str, Any]]:
    """
    Standalone function to create a pie chart.

    Args:
        data: DataFrame or data dictionary
        label_column: Column name for labels
        value_column: Column name for values
        title: Chart title
        width: Chart width in pixels
        height: Chart height in pixels
        **kwargs: Additional chart parameters

    Returns:
        Chart configuration dictionary or None if error
    """
    generator = ChartGenerator()
    return generator.create_pie_chart(
        data, label_column, value_column, title, width, height, **kwargs
    )

def create_bivariate_choropleth(data: Union['pd.DataFrame', Dict[str, Any]],
                               x_column: str = None,
                               y_column: str = None,
                               geoid_column: str = 'geoid',
                               title: str = "Bivariate Choropleth Map",
                               width: float = 12.0,
                               height: float = 8.0,
                               **kwargs) -> Optional['Image']:
    """
    Standalone function to create a bivariate choropleth map.

    Args:
        data: DataFrame or dictionary with data
        x_column: Column name for X-axis variable
        y_column: Column name for Y-axis variable
        geoid_column: Column name for geographic identifiers
        title: Map title
        width: Map width in inches
        height: Map height in inches
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_bivariate_choropleth(
        data, x_column, y_column, geoid_column, title, width, height, **kwargs
    )

def create_heatmap(data: Union['pd.DataFrame', Dict[str, Any]],
                  x_column: str = None,
                  y_column: str = None,
                  value_column: str = None,
                  title: str = "",
                  width: float = 8.0,
                  height: float = 6.0,
                  **kwargs) -> Optional['Image']:
    """
    Standalone function to create a heatmap.

    Args:
        data: DataFrame or dictionary with data
        x_column: Column name for X-axis
        y_column: Column name for Y-axis
        value_column: Column name for values
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional arguments to pass to create_heatmap

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_heatmap(
        data, x_column, y_column, value_column, title, width, height, **kwargs
    )


def create_choropleth_map(data: Union['pd.DataFrame', Dict[str, Any]],
                         location_column: str = None,
                         value_column: str = None,
                         title: str = "",
                         width: float = 8.0,
                         height: float = 6.0,
                         map_type: str = "world",
                         **kwargs) -> Optional['Image']:
    """
    Standalone function to create a choropleth map.

    Args:
        data: DataFrame or dictionary with data
        location_column: Column name for locations (country codes, state names, etc.)
        value_column: Column name for values to color by
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        map_type: Type of map ("world", "usa", "europe", etc.)
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_choropleth_map(
        data, location_column, value_column, title, width, height, map_type, **kwargs
    )


def create_marker_map(data: Union['pd.DataFrame', Dict[str, Any]],
                     latitude_column: str = None,
                     longitude_column: str = None,
                     value_column: str = None,
                     label_column: str = None,
                     title: str = "",
                     width: float = 10.0,
                     height: float = 8.0,
                     map_style: str = "open-street-map",
                     zoom_level: int = 10,
                     **kwargs) -> Optional['Image']:
    """
    Standalone function to create a marker map.

    Args:
        data: DataFrame or dictionary with data
        latitude_column: Column name for latitude values
        longitude_column: Column name for longitude values
        value_column: Column name for values (optional)
        label_column: Column name for labels (optional)
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        map_style: Map style
        zoom_level: Initial zoom level
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_marker_map(
        data, latitude_column, longitude_column, value_column, label_column,
        title, width, height, map_style, zoom_level, **kwargs
    )


def create_flow_map(data: Union['pd.DataFrame', Dict[str, Any]],
                   origin_lat_column: str = None,
                   origin_lon_column: str = None,
                   dest_lat_column: str = None,
                   dest_lon_column: str = None,
                   flow_value_column: str = None,
                   title: str = "",
                   width: float = 12.0,
                   height: float = 10.0,
                   **kwargs) -> Optional['Image']:
    """
    Standalone function to create a flow map.

    Args:
        data: DataFrame or dictionary with data
        origin_lat_column: Column name for origin latitude
        origin_lon_column: Column name for origin longitude
        dest_lat_column: Column name for destination latitude
        dest_lon_column: Column name for destination longitude
        flow_value_column: Column name for flow values (optional)
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_flow_map(
        data, origin_lat_column, origin_lon_column, dest_lat_column, dest_lon_column,
        flow_value_column, title, width, height, **kwargs
    )


def create_convergence_diagram(sources: List[Dict[str, Any]],
                               hub_label: str = "Unified Hub",
                               outputs: Optional[List[Dict[str, Any]]] = None,
                               title: str = "Convergence Diagram",
                               width: float = 10.0,
                               height: float = 6.0,
                               **kwargs) -> Optional['Image']:
    """
    Standalone function to create a convergence diagram.
    """
    generator = ChartGenerator()
    return generator.create_convergence_diagram(
        sources=sources,
        hub_label=hub_label,
        outputs=outputs,
        title=title,
        width=width,
        height=height,
        **kwargs,
    )


def create_dashboard(charts: list,
                    layout: str = "2x2",
                    width: float = 12.0,
                    height: float = 8.0,
                    **kwargs) -> Optional['Image']:
    """
    Standalone function to create a dashboard with multiple charts.

    Args:
        charts: List of chart configurations
        layout: Layout string (e.g., "2x2", "3x1")
        width: Total dashboard width in inches
        height: Total dashboard height in inches
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_dashboard(charts, layout, width, height, **kwargs)


def create_dataframe_summary_charts(df: 'pd.DataFrame',
                                   title: str = "",
                                   width: float = 8.0,
                                   height: float = 6.0,
                                   **kwargs) -> Optional['Image']:
    """
    Standalone function to create summary charts from a DataFrame.

    Args:
        df: Pandas DataFrame
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.create_dataframe_summary_charts(df, title, width, height, **kwargs)


def generate_chart_from_dataframe(df: 'pd.DataFrame',
                                 chart_type: str = "bar",
                                 x_column: str = None,
                                 y_columns: list = None,
                                 title: str = "",
                                 width: float = 6.0,
                                 height: float = 4.0,
                                 **kwargs) -> Optional['Image']:
    """
    Standalone function to generate a chart from a DataFrame.

    Args:
        df: Pandas DataFrame
        chart_type: Type of chart to create
        x_column: Column to use for X-axis labels
        y_columns: Columns to plot
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional arguments

    Returns:
        PIL Image object or None if error
    """
    generator = ChartGenerator()
    return generator.generate_chart_from_dataframe(
        df, chart_type, x_column, y_columns, title, width, height, **kwargs
    )
