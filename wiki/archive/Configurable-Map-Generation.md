# Configurable Map Generation - Customizable Markers, Colors & Export Formats

## Problem

You need to generate maps with highly customizable visual elements including markers, colors, and export formats. The maps should support multiple output formats (PNG, SVG, PDF, HTML), customizable styling, and integration with both Pandas and Spark data sources.

## Solution

Use Siege Utilities' configurable map generation system with a flexible configuration-driven approach that supports multiple visualization libraries, export formats, and styling options.

## Quick Start

```python
import siege_utilities
from siege_utilities.geo.map_generator import ConfigurableMapGenerator

# Initialize map generator with configuration
map_gen = ConfigurableMapGenerator()

# Generate map with custom configuration
map_config = {
    'markers': {'style': 'circle', 'color': 'red', 'size': 10},
    'colors': {'palette': 'viridis', 'scheme': 'sequential'},
    'export': {'format': 'png', 'resolution': 300, 'size': (1200, 800)}
}

map_result = map_gen.generate_map(data, map_config)
print("✅ Configurable map generated successfully")
```

## Complete Implementation

### 1. Configurable Map Generator Architecture

#### Core Map Generator Class
```python
import siege_utilities
from siege_utilities.geo.map_generator import MapGenerator
from siege_utilities.core.logging import Logger
import pandas as pd
import geopandas as gpd
from pathlib import Path
import json
from typing import Dict, Any, List, Tuple, Optional
import matplotlib.pyplot as plt
import folium
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class ConfigurableMapGenerator:
    """Highly configurable map generator with multiple export formats and styling options"""
    
    def __init__(self, default_config=None):
        self.logger = Logger("configurable_map_generator")
        self.default_config = default_config or self._get_default_config()
        
        # Initialize visualization backends
        self.backends = {
            'matplotlib': self._matplotlib_backend,
            'folium': self._folium_backend,
            'plotly': self._plotly_backend,
            'bokeh': self._bokeh_backend
        }
        
        # Load predefined configurations
        self.presets = self._load_map_presets()
    
    def _get_default_config(self):
        """Get default map configuration"""
        
        return {
            'markers': {
                'style': 'circle',
                'color': '#1f77b4',
                'size': 8,
                'alpha': 0.7,
                'edge_color': '#000000',
                'edge_width': 1,
                'symbols': ['o', 's', '^', 'v', '<', '>', 'D', 'p'],
                'svg_markers': {},  # Custom SVG marker definitions
                'svg_path': None,   # Path to custom SVG marker file
                'svg_scale': 1.0,   # Scale factor for SVG markers
                'svg_rotation': 0,  # Rotation angle for SVG markers
                'svg_colorize': True  # Whether to apply color to SVG markers
            },
            'colors': {
                'palette': 'viridis',
                'scheme': 'sequential',
                'custom_colors': [],
                'color_column': None,
                'color_range': None,
                'alpha': 0.8
            },
            'map_style': {
                'background': 'light',
                'boundary_color': '#666666',
                'boundary_width': 0.5,
                'grid': True,
                'grid_color': '#cccccc',
                'grid_alpha': 0.3
            },
            'labels': {
                'show': True,
                'font_size': 10,
                'font_color': '#000000',
                'font_weight': 'normal',
                'rotation': 0,
                'offset': (0, 0)
            },
            'export': {
                'format': 'png',
                'resolution': 300,
                'size': (1200, 800),
                'dpi': 100,
                'transparent': False,
                'bbox_inches': 'tight'
            },
            'backend': 'matplotlib'
        }
    
    def _load_map_presets(self):
        """Load predefined map configuration presets"""
        
        return {
            'professional': {
                'markers': {'style': 'circle', 'color': '#2E86AB', 'size': 10},
                'colors': {'palette': 'Blues', 'scheme': 'sequential'},
                'map_style': {'background': 'light', 'boundary_color': '#2E86AB'},
                'export': {'format': 'pdf', 'resolution': 300}
            },
            'modern': {
                'markers': {'style': 'square', 'color': '#FF6B6B', 'size': 12},
                'colors': {'palette': 'viridis', 'scheme': 'diverging'},
                'map_style': {'background': 'dark', 'boundary_color': '#FF6B6B'},
                'export': {'format': 'svg', 'resolution': 300}
            },
            'minimal': {
                'markers': {'style': 'circle', 'color': '#000000', 'size': 6},
                'colors': {'palette': 'Greys', 'scheme': 'sequential'},
                'map_style': {'background': 'white', 'grid': False},
                'export': {'format': 'png', 'resolution': 150}
            },
            'interactive': {
                'markers': {'style': 'circle', 'color': '#4ECDC4', 'size': 15},
                'colors': {'palette': 'plasma', 'scheme': 'sequential'},
                'map_style': {'background': 'light'},
                'export': {'format': 'html', 'resolution': 300}
            }
        }
    
    def generate_map(self, data, config=None, preset=None):
        """Generate map with custom configuration or preset"""
        
        try:
            # Merge configuration
            if preset and preset in self.presets:
                final_config = self._merge_configs(self.default_config, self.presets[preset])
            else:
                final_config = self._merge_configs(self.default_config, config or {})
            
            # Validate configuration
            self._validate_config(final_config)
            
            # Select backend
            backend = final_config.get('backend', 'matplotlib')
            if backend not in self.backends:
                raise ValueError(f"Unsupported backend: {backend}")
            
            # Generate map using selected backend
            map_result = self.backends[backend](data, final_config)
            
            self.logger.info(f"✅ Map generated successfully using {backend} backend")
            return map_result
            
        except Exception as e:
            self.logger.error(f"❌ Map generation failed: {e}")
            raise
    
    def _merge_configs(self, base_config, override_config):
        """Merge configuration dictionaries recursively"""
        
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _validate_config(self, config):
        """Validate map configuration"""
        
        # Validate export format
        valid_formats = ['png', 'svg', 'pdf', 'html', 'jpg', 'tiff']
        if config['export']['format'] not in valid_formats:
            raise ValueError(f"Invalid export format. Must be one of: {valid_formats}")
        
        # Validate marker style
        valid_marker_styles = ['circle', 'square', 'triangle', 'diamond', 'star', 'cross']
        if config['markers']['style'] not in valid_marker_styles:
            raise ValueError(f"Invalid marker style. Must be one of: {valid_marker_styles}")
        
        # Validate color palette
        valid_palettes = ['viridis', 'plasma', 'inferno', 'magma', 'Blues', 'Reds', 'Greens', 'Oranges', 'Purples']
        if config['colors']['palette'] not in valid_palettes:
            raise ValueError(f"Invalid color palette. Must be one of: {valid_palettes}")
    
    def add_svg_marker(self, name, svg_path, config=None):
        """Add a custom SVG marker to the marker library"""
        
        try:
            marker_config = config or {}
            svg_marker = self.svg_manager.load_svg_marker(svg_path, marker_config)
            
            if svg_marker:
                self.default_config['markers']['svg_markers'][name] = {
                    'path': svg_path,
                    'svg_data': svg_marker,
                    'config': marker_config
                }
                self.logger.info(f"✅ SVG marker '{name}' loaded successfully from {svg_path}")
                return True
            else:
                self.logger.error(f"❌ Failed to load SVG marker from {svg_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error adding SVG marker '{name}': {e}")
            return False
    
    def get_svg_marker(self, name):
        """Get a custom SVG marker by name"""
        
        return self.default_config['markers']['svg_markers'].get(name)
    
    def list_svg_markers(self):
        """List all available custom SVG markers"""
        
        return list(self.default_config['markers']['svg_markers'].keys())
    
    def remove_svg_marker(self, name):
        """Remove a custom SVG marker"""
        
        if name in self.default_config['markers']['svg_markers']:
            del self.default_config['markers']['svg_markers'][name]
            self.logger.info(f"✅ SVG marker '{name}' removed")
            return True
        else:
            self.logger.warning(f"⚠️ SVG marker '{name}' not found")
            return False
```

