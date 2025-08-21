# Complete Demographic Analysis Pipeline

This recipe demonstrates a full end-to-end demographic analysis workflow using real Census data, from data discovery to interactive visualization and reporting.

## 🎯 **Overview**

Build a comprehensive demographic analysis system that:
- Discovers and downloads Census demographic data
- Integrates with external data sources
- Performs spatial analysis and statistical modeling
- Creates interactive visualizations
- Generates professional reports
- Stores results in multiple formats

## 🚀 **Prerequisites**

```bash
pip install siege-utilities[geo,analytics,reporting,spatial]
pip install plotly dash folium seaborn scikit-learn
```

## 📊 **Sample Datasets We'll Use**

### **Primary Data Sources**
1. **Census TIGER/Line Boundaries**: County, tract, and block group boundaries
2. **Census Demographic Data**: Population, age, income, education statistics
3. **OpenStreetMap**: Points of interest, transportation networks
4. **Government Open Data**: Additional demographic and economic indicators

### **External Data Integration**
- **Facebook Business API**: Audience insights for geographic areas
- **Google Analytics**: Web traffic patterns by location
- **Data.world**: Additional demographic datasets
- **Snowflake**: Store and query large datasets

## 🔄 **Complete Workflow**

### **Step 1: Data Discovery and Planning**

```python
from siege_utilities.geo.spatial_data import census_source
from siege_utilities.analytics import search_datadotworld_datasets
from siege_utilities.core.logging import setup_logging
import pandas as pd
import geopandas as gpd

# Setup logging
setup_logging(level='INFO')

# Define analysis scope
target_states = ['06', '48', '36']  # CA, TX, NY
state_names = {fips: census_source.get_state_name(fips) for fips in target_states}
print(f"Target states: {[state_names[fips] for fips in target_states]}")

# Discover available Census data
years = census_source.discovery.get_available_years()
print(f"Available Census years: {years}")

# Choose optimal year for analysis
analysis_year = census_source.discovery.get_optimal_year(2020, 'county')
print(f"Using Census year: {analysis_year}")

# Get available boundary types
boundary_types = census_source.get_available_boundary_types(analysis_year)
print(f"Available boundary types: {list(boundary_types.keys())}")
```

### **Step 2: Download Geographic Boundaries**

```python
from siege_utilities.files import ensure_path_exists, get_download_directory
import time

# Create data directory structure
data_dir = get_download_directory() / "demographic_analysis" / str(analysis_year)
ensure_path_exists(data_dir)

# Download boundaries for each state
boundaries_data = {}
for state_fips in target_states:
    state_name = state_names[state_fips]
    print(f"\nProcessing {state_name}...")
    
    # Download county boundaries
    counties = census_source.get_geographic_boundaries(
        year=analysis_year,
        geographic_level='county',
        state_fips=state_fips
    )
    
    if counties is not None:
        # Download tract boundaries
        tracts = census_source.get_geographic_boundaries(
            year=analysis_year,
            geographic_level='tract',
            state_fips=state_fips
        )
        
        # Download block group boundaries
        block_groups = census_source.get_geographic_boundaries(
            year=analysis_year,
            geographic_level='block_group',
            state_fips=state_fips
        )
        
        boundaries_data[state_fips] = {
            'counties': counties,
            'tracts': tracts,
            'block_groups': block_groups,
            'name': state_name
        }
        
        print(f"✓ {state_name}: {len(counties)} counties, {len(tracts)} tracts, {len(block_groups)} block groups")
        
        # Save to files
        counties.to_file(data_dir / f"{state_fips}_counties.geojson", driver='GeoJSON')
        tracts.to_file(data_dir / f"{state_fips}_tracts.geojson", driver='GeoJSON')
        block_groups.to_file(data_dir / f"{state_fips}_block_groups.geojson", driver='GeoJSON')
    
    # Rate limiting to be respectful to Census servers
    time.sleep(1)
```

### **Step 3: Download Demographic Data**

