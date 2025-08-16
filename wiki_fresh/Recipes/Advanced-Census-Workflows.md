# Advanced Census Workflows with Siege Utilities

This recipe demonstrates how to combine the enhanced Census utilities with other Siege Utilities functions to create powerful, end-to-end spatial data workflows.

## 🎯 Overview

Learn how to integrate Census data with:
- **File operations** for data management
- **Spatial transformations** for format conversion
- **Reporting tools** for visualization
- **Analytics integration** for business intelligence
- **Multi-engine processing** for large datasets

## 🚀 Prerequisites

```bash
pip install siege-utilities[geo,analytics,reporting]
```

## 📊 Workflow 1: Multi-State Census Analysis

### Step 1: Discover and Download Data

```python
from siege_utilities.geo.spatial_data import census_source
from siege_utilities.files import ensure_path_exists, get_download_directory
from siege_utilities.core.logging import setup_logging
import geopandas as gpd
import pandas as pd

# Setup logging
setup_logging(level='INFO')

# Get available data
years = census_source.discovery.get_available_years()
print(f"Available Census years: {years}")

# Get state information
state_info = census_source.get_comprehensive_state_info()
target_states = ['06', '48', '36']  # CA, TX, NY

# Download county boundaries for multiple states
counties_data = {}
for state_fips in target_states:
    state_name = state_info[state_fips]['name']
    print(f"Downloading {state_name} counties...")
    
    counties = census_source.get_geographic_boundaries(
        year=2020,
        geographic_level='county',
        state_fips=state_fips
    )
    
    if counties is not None:
        counties_data[state_fips] = counties
        print(f"✓ Downloaded {len(counties)} counties for {state_name}")
    else:
        print(f"✗ Failed to download {state_name} counties")
```

### Step 2: Data Processing and Analysis

```python
# Combine all counties into one dataset
all_counties = []
for state_fips, counties in counties_data.items():
    state_name = state_info[state_fips]['name']
    counties['STATE_NAME'] = state_name
    counties['STATE_FIPS'] = state_fips
    all_counties.append(counties)

combined_counties = pd.concat(all_counties, ignore_index=True)

# Basic statistics
print(f"Total counties: {len(combined_counties)}")
print(f"States represented: {combined_counties['STATE_NAME'].nunique()}")
print(f"Total area: {combined_counties.geometry.area.sum():.2f} square units")

# Calculate county centroids for analysis
combined_counties['centroid'] = combined_counties.geometry.centroid
combined_counties['centroid_lon'] = combined_counties['centroid'].x
combined_counties['centroid_lat'] = combined_counties['centroid'].y
```

### Step 3: Export and Visualization

```python
from siege_utilities.files import ensure_path_exists
from siege_utilities.reporting.chart_generator import ChartGenerator

# Create output directory
output_dir = get_download_directory() / "census_analysis"
ensure_path_exists(output_dir)

# Export to multiple formats
combined_counties.to_file(output_dir / "multi_state_counties.geojson", driver='GeoJSON')
combined_counties.drop(columns='geometry').to_csv(output_dir / "multi_state_counties.csv", index=False)

# Create visualization
chart_gen = ChartGenerator()

# Generate a map showing the three states
chart_config = {
    'title': 'Multi-State County Analysis',
    'subtitle': 'California, Texas, and New York Counties',
    'data': combined_counties,
    'geometry_column': 'geometry',
    'color_column': 'STATE_NAME',
    'output_file': output_dir / "multi_state_map.png"
}

chart_gen.create_choropleth_map(chart_config)
print(f"✓ Analysis complete! Results saved to {output_dir}")
```

## 🗺️ Workflow 2: Congressional District Analysis with Demographics

### Step 1: Download Congressional Districts

```python
# Get available boundary types for 2020
boundary_types = census_source.get_available_boundary_types(2020)
print(f"Available boundary types: {list(boundary_types.keys())}")

# Download congressional districts
congressional_districts = census_source.get_geographic_boundaries(
    year=2020,
    geographic_level='cd118'  # 118th Congress
)

if congressional_districts is not None:
    print(f"✓ Downloaded {len(congressional_districts)} congressional districts")
    
    # Basic district information
    print("\nDistrict information:")
    print(f"States represented: {congressional_districts['STATEFP'].nunique()}")
    print(f"Districts per state:")
    state_district_counts = congressional_districts.groupby('STATEFP').size()
    for state_fips, count in state_district_counts.items():
        state_name = census_source.get_state_name(state_fips)
        print(f"  {state_name}: {count} districts")
```

### Step 2: Integrate with Analytics Data

