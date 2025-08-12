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

log = logging.getLogger(__name__)

class ChartGenerator:
    """
    Generates charts and visualizations for reports using matplotlib, seaborn, plotly, and folium.
    Supports pandas DataFrames, Spark DataFrames, and various data sources.
    """

    def __init__(self, branding_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the chart generator.
        
        Args:
            branding_config: Branding configuration for chart colors and styling
        """
        self.branding_config = branding_config or {}
        self.styles = getSampleStyleSheet()
        self._setup_default_colors()
        self._setup_plotting_style()
        
        # Set default figure size and DPI
        self.default_figsize = (10, 6)
        self.default_dpi = 300

    def _setup_default_colors(self):
        """Setup default color scheme for charts."""
        self.default_colors = {
            'primary': self.branding_config.get('colors', {}).get('primary', '#0077CC'),
            'secondary': self.branding_config.get('colors', {}).get('secondary', '#EEEEEE'),
            'accent': self.branding_config.get('colors', {}).get('accent', '#FF6B35'),
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8',
            'light': '#f8f9fa',
            'dark': '#343a40'
        }
        
        # Color palette for multiple series
        self.color_palette = [
            self.default_colors['primary'],
            self.default_colors['accent'],
            self.default_colors['success'],
            self.default_colors['warning'],
            self.default_colors['info']
        ]

    def _setup_plotting_style(self):
        """Setup matplotlib and seaborn styling."""
        if MATPLOTLIB_AVAILABLE:
            # Set style
            plt.style.use('default')
            
            # Configure seaborn
            if sns:
                sns.set_palette(self.color_palette)
                sns.set_style("whitegrid")
            
            # Set default font sizes
            plt.rcParams['font.size'] = 10
            plt.rcParams['axes.titlesize'] = 12
            plt.rcParams['axes.labelsize'] = 10
            plt.rcParams['xtick.labelsize'] = 9
            plt.rcParams['ytick.labelsize'] = 9
            plt.rcParams['legend.fontsize'] = 9
            plt.rcParams['figure.titlesize'] = 14

    def create_bar_chart(self, data: Union[pd.DataFrame, Dict[str, Any]], 
                        x_column: str = None, y_column: str = None,
                        title: str = "", width: float = 6.0, height: float = 4.0,
                        chart_type: str = "bar", group_by: str = None) -> Image:
        """
        Create a bar chart from data.
        
        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis (or 'index' for DataFrame index)
            y_column: Column name for Y-axis
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            chart_type: Type of chart ('bar', 'horizontal')
            group_by: Column to group by for grouped bars
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Handle different data formats
            if x_column == 'index':
                x_values = df.index.tolist()
            elif x_column:
                x_values = df[x_column].tolist()
            else:
                x_values = range(len(df))
            
            if y_column:
                y_values = df[y_column].tolist()
            else:
                # Use first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    y_column = numeric_cols[0]
                    y_values = df[y_column].tolist()
                else:
                    return self._create_placeholder_chart(width, height, "No numeric data found")
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create chart
            if chart_type == "horizontal":
                bars = ax.barh(x_values, y_values, color=self.default_colors['primary'])
                ax.set_xlabel(y_column)
                ax.set_ylabel(x_column if x_column != 'index' else 'Index')
            else:
                bars = ax.bar(x_values, y_values, color=self.default_colors['primary'])
                ax.set_xlabel(x_column if x_column != 'index' else 'Index')
                ax.set_ylabel(y_column)
            
            # Customize chart
            ax.set_title(title or f"{y_column} by {x_column if x_column != 'index' else 'Index'}")
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels if needed
            if len(x_values) > 5:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:,.0f}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating bar chart: {e}")
            return self._create_placeholder_chart(width, height, f"Chart Error: {str(e)}")

    def create_line_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                         x_column: str = None, y_columns: List[str] = None,
                         title: str = "", width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a line chart from data.
        
        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis
            y_columns: List of column names for Y-axis (multiple lines)
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Handle different data formats
            if x_column == 'index':
                x_values = df.index.tolist()
            elif x_column:
                x_values = df[x_column].tolist()
            else:
                x_values = range(len(df))
            
            if not y_columns:
                # Use all numeric columns except x_column
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if x_column in numeric_cols:
                    numeric_cols.remove(x_column)
                y_columns = numeric_cols[:5]  # Limit to 5 columns
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Plot each line
            for i, col in enumerate(y_columns):
                if col in df.columns:
                    color = self.color_palette[i % len(self.color_palette)]
                    ax.plot(x_values, df[col].tolist(), 
                           label=col, color=color, linewidth=2, marker='o')
            
            # Customize chart
            ax.set_title(title or f"Trends over time")
            ax.set_xlabel(x_column if x_column != 'index' else 'Index')
            ax.set_ylabel('Value')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels if needed
            if len(x_values) > 5:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating line chart: {e}")
            return self._create_placeholder_chart(width, height, f"Chart Error: {str(e)}")

    def create_pie_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                        labels_column: str = None, values_column: str = None,
                        title: str = "", width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a pie chart from data.
        
        Args:
            data: DataFrame or dictionary with data
            labels_column: Column name for labels
            values_column: Column name for values
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Handle different data formats
            if labels_column and values_column:
                labels = df[labels_column].tolist()
                values = df[values_column].tolist()
            else:
                # Use first two columns
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    labels = df[cols[0]].tolist()
                    values = df[cols[1]].tolist()
                else:
                    return self._create_placeholder_chart(width, height, "Need at least 2 columns for pie chart")
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create pie chart
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                             colors=self.color_palette[:len(values)],
                                             startangle=90)
            
            # Customize chart
            ax.set_title(title or "Data Distribution")
            
            # Add legend
            ax.legend(wedges, labels, title="Categories", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating pie chart: {e}")
            return self._create_placeholder_chart(width, height, f"Chart Error: {str(e)}")

    def create_choropleth_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                             location_column: str, value_column: str,
                             title: str = "", width: float = 8.0, height: float = 6.0,
                             map_type: str = "world") -> Image:
        """
        Create a choropleth map from data.
        
        Args:
            data: DataFrame or dictionary with data
            location_column: Column name for locations (country codes, state names, etc.)
            value_column: Column name for values to color by
            title: Map title
            width: Map width in inches
            height: Map height in inches
            map_type: Type of map ('world', 'us', 'europe', etc.)
            
        Returns:
            ReportLab Image object
        """
        if not FOLIUM_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Folium not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Create base map
            if map_type == "world":
                m = folium.Map(location=[20, 0], zoom_start=2)
            elif map_type == "us":
                m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)
            else:
                m = folium.Map(location=[20, 0], zoom_start=2)
            
            # Add choropleth layer
            folium.Choropleth(
                geo_data=None,  # You'll need to provide GeoJSON data
                name="choropleth",
                data=df,
                columns=[location_column, value_column],
                key_on="feature.id",
                fill_color="YlOrRd",
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name=value_column
            ).add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Save map to temporary file
            temp_map_path = Path.home() / ".siege_utilities" / "temp_map.html"
            temp_map_path.parent.mkdir(parents=True, exist_ok=True)
            m.save(str(temp_map_path))
            
            # Convert HTML to image (this is a simplified approach)
            # In practice, you might want to use selenium or similar to render the HTML
            return self._create_placeholder_chart(width, height, "Choropleth Map - HTML file saved")
            
        except Exception as e:
            log.error(f"Error creating choropleth map: {e}")
            return self._create_placeholder_chart(width, height, f"Map Error: {str(e)}")

    def create_bivariate_choropleth(self, data: Union[pd.DataFrame, Dict[str, Any]],
                                   location_column: str, value_column1: str, value_column2: str,
                                   title: str = "", width: float = 8.0, height: float = 6.0) -> Image:
        """
        Create a bivariate choropleth map from data using Folium.
        
        Args:
            data: DataFrame or dictionary with data
            location_column: Column name for locations (country codes, state names, etc.)
            value_column1: Column name for the first value to color by
            value_column2: Column name for the second value to color by
            title: Map title
            width: Map width in inches
            height: Map height in inches
            
        Returns:
            ReportLab Image object
        """
        if not FOLIUM_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Folium not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Create base map
            m = folium.Map(location=[20, 0], zoom_start=2)
            
            # Add bivariate choropleth layer
            folium.Choropleth(
                geo_data=None,  # You'll need to provide GeoJSON data
                name="bivariate_choropleth",
                data=df,
                columns=[location_column, value_column1, value_column2],
                key_on="feature.id",
                fill_color="YlOrRd",
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name=f"{value_column1} vs {value_column2}"
            ).add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Save map to temporary file
            temp_map_path = Path.home() / ".siege_utilities" / "temp_map.html"
            temp_map_path.parent.mkdir(parents=True, exist_ok=True)
            m.save(str(temp_map_path))
            
            # Convert HTML to image (this is a simplified approach)
            # In practice, you might want to use selenium or similar to render the HTML
            return self._create_placeholder_chart(width, height, "Bivariate Choropleth Map - HTML file saved")
            
        except Exception as e:
            log.error(f"Error creating bivariate choropleth map: {e}")
            return self._create_placeholder_chart(width, height, f"Bivariate Choropleth Map Error: {str(e)}")

    def create_bivariate_choropleth_matplotlib(self, data: Union[pd.DataFrame, Dict[str, Any]],
                                             geodata: Union[gpd.GeoDataFrame, str, Path],
                                             location_column: str, value_column1: str, value_column2: str,
                                             title: str = "", width: float = 10.0, height: float = 8.0,
                                             color_scheme: str = "default") -> Image:
        """
        Create a bivariate choropleth map using matplotlib and geopandas.
        This method follows the approach from the bivariate-choropleth repository.
        
        Args:
            data: DataFrame or dictionary with data
            geodata: GeoDataFrame or path to GeoJSON file
            location_column: Column name for locations (must match geodata)
            value_column1: Column name for the first value (X-axis in bivariate scheme)
            value_column2: Column name for the second value (Y-axis in bivariate scheme)
            title: Map title
            width: Map width in inches
            height: Map height in inches
            color_scheme: Color scheme ('default', 'custom', 'diverging')
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE or not GEOPANDAS_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib or GeoPandas not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Load geodata if it's a path
            if isinstance(geodata, (str, Path)):
                gdf = gpd.read_file(geodata)
            else:
                gdf = geodata.copy()
            
            # Merge data with geodata
            merged = gdf.merge(df, left_on=location_column, right_on=location_column, how='left')
            
            # Create bivariate color scheme
            colors = self._create_bivariate_color_scheme(color_scheme)
            
            # Create figure and axes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create bivariate choropleth
            merged.plot(
                column=value_column1,  # Primary variable
                cmap=colors,
                linewidth=0.5,
                edgecolor='black',
                ax=ax,
                legend=True,
                legend_kwds={'label': f'{value_column1} vs {value_column2}',
                            'orientation': 'vertical'}
            )
            
            # Add title and remove axes
            ax.set_title(title or f"Bivariate Choropleth: {value_column1} vs {value_column2}")
            ax.axis('off')
            
            # Add bivariate legend
            self._add_bivariate_legend(ax, value_column1, value_column2, colors)
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating bivariate choropleth with matplotlib: {e}")
            return self._create_placeholder_chart(width, height, f"Bivariate Choropleth Error: {str(e)}")

    def _create_bivariate_color_scheme(self, scheme: str = "default") -> str:
        """
        Create a bivariate color scheme for choropleth maps.
        
        Args:
            scheme: Color scheme type
            
        Returns:
            Color scheme name or custom colormap
        """
        if scheme == "default":
            # Use a built-in colormap that works well for bivariate data
            return "RdYlBu_r"
        elif scheme == "diverging":
            return "RdBu_r"
        elif scheme == "custom":
            # Create a custom bivariate colormap
            from matplotlib.colors import LinearSegmentedColormap
            
            # Define custom colors for bivariate visualization
            colors = ['#e8e8e8', '#e4acac', '#c85a5a', '#9c2929', '#67001f',
                     '#b8d6be', '#90b4a6', '#627f8c', '#3b738a', '#1a4f63',
                     '#7fc97f', '#5aae61', '#2d8a49', '#0d5a1e', '#00441b',
                     '#4d9221', '#7fbc41', '#a8dd35', '#c2e699', '#e6f5d0']
            
            return LinearSegmentedColormap.from_list('custom_bivariate', colors)
        else:
            return "viridis"

    def _add_bivariate_legend(self, ax, var1: str, var2: str, colors):
        """
        Add a bivariate legend to the map.
        
        Args:
            ax: Matplotlib axes
            var1: First variable name
            var2: Second variable name
            colors: Color scheme
        """
        try:
            # Create a simple bivariate legend
            legend_elements = [
                plt.Rectangle((0, 0), 1, 1, facecolor='lightgray', edgecolor='black', label=f'{var1} (Low)'),
                plt.Rectangle((0, 0), 1, 1, facecolor='darkred', edgecolor='black', label=f'{var1} (High)'),
                plt.Rectangle((0, 0), 1, 1, facecolor='lightblue', edgecolor='black', label=f'{var2} (Low)'),
                plt.Rectangle((0, 0), 1, 1, facecolor='darkblue', edgecolor='black', label=f'{var2} (High)')
            ]
            
            ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
            
        except Exception as e:
            log.warning(f"Could not add bivariate legend: {e}")

    def create_advanced_choropleth(self, data: Union[pd.DataFrame, Dict[str, Any]],
                                  geodata: Union[gpd.GeoDataFrame, str, Path],
                                  location_column: str, value_column: str,
                                  title: str = "", width: float = 10.0, height: float = 8.0,
                                  classification: str = "quantiles", bins: int = 5,
                                  color_scheme: str = "YlOrRd") -> Image:
        """
        Create an advanced choropleth map with multiple classification options.
        
        Args:
            data: DataFrame or dictionary with data
            geodata: GeoDataFrame or path to GeoJSON file
            location_column: Column name for locations
            value_column: Column name for values to color by
            title: Map title
            width: Map width in inches
            height: Map height in inches
            classification: Classification method ('quantiles', 'equal_interval', 'natural_breaks')
            bins: Number of bins for classification
            color_scheme: Color scheme for the map
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE or not GEOPANDAS_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib or GeoPandas not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Load geodata if it's a path
            if isinstance(geodata, (str, Path)):
                gdf = gpd.read_file(geodata)
            else:
                gdf = geodata.copy()
            
            # Merge data with geodata
            merged = gdf.merge(df, left_on=location_column, right_on=location_column, how='left')
            
            # Apply classification
            if classification == "quantiles":
                merged[f'{value_column}_classified'] = pd.qcut(merged[value_column], bins, labels=False, duplicates='drop')
            elif classification == "equal_interval":
                merged[f'{value_column}_classified'] = pd.cut(merged[value_column], bins, labels=False, duplicates='drop')
            elif classification == "natural_breaks":
                # Simple natural breaks using quantiles as approximation
                merged[f'{value_column}_classified'] = pd.qcut(merged[value_column], bins, labels=False, duplicates='drop')
            else:
                merged[f'{value_column}_classified'] = pd.qcut(merged[value_column], bins, labels=False, duplicates='drop')
            
            # Create figure and axes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create choropleth
            merged.plot(
                column=f'{value_column}_classified',
                cmap=color_scheme,
                linewidth=0.5,
                edgecolor='black',
                ax=ax,
                legend=True,
                legend_kwds={'label': value_column, 'orientation': 'vertical'}
            )
            
            # Add title and remove axes
            ax.set_title(title or f"Choropleth Map: {value_column}")
            ax.axis('off')
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating advanced choropleth: {e}")
            return self._create_placeholder_chart(width, height, f"Advanced Choropleth Error: {str(e)}")

    def create_bivariate_choropleth(self, data: Union[pd.DataFrame, Dict[str, Any]],
                                  location_column: str, value_column1: str, value_column2: str,
                                  title: str = "", width: float = 8.0, height: float = 6.0) -> Image:
        """
        Create a bivariate choropleth map from data.
        
        Args:
            data: DataFrame or dictionary with data
            location_column: Column name for locations (country codes, state names, etc.)
            value_column1: Column name for the first value to color by
            value_column2: Column name for the second value to color by
            title: Map title
            width: Map width in inches
            height: Map height in inches
            
        Returns:
            ReportLab Image object
        """
        if not FOLIUM_AVAILABLE or not GEOPANDAS_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Folium or GeoPandas not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Ensure location_column is a string
            if not isinstance(location_column, str):
                location_column = str(location_column)
            
            # Ensure value_column1 and value_column2 are strings
            if not isinstance(value_column1, str):
                value_column1 = str(value_column1)
            if not isinstance(value_column2, str):
                value_column2 = str(value_column2)
            
            # Create base map
            m = folium.Map(location=[20, 0], zoom_start=2)
            
            # Add bivariate choropleth layer
            folium.Choropleth(
                geo_data=None,  # You'll need to provide GeoJSON data
                name="bivariate_choropleth",
                data=df,
                columns=[location_column, value_column1, value_column2],
                key_on="feature.id",
                fill_color=["YlOrRd", "BuPu"], # Example color schemes
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name=f"{value_column1} vs {value_column2}",
                bins=[0, 10, 20, 30, 40, 50], # Example bins for bivariate
                overlay=True,
                highlight=True
            ).add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Save map to temporary file
            temp_map_path = Path.home() / ".siege_utilities" / "temp_map.html"
            temp_map_path.parent.mkdir(parents=True, exist_ok=True)
            m.save(str(temp_map_path))
            
            # Convert HTML to image (this is a simplified approach)
            # In practice, you might want to use selenium or similar to render the HTML
            return self._create_placeholder_chart(width, height, "Bivariate Choropleth Map - HTML file saved")
            
        except Exception as e:
            log.error(f"Error creating bivariate choropleth map: {e}")
            return self._create_placeholder_chart(width, height, f"Bivariate Choropleth Map Error: {str(e)}")

    def create_heatmap(self, data: Union[pd.DataFrame, Dict[str, Any]],
                      x_column: str = None, y_column: str = None, value_column: str = None,
                      title: str = "", width: float = 8.0, height: float = 6.0) -> Image:
        """
        Create a heatmap from data.
        
        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis
            y_column: Column name for Y-axis
            value_column: Column name for values
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE or not sns:
            return self._create_placeholder_chart(width, height, "Matplotlib/Seaborn not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Handle different data formats
            if x_column and y_column and value_column:
                # Pivot data for heatmap
                pivot_data = df.pivot_table(values=value_column, index=y_column, columns=x_column, aggfunc='mean')
            else:
                # Use correlation matrix if no specific columns provided
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 1:
                    pivot_data = df[numeric_cols].corr()
                else:
                    return self._create_placeholder_chart(width, height, "Need numeric data for heatmap")
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create heatmap
            sns.heatmap(pivot_data, annot=True, cmap='YlOrRd', center=0,
                       square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
            
            # Customize chart
            ax.set_title(title or "Data Heatmap")
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating heatmap: {e}")
            return self._create_placeholder_chart(width, height, f"Heatmap Error: {str(e)}")

    def create_scatter_plot(self, data: Union[pd.DataFrame, Dict[str, Any]],
                           x_column: str, y_column: str, color_column: str = None,
                           title: str = "", width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a scatter plot from data.
        
        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis
            y_column: Column name for Y-axis
            color_column: Column name for color coding
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")
        
        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create scatter plot
            if color_column and color_column in df.columns:
                scatter = ax.scatter(df[x_column], df[y_column], 
                                   c=df[color_column], cmap='viridis', alpha=0.6)
                plt.colorbar(scatter, ax=ax, label=color_column)
            else:
                ax.scatter(df[x_column], df[y_column], alpha=0.6, color=self.default_colors['primary'])
            
            # Customize chart
            ax.set_title(title or f"{y_column} vs {x_column}")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating scatter plot: {e}")
            return self._create_placeholder_chart(width, height, f"Scatter Plot Error: {str(e)}")

    def create_dashboard(self, charts: List[Dict[str, Any]], 
                        layout: str = "2x2", width: float = 12.0, height: float = 8.0) -> Image:
        """
        Create a dashboard with multiple charts.
        
        Args:
            charts: List of chart configurations
            layout: Layout string (e.g., "2x2", "3x1")
            width: Total dashboard width in inches
            height: Total dashboard height in inches
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")
        
        try:
            # Parse layout
            if 'x' in layout:
                cols, rows = map(int, layout.split('x'))
            else:
                cols, rows = 2, 2
            
            # Create subplot grid
            fig, axes = plt.subplots(rows, cols, figsize=(width, height), dpi=self.default_dpi)
            
            # Handle single subplot case
            if rows == 1 and cols == 1:
                axes = [axes]
            elif rows == 1 or cols == 1:
                axes = axes.flatten()
            else:
                axes = axes.flatten()
            
            # Create each chart
            for i, chart_config in enumerate(charts):
                if i >= len(axes):
                    break
                
                ax = axes[i]
                chart_type = chart_config.get('type', 'bar')
                chart_title = chart_config.get('title', f'Chart {i+1}')
                
                # Create chart based on type
                if chart_type == 'bar':
                    self._create_bar_subplot(ax, chart_config, chart_title)
                elif chart_type == 'line':
                    self._create_line_subplot(ax, chart_config, chart_title)
                elif chart_type == 'pie':
                    self._create_pie_subplot(ax, chart_config, chart_title)
                elif chart_type == 'scatter':
                    self._create_scatter_subplot(ax, chart_config, chart_title)
            
            # Hide empty subplots
            for i in range(len(charts), len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating dashboard: {e}")
            return self._create_placeholder_chart(width, height, f"Dashboard Error: {str(e)}")

    def create_dataframe_summary_charts(self, df: pd.DataFrame, 
                                     title: str = "", width: float = 8.0, height: float = 6.0) -> Image:
        """
        Create summary charts from a pandas DataFrame.
        
        Args:
            df: Pandas DataFrame
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE or not PANDAS_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib/Pandas not available")
        
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return self._create_placeholder_chart(width, height, "No numeric columns found")
            
            # Create subplots
            fig, axes = plt.subplots(2, 2, figsize=(width, height), dpi=self.default_dpi)
            axes = axes.flatten()
            
            # Distribution plots
            for i, col in enumerate(numeric_cols[:4]):
                if i < len(axes):
                    ax = axes[i]
                    ax.hist(df[col].dropna(), bins=20, alpha=0.7, color=self.color_palette[i % len(self.color_palette)])
                    ax.set_title(f'{col} Distribution')
                    ax.set_xlabel(col)
                    ax.set_ylabel('Frequency')
                    ax.grid(True, alpha=0.3)
            
            # Hide empty subplots
            for i in range(len(numeric_cols[:4]), len(axes)):
                axes[i].set_visible(False)
            
            plt.suptitle(title or "DataFrame Summary Charts")
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating DataFrame summary charts: {e}")
            return self._create_placeholder_chart(width, height, f"Summary Charts Error: {str(e)}")

    def _create_bar_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Create a bar chart in a subplot."""
        try:
            data = chart_config.get('data', {})
            labels = data.get('labels', [])
            datasets = data.get('datasets', [])
            
            if datasets and len(datasets) > 0:
                values = datasets[0].get('data', [])
                ax.bar(labels, values, color=self.default_colors['primary'])
                ax.set_title(title)
                ax.grid(True, alpha=0.3)
        except Exception as e:
            log.error(f"Error creating bar subplot: {e}")

    def _create_line_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Create a line chart in a subplot."""
        try:
            data = chart_config.get('data', {})
            labels = data.get('labels', [])
            datasets = data.get('datasets', [])
            
            for i, dataset in enumerate(datasets):
                values = dataset.get('data', [])
                color = self.color_palette[i % len(self.color_palette)]
                ax.plot(labels, values, color=color, marker='o')
            
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
        except Exception as e:
            log.error(f"Error creating line subplot: {e}")

    def _create_pie_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Create a pie chart in a subplot."""
        try:
            data = chart_config.get('data', {})
            labels = data.get('labels', [])
            values = data.get('data', [])
            
            ax.pie(values, labels=labels, autopct='%1.1f%%', colors=self.color_palette[:len(values)])
            ax.set_title(title)
        except Exception as e:
            log.error(f"Error creating pie subplot: {e}")

    def _create_scatter_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Create a scatter plot in a subplot."""
        try:
            data = chart_config.get('data', {})
            x_values = data.get('x', [])
            y_values = data.get('y', [])
            
            ax.scatter(x_values, y_values, alpha=0.6, color=self.default_colors['primary'])
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
        except Exception as e:
            log.error(f"Error creating scatter subplot: {e}")

    def _matplotlib_to_reportlab_image(self, fig, width: float, height: float) -> Image:
        """
        Convert matplotlib figure to ReportLab Image.
        
        Args:
            fig: Matplotlib figure
            width: Image width in inches
            height: Image height in inches
            
        Returns:
            ReportLab Image object
        """
        try:
            # Save figure to bytes buffer
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=self.default_dpi, bbox_inches='tight')
            img_buffer.seek(0)
            
            # Encode as base64
            img_data = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Create data URL
            data_url = f"data:image/png;base64,{img_data}"
            
            # Close the figure to free memory
            plt.close(fig)
            
            # Create ReportLab Image
            return Image(data_url, width=width*inch, height=height*inch)
            
        except Exception as e:
            log.error(f"Error converting matplotlib figure to ReportLab Image: {e}")
            return self._create_placeholder_chart(width, height, "Image Conversion Error")

    def _create_placeholder_chart(self, width: float, height: float, 
                                text: str = "Chart Placeholder") -> Image:
        """
        Create a placeholder chart when chart generation fails.
        
        Args:
            width: Chart width in inches
            height: Chart height in inches
            text: Text to display in placeholder
            
        Returns:
            ReportLab Image object
        """
        try:
            # Create a simple placeholder using matplotlib
            if MATPLOTLIB_AVAILABLE:
                fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
                ax.text(0.5, 0.5, text, ha='center', va='center', transform=ax.transAxes,
                       fontsize=12, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
                
                # Convert to ReportLab Image
                return self._matplotlib_to_reportlab_image(fig, width, height)
            else:
                # Fallback to simple text
                return Image("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                           width=width*inch, height=height*inch)
        except Exception as e:
            log.error(f"Error creating placeholder chart: {e}")
            # Return a minimal image
            return Image("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                       width=width*inch, height=height*inch)

    def create_chart_with_caption(self, chart: Image, caption: str, 
                                caption_style: Optional[str] = None) -> List:
        """
        Create a chart with a caption below it.
        
        Args:
            chart: The chart image
            caption: Caption text
            caption_style: Style name for the caption
            
        Returns:
            List containing chart and caption
        """
        if caption_style is None:
            caption_style = 'Caption' if 'Caption' in self.styles else 'Normal'
            
        return [chart, Paragraph(caption, self.styles[caption_style]), Spacer(1, 0.2 * inch)]

    def create_chart_section(self, title: str, charts: List[Image], 
                           description: str = "", width: float = 6.0) -> List:
        """
        Create a complete chart section with title, description, and charts.
        
        Args:
            title: Section title
            charts: List of chart images
            description: Section description
            width: Section width in inches
            
        Returns:
            List of flowables for the section
        """
        section = []
        
        # Add title
        if title:
            section.append(Paragraph(title, self.styles['h2']))
            section.append(Spacer(1, 0.1 * inch))
        
        # Add description
        if description:
            section.append(Paragraph(description, self.styles['BodyText']))
            section.append(Spacer(1, 0.2 * inch))
        
        # Add charts
        for chart in charts:
            section.append(chart)
            section.append(Spacer(1, 0.2 * inch))
        
        return section

    def generate_chart_from_dataframe(self, df: pd.DataFrame, chart_type: str = "bar", 
                                    x_column: str = None, y_columns: List[str] = None,
                                    title: str = "", width: float = 6.0, 
                                    height: float = 4.0) -> Image:
        """
        Generate a chart from a pandas DataFrame.
        
        Args:
            df: Pandas DataFrame
            chart_type: Type of chart to create
            x_column: Column to use for X-axis labels
            y_columns: Columns to use for Y-axis data
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        try:
            if chart_type == "bar":
                return self.create_bar_chart(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "line":
                return self.create_line_chart(df, x_column, y_columns, title, width, height)
            elif chart_type == "pie":
                return self.create_pie_chart(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "scatter":
                return self.create_scatter_plot(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "heatmap":
                return self.create_heatmap(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "choropleth":
                return self.create_choropleth_map(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "bivariate_choropleth":
                if y_columns and len(y_columns) >= 2:
                    return self.create_bivariate_choropleth(df, x_column, y_columns[0], y_columns[1], title, width, height)
                else:
                    return self._create_placeholder_chart(width, height, "Bivariate choropleth requires at least 2 value columns")
            else:
                return self.create_bar_chart(df, x_column, y_columns[0] if y_columns else None, title, width, height)
                
        except Exception as e:
            log.error(f"Error generating chart from DataFrame: {e}")
            return self._create_placeholder_chart(width, height, "DataFrame Chart Error")

    def create_custom_chart(self, chart_config: Dict[str, Any], 
                           width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a custom chart based on configuration.
        
        Args:
            chart_config: Complete chart configuration
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        try:
            # Validate chart configuration
            required_keys = ['type', 'data']
            if not all(key in chart_config for key in required_keys):
                raise ValueError(f"Chart configuration missing required keys: {required_keys}")
            
            chart_type = chart_config['type']
            
            if chart_type == 'bar':
                return self.create_bar_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'line':
                return self.create_line_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'pie':
                return self.create_pie_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'scatter':
                return self.create_scatter_plot(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'heatmap':
                return self.create_heatmap(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'choropleth':
                return self.create_choropleth_map(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'bivariate_choropleth':
                # For bivariate choropleth, we need additional configuration
                if 'location_column' in chart_config and 'value_columns' in chart_config and len(chart_config['value_columns']) >= 2:
                    return self.create_bivariate_choropleth(
                        chart_config['data'], 
                        chart_config['location_column'],
                        chart_config['value_columns'][0],
                        chart_config['value_columns'][1],
                        title=chart_config.get('title', ''),
                        width=width, 
                        height=height
                    )
                else:
                    return self._create_placeholder_chart(width, height, "Bivariate choropleth requires location_column and value_columns configuration")
            else:
                return self.create_bar_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            
        except Exception as e:
            log.error(f"Error creating custom chart: {e}")
            return self._create_placeholder_chart(width, height, "Custom Chart Error")