```python
import requests
from pathlib import Path

def download_census_demographics(year, state_fips, geography_level):
    """Download Census demographic data for a specific geography level."""
    
    # Census API endpoints for demographic data
    base_url = "https://api.census.gov/data"
    
    # Variables we want to collect
    variables = [
        'B01003_001E',  # Total population
        'B01001_002E',  # Male population
        'B01001_026E',  # Female population
        'B19013_001E',  # Median household income
        'B15003_022E',  # Bachelor's degree
        'B15003_023E',  # Master's degree
        'B15003_024E',  # Professional degree
        'B15003_025E',  # Doctorate degree
        'B08303_001E',  # Commute time
        'B25077_001E'   # Median home value
    ]
    
    # Construct API URL
    if geography_level == 'county':
        url = f"{base_url}/{year}/acs/acs5"
        params = {
            'get': ','.join(variables),
            'for': f'county:*&in=state:{state_fips}',
            'key': 'DEMO_KEY'  # Replace with your Census API key
        }
    elif geography_level == 'tract':
        url = f"{base_url}/{year}/acs/acs5"
        params = {
            'get': ','.join(variables),
            'for': f'tract:*&in=state:{state_fips}',
            'key': 'DEMO_KEY'
        }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Parse CSV response
        data = response.text.strip().split('\n')
        headers = data[0].split(',')
        rows = [row.split(',') for row in data[1:]]
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        # Clean column names
        df.columns = [col.strip('"') for col in df.columns]
        
        return df
        
    except Exception as e:
        print(f"Error downloading demographics for {state_fips} {geography_level}: {e}")
        return None

# Download demographic data for each state
demographics_data = {}
for state_fips in target_states:
    state_name = state_names[state_fips]
    print(f"\nDownloading demographics for {state_name}...")
    
    state_demographics = {}
    
    # Download county demographics
    county_demo = download_census_demographics(analysis_year, state_fips, 'county')
    if county_demo is not None:
        state_demographics['counties'] = county_demo
        county_demo.to_csv(data_dir / f"{state_fips}_county_demographics.csv", index=False)
    
    # Download tract demographics
    tract_demo = download_census_demographics(analysis_year, state_fips, 'tract')
    if tract_demo is not None:
        state_demographics['tracts'] = tract_demo
        tract_demo.to_csv(data_dir / f"{state_fips}_tract_demographics.csv", index=False)
    
    demographics_data[state_fips] = state_demographics
    print(f"✓ Downloaded demographics for {state_name}")
```

### **Step 4: Data Integration and Enrichment**

```python
from siege_utilities.analytics import search_datadotworld_datasets, load_datadotworld_dataset
from siege_utilities.geo.spatial_transformations import SpatialTransformer

# Search for additional demographic datasets on data.world
print("\nSearching for additional demographic datasets...")
additional_datasets = search_datadotworld_datasets(
    query="demographics population income education",
    limit=10
)

# Load relevant datasets
enrichment_data = {}
for dataset in additional_datasets[:3]:  # Load first 3 relevant datasets
    try:
        dataset_id = dataset['id']
        print(f"Loading dataset: {dataset['title']}")
        
        df = load_datadotworld_dataset(dataset_id)
        if df is not None:
            enrichment_data[dataset_id] = {
                'data': df,
                'title': dataset['title'],
                'description': dataset['description']
            }
            print(f"✓ Loaded {len(df)} rows from {dataset['title']}")
    
    except Exception as e:
        print(f"Failed to load dataset {dataset['id']}: {e}")

# Integrate data using spatial transformations
transformer = SpatialTransformer()

# Combine boundaries and demographics
integrated_data = {}
for state_fips in target_states:
    state_name = state_names[state_fips]
    print(f"\nIntegrating data for {state_name}...")
    
    # Get boundaries
    counties = boundaries_data[state_fips]['counties']
    tracts = boundaries_data[state_fips]['tracts']
    
    # Get demographics
    county_demo = demographics_data[state_fips].get('counties')
    tract_demo = demographics_data[state_fips].get('tracts')
    
    if county_demo is not None and counties is not None:
        # Merge county boundaries with demographics
        county_integrated = counties.merge(
            county_demo,
            left_on=['STATEFP', 'COUNTYFP'],
            right_on=['state', 'county'],
            how='left'
        )
        
        # Calculate additional metrics
        county_integrated['population_density'] = (
            county_integrated['B01003_001E'].astype(float) / 
            county_integrated.geometry.area
        )
        
        county_integrated['education_rate'] = (
            (county_integrated['B15003_022E'].astype(float) +
             county_integrated['B15003_023E'].astype(float) +
             county_integrated['B15003_024E'].astype(float) +
             county_integrated['B15003_025E'].astype(float)) /
            county_integrated['B01003_001E'].astype(float) * 100
        )
        
        integrated_data[f"{state_fips}_counties"] = county_integrated
    
    if tract_demo is not None and tracts is not None:
        # Similar integration for tracts
        tract_integrated = tracts.merge(
            tract_demo,
            left_on=['STATEFP', 'COUNTYFP', 'TRACTCE'],
            right_on=['state', 'county', 'tract'],
            how='left'
        )
        
        integrated_data[f"{state_fips}_tracts"] = tract_integrated

print(f"\n✓ Integrated data for {len(integrated_data)} geographic levels")
```

