# Geocoding Recipe

## Overview
This recipe demonstrates how to use the geocoding utilities in `siege_utilities` for address geocoding, reverse geocoding, spatial data processing, and geographic analysis.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Geocoding service API keys (Google Maps, OpenStreetMap, etc.)
- Basic understanding of geographic coordinate systems
- Required dependencies: `geopy`, `pandas`, `shapely`

## Installation
```bash
pip install siege_utilities
pip install geopy pandas shapely
```

## Basic Geocoding Operations

### 1. Address Geocoding

```python
from siege_utilities.geo.geocoding import GeocodingService
from siege_utilities.geo.spatial_data import SpatialDataProcessor

# Initialize geocoding service
geocoder = GeocodingService()

# Basic address geocoding
coordinates = geocoder.geocode_address("1600 Pennsylvania Avenue NW, Washington, DC")
print(f"Latitude: {coordinates['latitude']}")
print(f"Longitude: {coordinates['longitude']}")
print(f"Formatted address: {coordinates['formatted_address']}")

# Geocode with additional options
coordinates = geocoder.geocode_address(
    "Times Square, New York, NY",
    provider="google",  # or "osm", "bing"
    region="US",
    language="en"
)
```

### 2. Reverse Geocoding

```python
# Convert coordinates to address
address = geocoder.reverse_geocode(
    latitude=40.7589,
    longitude=-73.9851,
    provider="google"
)
print(f"Address: {address['formatted_address']}")
print(f"Street: {address['street']}")
print(f"City: {address['city']}")
print(f"State: {address['state']}")
print(f"Country: {address['country']}")
```

### 3. Batch Geocoding

```python
# Geocode multiple addresses
addresses = [
    "123 Main St, Anytown, USA",
    "456 Oak Ave, Somewhere, USA",
    "789 Pine Rd, Elsewhere, USA"
]

geocoded_results = []
for address in addresses:
    try:
        result = geocoder.geocode_address(address)
        geocoded_results.append({
            'address': address,
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'confidence': result['confidence']
        })
    except Exception as e:
        print(f"Failed to geocode {address}: {e}")

# Convert to DataFrame
import pandas as pd
df = pd.DataFrame(geocoded_results)
print(df)
```

## Advanced Geocoding Features

### 1. Geocoding with Confidence Scoring

```python
# Get detailed geocoding results with confidence
detailed_result = geocoder.geocode_address_detailed(
    "Central Park, New York, NY",
    include_confidence=True,
    include_components=True
)

print(f"Confidence: {detailed_result['confidence']}")
print(f"Accuracy: {detailed_result['accuracy']}")
print(f"Components: {detailed_result['components']}")

# Filter results by confidence threshold
if detailed_result['confidence'] > 0.8:
    print("High confidence result")
    # Use the coordinates
else:
    print("Low confidence, manual review needed")
```

### 2. Geocoding with Multiple Providers

```python
# Try multiple geocoding providers for better results
providers = ["google", "osm", "bing"]
address = "Eiffel Tower, Paris, France"

for provider in providers:
    try:
        result = geocoder.geocode_address(address, provider=provider)
        print(f"{provider.upper()}: {result['latitude']}, {result['longitude']}")
    except Exception as e:
        print(f"{provider.upper()}: Failed - {e}")

# Use provider fallback
result = geocoder.geocode_address_with_fallback(
    address,
    primary_provider="google",
    fallback_providers=["osm", "bing"]
)
```

### 3. Custom Geocoding Providers

```python
# Configure custom geocoding provider
custom_config = {
    "api_key": "your_api_key",
    "base_url": "https://api.customgeocoder.com",
    "endpoints": {
        "geocode": "/geocode",
        "reverse": "/reverse"
    }
}

geocoder.add_provider("custom", custom_config)
result = geocoder.geocode_address("Test Address", provider="custom")
```

## Spatial Data Processing

### 1. Coordinate System Conversions