### 2. SVG Marker Management

#### SVG Marker Manager Class
```python
class SVGMarkerManager:
    """Manages custom SVG markers for map generation"""
    
    def __init__(self):
        self.logger = Logger("svg_marker_manager")
        self.cached_markers = {}
        self.supported_formats = ['.svg']
    
    def load_svg_marker(self, svg_path, config=None):
        """Load and process an SVG marker file"""
        
        try:
            svg_path = Path(svg_path)
            
            # Validate file
            if not svg_path.exists():
                self.logger.error(f"❌ SVG file not found: {svg_path}")
                return None
            
            if svg_path.suffix.lower() not in self.supported_formats:
                self.logger.error(f"❌ Unsupported file format: {svg_path.suffix}")
                return None
            
            # Check cache
            cache_key = f"{svg_path}_{hash(str(config))}"
            if cache_key in self.cached_markers:
                self.logger.info(f"✅ SVG marker loaded from cache: {svg_path}")
                return self.cached_markers[cache_key]
            
            # Load SVG content
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Process SVG based on configuration
            processed_svg = self._process_svg_marker(svg_content, config)
            
            # Cache the result
            self.cached_markers[cache_key] = processed_svg
            
            self.logger.info(f"✅ SVG marker loaded and processed: {svg_path}")
            return processed_svg
            
        except Exception as e:
            self.logger.error(f"❌ Error loading SVG marker {svg_path}: {e}")
            return None
    
    def _process_svg_marker(self, svg_content, config):
        """Process SVG content based on configuration"""
        
        try:
            # Parse SVG content
            import xml.etree.ElementTree as ET
            from io import StringIO
            
            # Parse SVG
            tree = ET.parse(StringIO(svg_content))
            root = tree.getroot()
            
            # Apply transformations based on config
            if config:
                # Apply scale
                if 'scale' in config and config['scale'] != 1.0:
                    self._apply_svg_scale(root, config['scale'])
                
                # Apply rotation
                if 'rotation' in config and config['rotation'] != 0:
                    self._apply_svg_rotation(root, config['rotation'])
                
                # Apply colorization
                if config.get('colorize', True) and 'color' in config:
                    self._apply_svg_color(root, config['color'])
            
            # Convert back to string
            processed_svg = ET.tostring(root, encoding='unicode')
            return processed_svg
            
        except Exception as e:
            self.logger.error(f"❌ Error processing SVG: {e}")
            return svg_content
    
    def _apply_svg_scale(self, root, scale):
        """Apply scale transformation to SVG root element"""
        
        try:
            # Get current viewBox or dimensions
            viewbox = root.get('viewBox')
            if viewbox:
                # Parse viewBox
                parts = viewbox.split()
                if len(parts) == 4:
                    x, y, width, height = map(float, parts)
                    # Scale viewBox
                    new_viewbox = f"{x} {y} {width * scale} {height * scale}"
                    root.set('viewBox', new_viewbox)
            
            # Scale width and height attributes
            if root.get('width'):
                current_width = float(root.get('width').replace('px', ''))
                root.set('width', f"{current_width * scale}px")
            
            if root.get('height'):
                current_height = float(root.get('height').replace('px', ''))
                root.set('height', f"{current_height * scale}px")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Could not apply scale transformation: {e}")
    
    def _apply_svg_rotation(self, root, rotation_degrees):
        """Apply rotation transformation to SVG root element"""
        
        try:
            # Get current transform
            current_transform = root.get('transform', '')
            
            # Calculate center for rotation
            viewbox = root.get('viewBox')
            if viewbox:
                parts = viewbox.split()
                if len(parts) == 4:
                    x, y, width, height = map(float, parts)
                    center_x = x + width / 2
                    center_y = y + height / 2
                    
                    # Create rotation transform
                    rotation_transform = f"rotate({rotation_degrees} {center_x} {center_y})"
                    
                    # Combine with existing transform
                    if current_transform:
                        new_transform = f"{current_transform} {rotation_transform}"
                    else:
                        new_transform = rotation_transform
                    
                    root.set('transform', new_transform)
                    
        except Exception as e:
            self.logger.warning(f"⚠️ Could not apply rotation transformation: {e}")
    
    def _apply_svg_color(self, root, color):
        """Apply color to SVG elements"""
        
        try:
            # Apply color to all path, circle, rect, and polygon elements
            for element in root.iter():
                tag = element.tag.split('}')[-1]  # Remove namespace
                
                if tag in ['path', 'circle', 'rect', 'polygon', 'ellipse']:
                    # Set fill color
                    element.set('fill', color)
                    
                    # Remove stroke if it exists and we want solid color
                    if element.get('stroke'):
                        element.attrib.pop('stroke')
                        
        except Exception as e:
            self.logger.warning(f"⚠️ Could not apply color transformation: {e}")
    
    def create_marker_from_svg(self, svg_path, output_path, config=None):
        """Create a processed marker file from SVG"""
        
        try:
            processed_svg = self.load_svg_marker(svg_path, config)
            
            if processed_svg:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(processed_svg)
                
                self.logger.info(f"✅ Processed SVG marker saved to: {output_path}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error creating marker from SVG: {e}")
            return False
    
    def clear_cache(self):
        """Clear the SVG marker cache"""
        
        self.cached_markers.clear()
        self.logger.info("✅ SVG marker cache cleared")
```