### **Step 5: Advanced Spatial Analysis**

```python
import numpy as np
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def perform_spatial_analysis(geodataframe, analysis_type='clustering'):
    """Perform advanced spatial analysis on geographic data."""
    
    if analysis_type == 'clustering':
        # Prepare data for clustering
        numeric_cols = ['B01003_001E', 'B19013_001E', 'B25077_001E', 'education_rate']
        analysis_data = geodataframe[numeric_cols].fillna(0)
        
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(analysis_data)
        
        # Perform K-means clustering
        kmeans = KMeans(n_clusters=5, random_state=42)
        clusters = kmeans.fit_predict(scaled_data)
        
        geodataframe['cluster'] = clusters
        
        # Calculate cluster characteristics
        cluster_stats = geodataframe.groupby('cluster')[numeric_cols].agg(['mean', 'std'])
        
        return geodataframe, cluster_stats
    
    elif analysis_type == 'hotspot':
        # Calculate local spatial autocorrelation (Moran's I)
        from libpysal.weights import W
        from esda.moran import Moran
        
        # Create spatial weights matrix
        w = W.from_geodataframe(geodataframe)
        
        # Calculate Moran's I for population density
        population_density = geodataframe['population_density'].fillna(0)
        moran = Moran(population_density, w)
        
        geodataframe['moran_i'] = moran.I
        geodataframe['moran_p'] = moran.p_norm
        
        return geodataframe, {'moran_i': moran.I, 'p_value': moran.p_norm}
    
    return geodataframe, None

# Perform spatial analysis on each integrated dataset
analysis_results = {}
for key, data in integrated_data.items():
    print(f"\nPerforming spatial analysis on {key}...")
    
    # Clustering analysis
    clustered_data, cluster_stats = perform_spatial_analysis(data, 'clustering')
    
    # Hotspot analysis
    hotspot_data, hotspot_stats = perform_spatial_analysis(clustered_data, 'hotspot')
    
    analysis_results[key] = {
        'data': hotspot_data,
        'cluster_stats': cluster_stats,
        'hotspot_stats': hotspot_stats
    }
    
    print(f"✓ Completed analysis for {key}")
    if cluster_stats is not None:
        print(f"  Clusters: {len(cluster_stats)}")
    if hotspot_stats is not None:
        print(f"  Moran's I: {hotspot_stats['moran_i']:.3f}")

# Save analysis results
for key, result in analysis_results.items():
    result['data'].to_file(data_dir / f"{key}_analyzed.geojson", driver='GeoJSON')
    print(f"✓ Saved analyzed data: {key}")
```

### **Step 6: Interactive Visualization Dashboard**

