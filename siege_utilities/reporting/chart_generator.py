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

log = logging.getLogger(__name__)

class ChartGenerator:
    """
    Generates charts and visualizations for reports using matplotlib, seaborn, plotly, and folium.
    Supports pandas DataFrames, Spark DataFrames, and various data sources.
    """

    def __init__(self, branding_config: Optional[Dict[str, Any]] = None,
                 output_dir: Optional[Path] = None,
                 max_chart_width: Optional[float] = None,
                 max_chart_height: Optional[float] = None):
        """
        Initialize the chart generator.

        Args:
            branding_config: Branding configuration for chart colors and styling
            output_dir: Directory for saving Folium HTML map files.
                        Defaults to ``~/.siege_utilities`` for backward compatibility.
            max_chart_width: Maximum chart width in inches for ReportLab output.
                             When set, charts wider than this are uniformly scaled
                             down to fit.  ``None`` disables width clamping.
            max_chart_height: Maximum chart height in inches for ReportLab output.
                              When set, charts taller than this are uniformly scaled
                              down to fit.  ``None`` disables height clamping.
        """
        self.branding_config = branding_config or {}
        self.output_dir = Path(output_dir) if output_dir is not None else Path.home() / ".siege_utilities"
        self.max_chart_width = max_chart_width
        self.max_chart_height = max_chart_height
        self.styles = getSampleStyleSheet()
        self._setup_default_colors()
        self._setup_plotting_style()

        # Set default figure size and DPI for professional quality
        self.default_figsize = (8, 5)
        self.default_dpi = 150

        # Set matplotlib global DPI for consistency
        if MATPLOTLIB_AVAILABLE:
            plt.rcParams['figure.dpi'] = 150
            plt.rcParams['savefig.dpi'] = 150

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
            
            # Set default font sizes and DPI
            plt.rcParams['figure.dpi'] = 150
            plt.rcParams['font.size'] = 10
            plt.rcParams['axes.titlesize'] = 12
            plt.rcParams['axes.labelsize'] = 10
            plt.rcParams['xtick.labelsize'] = 9
            plt.rcParams['ytick.labelsize'] = 9
            plt.rcParams['legend.fontsize'] = 9
            plt.rcParams['figure.titlesize'] = 14
            
            # Enhanced legend settings to prevent label collisions
            plt.rcParams['legend.frameon'] = True
            plt.rcParams['legend.fancybox'] = True
            plt.rcParams['legend.shadow'] = True
            plt.rcParams['legend.framealpha'] = 0.9
            plt.rcParams['legend.edgecolor'] = 'black'
            plt.rcParams['legend.facecolor'] = 'white'

    def _scale_dimensions(self, width: float, height: float,
                          max_width: Optional[float] = None,
                          max_height: Optional[float] = None) -> tuple:
        """Return ``(width, height)`` uniformly scaled to fit within max bounds.

        Resolves effective maximums from instance-level defaults
        (``self.max_chart_width``/``self.max_chart_height``) and per-call
        overrides.  When both are set the *tighter* (smaller) limit wins.

        If no maximum is active, the original dimensions are returned
        unchanged.  Aspect ratio is always preserved.

        Args:
            width: Original width in inches.
            height: Original height in inches.
            max_width: Per-call maximum width override (``None`` → use instance default).
            max_height: Per-call maximum height override (``None`` → use instance default).

        Returns:
            ``(scaled_width, scaled_height)`` tuple.
        """
        # Resolve effective max — tighter of instance-level and per-call
        eff_max_w = self.max_chart_width
        if max_width is not None:
            eff_max_w = min(max_width, eff_max_w) if eff_max_w is not None else max_width

        eff_max_h = self.max_chart_height
        if max_height is not None:
            eff_max_h = min(max_height, eff_max_h) if eff_max_h is not None else max_height

        # No limits → nothing to do
        if eff_max_w is None and eff_max_h is None:
            return width, height

        scale = 1.0
        if eff_max_w is not None and width > eff_max_w:
            scale = min(scale, eff_max_w / width)
        if eff_max_h is not None and height > eff_max_h:
            scale = min(scale, eff_max_h / height)

        if scale < 1.0:
            new_w = width * scale
            new_h = height * scale
            log.info(
                "Auto-scaling chart from %.2f×%.2f to %.2f×%.2f in "
                "(max %.1s×%.1s, scale=%.3f)",
                width, height, new_w, new_h,
                eff_max_w, eff_max_h, scale,
            )
            return new_w, new_h

        return width, height

    def _save_folium_map(self, folium_map, filename: str, label: str,
                         width: float, height: float) -> Image:
        """Save a Folium map to *self.output_dir* and return a placeholder chart.

        Consolidates the identical mkdir → save → log → placeholder pattern
        used by every Folium-based method.

        Args:
            folium_map: A ``folium.Map`` instance.
            filename: File name (e.g. ``"temp_choropleth_map.html"``).
            label: Human-readable label shown in the placeholder image.
            width: Placeholder chart width (inches).
            height: Placeholder chart height (inches).

        Returns:
            ReportLab Image placeholder.
        """
        map_path = self.output_dir / filename
        map_path.parent.mkdir(parents=True, exist_ok=True)
        folium_map.save(str(map_path))
        log.info(f"{label} saved to {map_path}")
        return self._create_placeholder_chart(width, height, f"{label} — saved to {map_path}")

    def create_bar_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                        x_column: str = None, y_column: str = None,
                        title: str = "", width: float = 6.0, height: float = 4.0,
                        chart_type: str = "bar", group_by: str = None,
                        show_legend: bool = True, legend_position: str = "best") -> Image:
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
            
            # Create figure with very conservative sizing to prevent ReportLab crashes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
            
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
                bar_height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., bar_height,
                       f'{bar_height:,.0f}', ha='center', va='bottom')
            
            # Add legend with better positioning
            if show_legend and (group_by or len(y_values) > 1):
                if legend_position == "outside":
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                elif legend_position == "bottom":
                    ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', ncol=min(3, len(y_values) if len(y_values) > 1 else 1))
                else:  # "best" or default
                    ax.legend(loc='best')
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating bar chart: {e}")
            return self._create_placeholder_chart(width, height, f"Chart Error: {str(e)}")

    def create_line_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                         x_column: str = None, y_columns: List[str] = None,
                         title: str = "", width: float = 6.0, height: float = 4.0,
                         show_legend: bool = True, legend_position: str = "best") -> Image:
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
            
            # Create figure with very conservative sizing to prevent ReportLab crashes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
            
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
            
            # Add legend with better positioning
            if show_legend and len(y_columns) > 1:
                if legend_position == "outside":
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                elif legend_position == "bottom":
                    ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', ncol=min(len(y_columns), 3))
                else:  # "best" or default
                    ax.legend(loc='best')
            elif show_legend and len(y_columns) == 1:
                # Single line - add legend if title suggests it's needed
                if "vs" in title.lower() or "comparison" in title.lower():
                    ax.legend([y_columns[0]], loc='best')
            
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels if needed
            if len(x_values) > 5:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating line chart: {e}")
            return self._create_placeholder_chart(width, height, f"Chart Error: {str(e)}")

    def create_pie_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                        labels_column: str = None, values_column: str = None,
                        title: str = "", width: float = 6.0, height: float = 4.0,
                        show_legend: bool = True, legend_position: str = "right") -> Image:
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
            
            # Create figure with larger size for dominant appearance
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Adjust subplot parameters to make room for legend table
            fig.subplots_adjust(left=0.1, right=0.6, top=0.9, bottom=0.1)
            
            # Create clean pie chart with NO LABELS AT ALL
            wedges = ax.pie(values, labels=None, autopct=None,
                           colors=self.color_palette[:len(values)],
                           startangle=90)[0]
            
            # Customize chart
            ax.set_title(title or "Data Distribution")
            
            # Add legend with configurable positioning to avoid collisions
            # Create legend table instead of matplotlib legend
            if show_legend:
                # Calculate percentages for the table
                total = sum(values)
                percentages = [(v/total)*100 for v in values]
                
                # Create legend table data
                legend_data = []
                for i, (label, value, pct) in enumerate(zip(labels, values, percentages)):
                    legend_data.append([
                        f"■",  # Color indicator
                        label,
                        f"{value:,}",
                        f"{pct:.1f}%"
                    ])
                
                # Create table — bbox is [left, bottom, width, height] in
                # axes coordinates.  With subplots_adjust(right=0.6) the axes
                # occupies ~50% of figure width, so 0.6 axes-widths ≈ 1.8in
                # on a 6-inch figure — enough room for the four columns.
                table = ax.table(cellText=legend_data,
                               colLabels=['', 'Label', 'Value', 'Percent'],
                               cellLoc='center',
                               loc='center',
                               bbox=[1.05, 0.0, 0.6, 0.9])

                # Style the table
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.5)
                
                # Color the first column with the actual colors
                for i, color in enumerate(self.color_palette[:len(values)]):
                    table[(i+1, 0)].set_facecolor(color)
                    table[(i+1, 0)].set_text_props(weight='bold')
                
                # Style header
                for i in range(4):
                    table[(0, i)].set_facecolor('#40466e')
                    table[(0, i)].set_text_props(weight='bold', color='white')
                
                # Remove table borders
                for i in range(len(legend_data) + 1):
                    for j in range(4):
                        table[(i, j)].set_edgecolor('none')
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating pie chart: {e}")
            return self._create_placeholder_chart(width, height, f"Chart Error: {str(e)}")

    def create_choropleth_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                             geo_data: Union['gpd.GeoDataFrame', str, Path, Dict, None] = None,
                             location_column: str = None, value_column: str = None,
                             title: str = "", width: float = 8.0, height: float = 6.0,
                             map_type: str = "us",
                             key_on: str = "feature.properties.geoid",
                             fill_color: str = "YlOrRd") -> Image:
        """
        Create a choropleth map from data using Folium.

        Args:
            data: DataFrame or dictionary with data
            geo_data: GeoDataFrame, path to GeoJSON, GeoJSON dict, or None.
                      If a GeoDataFrame is passed it is converted to GeoJSON automatically.
            location_column: Column name for locations (must match geo_data features via key_on)
            value_column: Column name for values to color by
            title: Map title
            width: Map width in inches
            height: Map height in inches
            map_type: Type of map ('world', 'us', 'europe')
            key_on: GeoJSON feature property to join on (e.g. 'feature.properties.geoid')
            fill_color: Brewer color scheme name (e.g. 'YlOrRd', 'BuGn', 'Blues')

        Returns:
            ReportLab Image object (placeholder — HTML saved to output_dir)
        """
        if not FOLIUM_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Folium not available")

        if geo_data is None:
            return self._create_placeholder_chart(width, height, "geo_data is required for choropleth map")

        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            # Convert GeoDataFrame to GeoJSON for Folium
            geojson_data = self._resolve_geo_data(geo_data)

            # Create base map
            if map_type == "world":
                m = folium.Map(location=[20, 0], zoom_start=2)
            elif map_type == "us":
                m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)
            elif map_type == "europe":
                m = folium.Map(location=[50, 10], zoom_start=4)
            else:
                m = folium.Map(location=[20, 0], zoom_start=2)

            # Add choropleth layer
            folium.Choropleth(
                geo_data=geojson_data,
                name="choropleth",
                data=df,
                columns=[location_column, value_column],
                key_on=key_on,
                fill_color=fill_color,
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name=value_column
            ).add_to(m)

            # Add layer control
            folium.LayerControl().add_to(m)

            return self._save_folium_map(m, "temp_choropleth_map.html",
                                        "Choropleth Map", width, height)

        except Exception as e:
            log.error(f"Error creating choropleth map: {e}")
            return self._create_placeholder_chart(width, height, f"Map Error: {str(e)}")

    def _resolve_geo_data(self, geo_data) -> Union[str, Dict]:
        """Convert geo_data argument to a format Folium accepts (GeoJSON dict or path string)."""
        if GEOPANDAS_AVAILABLE and isinstance(geo_data, gpd.GeoDataFrame):
            return json.loads(geo_data.to_json())
        if isinstance(geo_data, (str, Path)):
            return str(geo_data)
        if isinstance(geo_data, dict):
            return geo_data
        raise TypeError(f"Unsupported geo_data type: {type(geo_data)}")

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
            
            # Create proper bivariate classification and coloring
            color_matrix = self._create_bivariate_color_matrix(color_scheme)
            merged_with_colors = self._apply_bivariate_colors(merged, value_column1, value_column2, color_matrix)
            
            # Create figure with very conservative sizing to prevent ReportLab crashes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            
            # Create true bivariate choropleth
            merged_with_colors.plot(
                color=merged_with_colors['bivariate_color'],
                linewidth=0.5,
                edgecolor='black',
                ax=ax
            )
            
            # Add title and remove axes
            ax.set_title(title or f"Bivariate Choropleth: {value_column1} vs {value_column2}")
            ax.axis('off')
            
            # Add proper bivariate legend
            self._add_bivariate_legend(ax, value_column1, value_column2, color_matrix)
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating bivariate choropleth with matplotlib: {e}")
            return self._create_placeholder_chart(width, height, f"Bivariate Choropleth Error: {str(e)}")

    def _create_bivariate_color_matrix(self, scheme: str = "default") -> np.ndarray:
        """
        Create a proper 2D bivariate color matrix for choropleth maps.
        
        Args:
            scheme: Color scheme type ('default', 'blue_red', 'green_orange')
            
        Returns:
            3x3 numpy array of hex colors for bivariate classification
        """
        if scheme == "blue_red":
            # Blue-Red bivariate scheme (classic)
            return np.array([
                ['#e8e8e8', '#e4acac', '#c85a5a'],  # Low var1: gray to red
                ['#b8d6be', '#90b4a6', '#627f8c'],  # Med var1: green-gray to blue-gray  
                ['#7fc97f', '#5aae61', '#2d8a49']   # High var1: green spectrum
            ])
        elif scheme == "green_orange":
            # Green-Orange bivariate scheme
            return np.array([
                ['#f7f7f7', '#fdd49e', '#fc8d59'],  # Low var1
                ['#d9f0a3', '#addd8e', '#78c679'],  # Med var1
                ['#41b6c4', '#225ea8', '#253494']   # High var1  
            ])
        else:  # default
            # Default purple-blue bivariate scheme (Teuling et al.)
            return np.array([
                ['#e8e8e8', '#c1a5cc', '#9972af'],  # Low var1: gray to purple
                ['#b8d6be', '#909eb1', '#6771a5'],  # Med var1: light blue-gray
                ['#7fc97f', '#5db08a', '#3a9c95']   # High var1: green to teal
            ])
    
    def _apply_bivariate_colors(self, gdf, var1_col: str, var2_col: str, color_matrix: np.ndarray):
        """
        Apply bivariate colors to geodataframe based on quantile classification.
        
        Args:
            gdf: GeoDataFrame with data
            var1_col: First variable column name
            var2_col: Second variable column name  
            color_matrix: 3x3 color matrix from _create_bivariate_color_matrix
            
        Returns:
            GeoDataFrame with bivariate_color column added
        """
        gdf = gdf.copy()
        
        # Remove NaN values for classification
        valid_mask = gdf[var1_col].notna() & gdf[var2_col].notna()
        
        if not valid_mask.any():
            gdf['bivariate_color'] = '#cccccc'  # Gray for no data
            return gdf
        
        # Classify variables into 3 quantile-based bins each
        var1_bins = pd.qcut(gdf.loc[valid_mask, var1_col], 3, labels=[0, 1, 2], duplicates='drop')
        var2_bins = pd.qcut(gdf.loc[valid_mask, var2_col], 3, labels=[0, 1, 2], duplicates='drop')
        
        # Initialize color column
        gdf['bivariate_color'] = '#cccccc'  # Default gray for NaN/invalid
        
        # Assign colors based on bivariate classification
        for i, (idx, row) in enumerate(gdf[valid_mask].iterrows()):
            try:
                bin1 = int(var1_bins.iloc[i]) if pd.notna(var1_bins.iloc[i]) else 1
                bin2 = int(var2_bins.iloc[i]) if pd.notna(var2_bins.iloc[i]) else 1
                color = color_matrix[bin2, bin1]  # Note: row=var2, col=var1
                gdf.loc[idx, 'bivariate_color'] = color
            except (ValueError, IndexError):
                gdf.loc[idx, 'bivariate_color'] = '#cccccc'
        
        return gdf

    def _add_bivariate_legend(self, ax, var1: str, var2: str, color_matrix: np.ndarray):
        """
        Add a proper 3x3 bivariate legend grid to the map.
        
        Args:
            ax: Matplotlib axes
            var1: First variable name (horizontal axis)
            var2: Second variable name (vertical axis)
            color_matrix: 3x3 color matrix
        """
        try:
            # Create inset axes for the bivariate legend
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes
            legend_ax = inset_axes(ax, width='20%', height='20%', loc='upper right')
            
            # Display the 3x3 color matrix as legend
            legend_ax.imshow(color_matrix, aspect='equal')
            legend_ax.set_xticks([0, 1, 2])
            legend_ax.set_yticks([0, 1, 2])
            legend_ax.set_xticklabels(['Low', 'Med', 'High'], fontsize=8)
            legend_ax.set_yticklabels(['High', 'Med', 'Low'], fontsize=8)
            legend_ax.set_xlabel(var1, fontsize=9, fontweight='bold')
            legend_ax.set_ylabel(var2, fontsize=9, fontweight='bold')
            legend_ax.tick_params(length=0, labelsize=8)
            
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
            
            # Create figure with very conservative sizing to prevent ReportLab crashes
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

    def create_marker_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                          latitude_column: str, longitude_column: str,
                          value_column: str = None, label_column: str = None,
                          title: str = "", width: float = 10.0, height: float = 8.0,
                          map_style: str = "open-street-map", zoom_level: int = 10) -> Image:
        """
        Create a map with markers showing point locations.
        
        Args:
            data: DataFrame or dictionary with data
            latitude_column: Column name for latitude values
            longitude_column: Column name for longitude values
            value_column: Column name for marker size/color values
            label_column: Column name for marker labels
            title: Map title
            width: Map width in inches
            height: Map height in inches
            map_style: Map tile style ('open-street-map', 'cartodb-positron', 'stamen-terrain')
            zoom_level: Initial zoom level for the map
            
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
            
            # Calculate center point for map
            center_lat = df[latitude_column].mean()
            center_lon = df[longitude_column].mean()
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=zoom_level,
                tiles=map_style
            )
            
            # Add markers
            for idx, row in df.iterrows():
                lat = row[latitude_column]
                lon = row[longitude_column]
                
                # Create popup content
                popup_content = []
                if label_column and label_column in row:
                    popup_content.append(f"<b>{row[label_column]}</b>")
                if value_column and value_column in row:
                    popup_content.append(f"Value: {row[value_column]:,.2f}")
                popup_content.append(f"Lat: {lat:.4f}, Lon: {lon:.4f}")
                
                popup_html = "<br>".join(popup_content)
                
                # Determine marker size based on value
                if value_column and value_column in row:
                    # Normalize values to marker sizes (10-50 pixels)
                    value = row[value_column]
                    marker_size = max(10, min(50, int(10 + (value / df[value_column].max()) * 40)))
                else:
                    marker_size = 15
                
                # Add marker
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=marker_size,
                    popup=folium.Popup(popup_html, max_width=300),
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.7,
                    weight=2
                ).add_to(m)
            
            # Add title
            if title:
                folium.TileLayer(
                    tiles='',
                    attr='',
                    name=title,
                    overlay=True,
                    control=False
                ).add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            return self._save_folium_map(m, "temp_marker_map.html",
                                        "Marker Map", width, height)
            
        except Exception as e:
            log.error(f"Error creating marker map: {e}")
            return self._create_placeholder_chart(width, height, f"Marker Map Error: {str(e)}")

    def create_3d_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                      latitude_column: str, longitude_column: str, elevation_column: str,
                      title: str = "", width: float = 12.0, height: float = 10.0,
                      view_angle: int = 45, elevation_scale: float = 1.0) -> Image:
        """
        Create a 3D map visualization showing elevation or height data.
        
        Args:
            data: DataFrame or dictionary with data
            latitude_column: Column name for latitude values
            longitude_column: Column name for longitude values
            elevation_column: Column name for elevation/height values
            title: Map title
            width: Map width in inches
            height: Map height in inches
            view_angle: 3D viewing angle in degrees
            elevation_scale: Scale factor for elevation values
            
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
            
            # Create 3D figure
            fig = plt.figure(figsize=(width, height), dpi=self.default_dpi)
            ax = fig.add_subplot(111, projection='3d')
            
            # Extract coordinates and elevation
            x = df[longitude_column].values
            y = df[latitude_column].values
            z = df[elevation_column].values * elevation_scale
            
            # Create 3D surface plot
            if len(df) > 100:  # For large datasets, use triangulation
                from scipy.spatial import Delaunay
                points = np.column_stack([x, y])
                tri = Delaunay(points)
                
                ax.plot_trisurf(x, y, z, triangles=tri.simplices, cmap='terrain', alpha=0.8)
            else:
                # For smaller datasets, use scatter plot
                scatter = ax.scatter(x, y, z, c=z, cmap='terrain', s=50, alpha=0.8)
                plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
            
            # Customize 3D plot
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_zlabel('Elevation')
            ax.set_title(title or "3D Map Visualization")
            
            # Set viewing angle
            ax.view_init(elev=view_angle, azim=45)
            
            # Add grid
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)
            
        except Exception as e:
            log.error(f"Error creating 3D map: {e}")
            return self._create_placeholder_chart(width, height, f"3D Map Error: {str(e)}")

    def create_heatmap_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                           latitude_column: str, longitude_column: str, value_column: str,
                           title: str = "", width: float = 10.0, height: float = 8.0,
                           grid_size: int = 50, blur_radius: float = 0.5) -> Image:
        """
        Create a heatmap overlay on a geographic map.
        
        Args:
            data: DataFrame or dictionary with data
            latitude_column: Column name for latitude values
            longitude_column: Column name for longitude values
            value_column: Column name for intensity values
            title: Map title
            width: Map width in inches
            height: Map height in inches
            grid_size: Number of grid cells for heatmap
            blur_radius: Blur radius for smoothing
            
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
            
            # Calculate center point for map
            center_lat = df[latitude_column].mean()
            center_lon = df[longitude_column].mean()
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='cartodbpositron'
            )
            
            # Prepare data for heatmap
            heat_data = []
            for idx, row in df.iterrows():
                heat_data.append([row[latitude_column], row[longitude_column], row[value_column]])
            
            # Add heatmap layer
            folium.plugins.HeatMap(
                heat_data,
                radius=20,
                blur=blur_radius,
                max_zoom=13,
                gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 1: 'red'}
            ).add_to(m)
            
            # Add title
            if title:
                folium.TileLayer(
                    tiles='',
                    attr='',
                    name=title,
                    overlay=True,
                    control=False
                ).add_to(m)
            
            return self._save_folium_map(m, "temp_heatmap.html",
                                        "Heatmap", width, height)
            
        except Exception as e:
            log.error(f"Error creating heatmap: {e}")
            return self._create_placeholder_chart(width, height, f"Heatmap Error: {str(e)}")

    def create_cluster_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                           latitude_column: str, longitude_column: str,
                           cluster_column: str = None, label_column: str = None,
                           title: str = "", width: float = 10.0, height: float = 8.0,
                           max_cluster_radius: int = 80) -> Image:
        """
        Create a map with clustered markers for better visualization of dense data.
        
        Args:
            data: DataFrame or dictionary with data
            latitude_column: Column name for latitude values
            longitude_column: Column name for longitude values
            cluster_column: Column name for clustering values
            label_column: Column name for marker labels
            title: Map title
            width: Map width in inches
            height: Map height in inches
            max_cluster_radius: Maximum radius for clustering
            
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
            
            # Calculate center point for map
            center_lat = df[latitude_column].mean()
            center_lon = df[longitude_column].mean()
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='cartodbpositron'
            )
            
            # Create marker cluster
            marker_cluster = folium.plugins.MarkerCluster(
                name="Data Points",
                overlay=True,
                control=True,
                options={'maxClusterRadius': max_cluster_radius}
            )
            
            # Add individual markers
            for idx, row in df.iterrows():
                lat = row[latitude_column]
                lon = row[longitude_column]
                
                # Create popup content
                popup_content = []
                if label_column and label_column in row:
                    popup_content.append(f"<b>{row[label_column]}</b>")
                if cluster_column and cluster_column in row:
                    popup_content.append(f"Cluster: {row[cluster_column]}")
                popup_content.append(f"Lat: {lat:.4f}, Lon: {lon:.4f}")
                
                popup_html = "<br>".join(popup_content)
                
                # Add marker to cluster
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(marker_cluster)
            
            # Add cluster to map
            marker_cluster.add_to(m)
            
            # Add title
            if title:
                folium.TileLayer(
                    tiles='',
                    attr='',
                    name=title,
                    overlay=True,
                    control=False
                ).add_to(m)
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            return self._save_folium_map(m, "temp_cluster_map.html",
                                        "Cluster Map", width, height)
            
        except Exception as e:
            log.error(f"Error creating cluster map: {e}")
            return self._create_placeholder_chart(width, height, f"Cluster Map Error: {str(e)}")

    def create_flow_map(self, data: Union[pd.DataFrame, Dict[str, Any]],
                        origin_lat_column: str, origin_lon_column: str,
                        dest_lat_column: str, dest_lon_column: str,
                        flow_value_column: str = None, title: str = "",
                        width: float = 12.0, height: float = 10.0) -> Image:
        """
        Create a flow map showing movement or connections between locations.
        
        Args:
            data: DataFrame or dictionary with data
            origin_lat_column: Column name for origin latitude
            origin_lon_column: Column name for origin longitude
            dest_lat_column: Column name for destination latitude
            dest_lon_column: Column name for destination longitude
            flow_value_column: Column name for flow intensity values
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
            
            # Calculate center point for map
            all_lats = df[origin_lat_column].tolist() + df[dest_lat_column].tolist()
            all_lons = df[origin_lon_column].tolist() + df[dest_lon_column].tolist()
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=8,
                tiles='cartodbpositron'
            )
            
            # Add flow lines
            for idx, row in df.iterrows():
                origin = [row[origin_lat_column], row[origin_lon_column]]
                destination = [row[dest_lat_column], row[dest_lon_column]]
                
                # Determine line weight based on flow value
                if flow_value_column and flow_value_column in row:
                    weight = max(1, min(10, int(row[flow_value_column] / df[flow_value_column].max() * 10)))
                else:
                    weight = 3
                
                # Create flow line
                folium.PolyLine(
                    locations=[origin, destination],
                    weight=weight,
                    color='red',
                    opacity=0.7,
                    popup=f"Flow: {row.get(flow_value_column, 'N/A') if flow_value_column else 'N/A'}"
                ).add_to(m)
                
                # Add origin and destination markers
                folium.CircleMarker(
                    location=origin,
                    radius=5,
                    color='blue',
                    fill=True,
                    popup="Origin"
                ).add_to(m)
                
                folium.CircleMarker(
                    location=destination,
                    radius=5,
                    color='green',
                    fill=True,
                    popup="Destination"
                ).add_to(m)
            
            # Add title
            if title:
                folium.TileLayer(
                    tiles='',
                    attr='',
                    name=title,
                    overlay=True,
                    control=False
                ).add_to(m)
            
            return self._save_folium_map(m, "temp_flow_map.html",
                                        "Flow Map", width, height)
            
        except Exception as e:
            log.error(f"Error creating flow map: {e}")
            return self._create_placeholder_chart(width, height, f"Flow Map Error: {str(e)}")

    def create_bivariate_choropleth(self, data: Union[pd.DataFrame, Dict[str, Any]],
                                  geo_data: Union['gpd.GeoDataFrame', str, Path, Dict, None] = None,
                                  location_column: str = None,
                                  value_column1: str = None, value_column2: str = None,
                                  title: str = "", width: float = 8.0, height: float = 6.0,
                                  color_scheme: str = "default") -> Image:
        """
        Create a bivariate choropleth map from data using Folium.

        Uses the same 3x3 bivariate color classification as
        ``create_bivariate_choropleth_matplotlib`` but renders the result as an
        interactive Folium map.

        Args:
            data: DataFrame or dictionary with data (must include geometry if GeoDataFrame,
                  or be joinable to *geo_data* via *location_column*)
            geo_data: GeoDataFrame, path to GeoJSON, GeoJSON dict, or None.
                      If *data* is already a GeoDataFrame this can be omitted.
            location_column: Column to join data ↔ geo_data on
            value_column1: First variable (X-axis in bivariate scheme)
            value_column2: Second variable (Y-axis in bivariate scheme)
            title: Map title
            width: Map width in inches
            height: Map height in inches
            color_scheme: Bivariate color scheme ('default', 'blue_red', 'green_orange')

        Returns:
            ReportLab Image object (placeholder — HTML saved to output_dir)
        """
        if not FOLIUM_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Folium not available")
        if not GEOPANDAS_AVAILABLE:
            return self._create_placeholder_chart(width, height, "GeoPandas not available")

        try:
            # Convert data to DataFrame / GeoDataFrame
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            # Resolve geodata
            if geo_data is not None:
                if isinstance(geo_data, (str, Path)):
                    gdf = gpd.read_file(geo_data)
                elif isinstance(geo_data, dict):
                    gdf = gpd.GeoDataFrame.from_features(geo_data.get('features', geo_data))
                else:
                    gdf = geo_data.copy()
                # Merge tabular data onto geometry
                if location_column and location_column in df.columns:
                    gdf = gdf.merge(df, on=location_column, how='left', suffixes=('', '_data'))
            elif hasattr(df, 'geometry'):
                gdf = df
            else:
                return self._create_placeholder_chart(width, height,
                    "geo_data is required (GeoDataFrame, GeoJSON path, or dict)")

            # Apply bivariate classification using existing helpers
            color_matrix = self._create_bivariate_color_matrix(color_scheme)
            gdf = self._apply_bivariate_colors(gdf, value_column1, value_column2, color_matrix)

            # Build a color lookup keyed by index for the style_function
            color_lookup = gdf['bivariate_color'].to_dict()

            # Calculate map center from geometry bounds
            bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2

            m = folium.Map(location=[center_lat, center_lon], zoom_start=6,
                           tiles='cartodbpositron')

            # Convert to GeoJSON and add styled layer
            geojson_data = json.loads(gdf.to_json())

            # Attach index to each feature so we can look up color
            for i, feature in enumerate(geojson_data['features']):
                feature['properties']['_idx'] = list(color_lookup.keys())[i]

            folium.GeoJson(
                geojson_data,
                name=title or "Bivariate Choropleth",
                style_function=lambda feature: {
                    'fillColor': color_lookup.get(feature['properties'].get('_idx'), '#cccccc'),
                    'color': 'black',
                    'weight': 0.5,
                    'fillOpacity': 0.7,
                },
            ).add_to(m)

            folium.LayerControl().add_to(m)

            return self._save_folium_map(m, "temp_bivariate_choropleth.html",
                                        "Bivariate Choropleth", width, height)

        except Exception as e:
            log.error(f"Error creating bivariate choropleth map: {e}")
            return self._create_placeholder_chart(width, height, f"Bivariate Choropleth Error: {str(e)}")

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
            
            # Create figure with very conservative sizing to prevent ReportLab crashes
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
            
            # Create subplot grid with very conservative sizing to prevent ReportLab crashes
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

    def _matplotlib_to_reportlab_image(self, fig, width: float, height: float,
                                       max_width: Optional[float] = None,
                                       max_height: Optional[float] = None) -> Image:
        """
        Convert matplotlib figure to ReportLab Image with size optimization.

        Args:
            fig: Matplotlib figure
            width: Image width in inches
            height: Image height in inches
            max_width: Per-call max width override for ``_scale_dimensions``.
            max_height: Per-call max height override for ``_scale_dimensions``.

        Returns:
            ReportLab Image object
        """
        try:
            # Use high DPI for crisp, professional quality
            optimal_dpi = self.default_dpi

            # Save figure to bytes buffer with optimized settings
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=optimal_dpi,
                       facecolor='white', edgecolor='none', pad_inches=0.1)
            img_buffer.seek(0)

            # Check if image is still too large
            img_size = len(img_buffer.getvalue())
            if img_size > 5 * 1024 * 1024:  # 5MB limit
                log.warning(f"Image size {img_size/1024/1024:.1f}MB exceeds limit, reducing quality")
                img_buffer.seek(0)
                fig.savefig(img_buffer, format='png', dpi=100,
                           facecolor='white', edgecolor='none', pad_inches=0.1)
                img_buffer.seek(0)

            # Encode as base64
            img_data = base64.b64encode(img_buffer.getvalue()).decode()

            # Create data URL
            data_url = f"data:image/png;base64,{img_data}"

            # Close the figure to free memory
            plt.close(fig)

            # Auto-scale to fit within max bounds (if configured)
            scaled_w, scaled_h = self._scale_dimensions(
                width, height, max_width=max_width, max_height=max_height,
            )

            if scaled_w != width or scaled_h != height:
                # Scaling occurred — set both dimensions explicitly
                rl_image = Image(data_url, width=scaled_w * inch,
                                 height=scaled_h * inch)
            else:
                # No scaling — let ReportLab determine height from image
                rl_image = Image(data_url, width=width * inch)

            return rl_image

        except Exception as e:
            log.error(f"Error converting matplotlib figure to ReportLab Image: {e}")
            return self._create_placeholder_chart(width, height, "Image Conversion Error")

    def create_proportional_text_bar_chart(self, 
                                         data: pd.DataFrame,
                                         labels_column: str,
                                         values_column: str,
                                         title: str = "Proportional Text Bar Chart",
                                         max_width: int = 50,
                                         bar_char: str = "█",
                                         show_values: bool = True,
                                         sort_descending: bool = True) -> str:
        """
        Create a proportional text-based bar chart
        
        Args:
            data: DataFrame containing the data
            labels_column: Column name for labels
            values_column: Column name for values
            title: Chart title
            max_width: Maximum width of bars in characters
            bar_char: Character to use for bars
            show_values: Whether to show actual values
            sort_descending: Whether to sort by values descending
            
        Returns:
            Formatted text chart string
        """
        try:
            if data.empty:
                return f"<i>No data available for {title}</i>"
            
            # Sort data if requested
            if sort_descending:
                data = data.sort_values(values_column, ascending=False)
            
            # Get max value for proportional scaling
            max_value = data[values_column].max()
            
            # Create chart
            chart_lines = [f"<b>{title}</b>", "=" * len(title), ""]
            
            for _, row in data.iterrows():
                label = str(row[labels_column])
                value = row[values_column]
                
                # Calculate proportional bar length
                if max_value > 0:
                    bar_length = int((value / max_value) * max_width)
                else:
                    bar_length = 0
                
                # Create bar
                bar = bar_char * bar_length
                
                # Format the line
                if show_values:
                    chart_lines.append(f"{label:<20} {bar} {value:,}")
                else:
                    chart_lines.append(f"{label:<20} {bar}")
            
            return "<br/>".join(chart_lines)
            
        except Exception as e:
            log.error(f"Error creating proportional text bar chart: {e}")
            return f"<i>Error creating text bar chart: {str(e)}</i>"
    
    def create_heatmap_text_chart(self,
                                data: pd.DataFrame,
                                x_column: str,
                                y_column: str,
                                value_column: str,
                                title: str = "Text Heatmap",
                                max_width: int = 20,
                                max_height: int = 10,
                                heat_chars: str = " ░▒▓█") -> str:
        """
        Create a text-based heatmap visualization
        
        Args:
            data: DataFrame containing the data
            x_column: Column name for x-axis labels
            y_column: Column name for y-axis labels
            value_column: Column name for values
            title: Chart title
            max_width: Maximum width in characters
            max_height: Maximum height in characters
            heat_chars: Characters for heat intensity (light to dark)
            
        Returns:
            Formatted text heatmap string
        """
        try:
            if data.empty:
                return f"<i>No data available for {title}</i>"
            
            # Create pivot table
            pivot_data = data.pivot_table(
                values=value_column, 
                index=y_column, 
                columns=x_column, 
                fill_value=0
            )
            
            # Normalize values to heat character indices
            max_value = pivot_data.values.max()
            min_value = pivot_data.values.min()
            value_range = max_value - min_value if max_value > min_value else 1
            
            # Create heatmap
            chart_lines = [f"<b>{title}</b>", "=" * len(title), ""]
            
            # Add column headers
            col_headers = [f"{col:<8}" for col in pivot_data.columns]
            chart_lines.append(" " * 12 + "".join(col_headers))
            chart_lines.append(" " * 12 + "-" * len("".join(col_headers)))
            
            # Add rows
            for idx, row in pivot_data.iterrows():
                row_label = f"{str(idx):<10}"
                heat_row = ""
                
                for value in row:
                    # Normalize value to heat character index
                    normalized = (value - min_value) / value_range
                    char_index = int(normalized * (len(heat_chars) - 1))
                    char_index = max(0, min(char_index, len(heat_chars) - 1))
                    heat_row += heat_chars[char_index] * 2
                
                chart_lines.append(f"{row_label} {heat_row}")
            
            # Add legend
            chart_lines.append("")
            chart_lines.append("Legend: " + " ".join([f"{heat_chars[i]} {i/(len(heat_chars)-1)*100:.0f}%" for i in range(len(heat_chars))]))
            
            return "<br/>".join(chart_lines)
            
        except Exception as e:
            log.error(f"Error creating text heatmap: {e}")
            return f"<i>Error creating text heatmap: {str(e)}</i>"

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

                # Convert to ReportLab Image (inherits auto-scaling)
                return self._matplotlib_to_reportlab_image(fig, width, height)
            else:
                # Fallback to simple text — still honour auto-scaling
                sw, sh = self._scale_dimensions(width, height)
                return Image("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                           width=sw*inch, height=sh*inch)
        except Exception as e:
            log.error(f"Error creating placeholder chart: {e}")
            # Return a minimal image — still honour auto-scaling
            sw, sh = self._scale_dimensions(width, height)
            return Image("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                       width=sw*inch, height=sh*inch)

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
                return self.create_heatmap(df, title=title, width=width, height=height)
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