### 3. Backend Implementations

#### Matplotlib Backend
```python
    def _matplotlib_backend(self, data, config):
        """Generate map using Matplotlib backend"""
        
        try:
            # Create figure and axis
            fig, ax = plt.subplots(figsize=config['export']['size'])
            
            # Handle different data types
            if isinstance(data, pd.DataFrame):
                map_data = self._prepare_dataframe_for_mapping(data, config)
            elif isinstance(data, gpd.GeoDataFrame):
                map_data = data
            else:
                raise ValueError("Unsupported data type for matplotlib backend")
            
            # Apply map styling
            self._apply_matplotlib_styling(ax, config)
            
            # Plot data based on configuration
            if config['colors']['color_column'] and config['colors']['color_column'] in map_data.columns:
                # Color-coded plot
                scatter = ax.scatter(
                    map_data.geometry.x, 
                    map_data.geometry.y,
                    c=map_data[config['colors']['color_column']],
                    cmap=config['colors']['palette'],
                    s=config['markers']['size']**2,
                    alpha=config['colors']['alpha'],
                    edgecolors=config['markers']['edge_color'],
                    linewidth=config['markers']['edge_width']
                )
                
                # Add colorbar
                plt.colorbar(scatter, ax=ax, label=config['colors']['color_column'])
            else:
                # Check if using SVG markers
                if config['markers'].get('svg_path') or config['markers'].get('svg_markers'):
                    self._plot_svg_markers(ax, map_data, config)
                else:
                    # Single color plot with standard markers
                    ax.scatter(
                        map_data.geometry.x, 
                        map_data.geometry.y,
                        c=config['markers']['color'],
                        s=config['markers']['size']**2,
                        alpha=config['markers']['alpha'],
                        edgecolors=config['markers']['edge_color'],
                        linewidth=config['markers']['edge_width']
                    )
            
            # Add labels if enabled
            if config['labels']['show']:
                self._add_matplotlib_labels(ax, map_data, config)
            
            # Export map
            output_path = self._export_matplotlib_map(fig, config)
            
            return {
                'backend': 'matplotlib',
                'figure': fig,
                'output_path': output_path,
                'config': config
            }
            
        except Exception as e:
            self.logger.error(f"❌ Matplotlib backend failed: {e}")
            raise
    
    def _apply_matplotlib_styling(self, ax, config):
        """Apply styling to matplotlib axis"""
        
        # Set background
        if config['map_style']['background'] == 'dark':
            ax.set_facecolor('#2b2b2b')
            ax.grid(True, color=config['map_style']['grid_color'], alpha=config['map_style']['grid_alpha'])
        else:
            ax.set_facecolor('#ffffff')
            if config['map_style']['grid']:
                ax.grid(True, color=config['map_style']['grid_color'], alpha=config['map_style']['grid_alpha'])
        
        # Set boundary styling
        ax.spines['top'].set_color(config['map_style']['boundary_color'])
        ax.spines['bottom'].set_color(config['map_style']['boundary_color'])
        ax.spines['left'].set_color(config['map_style']['boundary_color'])
        ax.spines['right'].set_color(config['map_style']['boundary_color'])
        ax.spines['top'].set_linewidth(config['map_style']['boundary_width'])
        ax.spines['bottom'].set_linewidth(config['map_style']['boundary_width'])
        ax.spines['left'].set_linewidth(config['map_style']['boundary_width'])
        ax.spines['right'].set_linewidth(config['map_style']['boundary_width'])
    
    def _add_matplotlib_labels(self, ax, data, config):
        """Add labels to matplotlib plot"""
        
        for idx, row in data.iterrows():
            if 'name' in data.columns:
                ax.annotate(
                    row['name'],
                    (row.geometry.x, row.geometry.y),
                    xytext=config['labels']['offset'],
                    textcoords='offset points',
                    fontsize=config['labels']['font_size'],
                    color=config['labels']['font_color'],
                    weight=config['labels']['font_weight'],
                    rotation=config['labels']['rotation']
                )
    
    def _plot_svg_markers(self, ax, data, config):
        """Plot SVG markers on matplotlib axis"""
        
        try:
            import matplotlib.patches as patches
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            from matplotlib.transforms import Affine2D
            import matplotlib.image as mpimg
            from io import BytesIO
            import base64
            
            for idx, row in data.iterrows():
                # Get SVG marker configuration
                svg_config = self._get_svg_marker_config(config, row)
                
                if svg_config:
                    # Create SVG marker image
                    marker_img = self._create_svg_marker_image(svg_config, config)
                    
                    if marker_img:
                        # Create annotation box with SVG marker
                        imagebox = OffsetImage(
                            marker_img, 
                            zoom=config['markers'].get('svg_scale', 1.0),
                            alpha=config['markers'].get('alpha', 0.7)
                        )
                        
                        # Create annotation
                        ab = AnnotationBbox(
                            imagebox, 
                            (row.geometry.x, row.geometry.y),
                            frameon=False,
                            pad=0
                        )
                        
                        ax.add_artist(ab)
                        
        except Exception as e:
            self.logger.error(f"❌ Error plotting SVG markers: {e}")
            # Fallback to standard markers
            ax.scatter(
                data.geometry.x, 
                data.geometry.y,
                c=config['markers']['color'],
                s=config['markers']['size']**2,
                alpha=config['markers']['alpha'],
                edgecolors=config['markers']['edge_color'],
                linewidth=config['markers']['edge_width']
            )
    
    def _get_svg_marker_config(self, config, row):
        """Get SVG marker configuration for a specific data row"""
        
        # Check for custom SVG markers
        if config['markers'].get('svg_markers'):
            # Look for marker based on data attributes
            for marker_name, marker_info in config['markers']['svg_markers'].items():
                if 'condition' in marker_info:
                    # Apply condition to determine if this marker should be used
                    if self._evaluate_marker_condition(marker_info['condition'], row):
                        return marker_info
                else:
                    # Use default marker
                    return marker_info
        
        # Check for single SVG path
        if config['markers'].get('svg_path'):
            return {
                'path': config['markers']['svg_path'],
                'config': {
                    'scale': config['markers'].get('svg_scale', 1.0),
                    'rotation': config['markers'].get('svg_rotation', 0),
                    'colorize': config['markers'].get('svg_colorize', True),
                    'color': config['markers']['color']
                }
            }
        
        return None
    
    def _evaluate_marker_condition(self, condition, row):
        """Evaluate marker condition for a data row"""
        
        try:
            # Simple condition evaluation
            if isinstance(condition, dict):
                for field, value in condition.items():
                    if field in row and row[field] != value:
                        return False
                return True
            elif callable(condition):
                return condition(row)
            else:
                return True
        except Exception as e:
            self.logger.warning(f"⚠️ Error evaluating marker condition: {e}")
            return True
    
    def _create_svg_marker_image(self, svg_config, config):
        """Create matplotlib image from SVG marker"""
        
        try:
            import cairosvg
            from PIL import Image
            import numpy as np
            
            # Get SVG content
            if 'svg_data' in svg_config:
                svg_content = svg_config['svg_data']
            elif 'path' in svg_config:
                with open(svg_config['path'], 'r', encoding='utf-8') as f:
                    svg_content = f.read()
            else:
                return None
            
            # Convert SVG to PNG using cairosvg
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=config['markers'].get('svg_scale', 1.0) * 64,  # Base size 64px
                output_height=config['markers'].get('svg_scale', 1.0) * 64
            )
            
            # Convert PNG to PIL Image
            pil_image = Image.open(BytesIO(png_data))
            
            # Convert to numpy array for matplotlib
            img_array = np.array(pil_image)
            
            return img_array
            
        except ImportError:
            self.logger.warning("⚠️ cairosvg not available, falling back to standard markers")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error creating SVG marker image: {e}")
            return None

#### Export Method
```python
    def _export_matplotlib_map(self, fig, config):
        """Export matplotlib map to file"""
        
        export_config = config['export']
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        
        if export_config['format'] == 'png':
            output_path = f"map_{timestamp}.png"
            fig.savefig(
                output_path,
                dpi=export_config['dpi'],
                bbox_inches=export_config['bbox_inches'],
                transparent=export_config['transparent']
            )
        elif export_config['format'] == 'pdf':
            output_path = f"map_{timestamp}.pdf"
            fig.savefig(
                output_path,
                format='pdf',
                bbox_inches=export_config['bbox_inches'],
                transparent=export_config['transparent']
            )
        elif export_config['format'] == 'svg':
            output_path = f"map_{timestamp}.svg"
            fig.savefig(
                output_path,
                format='svg',
                bbox_inches=export_config['bbox_inches'],
                transparent=export_config['transparent']
            )
        
        self.logger.info(f"✅ Map exported to: {output_path}")
        return output_path