```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import folium
from folium.plugins import MarkerCluster

def create_interactive_dashboard(analysis_results):
    """Create an interactive Dash dashboard for demographic analysis."""
    
    app = dash.Dash(__name__)
    
    # Prepare data for visualization
    all_counties = []
    for key, result in analysis_results.items():
        if 'counties' in key:
            all_counties.append(result['data'])
    
    if all_counties:
        combined_counties = pd.concat(all_counties, ignore_index=True)
        
        # Create dashboard layout
        app.layout = html.Div([
            html.H1("Demographic Analysis Dashboard", 
                    style={'textAlign': 'center', 'color': '#2c3e50'}),
            
            html.Div([
                html.H3("Geographic Distribution"),
                dcc.Graph(
                    id='map-plot',
                    figure=px.choropleth(
                        combined_counties,
                        geojson=combined_counties.geometry.__geo_interface__,
                        locations=combined_counties.index,
                        color='cluster',
                        hover_data=['NAMELSAD', 'B01003_001E', 'B19013_001E'],
                        title="Demographic Clusters by County"
                    )
                )
            ]),
            
            html.Div([
                html.H3("Population vs. Income Analysis"),
                dcc.Graph(
                    id='scatter-plot',
                    figure=px.scatter(
                        combined_counties,
                        x='B19013_001E',
                        y='B01003_001E',
                        color='cluster',
                        size='education_rate',
                        hover_data=['NAMELSAD'],
                        title="Population vs. Median Income (Size = Education Rate)"
                    )
                )
            ]),
            
            html.Div([
                html.H3("Education Distribution"),
                dcc.Graph(
                    id='histogram-plot',
                    figure=px.histogram(
                        combined_counties,
                        x='education_rate',
                        color='cluster',
                        title="Distribution of Education Rates by Cluster"
                    )
                )
            ])
        ])
    
    return app

# Create and run dashboard
dashboard = create_interactive_dashboard(analysis_results)
print("✓ Interactive dashboard created")

# Save dashboard as HTML
dashboard.layout.children[0].children[1].figure.write_html(
    data_dir / "demographic_dashboard.html"
)
print("✓ Dashboard saved as HTML")

# Create static visualizations
def create_static_visualizations(analysis_results):
    """Create static visualizations using matplotlib/seaborn."""
    
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Set style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Demographic Analysis Results', fontsize=16, fontweight='bold')
    
    # Plot 1: Population distribution
    all_data = []
    for key, result in analysis_results.items():
        if 'counties' in key:
            all_data.append(result['data'])
    
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # Population distribution
        axes[0, 0].hist(combined_data['B01003_001E'].astype(float), bins=30, alpha=0.7)
        axes[0, 0].set_title('Population Distribution')
        axes[0, 0].set_xlabel('Population')
        axes[0, 0].set_ylabel('Frequency')
        
        # Income vs Education
        axes[0, 1].scatter(
            combined_data['B19013_001E'].astype(float),
            combined_data['education_rate'],
            alpha=0.6
        )
        axes[0, 1].set_title('Income vs Education Rate')
        axes[0, 1].set_xlabel('Median Household Income')
        axes[0, 1].set_ylabel('Education Rate (%)')
        
        # Cluster analysis
        cluster_counts = combined_data['cluster'].value_counts().sort_index()
        axes[1, 0].bar(cluster_counts.index, cluster_counts.values)
        axes[1, 0].set_title('Cluster Distribution')
        axes[1, 0].set_xlabel('Cluster')
        axes[1, 0].set_ylabel('Count')
        
        # Geographic distribution
        combined_data.plot(
            column='cluster',
            ax=axes[1, 1],
            legend=True,
            cmap='Set3'
        )
        axes[1, 1].set_title('Geographic Cluster Distribution')
        axes[1, 1].axis('off')
    
    plt.tight_layout()
    plt.savefig(data_dir / "demographic_analysis_charts.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ Static visualizations created and saved")

create_static_visualizations(analysis_results)
```

### **Step 7: Data Storage and Export**

```python
from siege_utilities.analytics import upload_to_snowflake
from siege_utilities.files import ensure_path_exists

# Export to multiple formats
export_dir = data_dir / "exports"
ensure_path_exists(export_dir)

# Export as GeoJSON
for key, result in analysis_results.items():
    result['data'].to_file(export_dir / f"{key}.geojson", driver='GeoJSON')

# Export as CSV (without geometry)
for key, result in analysis_results.items():
    csv_data = result['data'].drop(columns='geometry')
    csv_data.to_csv(export_dir / f"{key}.csv", index=False)

# Export as Shapefile
for key, result in analysis_results.items():
    result['data'].to_file(export_dir / f"{key}.shp", driver='ESRI Shapefile')

# Export summary statistics
summary_stats = {}
for key, result in analysis_results.items():
    if result['cluster_stats'] is not None:
        summary_stats[key] = {
            'cluster_stats': result['cluster_stats'].to_dict(),
            'hotspot_stats': result['hotspot_stats']
        }

with open(export_dir / "analysis_summary.json", 'w') as f:
    json.dump(summary_stats, f, indent=2, default=str)

print("✓ Data exported to multiple formats")

# Optional: Upload to Snowflake (if configured)
try:
    # Combine all county data
    all_counties = []
    for key, result in analysis_results.items():
        if 'counties' in key:
            all_counties.append(result['data'])
    
    if all_counties:
        combined_counties = pd.concat(all_counties, ignore_index=True)
        
        # Upload to Snowflake
        success = upload_to_snowflake(
            combined_counties.drop(columns='geometry'),
            'demographic_analysis_counties',
            overwrite=True
        )
        
        if success:
            print("✓ Data uploaded to Snowflake")
        else:
            print("✗ Failed to upload to Snowflake")
            
except Exception as e:
    print(f"Snowflake upload not available: {e}")
```

### **Step 8: Generate Professional Report**

