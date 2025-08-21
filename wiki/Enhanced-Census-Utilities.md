# Enhanced Census Utilities Recipe

This recipe demonstrates how to use the enhanced Census utilities that provide dynamic discovery and intelligent data access to U.S. Census Bureau TIGER/Line shapefiles.

## Overview

The enhanced Census utilities solve the fundamental problem that the Census Bureau doesn't provide an official API for TIGER/Line data. Instead, they maintain a complex directory structure that changes over time, with different URL patterns for different years and geography types.

**Key Benefits:**
- **No more hardcoded URLs** - The system automatically discovers what's available
- **Handles changing directory structures** - Adapts to Census Bureau updates
- **Comprehensive boundary support** - Covers all major Census boundary types
- **Intelligent fallbacks** - Finds the best available data when requested isn't available
- **Built-in validation** - Prevents common errors before they happen

## Prerequisites

```bash
# Install required dependencies
pip install requests beautifulsoup4 lxml geopandas shapely pyproj fiona
```

## Basic Usage

### 1. Initialize the Census Data Source

```python
from siege_utilities.geo.spatial_data import CensusDataSource

# Create a Census data source instance
census = CensusDataSource()

# The system automatically discovers available years
print(f"Available Census years: {census.available_years}")
```

### 2. Discover Available Data

```python
# See what boundary types are available for a specific year
boundary_types = census.get_available_boundary_types(2020)
print("Available boundary types for 2020:")
for boundary_type, directory in boundary_types.items():
    print(f"  {boundary_type}: {directory}")
```

### 3. Download Geographic Boundaries

```python
# Download national-level boundaries (no state FIPS needed)
counties = census.get_geographic_boundaries(2020, 'county')
states = census.get_geographic_boundaries(2020, 'state')

# Download state-specific boundaries (state FIPS required)
california_tracts = census.get_geographic_boundaries(
    2020, 'tract', state_fips='06'
)

texas_block_groups = census.get_geographic_boundaries(
    2020, 'block_group', state_fips='48'
)
```

## Advanced Features

### 1. State FIPS Management

```python
# Get all available state FIPS codes
state_fips = census.get_available_state_fips()

# Find California's FIPS code
california_fips = None
for fips, name in state_fips.items():
    if 'California' in name:
        california_fips = fips
        break

print(f"California FIPS: {california_fips}")  # Should be '06'

# Validate a FIPS code
if census.validate_state_fips('06'):
    state_name = census.get_state_name('06')
    print(f"Valid FIPS '06' corresponds to: {state_name}")
```

### 2. Congressional Districts

```python
# Download current congressional districts (118th Congress)
congress_118 = census.get_geographic_boundaries(2020, 'cd118')

# Or use the congress_number parameter
congress_118_alt = census.get_geographic_boundaries(
    2020, 'cd', congress_number=118
)
```

### 3. Intelligent Year Selection

```python
# Request 2018 data - system will find the closest available year
optimal_year = census.discovery.get_optimal_year(2018, 'county')
print(f"Requested 2018, using year: {optimal_year}")

# Download using the optimal year
counties = census.get_geographic_boundaries(optimal_year, 'county')
```

### 4. URL Validation

```python
# Construct a download URL
url = census.discovery.construct_download_url(2020, 'county')

# Validate it before attempting download
if census.discovery.validate_download_url(url):
    print(f"URL is valid: {url}")
else:
    print("URL is not accessible")
```

## Practical Examples

### Example 1: Multi-State Analysis

```python
def download_multiple_states(year, boundary_type, state_fips_list):
    """Download boundaries for multiple states."""
    results = {}
    
    for state_fips in state_fips_list:
        try:
            print(f"Downloading {boundary_type} for state {state_fips}...")
            data = census.get_geographic_boundaries(
                year, boundary_type, state_fips=state_fips
            )
            if data is not None:
                results[state_fips] = data
                print(f"  ✓ Success: {len(data)} features")
            else:
                print(f"  ✗ Failed to download data")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    return results

# Download tract boundaries for multiple states
states_to_analyze = ['06', '48', '36']  # CA, TX, NY
tract_data = download_multiple_states(2020, 'tract', states_to_analyze)
```

### Example 2: Year Comparison