```python
from siege_utilities.geo.spatial_transformations import CoordinateTransformer

transformer = CoordinateTransformer()

# Convert between coordinate systems
wgs84_coords = (40.7589, -73.9851)  # WGS84 (standard GPS)
utm_coords = transformer.transform_coordinates(
    wgs84_coords,
    from_system="WGS84",
    to_system="UTM",
    zone="18N"
)
print(f"UTM coordinates: {utm_coords}")

# Convert back to WGS84
wgs84_back = transformer.transform_coordinates(
    utm_coords,
    from_system="UTM",
    to_system="WGS84",
    zone="18N"
)
print(f"WGS84 coordinates: {wgs84_back}")
```

### 2. Distance and Bearing Calculations

```python
# Calculate distance between two points
point1 = (40.7589, -73.9851)  # Times Square
point2 = (40.7484, -73.9857)  # Empire State Building

distance = transformer.calculate_distance(point1, point2)
bearing = transformer.calculate_bearing(point1, point2)

print(f"Distance: {distance:.2f} meters")
print(f"Bearing: {bearing:.2f} degrees")

# Calculate distance with different units
distance_km = transformer.calculate_distance(point1, point2, unit="kilometers")
distance_miles = transformer.calculate_distance(point1, point2, unit="miles")
```

### 3. Spatial Queries and Filtering

```python
# Find points within a radius
center_point = (40.7589, -73.9851)
radius_meters = 1000

nearby_points = transformer.find_points_within_radius(
    center_point,
    radius_meters,
    point_list=[
        (40.7484, -73.9857),  # Empire State Building
        (40.7505, -73.9934),  # Madison Square Garden
        (40.7589, -73.9851)   # Times Square
    ]
)

print(f"Points within {radius_meters}m: {len(nearby_points)}")
```

## Geographic Data Analysis

### 1. Address Standardization

```python
from siege_utilities.geo.spatial_data import AddressStandardizer

standardizer = AddressStandardizer()

# Standardize address format
raw_address = "123 main st, anytown, ny 12345"
standardized = standardizer.standardize_address(raw_address)
print(f"Standardized: {standardized}")

# Parse address components
components = standardizer.parse_address(raw_address)
print(f"Street: {components['street']}")
print(f"City: {components['city']}")
print(f"State: {components['state']}")
print(f"ZIP: {components['zip']}")
```

### 2. Geographic Clustering

```python
# Cluster geographic points
points = [
    (40.7589, -73.9851),  # Times Square
    (40.7484, -73.9857),  # Empire State Building
    (40.7505, -73.9934),  # Madison Square Garden
    (40.7527, -73.9772),  # Grand Central Terminal
    (40.7484, -73.9857)   # Another point
]

clusters = transformer.cluster_points(
    points,
    method="kmeans",
    n_clusters=3
)

for i, cluster in enumerate(clusters):
    print(f"Cluster {i+1}: {len(cluster)} points")
    print(f"Centroid: {transformer.calculate_centroid(cluster)}")
```

### 3. Geographic Heatmaps

```python
# Generate geographic heatmap data
heatmap_data = transformer.generate_heatmap_data(
    points,
    grid_size=100,  # meters
    radius=500      # meters
)

# Convert to visualization format
import folium

# Create map centered on NYC
m = folium.Map(location=[40.7589, -73.9851], zoom_start=13)

# Add heatmap
folium.plugins.HeatMap(heatmap_data).add_to(m)

# Save map
m.save("nyc_heatmap.html")
```

## Integration with Data Pipelines

### 1. Batch Processing with Pandas

```python
import pandas as pd

# Load address data
df = pd.read_csv("addresses.csv")
print(f"Loaded {len(df)} addresses")

# Geocode addresses
def geocode_row(row):
    try:
        result = geocoder.geocode_address(row['address'])
        return pd.Series({
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'confidence': result['confidence']
        })
    except Exception as e:
        return pd.Series({
            'latitude': None,
            'longitude': None,
            'confidence': 0
        })

# Apply geocoding
geocoded_df = df.join(df.apply(geocode_row, axis=1))

# Save results
geocoded_df.to_csv("geocoded_addresses.csv", index=False)
print("Geocoding completed and saved")
```