```python
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.chart_types import ChartType

def generate_demographic_report(analysis_results, data_dir):
    """Generate a professional PDF report of the demographic analysis."""
    
    report_gen = ReportGenerator()
    
    # Calculate summary statistics
    total_counties = sum(len(result['data']) for key, result in analysis_results.items() 
                        if 'counties' in key)
    total_population = sum(
        result['data']['B01003_001E'].astype(float).sum() 
        for key, result in analysis_results.items() 
        if 'counties' in key
    )
    
    # Create report configuration
    report_config = {
        'title': 'Comprehensive Demographic Analysis Report',
        'subtitle': f'Analysis of {len(target_states)} States - Census Year {analysis_year}',
        'sections': [
            {
                'title': 'Executive Summary',
                'content': f"""
                This report presents a comprehensive demographic analysis of {len(target_states)} states
                using Census {analysis_year} data. The analysis covers {total_counties} counties with a
                combined population of {total_population:,.0f} people.
                
                **Key Findings:**
                - Geographic clustering reveals distinct demographic patterns
                - Education rates show strong correlation with income levels
                - Spatial autocorrelation indicates regional demographic trends
                - Multiple geographic scales provide comprehensive coverage
                """
            },
            {
                'title': 'Methodology',
                'content': """
                **Data Sources:**
                - U.S. Census Bureau TIGER/Line boundaries
                - American Community Survey demographic data
                - Additional enrichment from data.world
                
                **Analysis Techniques:**
                - K-means clustering for demographic segmentation
                - Spatial autocorrelation analysis (Moran's I)
                - Multi-scale geographic analysis
                - Statistical correlation analysis
                """
            },
            {
                'title': 'Geographic Coverage',
                'content': f"""
                **States Analyzed:**
                {chr(10).join([f"- {state_names[fips]}" for fips in target_states])}
                
                **Geographic Levels:**
                - County boundaries
                - Census tracts
                - Block groups
                
                **Total Geographic Units:**
                - Counties: {total_counties}
                - Tracts: {sum(len(result["data"]) for key, result in analysis_results.items() if "tracts" in key)}
                - Block Groups: {sum(len(result["data"]) for key, result in analysis_results.items() if "block_groups" in key)}
                """
            }
        ],
        'charts': [
            {
                'type': ChartType.CHOROPLETH,
                'data': analysis_results[f"{target_states[0]}_counties"]['data'],
                'title': f'Demographic Clusters - {state_names[target_states[0]]}',
                'geometry_column': 'geometry',
                'color_column': 'cluster'
            }
        ]
    }
    
    # Generate report
    report_file = data_dir / "demographic_analysis_report.pdf"
    report_gen.generate_report(report_config, report_file)
    
    print(f"✓ Professional report generated: {report_file}")
    return report_file

# Generate the report
report_file = generate_demographic_report(analysis_results, data_dir)
```

### **Step 9: Performance Monitoring and Optimization**

```python
import time
import psutil
import gc

def monitor_performance():
    """Monitor system performance during analysis."""
    
    # Memory usage
    memory = psutil.virtual_memory()
    print(f"\n📊 Performance Summary:")
    print(f"Memory usage: {memory.percent}%")
    print(f"Available memory: {memory.available / (1024**3):.2f} GB")
    
    # Data size
    total_size = 0
    for key, result in analysis_results.items():
        total_size += result['data'].memory_usage(deep=True).sum()
    
    print(f"Total data size: {total_size / (1024**2):.2f} MB")
    
    # Clean up memory
    gc.collect()
    print("✓ Memory cleaned up")

monitor_performance()
```

## 🎉 **Final Results**

After running this complete pipeline, you'll have:

1. **📁 Organized Data**: Structured data files in multiple formats
2. **🗺️ Interactive Dashboard**: Web-based visualization tool
3. **📊 Static Charts**: High-quality images for reports
4. **📄 Professional Report**: PDF with analysis results
5. **💾 Multiple Exports**: GeoJSON, CSV, Shapefile formats
6. **☁️ Cloud Storage**: Optional Snowflake integration
7. **📈 Analysis Results**: Clustering, hotspots, correlations

## 🔧 **Customization Options**

### **Add More States**
```python
target_states = ['06', '48', '36', '12', '17']  # Add FL, IL
```

### **Include More Variables**
```python
variables.extend([
    'B08301_010E',  # 60+ minute commute
    'B25064_001E',  # Median gross rent
    'B23025_005E'   # Unemployed
])
```

### **Add Machine Learning**
```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Predict income based on demographics
X = combined_data[['B01003_001E', 'education_rate', 'B25077_001E']]
y = combined_data['B19013_001E']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

print(f"Model R² score: {model.score(X_test, y_test):.3f}")
```

## 🚀 **Next Steps**

1. **Automate the Pipeline**: Schedule regular updates
2. **Add Real-time Data**: Integrate with live data sources
3. **Build Web Application**: Deploy dashboard to production
4. **Add User Authentication**: Secure access to sensitive data
5. **Expand Geographic Coverage**: Include all 50 states

This recipe demonstrates the full power of combining enhanced Census utilities with analytics integration, spatial analysis, and professional reporting capabilities!
