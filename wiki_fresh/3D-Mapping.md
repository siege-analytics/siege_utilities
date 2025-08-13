# 3D Mapping Recipe

## Overview
This recipe demonstrates how to use the 3D mapping utilities in `siege_utilities` for creating interactive 3D visualizations, terrain models, building models, and spatial data representations in three dimensions.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Basic understanding of 3D graphics and spatial data
- Required dependencies: `plotly`, `numpy`, `pandas`, `geopandas`, `pyproj`, `rasterio`

## Installation
```bash
pip install siege_utilities
pip install plotly numpy pandas geopandas pyproj rasterio
```

## Basic 3D Mapping Setup

### 1. Initialize 3D Mapping Engine

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.geo.spatial_data import SpatialDataProcessor
from siege_utilities.reporting.chart_types import ChartTypes

# Initialize 3D mapping components
chart_generator = ChartGenerator()
spatial_processor = SpatialDataProcessor()

# Set up 3D mapping configuration
map_config = {
    "projection": "EPSG:4326",  # WGS84
    "center_lat": 40.7589,      # Default center (NYC)
    "center_lon": -73.9851,
    "zoom_level": 10,
    "map_style": "satellite",    # or "streets", "outdoors", "light"
    "height": 800,
    "width": 1200
}
```

### 2. Basic 3D Terrain Map

```python
# Create basic 3D terrain map
def create_3d_terrain_map(center_lat, center_lon, zoom_level=10):
    """Create a basic 3D terrain visualization"""
    
    # Generate terrain data around the center point
    terrain_data = spatial_processor.generate_terrain_data(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=50,
        resolution_m=100
    )
    
    # Create 3D surface plot
    terrain_map = chart_generator.create_3d_surface(
        data=terrain_data,
        x_column="longitude",
        y_column="latitude", 
        z_column="elevation",
        title="3D Terrain Map",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        zaxis_title="Elevation (meters)"
    )
    
    return terrain_map

# Create terrain map for NYC area
nyc_terrain = create_3d_terrain_map(40.7589, -73.9851, 12)
nyc_terrain.show()
```

### 3. 3D Building and City Model

```python
# Create 3D city model with buildings
def create_3d_city_model(city_data, building_heights):
    """Create 3D city model with building heights"""
    
    # Process building data
    buildings_3d = spatial_processor.process_building_data(
        city_data,
        height_data=building_heights,
        include_textures=True
    )
    
    # Create 3D building visualization
    city_model = chart_generator.create_3d_scatter(
        data=buildings_3d,
        x_column="longitude",
        y_column="latitude",
        z_column="height",
        size_column="area",
        color_column="building_type",
        title="3D City Model",
        xaxis_title="Longitude",
        yaxis_title="Latitude", 
        zaxis_title="Height (meters)"
    )
    
    return city_model

# Example city data
city_buildings = [
    {"longitude": -73.9851, "latitude": 40.7589, "height": 443, "area": 1000, "building_type": "skyscraper"},
    {"longitude": -73.9857, "latitude": 40.7484, "height": 381, "area": 800, "building_type": "office"},
    {"longitude": -73.9934, "latitude": 40.7505, "height": 262, "area": 600, "building_type": "residential"}
]

nyc_city_model = create_3d_city_model(city_buildings, None)
nyc_city_model.show()
```

## Advanced 3D Mapping Features

### 1. Interactive 3D Maps with Plotly

```python
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def create_interactive_3d_map(geospatial_data, map_type="terrain"):
    """Create interactive 3D map with multiple visualization options"""
    
    if map_type == "terrain":
        # Create 3D terrain surface
        fig = go.Figure(data=[go.Surface(
            x=geospatial_data['longitude'],
            y=geospatial_data['latitude'],
            z=geospatial_data['elevation'],
            colorscale='terrain',
            showscale=True,
            colorbar=dict(title="Elevation (m)")
        )])
        
    elif map_type == "buildings":
        # Create 3D building visualization
        fig = go.Figure(data=[go.Scatter3d(
            x=geospatial_data['longitude'],
            y=geospatial_data['latitude'],
            z=geospatial_data['height'],
            mode='markers',
            marker=dict(
                size=geospatial_data['area'] / 100,
                color=geospatial_data['height'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Height (m)")
            ),
            text=geospatial_data['building_name'],
            hovertemplate="<b>%{text}</b><br>" +
                         "Height: %{z}m<br>" +
                         "Area: %{marker.size}m²<br>" +
                         "<extra></extra>"
        )])
    
    # Update layout for 3D
    fig.update_layout(
        title=f"Interactive 3D {map_type.title()} Map",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Elevation/Height (m)",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1200,
        height=800
    )
    
    return fig

# Create interactive terrain map
terrain_data = spatial_processor.generate_sample_terrain_data()
interactive_terrain = create_interactive_3d_map(terrain_data, "terrain")
interactive_terrain.show()
```

### 2. 3D Choropleth Maps

```python
def create_3d_choropleth_map(geojson_data, value_column, title="3D Choropleth Map"):
    """Create 3D choropleth map with extruded polygons"""
    
    # Process GeoJSON data for 3D visualization
    processed_data = spatial_processor.process_geojson_for_3d(
        geojson_data,
        value_column=value_column,
        extrusion_height=1000  # Base height for 3D effect
    )
    
    # Create 3D choropleth
    fig = go.Figure()
    
    for feature in processed_data['features']:
        # Extract polygon coordinates
        coords = feature['geometry']['coordinates'][0]
        lons = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        
        # Create 3D polygon
        fig.add_trace(go.Mesh3d(
            x=lons,
            y=lats,
            z=[feature['properties']['height']] * len(lons),
            i=[0, 0, 0, 0],
            j=[1, 2, 3, 4],
            k=[2, 3, 4, 1],
            intensity=feature['properties']['value'],
            colorscale='Viridis',
            showscale=True,
            name=feature['properties']['name']
        ))
    
    # Update layout
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Value",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1200,
        height=800
    )
    
    return fig