```python
from siege_utilities.analytics.facebook_business import FacebookBusinessAPI
from siege_utilities.analytics.google_analytics import GoogleAnalyticsAPI

# Example: Get Facebook audience data for districts
# (This would require valid API credentials)
try:
    fb_api = FacebookBusinessAPI()
    
    # Get audience insights for each district
    district_insights = {}
    for idx, district in congressional_districts.head(5).iterrows():  # Sample first 5
        district_name = district['NAMELSAD']
        centroid = district.geometry.centroid
        
        # Get audience insights for district area
        insights = fb_api.get_audience_insights(
            latitude=centroid.y,
            longitude=centroid.x,
            radius_km=50
        )
        
        if insights:
            district_insights[district_name] = insights
            print(f"✓ Got insights for {district_name}")
    
except Exception as e:
    print(f"Facebook API not available: {e}")
    # Continue with other analysis
```

### Step 3: Advanced Spatial Analysis

```python
from siege_utilities.geo.spatial_transformations import SpatialTransformer
import numpy as np

# Create spatial transformer
transformer = SpatialTransformer()

# Calculate district characteristics
congressional_districts['area_sq_km'] = congressional_districts.geometry.area * 111 * 111  # Rough conversion
congressional_districts['perimeter_km'] = congressional_districts.geometry.length * 111

# Find districts with unusual characteristics
large_districts = congressional_districts[congressional_districts['area_sq_km'] > 
                                        congressional_districts['area_sq_km'].quantile(0.9)]

print(f"\nLargest districts by area:")
for idx, district in large_districts.iterrows():
    state_name = census_source.get_state_name(district['STATEFP'])
    print(f"  {district['NAMELSAD']} ({state_name}): {district['area_sq_km']:.1f} sq km")

# Calculate compactness (isoperimetric ratio)
congressional_districts['compactness'] = (4 * np.pi * congressional_districts['area_sq_km']) / \
                                        (congressional_districts['perimeter_km'] ** 2)

print(f"\nMost compact districts:")
compact_districts = congressional_districts.nlargest(5, 'compactness')
for idx, district in compact_districts.iterrows():
    state_name = census_source.get_state_name(district['STATEFP'])
    print(f"  {district['NAMELSAD']} ({state_name}): {district['compactness']:.3f}")
```

## 🔄 Workflow 3: Batch Processing with Spark

### Step 1: Setup Spark Environment

```python
from siege_utilities.distributed.spark_utils import SparkManager
from siege_utilities.distributed.multi_engine import MultiEngineProcessor

# Initialize Spark
spark_manager = SparkManager()
spark = spark_manager.get_spark_session()

# Create multi-engine processor
processor = MultiEngineProcessor()
```

### Step 2: Batch Download and Process

```python
# Define batch processing parameters
years_to_process = [2010, 2020]
boundary_types_to_process = ['county', 'tract', 'block_group']
target_states = ['06', '48']  # CA, TX

# Batch download function
def download_boundaries_batch(year, boundary_type, state_fips):
    try:
        boundaries = census_source.get_geographic_boundaries(
            year=year,
            geographic_level=boundary_type,
            state_fips=state_fips
        )
        
        if boundaries is not None:
            # Convert to Spark DataFrame
            spark_df = processor.geodataframe_to_spark(boundaries)
            return spark_df
        else:
            return None
    except Exception as e:
        print(f"Error downloading {year}-{boundary_type}-{state_fips}: {e}")
        return None

# Process in batches
all_data = {}
for year in years_to_process:
    for boundary_type in boundary_types_to_process:
        for state_fips in target_states:
            print(f"Processing {year}-{boundary_type}-{state_fips}")
            
            spark_df = download_boundaries_batch(year, boundary_type, state_fips)
            if spark_df is not None:
                key = f"{year}_{boundary_type}_{state_fips}"
                all_data[key] = spark_df
                
                # Basic analysis
                count = spark_df.count()
                print(f"  ✓ {count} features loaded")
                
                # Cache for performance
                spark_df.cache()
```

### Step 3: Spark Analysis

```python
# Combine all data for analysis
if all_data:
    # Union all DataFrames
    combined_df = None
    for key, df in all_data.items():
        if combined_df is None:
            combined_df = df
        else:
            combined_df = combined_df.union(df)
    
    # Perform analysis
    print(f"\nCombined analysis:")
    total_features = combined_df.count()
    print(f"Total features: {total_features}")
    
    # Group by year and boundary type
    summary = combined_df.groupBy("YEAR", "BOUNDARY_TYPE").count()
    summary.show()
    
    # Spatial analysis (if using GeoSpark)
    try:
        from pyspark.sql.functions import expr
        
        # Calculate area for each feature
        area_df = combined_df.withColumn(
            "area_sq_km", 
            expr("ST_Area(geometry) * 111 * 111")
        )
        
        # Show area statistics
        area_stats = area_df.select("area_sq_km").summary()
        area_stats.show()
        
    except Exception as e:
        print(f"Spatial analysis not available: {e}")
```

## 📈 Workflow 4: Reporting and Visualization

### Step 1: Generate Comprehensive Report