```

#### Folium Backend
```python
    def _folium_backend(self, data, config):
        """Generate map using Folium backend for interactive HTML maps"""
        
        try:
            # Create base map
            if config['map_style']['background'] == 'dark':
                tiles = 'CartoDB dark_matter'
            else:
                tiles = 'CartoDB positron'
            
            # Calculate center of data
            if isinstance(data, gpd.GeoDataFrame):
                center_lat = data.geometry.y.mean()
                center_lon = data.geometry.x.mean()
            else:
                center_lat, center_lon = 0, 0
            
            # Create map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles=tiles,
                control_scale=True
            )
            
            # Add data to map
            if isinstance(data, gpd.GeoDataFrame):
                self._add_folium_data(m, data, config)
            
            # Export map
            output_path = self._export_folium_map(m, config)
            
            return {
                'backend': 'folium',
                'map': m,
                'output_path': output_path,
                'config': config
            }
            
        except Exception as e:
            self.logger.error(f"❌ Folium backend failed: {e}")
            raise
    
    def _add_folium_data(self, m, data, config):
        """Add data to Folium map"""
        
        for idx, row in data.iterrows():
            # Create popup content
            popup_content = f"<b>{row.get('name', f'Point {idx}')}</b><br>"
            for col in data.columns:
                if col != 'geometry' and col != 'name':
                    popup_content += f"{col}: {row[col]}<br>"
            
            # Check if using SVG markers
            if config['markers'].get('svg_path') or config['markers'].get('svg_markers'):
                self._add_svg_marker_to_folium(m, row, config, popup_content)
            else:
                # Create standard marker
                if config['markers']['style'] == 'circle':
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=config['markers']['size'],
                        color=config['markers']['color'],
                        fill=True,
                        fillColor=config['markers']['color'],
                        fillOpacity=config['markers']['alpha'],
                        popup=popup_content
                    ).add_to(m)
                else:
                    folium.Marker(
                        location=[row.geometry.y, row.geometry.x],
                        popup=popup_content,
                        icon=folium.Icon(color=config['markers']['color'])
                    ).add_to(m)
    
    def _add_svg_marker_to_folium(self, m, row, config, popup_content):
        """Add SVG marker to Folium map"""
        
        try:
            # Get SVG marker configuration
            svg_config = self._get_svg_marker_config(config, row)
            
            if svg_config:
                # Create custom icon with SVG
                custom_icon = folium.CustomIcon(
                    icon_image=svg_config.get('svg_data', svg_config.get('path')),
                    icon_size=(config['markers'].get('svg_scale', 1.0) * 32, 
                              config['markers'].get('svg_scale', 1.0) * 32),
                    icon_anchor=(config['markers'].get('svg_scale', 1.0) * 16, 
                                config['markers'].get('svg_scale', 1.0) * 16)
                )
                
                # Add marker with custom icon
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    popup=popup_content,
                    icon=custom_icon
                ).add_to(m)
            else:
                # Fallback to standard marker
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    popup=popup_content,
                    icon=folium.Icon(color=config['markers']['color'])
                ).add_to(m)
                
        except Exception as e:
            self.logger.error(f"❌ Error adding SVG marker to Folium: {e}")
            # Fallback to standard marker
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                popup=popup_content,
                icon=folium.Icon(color=config['markers']['color'])
            ).add_to(m)
    
    def _export_folium_map(self, m, config):
        """Export Folium map to HTML file"""
        
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"interactive_map_{timestamp}.html"
        
        m.save(output_path)
        self.logger.info(f"✅ Interactive map exported to: {output_path}")
        return output_path
