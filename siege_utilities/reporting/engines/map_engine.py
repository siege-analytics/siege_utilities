"""
Map chart mixins — choropleth, marker, 3D, heatmap, cluster, flow, and bivariate maps.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Union

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

try:
    from reportlab.platypus import Image
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    Image = None

log = logging.getLogger(__name__)


class MapChartMixin:
    """Geographic map chart methods (choropleth, marker, 3D, heatmap, cluster, flow)."""

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
                                             geodata: Union['gpd.GeoDataFrame', str, Path],
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

            # Merge data with geodata — only if gdf is missing the value columns.
            # When data and geodata are the same GeoDataFrame the merge would
            # create suffixed duplicates (population_x / population_y) and the
            # subsequent column lookup would fail with KeyError.
            if value_column1 in gdf.columns and value_column2 in gdf.columns:
                merged = gdf
            else:
                df_tabular = df.drop(columns='geometry', errors='ignore')
                merged = gdf.merge(df_tabular, on=location_column, how='left',
                                   suffixes=('', '_data'))

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

    def _create_bivariate_color_matrix(self, scheme: str = "default") -> 'np.ndarray':
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

    def _apply_bivariate_colors(self, gdf, var1_col: str, var2_col: str, color_matrix: 'np.ndarray'):
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

    def _add_bivariate_legend(self, ax, var1: str, var2: str, color_matrix: 'np.ndarray'):
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
            from matplotlib.colors import to_rgba
            legend_ax = inset_axes(ax, width='20%', height='20%', loc='upper right')

            # Convert hex color strings to RGBA array for imshow
            rgb_matrix = np.array([[to_rgba(c) for c in row] for row in color_matrix])
            legend_ax.imshow(rgb_matrix, aspect='equal')
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
                                  geodata: Union['gpd.GeoDataFrame', str, Path],
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

            # Merge data with geodata — only if gdf is missing the value column.
            # When data and geodata are the same GeoDataFrame the merge would
            # create suffixed duplicates (population_x / population_y) and the
            # subsequent column lookup would fail with KeyError.
            if value_column not in gdf.columns:
                df_tabular = df.drop(columns='geometry', errors='ignore')
                merged = gdf.merge(df_tabular, on=location_column, how='left',
                                   suffixes=('', '_data'))
            else:
                merged = gdf

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
            plugins.HeatMap(
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
            marker_cluster = plugins.MarkerCluster(
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
                # Merge tabular data onto geometry — drop geometry from the
                # tabular side first to avoid a duplicate geometry column
                # (e.g. ``geometry_data``) that breaks JSON serialization.
                if location_column and location_column in df.columns:
                    df_tabular = df.drop(columns='geometry', errors='ignore')
                    gdf = gdf.merge(df_tabular, on=location_column, how='left', suffixes=('', '_data'))
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
