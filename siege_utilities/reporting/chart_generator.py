"""
Chart generation utilities for siege_utilities reporting system.
Supports multiple chart types, maps, and data sources including pandas and Spark DataFrames.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Core plotting libraries
try:
    import matplotlib.pyplot as plt
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
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None

# Geographic plotting
try:
    import folium
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

try:
    from reportlab.platypus import Image
except ImportError:
    Image = None

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

__all__ = [
    "ChartGenerator",
    "create_bar_chart",
    "create_bivariate_choropleth",
    "create_choropleth_map",
    "create_convergence_diagram",
    "create_dashboard",
    "create_dataframe_summary_charts",
    "create_flow_map",
    "create_heatmap",
    "create_line_chart",
    "create_marker_map",
    "create_pie_chart",
    "create_scatter_plot",
    "generate_chart_from_dataframe",
]


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
                    width: float = 8.0,
                    height: float = 6.0,
                    **kwargs) -> 'Image':
    """
    Standalone function to create a bar chart.

    Args:
        data: DataFrame or data dictionary
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional chart parameters

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_bar_chart(
        data=data, x_column=x_column, y_column=y_column,
        title=title, width=width, height=height, **kwargs
    )


def create_line_chart(data: Union['pd.DataFrame', Dict[str, Any]],
                     x_column: Optional[str] = None,
                     y_column: Optional[Union[str, List[str]]] = None,
                     title: str = "",
                     width: float = 8.0,
                     height: float = 6.0,
                     **kwargs) -> 'Image':
    """
    Standalone function to create a line chart.

    Args:
        data: DataFrame or data dictionary
        x_column: Column name for x-axis
        y_column: One column name or a list of column names for y-axis
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional chart parameters

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    y_columns = [y_column] if isinstance(y_column, str) else y_column
    generator = ChartGenerator()
    return generator.create_line_chart(
        data=data, x_column=x_column, y_columns=y_columns,
        title=title, width=width, height=height, **kwargs
    )


def create_scatter_plot(data: Union['pd.DataFrame', Dict[str, Any]],
                       x_column: Optional[str] = None,
                       y_column: Optional[str] = None,
                       title: str = "",
                       width: float = 8.0,
                       height: float = 6.0,
                       **kwargs) -> 'Image':
    """
    Standalone function to create a scatter plot.

    Args:
        data: DataFrame or data dictionary
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional chart parameters

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_scatter_plot(
        data=data, x_column=x_column, y_column=y_column,
        title=title, width=width, height=height, **kwargs
    )


