# Managed Environments Setup Guide

## Tiered Geo Extras

siege_utilities offers three tiers of geospatial functionality:

| Extra | What it installs | System deps | Works on |
|-------|-----------------|-------------|----------|
| `[geo-lite]` | shapely, pyproj, geopy, censusgeocode | None | Everywhere |
| `[geo]` | geo-lite + geopandas, fiona, rtree, mapclassify, tobler, osmnx, pysal | GDAL, GEOS, PROJ | Systems with C libs |
| `[geodjango]` | geo + Django, DRF, PostGIS bindings | GDAL + PostgreSQL | Full PostGIS stack |

### Which tier do I need?

| Use case | Tier |
|----------|------|
| Geocoding, coordinate transforms, GEOID validation | `geo-lite` |
| Census data download, spatial joins, choropleth maps | `geo` |
| Django models with PostGIS geometry fields | `geodjango` |
| Everything | `all` |

### Runtime detection

```python
from siege_utilities.geo import geo_capabilities

caps = geo_capabilities()
print(caps["tier"])      # "geodjango", "geo", "geo-lite", or "none"
print(caps["geopandas"]) # True / False
```

## Azure Databricks

Databricks runtimes include numpy, pandas, and scipy but **not** GDAL/GEOS/PROJ.

```bash
# In a notebook cell or init script:
%pip install siege-utilities[geo-lite,data]
```

For full geo support, use a Databricks init script to install system libraries:

```bash
#!/bin/bash
apt-get update && apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
pip install siege-utilities[geo,data]
```

### Spark integration

PySpark and Apache Sedona are pure Python packages — install them with:

```bash
%pip install siege-utilities[distributed]
```

## Google Colab

Colab includes most Python data science packages but not GDAL.

```python
# geo-lite works out of the box
!pip install siege-utilities[geo-lite,data]

# For full geo, install GDAL first
!apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
!pip install siege-utilities[geo,data,reporting]
```

## AWS SageMaker

SageMaker conda environments include numpy/pandas but not GDAL.

```bash
# In a lifecycle config or notebook:
pip install siege-utilities[geo-lite,data]

# For full geo:
conda install -c conda-forge gdal geopandas fiona
pip install siege-utilities[geo,data]
```

## Functions by Tier

### geo-lite (no GDAL required)

- `validate_geoid()`, `normalize_geoid()`, `parse_geoid()` — GEOID utilities
- `geocode_single()`, `geocode_batch()` — Census geocoder
- `concatenate_addresses()`, `use_nominatim_geocoder()` — Nominatim geocoding
- `get_default_crs()`, `set_default_crs()` — CRS management
- `geo_capabilities()` — runtime detection
- Census constants, FIPS lookups, state normalization

### geo (requires GDAL)

- `get_census_boundaries()`, `download_data()` — boundary downloads
- `interpolate_areal()` — areal interpolation
- `create_choropleth()` — map creation
- `SpatialDataTransformer` — format conversion
- All Django boundary models and services

### geodjango (requires GDAL + PostgreSQL)

- All geo models (`CongressionalDistrict`, `CensusTract`, etc.)
- Population services, management commands
- DRF GeoJSON serializers