```python
def compare_boundaries_across_years(boundary_type, years, state_fips=None):
    """Compare boundaries across different Census years."""
    results = {}
    
    for year in years:
        try:
            print(f"Downloading {boundary_type} for year {year}...")
            data = census.get_geographic_boundaries(
                year, boundary_type, state_fips=state_fips
            )
            if data is not None:
                results[year] = data
                print(f"  ✓ Success: {len(data)} features")
            else:
                print(f"  ✗ Failed to download data")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    return results

# Compare county boundaries across years
years_to_compare = [2010, 2015, 2020]
county_comparison = compare_boundaries_across_years('county', years_to_compare)
```

### Example 3: Boundary Type Discovery

```python
def explore_available_boundaries(year):
    """Explore all available boundary types for a given year."""
    print(f"Exploring available boundaries for year {year}...")
    
    # Get available boundary types
    boundary_types = census.get_available_boundaries(year)
    
    print(f"Found {len(boundary_types)} boundary types:")
    for boundary_type, directory in boundary_types.items():
        print(f"  {boundary_type}: {directory}")
        
        # Try to construct a URL for this boundary type
        if boundary_type in ['state', 'county', 'place', 'zcta']:
            # National boundaries
            url = census.discovery.construct_download_url(year, boundary_type)
            print(f"    URL: {url}")
        elif boundary_type in ['tract', 'block_group', 'block']:
            # State-specific boundaries - show example with California
            url = census.discovery.construct_download_url(year, boundary_type, '06')
            print(f"    Example URL (CA): {url}")
        else:
            # Other types
            url = census.discovery.construct_download_url(year, boundary_type)
            print(f"    URL: {url}")

# Explore 2020 boundaries
explore_available_boundaries(2020)
```

## Error Handling and Validation

### 1. Parameter Validation

```python
def safe_download_boundaries(year, boundary_type, state_fips=None):
    """Safely download boundaries with comprehensive error handling."""
    try:
        # Validate parameters first
        census._validate_census_parameters(year, boundary_type, state_fips)
        
        # Attempt download
        data = census.get_geographic_boundaries(year, boundary_type, state_fips)
        return data
        
    except ValueError as e:
        print(f"Parameter validation failed: {e}")
        return None
    except Exception as e:
        print(f"Download failed: {e}")
        return None

# Test various scenarios
test_cases = [
    (2020, 'county', None),      # Valid - national boundaries
    (2020, 'tract', None),       # Invalid - missing state FIPS
    (2020, 'tract', '06'),       # Valid - state-specific
    (1800, 'county', None),      # Invalid - year too old
    (2020, 'invalid_type', None), # Invalid - unknown boundary type
]

for year, boundary_type, state_fips in test_cases:
    print(f"\nTesting: year={year}, type={boundary_type}, fips={state_fips}")
    result = safe_download_boundaries(year, boundary_type, state_fips)
    if result is not None:
        print(f"  ✓ Success: {len(result)} features")
    else:
        print("  ✗ Failed")
```

### 2. Network Error Handling

```python
def robust_download_with_retry(year, boundary_type, state_fips=None, max_retries=3):
    """Download with retry logic for network issues."""
    for attempt in range(max_retries):
        try:
            print(f"Download attempt {attempt + 1}/{max_retries}...")
            data = census.get_geographic_boundaries(year, boundary_type, state_fips)
            if data is not None:
                print(f"✓ Download successful on attempt {attempt + 1}")
                return data
            else:
                print(f"✗ Download returned None on attempt {attempt + 1}")
        except Exception as e:
            print(f"✗ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("  Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    print("✗ All download attempts failed")
    return None
```

## Performance Optimization

### 1. Cache Management

```python
# Refresh cache to get latest data
census.refresh_discovery_cache()

# Check cache status
print(f"Discovery cache has {len(census.discovery.cache)} entries")
print(f"Available years: {census.available_years}")
```

### 2. Batch Operations