```

### 3. Advanced Configuration Options

#### Custom Marker and Color Schemes
```python
    def create_custom_marker_scheme(self, name, marker_config):
        """Create custom marker scheme"""
        
        valid_marker_config = {
            'style': marker_config.get('style', 'circle'),
            'color': marker_config.get('color', '#1f77b4'),
            'size': marker_config.get('size', 8),
            'alpha': marker_config.get('alpha', 0.7),
            'edge_color': marker_config.get('edge_color', '#000000'),
            'edge_width': marker_config.get('edge_width', 1),
            'symbols': marker_config.get('symbols', ['o', 's', '^', 'v'])
        }
        
        self.presets[name] = {
            'markers': valid_marker_config,
            'colors': self.default_config['colors'],
            'map_style': self.default_config['map_style'],
            'export': self.default_config['export']
        }
        
        self.logger.info(f"✅ Custom marker scheme '{name}' created")
        return valid_marker_config
    
    def create_custom_color_scheme(self, name, color_config):
        """Create custom color scheme"""
        
        valid_color_config = {
            'palette': color_config.get('palette', 'viridis'),
            'scheme': color_config.get('scheme', 'sequential'),
            'custom_colors': color_config.get('custom_colors', []),
            'color_column': color_config.get('color_column'),
            'color_range': color_config.get('color_range'),
            'alpha': color_config.get('alpha', 0.8)
        }
        
        if name not in self.presets:
            self.presets[name] = self.default_config.copy()
        
        self.presets[name]['colors'] = valid_color_config
        self.logger.info(f"✅ Custom color scheme '{name}' created")
        return valid_color_config