### 2. Real-time Geocoding Service

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/geocode', methods=['POST'])
def geocode_endpoint():
    data = request.get_json()
    address = data.get('address')
    
    if not address:
        return jsonify({'error': 'Address required'}), 400
    
    try:
        result = geocoder.geocode_address(address)
        return jsonify({
            'success': True,
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'formatted_address': result['formatted_address']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
```

## Performance Optimization

### 1. Caching Geocoding Results

```python
import json
import os

class CachedGeocoder:
    def __init__(self, cache_file="geocoding_cache.json"):
        self.cache_file = cache_file
        self.cache = self.load_cache()
    
    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    def geocode_with_cache(self, address):
        if address in self.cache:
            return self.cache[address]
        
        result = geocoder.geocode_address(address)
        self.cache[address] = result
        self.save_cache()
        return result

# Use cached geocoder
cached_geocoder = CachedGeocoder()
result = cached_geocoder.geocode_with_cache("1600 Pennsylvania Avenue NW, Washington, DC")
```

### 2. Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor
import threading

def geocode_address_parallel(address):
    try:
        return geocoder.geocode_address(address)
    except Exception as e:
        return {'error': str(e)}

# Parallel geocoding
addresses = ["Address 1", "Address 2", "Address 3", "Address 4"]

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(geocode_address_parallel, addresses))

# Process results
for address, result in zip(addresses, results):
    if 'error' not in result:
        print(f"{address}: {result['latitude']}, {result['longitude']}")
    else:
        print(f"{address}: Failed - {result['error']}")
```

## Error Handling and Validation

### 1. Input Validation

```python
def validate_address(address):
    if not address or not isinstance(address, str):
        raise ValueError("Address must be a non-empty string")
    
    if len(address.strip()) < 5:
        raise ValueError("Address too short")
    
    return address.strip()

def validate_coordinates(lat, lon):
    if not (-90 <= lat <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    
    if not (-180 <= lon <= 180):
        raise ValueError("Longitude must be between -180 and 180")
    
    return True

# Use validation
try:
    valid_address = validate_address("1600 Pennsylvania Avenue NW, Washington, DC")
    result = geocoder.geocode_address(valid_address)
    
    validate_coordinates(result['latitude'], result['longitude'])
    print("Coordinates validated successfully")
except ValueError as e:
    print(f"Validation error: {e}")
```

### 2. Rate Limiting and Retry Logic

```python
import time
from siege_utilities.core.logging import Logger

logger = Logger("geocoding")

def geocode_with_retry(address, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return geocoder.geocode_address(address)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            else:
                raise e

# Use retry logic
try:
    result = geocode_with_retry("1600 Pennsylvania Avenue NW, Washington, DC")
    print(f"Geocoded successfully: {result}")
except Exception as e:
    print(f"All attempts failed: {e}")
```

## Best Practices

### 1. API Key Management
- Store API keys in environment variables
- Use different keys for different environments
- Monitor API usage and quotas

### 2. Data Quality
- Validate input addresses before geocoding
- Check geocoding confidence scores
- Implement address standardization

### 3. Performance
- Use caching for repeated addresses
- Implement parallel processing for batch operations
- Monitor API response times

### 4. Error Handling
- Implement proper retry logic
- Log all geocoding failures
- Provide fallback options

## Troubleshooting

### Common Issues

1. **API Rate Limits**
   ```python
   # Implement rate limiting
   import time
   time.sleep(0.1)  # 100ms delay between requests
   ```

2. **Invalid Addresses**
   ```python
   # Validate address format
   if not re.match(r'^[\w\s,.-]+$', address):
       print("Invalid address format")
   ```

3. **Coordinate Precision**
   ```python
   # Round coordinates to appropriate precision
   lat = round(result['latitude'], 6)
   lon = round(result['longitude'], 6)
   ```

## Conclusion

The geocoding utilities in `siege_utilities` provide comprehensive tools for geographic data processing. By following this recipe, you can:

- Efficiently geocode addresses and reverse geocode coordinates
- Process spatial data and perform geographic analysis
- Integrate geocoding into data pipelines and applications
- Optimize performance with caching and parallel processing
- Handle errors gracefully with proper validation and retry logic

Remember to always validate inputs, implement proper error handling, and follow API usage guidelines when working with geocoding services.