```python
def batch_download_boundaries(requests):
    """Download multiple boundaries efficiently."""
    results = {}
    
    # Group by year to minimize discovery calls
    requests_by_year = {}
    for request in requests:
        year = request['year']
        if year not in requests_by_year:
            requests_by_year[year] = []
        requests_by_year[year].append(request)
    
    # Process each year
    for year, year_requests in requests_by_year.items():
        print(f"Processing year {year}...")
        
        # Get boundary types once for this year
        boundary_types = census.get_available_boundaries(year)
        
        for request in year_requests:
            boundary_type = request['boundary_type']
            state_fips = request.get('state_fips')
            
            if boundary_type in boundary_types:
                try:
                    data = census.get_geographic_boundaries(year, boundary_type, state_fips)
                    results[f"{year}_{boundary_type}_{state_fips or 'national'}"] = data
                except Exception as e:
                    print(f"Failed to download {year} {boundary_type}: {e}")
            else:
                print(f"Boundary type {boundary_type} not available for year {year}")
    
    return results

# Example batch download
batch_requests = [
    {'year': 2020, 'boundary_type': 'county'},
    {'year': 2020, 'boundary_type': 'tract', 'state_fips': '06'},
    {'year': 2020, 'boundary_type': 'tract', 'state_fips': '48'},
    {'year': 2010, 'boundary_type': 'county'},
]

batch_results = batch_download_boundaries(batch_requests)
```

## Integration with Other Tools

### 1. Pandas Integration

```python
import pandas as pd

def boundaries_to_dataframe(boundaries_dict):
    """Convert boundaries dictionary to pandas DataFrame."""
    rows = []
    
    for key, gdf in boundaries_dict.items():
        if gdf is not None:
            # Extract metadata
            year, boundary_type, state_fips = key.split('_')
            
            row = {
                'year': int(year),
                'boundary_type': boundary_type,
                'state_fips': state_fips if state_fips != 'national' else None,
                'feature_count': len(gdf),
                'geometry_type': str(gdf.geometry.geom_type.iloc[0]) if len(gdf) > 0 else None,
                'crs': str(gdf.crs) if gdf.crs else None
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

# Convert batch results to DataFrame
df = boundaries_to_dataframe(batch_results)
print(df)
```

### 2. Export to Various Formats

```python
def export_boundaries(boundaries_dict, output_dir):
    """Export boundaries to various formats."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    for key, gdf in boundaries_dict.items():
        if gdf is not None:
            # Export to GeoPackage
            gpkg_path = output_path / f"{key}.gpkg"
            gdf.to_file(gpkg_path, driver='GPKG')
            print(f"Exported {key} to {gpkg_path}")
            
            # Export to GeoJSON
            geojson_path = output_path / f"{key}.geojson"
            gdf.to_file(geojson_path, driver='GeoJSON')
            print(f"Exported {key} to {geojson_path}")

# Export batch results
export_boundaries(batch_results, "census_boundaries")
```

## Troubleshooting

### Common Issues and Solutions

1. **"State FIPS required" error**
   - Solution: Provide state_fips parameter for state-specific boundaries
   - Use `census.get_available_state_fips()` to see valid codes

2. **"Invalid geographic level" error**
   - Solution: Check available boundary types with `census.get_available_boundaries(year)`
   - Some boundary types may not be available for all years

3. **Network timeouts**
   - Solution: Increase timeout values or use retry logic
   - Check internet connection and Census Bureau website status

4. **Cache issues**
   - Solution: Use `census.refresh_discovery_cache()` to clear stale data
   - Force refresh with `force_refresh=True` parameter

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Now you'll see detailed discovery operations
census = CensusDataSource()
```

## Best Practices

1. **Always validate parameters** before attempting downloads
2. **Use the discovery system** rather than hardcoding URLs
3. **Handle errors gracefully** with try-catch blocks
4. **Refresh cache periodically** for long-running applications
5. **Group operations by year** to minimize discovery calls
6. **Use batch operations** for multiple downloads
7. **Validate URLs** before attempting downloads
8. **Provide meaningful error messages** to users

## Conclusion

The enhanced Census utilities provide a robust, intelligent solution for accessing Census Bureau TIGER/Line data. By automatically discovering available data and constructing correct URLs, they eliminate the need for hardcoded URLs and handle the complex, changing directory structure maintained by the Census Bureau.

This system is particularly valuable for:
- **Research applications** that need to work with multiple years of data
- **Production systems** that require reliable data access
- **Educational projects** that benefit from comprehensive boundary coverage
- **Analytical workflows** that need to handle various geographic levels

The utilities maintain backward compatibility while providing significant enhancements, making them suitable for both new projects and existing codebases.