```

### 4. Usage Examples

#### Generate Professional Map
```python
def generate_professional_map():
    """Generate a professional-looking map using preset configuration"""
    
    try:
        print("🗺️ Generating Professional Map")
        print("=" * 40)
        
        # Sample data
        sample_data = {
            'name': ['Office A', 'Office B', 'Office C', 'Office D'],
            'geometry': [
                'POINT(-122.4194 37.7749)',
                'POINT(-74.0060 40.7128)',
                'POINT(-87.6298 41.8781)',
                'POINT(-118.2437 34.0522)'
            ],
            'employees': [150, 200, 120, 180],
            'revenue': [5000000, 7500000, 3000000, 6000000]
        }
        
        df = pd.DataFrame(sample_data)
        
        # Convert to GeoDataFrame
        from shapely.wkt import loads
        df['geometry'] = df['geometry'].apply(loads)
        gdf = gpd.GeoDataFrame(df, crs='EPSG:4326')
        
        # Initialize map generator
        map_gen = ConfigurableMapGenerator()
        
        # Generate map with professional preset
        map_result = map_gen.generate_map(gdf, preset='professional')
        
        print(f"✅ Professional map generated successfully")
        print(f"📁 Output file: {map_result['output_path']}")
        print(f"🔧 Backend used: {map_result['backend']}")
        
        return map_result
        
    except Exception as e:
        print(f"❌ Professional map generation failed: {e}")
        return None