```python
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.chart_types import ChartType

# Initialize report generator
report_gen = ReportGenerator()

# Create report with Census analysis
report_config = {
    'title': 'Census Data Analysis Report',
    'subtitle': 'Multi-state Geographic Analysis',
    'sections': [
        {
            'title': 'Data Summary',
            'content': f"""
            - Total counties analyzed: {len(combined_counties)}
            - States included: {', '.join([state_info[fips]['name'] for fips in target_states])}
            - Data year: 2020
            - Boundary types: County, Tract, Block Group
            """
        },
        {
            'title': 'Geographic Statistics',
            'content': f"""
            - Total area: {combined_counties.geometry.area.sum():.2f} square units
            - Average county area: {combined_counties.geometry.area.mean():.2f} square units
            - Largest county: {combined_counties.loc[combined_counties.geometry.area.idxmax(), 'NAMELSAD']}
            """
        }
    ],
    'charts': [
        {
            'type': ChartType.CHOROPLETH,
            'data': combined_counties,
            'title': 'Multi-State County Map',
            'geometry_column': 'geometry',
            'color_column': 'STATE_NAME'
        }
    ]
}

# Generate report
report_file = output_dir / "census_analysis_report.pdf"
report_gen.generate_report(report_config, report_file)
print(f"✓ Report generated: {report_file}")
```

### Step 2: Interactive Dashboard

```python
try:
    import folium
    from folium.plugins import MarkerCluster
    
    # Create interactive map
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)
    
    # Add county boundaries
    for idx, county in combined_counties.iterrows():
        folium.GeoJson(
            county.geometry,
            name=county['NAMELSAD'],
            popup=f"<b>{county['NAMELSAD']}</b><br>State: {county['STATE_NAME']}<br>Area: {county.geometry.area:.2f}",
            style_function=lambda x: {'fillColor': 'blue', 'color': 'black', 'weight': 1, 'fillOpacity': 0.3}
        ).add_to(m)
    
    # Save interactive map
    map_file = output_dir / "interactive_census_map.html"
    m.save(map_file)
    print(f"✓ Interactive map created: {map_file}")
    
except ImportError:
    print("Folium not available for interactive maps")
```

## 🔧 Advanced Configuration

### Custom Download Directory

```python
from siege_utilities.config import update_user_config

# Set custom download directory
update_user_config({
    'download_directory': '/path/to/custom/census/data',
    'cache_timeout': 7200,  # 2 hours
    'max_retries': 3
})
```

### Error Handling and Retry Logic

```python
import time
from functools import wraps

def retry_on_failure(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Apply retry logic to download function
@retry_on_failure(max_attempts=3, delay=2)
def robust_download(year, boundary_type, state_fips=None):
    return census_source.get_geographic_boundaries(year, boundary_type, state_fips)
```

## 📊 Performance Optimization

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def download_parallel(years, boundary_types, state_fips_list):
    """Download multiple datasets in parallel"""
    results = {}
    
    def download_single(params):
        year, boundary_type, state_fips = params
        key = f"{year}_{boundary_type}_{state_fips}"
        
        try:
            data = census_source.get_geographic_boundaries(year, boundary_type, state_fips)
            return key, data
        except Exception as e:
            return key, None
    
    # Create parameter combinations
    params_list = []
    for year in years:
        for boundary_type in boundary_types:
            for state_fips in state_fips_list:
                params_list.append((year, boundary_type, state_fips))
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_params = {executor.submit(download_single, params): params 
                           for params in params_list}
        
        for future in as_completed(future_to_params):
            key, data = future.result()
            results[key] = data
            print(f"Completed: {key}")
    
    return results

# Example usage
parallel_results = download_parallel(
    years=[2020],
    boundary_types=['county', 'tract'],
    state_fips_list=['06', '48']
)
```

## 🧪 Testing Your Workflows

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch

def test_census_workflow():
    """Test the complete Census workflow"""
    with patch('siege_utilities.geo.spatial_data.census_source') as mock_census:
        # Mock the download method
        mock_census.get_geographic_boundaries.return_value = Mock()
        
        # Test workflow
        result = download_boundaries_batch(2020, 'county', '06')
        assert result is not None

# Run tests
if __name__ == "__main__":
    pytest.main([__file__])
```

## 🚀 Next Steps

1. **Explore More Boundary Types**: Try different Census boundary types like `place`, `zcta`, or `cd`
2. **Integrate with External APIs**: Connect Census data with other data sources
3. **Build Custom Visualizations**: Create specialized maps and charts for your use case
4. **Scale Up**: Use Spark for processing larger datasets
5. **Automate Workflows**: Schedule regular data updates and analysis

## 🔗 Related Recipes

- [Enhanced Census Utilities](Enhanced-Census-Utilities.md) - Core Census functionality
- [Spatial Transformations](Spatial-Transformations.md) - Data format conversion
- [Analytics Integration](Analytics-Integration.md) - Third-party data integration
- [Comprehensive Reporting](Comprehensive-Reporting.md) - Report generation
- [Spark Processing](Spark-Processing.md) - Distributed processing

---

**This recipe demonstrates the power of combining multiple Siege Utilities functions for comprehensive spatial data workflows. The enhanced Census utilities provide the foundation, while other utilities add data management, analysis, and visualization capabilities.**