# Example: Create 3D population density map
population_data = spatial_processor.load_sample_population_data()
population_3d_map = create_3d_choropleth_map(
    population_data,
    "population_density",
    "3D Population Density Map"
)
population_3d_map.show()
```

### 3. 3D Time Series Maps

```python
def create_3d_time_series_map(spatial_data, time_column, value_column):
    """Create 3D map showing changes over time"""
    
    # Process temporal spatial data
    temporal_data = spatial_processor.process_temporal_spatial_data(
        spatial_data,
        time_column=time_column,
        value_column=value_column
    )
    
    # Create 3D time series visualization
    fig = go.Figure()
    
    # Add traces for each time period
    for time_period in temporal_data['time_periods']:
        period_data = temporal_data['data'][time_period]
        
        fig.add_trace(go.Scatter3d(
            x=period_data['longitude'],
            y=period_data['latitude'],
            z=[time_period] * len(period_data['longitude']),
            mode='markers',
            marker=dict(
                size=period_data[value_column] / 100,
                color=period_data[value_column],
                colorscale='Viridis',
                showscale=True
            ),
            name=f"Time: {time_period}",
            hovertemplate=f"<b>Time: {time_period}</b><br>" +
                         f"{value_column}: %{{marker.color}}<br>" +
                         "<extra></extra>"
        ))
    
    # Update layout
    fig.update_layout(
        title="3D Time Series Map",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude", 
            zaxis_title="Time",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1200,
        height=800
    )
    
    return fig

# Example: Create 3D temperature change map
temperature_data = spatial_processor.load_sample_temperature_data()
temperature_3d_map = create_3d_time_series_map(
    temperature_data,
    "year",
    "temperature_change"
)
temperature_3d_map.show()
```

## Specialized 3D Mapping Applications

### 1. 3D Geological Maps

```python
def create_3d_geological_map(geological_data, rock_types):
    """Create 3D geological map with different rock layers"""
    
    # Process geological data for 3D visualization
    processed_geo = spatial_processor.process_geological_data(
        geological_data,
        rock_types=rock_types,
        layer_depth=1000
    )
    
    # Create 3D geological visualization
    fig = go.Figure()
    
    for rock_type in rock_types:
        type_data = processed_geo[rock_type]
        
        fig.add_trace(go.Surface(
            x=type_data['longitude'],
            y=type_data['latitude'],
            z=type_data['depth'],
            colorscale=type_data['color_scheme'],
            showscale=True,
            name=rock_type,
            opacity=0.8
        ))
    
    # Update layout
    fig.update_layout(
        title="3D Geological Map",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Depth (m)",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1200,
        height=800
    )
    
    return fig

# Example geological data
geological_data = spatial_processor.load_sample_geological_data()
rock_types = ["sedimentary", "igneous", "metamorphic"]
geological_3d_map = create_3d_geological_map(geological_data, rock_types)
geological_3d_map.show()
```

### 2. 3D Environmental Maps

```python
def create_3d_environmental_map(environmental_data, parameter):
    """Create 3D environmental parameter map"""
    
    # Process environmental data
    processed_env = spatial_processor.process_environmental_data(
        environmental_data,
        parameter=parameter,
        interpolation_method="kriging"
    )
    
    # Create 3D environmental visualization
    fig = go.Figure(data=[go.Surface(
        x=processed_env['longitude'],
        y=processed_env['latitude'],
        z=processed_env[parameter],
        colorscale='RdYlBu_r',  # Red to Blue scale
        showscale=True,
        colorbar=dict(title=f"{parameter.title()}"),
        hovertemplate=f"<b>{parameter.title()}</b><br>" +
                      "Longitude: %{x}<br>" +
                      "Latitude: %{y}<br>" +
                      f"{parameter.title()}: %{{z}}<br>" +
                      "<extra></extra>"
    )])
    
    # Update layout
    fig.update_layout(
        title=f"3D {parameter.title()} Map",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title=parameter.title(),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1200,
        height=800
    )
    
    return fig