# Generate professional map
professional_map = generate_professional_map()
```

#### Generate Custom Interactive Map
```python
def generate_custom_interactive_map():
    """Generate a custom interactive map with specific configuration"""
    
    try:
        print("\n🎨 Generating Custom Interactive Map")
        print("=" * 40)
        
        # Sample data
        sample_data = {
            'city': ['San Francisco', 'New York', 'Chicago', 'Los Angeles'],
            'geometry': [
                'POINT(-122.4194 37.7749)',
                'POINT(-74.0060 40.7128)',
                'POINT(-87.6298 41.8781)',
                'POINT(-118.2437 34.0522)'
            ],
            'population': [873965, 8336817, 2693976, 3979576],
            'avg_temp': [14.2, 12.9, 9.8, 18.6]
        }
        
        df = pd.DataFrame(sample_data)
        
        # Convert to GeoDataFrame
        from shapely.wkt import loads
        df['geometry'] = df['geometry'].apply(loads)
        gdf = gpd.GeoDataFrame(df, crs='EPSG:4326')
        
        # Custom configuration
        custom_config = {
            'markers': {
                'style': 'star',
                'color': '#FF6B6B',
                'size': 15,
                'alpha': 0.9
            },
            'colors': {
                'palette': 'plasma',
                'scheme': 'sequential',
                'color_column': 'population'
            },
            'map_style': {
                'background': 'dark',
                'grid': True
            },
            'export': {
                'format': 'html',
                'size': (1400, 900)
            },
            'backend': 'folium'
        }
        
        # Initialize map generator
        map_gen = ConfigurableMapGenerator()
        
        # Generate custom map
        map_result = map_gen.generate_map(gdf, config=custom_config)
        
        print(f"✅ Custom interactive map generated successfully")
        print(f"📁 Output file: {map_result['output_path']}")
        print(f"🔧 Backend used: {map_result['backend']}")
        print(f"🎨 Marker style: {custom_config['markers']['style']}")
        print(f"🌈 Color palette: {custom_config['colors']['palette']}")
        
        return map_result
        
    except Exception as e:
        print(f"❌ Custom map generation failed: {e}")
        return None

# Generate custom interactive map
custom_map = generate_custom_interactive_map()
```

#### Generate Map with Custom SVG Markers
```python
def generate_svg_marker_map():
    """Generate a map using custom SVG markers"""
    
    try:
        print("\n🎨 Generating Map with Custom SVG Markers")
        print("=" * 50)
        
        # Sample data
        sample_data = {
            'name': ['Office A', 'Store B', 'Warehouse C', 'Factory D'],
            'geometry': [
                'POINT(-122.4194 37.7749)',
                'POINT(-74.0060 40.7128)',
                'POINT(-87.6298 41.8781)',
                'POINT(-118.2437 34.0522)'
            ],
            'type': ['office', 'store', 'warehouse', 'factory'],
            'employees': [150, 25, 80, 200]
        }
        
        df = pd.DataFrame(sample_data)
        
        # Convert to GeoDataFrame
        from shapely.wkt import loads
        df['geometry'] = df['geometry'].apply(loads)
        gdf = gpd.GeoDataFrame(df, crs='EPSG:4326')
        
        # Initialize map generator
        map_gen = ConfigurableMapGenerator()
        
        # Add custom SVG markers
        map_gen.add_svg_marker('office', 'markers/office_icon.svg', {
            'scale': 1.2,
            'colorize': True,
            'color': '#2E86AB'
        })
        
        map_gen.add_svg_marker('store', 'markers/store_icon.svg', {
            'scale': 1.0,
            'colorize': True,
            'color': '#FF6B6B'
        })
        
        map_gen.add_svg_marker('warehouse', 'markers/warehouse_icon.svg', {
            'scale': 1.5,
            'colorize': True,
            'color': '#4ECDC4'
        })
        
        map_gen.add_svg_marker('factory', 'markers/factory_icon.svg', {
            'scale': 1.3,
            'colorize': True,
            'color': '#45B7D1'
        })
        
        # Configuration with SVG markers
        svg_config = {
            'markers': {
                'svg_markers': {
                    'office': {'condition': {'type': 'office'}},
                    'store': {'condition': {'type': 'store'}},
                    'warehouse': {'condition': {'type': 'warehouse'}},
                    'factory': {'condition': {'type': 'factory'}}
                },
                'svg_scale': 1.0,
                'svg_colorize': True
            },
            'colors': {
                'palette': 'viridis',
                'scheme': 'categorical'
            },
            'map_style': {
                'background': 'light',
                'grid': True
            },
            'export': {
                'format': 'png',
                'size': (1400, 900),
                'resolution': 300
            },
            'backend': 'matplotlib'
        }
        
        # Generate map with SVG markers
        map_result = map_gen.generate_map(gdf, config=svg_config)
        
        print(f"✅ SVG marker map generated successfully")
        print(f"📁 Output file: {map_result['output_path']}")
        print(f"🔧 Backend used: {map_result['backend']}")
        print(f"🎨 SVG markers: {map_gen.list_svg_markers()}")
        
        return map_result
        
    except Exception as e:
        print(f"❌ SVG marker map generation failed: {e}")
        return None