def create_pie_chart(data: Union['pd.DataFrame', Dict[str, Any]],
                    label_column: Optional[str] = None,
                    value_column: Optional[str] = None,
                    title: str = "",
                    width: float = 8.0,
                    height: float = 6.0,
                    **kwargs) -> 'Image':
    """
    Standalone function to create a pie chart.

    Args:
        data: DataFrame or data dictionary
        label_column: Column name for labels
        value_column: Column name for values
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional chart parameters

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_pie_chart(
        data=data, labels_column=label_column, values_column=value_column,
        title=title, width=width, height=height, **kwargs
    )

def create_bivariate_choropleth(data: Union['pd.DataFrame', Dict[str, Any]],
                               x_column: str = None,
                               y_column: str = None,
                               geoid_column: str = 'geoid',
                               title: str = "Bivariate Choropleth Map",
                               width: float = 12.0,
                               height: float = 8.0,
                               *,
                               geo_data: Union['gpd.GeoDataFrame', str, Path, Dict, None] = None,
                               **kwargs) -> 'Image':
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
        geo_data: GeoDataFrame, GeoJSON path or dictionary. Required for maps
            unless bivariate data already contains geometry.
        **kwargs: Additional arguments

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_bivariate_choropleth(
        data=data, geo_data=geo_data, location_column=geoid_column,
        value_column1=x_column, value_column2=y_column,
        title=title, width=width, height=height, **kwargs
    )

def create_heatmap(data: Union['pd.DataFrame', Dict[str, Any]],
                  x_column: str = None,
                  y_column: str = None,
                  value_column: str = None,
                  title: str = "",
                  width: float = 8.0,
                  height: float = 6.0,
                  **kwargs) -> 'Image':
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
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_heatmap(
        data=data, x_column=x_column, y_column=y_column, value_column=value_column,
        title=title, width=width, height=height, **kwargs
    )


def create_choropleth_map(data: Union['pd.DataFrame', Dict[str, Any]],
                         location_column: str = None,
                         value_column: str = None,
                         title: str = "",
                         width: float = 8.0,
                         height: float = 6.0,
                         map_type: str = "world",
                         *,
                         geo_data: Union['gpd.GeoDataFrame', str, Path, Dict, None] = None,
                         **kwargs) -> 'Image':
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
        geo_data: GeoDataFrame, GeoJSON path or dictionary. Required to render
            the choropleth; locations alone do not provide geometry.
        **kwargs: Additional arguments

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_choropleth_map(
        data=data, geo_data=geo_data, location_column=location_column,
        value_column=value_column, title=title, width=width, height=height,
        map_type=map_type, **kwargs
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
                     **kwargs) -> 'Image':
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
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_marker_map(
        data=data, latitude_column=latitude_column, longitude_column=longitude_column,
        value_column=value_column, label_column=label_column,
        title=title, width=width, height=height,
        map_style=map_style, zoom_level=zoom_level, **kwargs
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
                   **kwargs) -> 'Image':
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
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_flow_map(
        data=data, origin_lat_column=origin_lat_column, origin_lon_column=origin_lon_column,
        dest_lat_column=dest_lat_column, dest_lon_column=dest_lon_column,
        flow_value_column=flow_value_column, title=title, width=width, height=height, **kwargs
    )


def create_convergence_diagram(sources: List[Dict[str, Any]],
                               hub_label: str = "Unified Hub",
                               outputs: Optional[List[Dict[str, Any]]] = None,
                               title: str = "Convergence Diagram",
                               width: float = 10.0,
                               height: float = 6.0,
                               **kwargs) -> 'Image':
    """Standalone function to create a convergence diagram.

    Args:
        sources: Source node dicts with keys ``label`` (required),
            ``color`` (optional), and an optional magnitude key.
        hub_label: Center node label.
        outputs: Optional output node dicts (same schema as *sources*).
        title: Diagram title.
        width: Figure width in inches.
        height: Figure height in inches.
        **kwargs: Forwarded to
            :meth:`CompositeChartMixin.create_convergence_diagram`.
            Accepts ``arrow_style`` (``'curved'``, ``'radial'``, or
            ``'orthogonal'``), ``arrow_count``, ``arrow_color``,
            ``show_magnitudes``, and ``magnitude_key``.

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
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
                    **kwargs) -> 'Image':
    """
    Standalone function to create a dashboard with multiple charts.

    Args:
        charts: List of chart configurations
        layout: Layout string (e.g., "2x2", "3x1")
        width: Total dashboard width in inches
        height: Total dashboard height in inches
        **kwargs: Additional arguments

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_dashboard(
        charts=charts, layout=layout, width=width, height=height, **kwargs
    )


def create_dataframe_summary_charts(df: 'pd.DataFrame',
                                   title: str = "",
                                   width: float = 8.0,
                                   height: float = 6.0,
                                   **kwargs) -> 'Image':
    """
    Standalone function to create summary charts from a DataFrame.

    Args:
        df: Pandas DataFrame
        title: Chart title
        width: Chart width in inches
        height: Chart height in inches
        **kwargs: Additional arguments

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.create_dataframe_summary_charts(
        df=df, title=title, width=width, height=height, **kwargs
    )


def generate_chart_from_dataframe(df: 'pd.DataFrame',
                                 chart_type: str = "bar",
                                 x_column: str = None,
                                 y_columns: list = None,
                                 title: str = "",
                                 width: float = 6.0,
                                 height: float = 4.0,
                                 *,
                                 geo_data: Union['gpd.GeoDataFrame', str, Path, Dict, None] = None,
                                 **kwargs) -> 'Image':
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
        geo_data: GeoDataFrame, GeoJSON path or dictionary. Required for maps
            unless bivariate data already contains geometry.
        **kwargs: Additional arguments

    Returns:
        ReportLab Image object (including dependency placeholders).
        Chart generation errors propagate to the caller.
    """
    generator = ChartGenerator()
    return generator.generate_chart_from_dataframe(
        df=df, chart_type=chart_type, x_column=x_column, y_columns=y_columns,
        title=title, width=width, height=height, geo_data=geo_data, **kwargs
    )
