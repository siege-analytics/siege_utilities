# 🗺️ Mapping & Visualization

<div align="center">

**Comprehensive Geographic Data Visualization with 7+ Map Types**

![Mapping System](https://img.shields.io/badge/Mapping%20System-7%2B%20Map%20Types-green?style=for-the-badge&logo=map)

</div>

---

## 🎯 **Overview**

The Siege Utilities mapping system provides **enterprise-grade geographic visualization** capabilities that go far beyond basic mapping. With support for 7+ map types, advanced classification methods, and professional styling, you can create publication-quality geographic insights for any business need.

---

## 🚀 **Quick Start**

### **Installation**
```bash
pip install -r siege_utilities/reporting/requirements_bivariate_choropleth.txt
```

### **Basic Example**
```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize chart generator
chart_gen = ChartGenerator()

# Sample data
data = {
    'state': ['California', 'Texas', 'New York', 'Florida'],
    'population': [39512223, 28995881, 19453561, 21477737],
    'income': [75235, 64034, 72741, 59227]
}
df = pd.DataFrame(data)

# Create bivariate choropleth
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=df,
    location_column='state',
    value_column1='population',
    value_column2='income',
    title="Population vs Income by State"
)
```

---

## 🗺️ **Map Types Reference**

### **1. 🌈 Bivariate Choropleth Maps**

**Purpose**: Show relationships between two variables across geographic regions

**Methods**:
- `create_bivariate_choropleth()` - Folium-based interactive maps
- `create_bivariate_choropleth_matplotlib()` - Matplotlib-based static maps

**Example**:
```python
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=regional_data,
    geodata=geodataframe,
    location_column='region',
    value_column1='market_penetration',
    value_column2='customer_satisfaction',
    title="Market Performance Analysis",
    width=12.0,
    height=10.0,
    color_scheme='custom'
)
```

**Use Cases**:
- Market penetration vs. customer satisfaction
- Population density vs. median income
- Sales performance vs. market potential
- Economic indicators vs. social metrics

---

### **2. 📍 Marker Maps**

**Purpose**: Visualize point locations with customizable markers and popups

**Method**: `create_marker_map()`

**Example**:
```python
marker_map = chart_gen.create_marker_map(
    data=cities_data,
    latitude_column='latitude',
    longitude_column='longitude',
    value_column='population',
    label_column='city',
    title="US Cities Population Map",
    map_style='cartodb-positron',
    zoom_level=10
)
```

**Features**:
- **Size encoding**: Marker size based on quantitative values
- **Interactive popups**: Detailed information on click
- **Multiple tile styles**: OpenStreetMap, CartoDB, Stamen
- **Zoom control**: Configurable initial zoom levels

**Use Cases**:
- Store locations and performance
- Customer distribution analysis
- Event locations and attendance
- Asset tracking and management

---

### **3. 🏔️ 3D Maps**

**Purpose**: Three-dimensional visualization of elevation and height data

**Method**: `create_3d_map()`

**Example**:
```python
elevation_map = chart_gen.create_3d_map(
    data=cities_data,
    latitude_column='latitude',
    longitude_column='longitude',
    elevation_column='elevation',
    title="City Elevation 3D Visualization",
    view_angle=45,
    elevation_scale=1.0
)
```

**Features**:
- **3D surface plotting**: For large datasets using triangulation
- **Scatter plotting**: For smaller datasets with individual points
- **Customizable viewing angles**: Adjustable 3D perspective
- **Terrain color schemes**: Professional elevation visualization

**Use Cases**:
- Geographic elevation analysis
- Urban planning and development
- Environmental impact assessment
- Infrastructure planning

---

### **4. 🔥 Heatmap Maps**

**Purpose**: Density and intensity visualization across geographic areas

**Method**: `create_heatmap_map()`

**Example**:
```python
heatmap = chart_gen.create_heatmap_map(
    data=cities_data,
    latitude_column='latitude',
    longitude_column='longitude',
    value_column='population',
    title="Population Density Heatmap",
    grid_size=50,
    blur_radius=0.5
)
```

**Features**:
- **Configurable grid sizes**: Adjustable resolution
- **Blur radius control**: Smoothing and visual appeal
- **Gradient color schemes**: Blue to red intensity mapping
- **Interactive zoom levels**: Geographic exploration

**Use Cases**:
- Population density analysis
- Crime hotspot mapping
- Traffic pattern visualization
- Resource concentration analysis

---

### **5. 🔗 Cluster Maps**

**Purpose**: Group dense point data into interactive clusters

**Method**: `create_cluster_map()`

**Example**:
```python
cluster_map = chart_gen.create_cluster_map(
    data=cities_data,
    latitude_column='latitude',
    longitude_column='longitude',
    cluster_column='region',
    label_column='city',
    title="City Clusters by Region",
    max_cluster_radius=80
)
```

**Features**:
- **Automatic clustering**: Intelligent grouping of nearby points
- **Configurable radius**: Adjustable cluster boundaries
- **Interactive expansion**: Click to expand clusters
- **Professional styling**: Consistent with brand guidelines

**Use Cases**:
- High-density location data
- Regional analysis and grouping
- Customer segmentation mapping
- Asset clustering analysis

---

### **6. 🌊 Flow Maps**

**Purpose**: Visualize movement and connections between locations

**Method**: `create_flow_map()`

**Example**:
```python
flow_map = chart_gen.create_flow_map(
    data=migration_data,
    origin_lat_column='origin_lat',
    origin_lon_column='origin_lon',
    dest_lat_column='dest_lat',
    dest_lon_column='dest_lon',
    flow_value_column='migration_volume',
    title="Migration Flows Between Cities"
)
```

**Features**:
- **Origin-destination flows**: Clear movement visualization
- **Weighted line thickness**: Flow intensity encoding
- **Geographic routing**: Direct connections between points
- **Interactive elements**: Click for flow details

**Use Cases**:
- Migration pattern analysis
- Supply chain visualization
- Transportation route mapping
- Trade flow analysis

---

### **7. 🎨 Advanced Choropleth Maps**

**Purpose**: Sophisticated choropleth mapping with multiple classification options

**Method**: `create_advanced_choropleth()`

**Example**:
```python
advanced_choropleth = chart_gen.create_advanced_choropleth(
    data=regional_data,
    geodata=geodataframe,
    location_column='region',
    value_column='gdp_growth',
    title="GDP Growth by Region (Natural Breaks)",
    classification='natural_breaks',
    bins=7,
    color_scheme='RdYlGn'
)
```

**Classification Methods**:
- **Quantiles**: Equal number of observations per bin
- **Equal Interval**: Equal width bins across data range
- **Natural Breaks**: Statistical grouping based on data distribution

**Use Cases**:
- Economic indicator mapping
- Demographic analysis
- Performance metric visualization
- Policy impact assessment

---

## 🎨 **Advanced Features**

### **Color Schemes**

**Built-in Palettes**:
- `YlOrRd`: Yellow to Orange to Red (sequential)
- `RdYlGn`: Red to Yellow to Green (diverging)
- `Set3`: Qualitative color palette
- `custom`: User-defined color schemes

**Custom Color Creation**:
```python
# Create custom color palette
custom_colors = ['#e8e8e8', '#e4acac', '#c85a5a', '#9c2929', '#67001f']

chart = chart_gen.create_bivariate_choropleth_matplotlib(
    # ... other parameters ...
    color_scheme='custom'
)
```

### **Classification Methods**

**Statistical Classification**:
```python
# Natural breaks classification
chart = chart_gen.create_advanced_choropleth(
    data=data,
    classification='natural_breaks',
    bins=7
)

# Quantile classification
chart = chart_gen.create_advanced_choropleth(
    data=data,
    classification='quantiles',
    bins=5
)
```

### **Interactive Features**

**Folium-based Maps**:
- **Zoom controls**: Pan and zoom functionality
- **Layer controls**: Toggle different map layers
- **Interactive popups**: Click for detailed information
- **Custom markers**: Branded and styled markers

**Matplotlib Maps**:
- **High resolution**: Publication-quality output
- **Custom styling**: Professional appearance
- **Legend customization**: Clear and informative legends
- **Export options**: Multiple file formats

---

## 🔧 **Technical Implementation**

### **Data Requirements**

**Geographic Data**:
- **GeoJSON files**: Standard geographic boundary format
- **Shapefiles**: ESRI shapefile format support
- **GeoPandas DataFrames**: Python geographic data structures
- **Coordinate systems**: WGS84 and other projections

**Business Data**:
- **Pandas DataFrames**: Standard Python data format
- **CSV files**: Comma-separated value imports
- **Database queries**: Direct database connectivity
- **API responses**: External data source integration

### **Performance Optimization**

**Large Dataset Handling**:
```python
# Data sampling for large datasets
sampled_data = large_dataset.sample(n=10000, random_state=42)

# Aggregation for performance
aggregated_data = large_dataset.groupby('region').agg({
    'population': 'sum',
    'income': 'mean'
}).reset_index()
```

**Memory Management**:
- **Efficient data types**: Use appropriate numeric types
- **Chunked processing**: Process data in manageable chunks
- **Caching**: Cache frequently used geographic boundaries
- **Cleanup**: Proper memory cleanup after processing

---

## 📊 **Integration Examples**

### **Google Analytics Integration**

```python
from siege_utilities.analytics.google_analytics import GoogleAnalyticsConnector

# Initialize connector
ga_connector = GoogleAnalyticsConnector(
    credentials_path='credentials.json',
    property_id='your_property_id'
)

# Retrieve geographic data
ga_data = ga_connector.batch_retrieve_ga_data(
    metrics=['sessions', 'bounce_rate'],
    dimensions=['country', 'region'],
    date_range=['2023-01-01', '2023-12-31']
)

# Create geographic visualization
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=ga_data,
    location_column='region',
    value_column1='sessions',
    value_column2='bounce_rate'
)
```

### **Database Integration**

```python
from siege_utilities.config.databases import DatabaseConnector

# Initialize database connector
db_connector = DatabaseConnector(
    connection_string='postgresql://user:password@localhost/dbname'
)

# Query customer data
customer_data = db_connector.execute_query("""
    SELECT state, COUNT(*) as customers, AVG(revenue) as avg_revenue
    FROM customers GROUP BY state
""")

# Create customer analysis map
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=customer_data,
    location_column='state',
    value_column1='customers',
    value_column2='avg_revenue'
)
```

---

## 🎯 **Best Practices**

### **Data Preparation**

1. **Clean Data**: Remove duplicates and handle missing values
2. **Coordinate Systems**: Ensure consistent geographic projections
3. **Data Types**: Use appropriate numeric and string types
4. **Validation**: Verify geographic identifier matches

### **Map Design**

1. **Color Schemes**: Choose appropriate palettes for data characteristics
2. **Legend Design**: Clear and informative legends
3. **Title and Labels**: Descriptive and concise
4. **Scale and Projection**: Appropriate for geographic scope

### **Performance Optimization**

1. **Data Sampling**: Use sampling for large datasets
2. **Caching**: Cache frequently used geographic data
3. **Parallel Processing**: Use multi-core processing when available
4. **Memory Management**: Optimize data structures

---

## 🚨 **Troubleshooting**

### **Common Issues**

**"GeoPandas not available"**:
```bash
pip install geopandas shapely
```

**"Location column not found"**:
```python
# Check column names
print(df.columns.tolist())

# Ensure exact match
location_column = 'state'  # Must match exactly
```

**"No numeric data found"**:
```python
# Check data types
print(df.dtypes)

# Convert to numeric
df['value'] = pd.to_numeric(df['value'], errors='coerce')
```

### **Performance Issues**

**Large Datasets**:
```python
# Use data aggregation
aggregated = df.groupby('region').agg({
    'metric': 'mean'
}).reset_index()

# Sample data for testing
sample = df.sample(n=1000, random_state=42)
```

**Memory Issues**:
```python
# Clear memory after processing
import gc
gc.collect()

# Use smaller data types
df['value'] = df['value'].astype('float32')
```

---

## 📚 **Additional Resources**

- **[Report Generation](Report-Generation)**: Create professional reports with your maps
- **[Integration & APIs](Integration-and-APIs)**: Connect with external data sources
- **[Recipes & Examples](Recipes-and-Examples)**: Step-by-step implementation guides
- **[API Reference](https://siege-analytics.github.io/siege_utilities/)**: Complete method documentation

---

<div align="center">

**Ready to create professional geographic visualizations?**

[📄 Create Reports](Report-Generation) • [🔌 Integrate APIs](Integration-and-APIs) • [📖 View Examples](Recipes-and-Examples)

---

*Transform your data into geographic insights with Siege Utilities* 🗺️✨

</div>