# Generate SVG marker map
svg_marker_map = generate_svg_marker_map()
```

#### Create and Process SVG Markers
```python
def demonstrate_svg_marker_processing():
    """Demonstrate SVG marker processing capabilities"""
    
    try:
        print("\n🔧 SVG Marker Processing Demo")
        print("=" * 40)
        
        # Initialize SVG marker manager
        svg_manager = SVGMarkerManager()
        
        # Process an SVG marker with transformations
        svg_config = {
            'scale': 1.5,
            'rotation': 45,
            'colorize': True,
            'color': '#FF6B6B'
        }
        
        # Load and process SVG marker
        processed_svg = svg_manager.load_svg_marker('markers/custom_icon.svg', svg_config)
        
        if processed_svg:
            print(f"✅ SVG marker processed successfully")
            print(f"📏 Applied scale: {svg_config['scale']}x")
            print(f"🔄 Applied rotation: {svg_config['rotation']}°")
            print(f"🎨 Applied color: {svg_config['color']}")
            
            # Save processed marker
            output_path = 'markers/processed_icon.svg'
            svg_manager.create_marker_from_svg('markers/custom_icon.svg', output_path, svg_config)
            
            return processed_svg
        else:
            print(f"❌ Failed to process SVG marker")
            return None
            
    except Exception as e:
        print(f"❌ SVG marker processing failed: {e}")
        return None

# Demonstrate SVG marker processing
svg_processing_demo = demonstrate_svg_marker_processing()
```

## Configuration Options

### Marker Configuration
```yaml
markers:
  # Marker styles
  style: "circle"  # circle, square, triangle, diamond, star, cross
  
  # Visual properties
  color: "#1f77b4"
  size: 8
  alpha: 0.7
  edge_color: "#000000"
  edge_width: 1
  
  # Symbol options
  symbols: ["o", "s", "^", "v", "<", ">", "D", "p"]
  
  # SVG marker support
  svg_path: null  # Path to custom SVG marker file
  svg_scale: 1.0  # Scale factor for SVG markers
  svg_rotation: 0  # Rotation angle for SVG markers
  svg_colorize: true  # Whether to apply color to SVG markers
  
  # Custom SVG marker definitions
  svg_markers:
    office: 
      path: "markers/office_icon.svg"
      condition: {"type": "office"}
      scale: 1.2
      color: "#2E86AB"
    store:
      path: "markers/store_icon.svg"
      condition: {"type": "store"}
      scale: 1.0
      color: "#FF6B6B"
    warehouse:
      path: "markers/warehouse_icon.svg"
      condition: {"type": "warehouse"}
      scale: 1.5
      color: "#4ECDC4"
```

### Color Configuration
```yaml
colors:
  # Color palettes
  palette: "viridis"  # viridis, plasma, inferno, magma, Blues, Reds, Greens
  
  # Color schemes
  scheme: "sequential"  # sequential, diverging, categorical
  
  # Custom colors
  custom_colors: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
  
  # Color mapping
  color_column: "population"
  color_range: [0, 1000000]
  
  # Transparency
  alpha: 0.8
```

### Export Configuration
```yaml
export:
  # Output formats
  format: "png"  # png, svg, pdf, html, jpg, tiff
  
  # Image properties
  resolution: 300
  size: [1200, 800]
  dpi: 100
  
  # Output options
  transparent: false
  bbox_inches: "tight"
  
  # HTML-specific
  include_legend: true
  include_controls: true
```

## Expected Output

```
🗺️ Generating Professional Map
========================================
✅ Professional map generated successfully
📁 Output file: map_20240214_143022.pdf
🔧 Backend used: matplotlib

🎨 Generating Custom Interactive Map
========================================
✅ Custom interactive map generated successfully
📁 Output file: interactive_map_20240214_143025.html
🔧 Backend used: folium
🎨 Marker style: star
🌈 Color palette: plasma

🎨 Generating Map with Custom SVG Markers
==================================================
✅ SVG marker map generated successfully
📁 Output file: map_20240214_143030.png
🔧 Backend used: matplotlib
🎨 SVG markers: ['office', 'store', 'warehouse', 'factory']

🔧 SVG Marker Processing Demo
========================================
✅ SVG marker processed successfully
📏 Applied scale: 1.5x
🔄 Applied rotation: 45°
🎨 Applied color: #FF6B6B
✅ Processed SVG marker saved to: markers/processed_icon.svg
```

## Next Steps

After mastering configurable map generation with SVG markers:

- **Advanced SVG Processing**: Create complex SVG transformations and animations
- **Custom Icon Libraries**: Build comprehensive icon libraries for different use cases
- **Interactive SVG Markers**: Add click events and hover effects to SVG markers
- **3D SVG Markers**: Extend to 3D SVG marker support
- **Real-time SVG Updates**: Implement dynamic SVG marker updates

## Related Recipes

- **[3D Mapping](3D-Mapping)** - Create 3D visualizations and terrain models
- **[Geocoding](Geocoding)** - Convert addresses to coordinates for mapping
- **[Database Connections](Database-Connections)** - Connect to spatial databases
- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate map-based reports