# Example: Create 3D air quality map
air_quality_data = spatial_processor.load_sample_air_quality_data()
air_quality_3d_map = create_3d_environmental_map(air_quality_data, "pm25")
air_quality_3d_map.show()
```

### 3. 3D Transportation Networks

```python
def create_3d_transportation_map(transport_data, network_type):
    """Create 3D transportation network map"""
    
    # Process transportation network data
    processed_transport = spatial_processor.process_transportation_data(
        transport_data,
        network_type=network_type,
        include_elevation=True
    )
    
    # Create 3D transportation visualization
    fig = go.Figure()
    
    # Add network lines
    for route in processed_transport['routes']:
        fig.add_trace(go.Scatter3d(
            x=route['longitude'],
            y=route['latitude'],
            z=route['elevation'],
            mode='lines',
            line=dict(
                color=route['color'],
                width=route['width']
            ),
            name=route['name'],
            hovertemplate=f"<b>{route['name']}</b><br>" +
                         "Type: {network_type}<br>" +
                         "<extra></extra>"
        ))
    
    # Add nodes/stations
    for node in processed_transport['nodes']:
        fig.add_trace(go.Scatter3d(
            x=[node['longitude']],
            y=[node['latitude']],
            z=[node['elevation']],
            mode='markers',
            marker=dict(
                size=node['size'],
                color=node['color'],
                symbol='diamond'
            ),
            name=node['name'],
            hovertemplate=f"<b>{node['name']}</b><br>" +
                         "Type: {node['type']}<br>" +
                         "<extra></extra>"
        ))
    
    # Update layout
    fig.update_layout(
        title=f"3D {network_type.title()} Network Map",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Elevation (m)",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1200,
        height=800
    )
    
    return fig

# Example: Create 3D subway network map
subway_data = spatial_processor.load_sample_subway_data()
subway_3d_map = create_3d_transportation_map(subway_data, "subway")
subway_3d_map.show()
```

## Performance Optimization

### 1. Large Dataset Handling

```python
def create_optimized_3d_map(large_spatial_data, optimization_level="medium"):
    """Create 3D map optimized for large datasets"""
    
    # Apply data reduction based on optimization level
    if optimization_level == "high":
        reduced_data = spatial_processor.reduce_large_dataset(
            large_spatial_data,
            target_points=10000,
            method="uniform_sampling"
        )
    elif optimization_level == "medium":
        reduced_data = spatial_processor.reduce_large_dataset(
            large_spatial_data,
            target_points=50000,
            method="adaptive_sampling"
        )
    else:
        reduced_data = large_spatial_data
    
    # Create optimized 3D visualization
    fig = go.Figure(data=[go.Scatter3d(
        x=reduced_data['longitude'],
        y=reduced_data['latitude'],
        z=reduced_data['value'],
        mode='markers',
        marker=dict(
            size=3,
            color=reduced_data['value'],
            colorscale='Viridis',
            showscale=True
        )
    )])
    
    # Update layout
    fig.update_layout(
        title="Optimized 3D Map",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Value"
        ),
        width=1200,
        height=800
    )
    
    return fig

# Example: Create optimized map for large dataset
large_dataset = spatial_processor.load_large_spatial_dataset()
optimized_3d_map = create_optimized_3d_map(large_dataset, "high")
optimized_3d_map.show()
```

### 2. Real-time 3D Mapping

```python
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

def create_real_time_3d_map():
    """Create real-time 3D map with Dash"""
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Real-time 3D Map"),
        dcc.Graph(id='3d-map'),
        dcc.Interval(
            id='interval-component',
            interval=5*1000,  # Update every 5 seconds
            n_intervals=0
        )
    ])
    
    @app.callback(
        Output('3d-map', 'figure'),
        Input('interval-component', 'n_intervals')
    )
    def update_3d_map(n):
        # Get real-time data
        real_time_data = spatial_processor.get_real_time_spatial_data()
        
        # Create 3D visualization
        fig = go.Figure(data=[go.Scatter3d(
            x=real_time_data['longitude'],
            y=real_time_data['latitude'],
            z=real_time_data['value'],
            mode='markers',
            marker=dict(
                size=5,
                color=real_time_data['value'],
                colorscale='Viridis',
                showscale=True
            )
        )])
        
        fig.update_layout(
            title="Real-time 3D Map",
            scene=dict(
                xaxis_title="Longitude",
                yaxis_title="Latitude",
                zaxis_title="Value"
            ),
            width=1200,
            height=800
        )
        
        return fig
    
    return app

# Start real-time 3D map
real_time_app = create_real_time_3d_map()
real_time_app.run_server(debug=True)
```

## Integration Examples

### 1. With Data Processing Pipeline

```python
def create_3d_mapping_pipeline(data_source, output_format="html"):
    """Complete 3D mapping pipeline from data to visualization"""
    
    # 1. Load and preprocess data
    raw_data = spatial_processor.load_spatial_data(data_source)
    processed_data = spatial_processor.preprocess_spatial_data(raw_data)
    
    # 2. Generate 3D visualization
    if processed_data['type'] == 'terrain':
        map_3d = create_3d_terrain_map(
            processed_data['center_lat'],
            processed_data['center_lon']
        )
    elif processed_data['type'] == 'buildings':
        map_3d = create_3d_city_model(
            processed_data['buildings'],
            processed_data['heights']
        )
    elif processed_data['type'] == 'environmental':
        map_3d = create_3d_environmental_map(
            processed_data['data'],
            processed_data['parameter']
        )
    
    # 3. Export in specified format
    if output_format == "html":
        map_3d.write_html("3d_map.html")
    elif output_format == "png":
        map_3d.write_image("3d_map.png")
    elif output_format == "pdf":
        map_3d.write_image("3d_map.pdf")
    
    return map_3d

# Use the pipeline
pipeline_result = create_3d_mapping_pipeline(
    "data/nyc_spatial_data.geojson",
    output_format="html"
)
```

### 2. With Reporting System

```python
from siege_utilities.reporting.report_generator import ReportGenerator

def create_3d_mapping_report(spatial_data, report_config):
    """Create comprehensive report with 3D maps"""
    
    # Initialize report generator
    report_gen = ReportGenerator()
    
    # Create 3D visualizations
    terrain_map = create_3d_terrain_map(
        spatial_data['center_lat'],
        spatial_data['center_lon']
    )
    
    building_map = create_3d_city_model(
        spatial_data['buildings'],
        spatial_data['heights']
    )
    
    # Add to report
    report_gen.add_section("3D Terrain Analysis")
    report_gen.add_chart(terrain_map, "3D Terrain Visualization")
    
    report_gen.add_section("3D Building Analysis")
    report_gen.add_chart(building_map, "3D Building Model")
    
    # Generate report
    report_path = report_gen.generate_report(
        title="3D Spatial Analysis Report",
        output_format="pdf"
    )
    
    return report_path

# Create 3D mapping report
report_config = {
    "include_summary": True,
    "include_analysis": True,
    "output_format": "pdf"
}

report_path = create_3d_mapping_report(spatial_data, report_config)
print(f"Report generated: {report_path}")
```

## Best Practices

### 1. Data Preparation
- Ensure spatial data is properly projected and aligned
- Clean and validate coordinates before 3D visualization
- Use appropriate data reduction for large datasets
- Implement proper error handling for missing or invalid data

### 2. Visualization Design
- Choose appropriate color schemes for data types
- Use consistent axis labels and scales
- Implement proper camera positioning for optimal viewing
- Add interactive elements for better user experience

### 3. Performance
- Optimize large datasets with sampling techniques
- Use appropriate visualization types for data size
- Implement lazy loading for real-time applications
- Cache processed data when possible

### 4. Accessibility
- Provide alternative 2D views when possible
- Include proper titles and descriptions
- Use colorblind-friendly color schemes
- Ensure keyboard navigation support

## Troubleshooting

### Common Issues

1. **Memory Issues with Large Datasets**
   ```python
   # Use data reduction
   reduced_data = spatial_processor.reduce_large_dataset(
       large_data,
       target_points=10000
   )
   ```

2. **Slow Rendering**
   ```python
   # Optimize visualization settings
   fig.update_layout(
       uirevision=True,  # Preserve zoom/pan state
       showlegend=False  # Hide legend for performance
   )
   ```

3. **Coordinate System Mismatches**
   ```python
   # Ensure proper projection
   spatial_processor.reproject_data(
       data,
       from_crs="EPSG:4326",
       to_crs="EPSG:3857"
   )
   ```

## Conclusion

The 3D mapping utilities in `siege_utilities` provide comprehensive tools for creating advanced three-dimensional spatial visualizations. By following this recipe, you can:

- Create interactive 3D terrain and building models
- Generate 3D choropleth and time series maps
- Build specialized geological and environmental visualizations
- Implement real-time 3D mapping applications
- Integrate 3D maps into comprehensive reporting systems

Remember to always optimize for performance with large datasets, use appropriate visualization types for your data, and follow accessibility best practices for inclusive user experiences.
