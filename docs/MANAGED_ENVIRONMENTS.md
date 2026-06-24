# Managed Environments Setup Guide

## Geo Extras and GDAL

As of the GDAL-optional-extra split, `[geo]` installs the pure-Python
geospatial stack — its wheels bundle their own GDAL/GEOS/PROJ, so it needs
**no system GDAL**. The native OSGeo bindings are a separate opt-in `[gdal]`
extra. This is what makes managed environments that cannot install system
GDAL (Databricks, Colab, SageMaker) work with a plain `pip install`.

| Extra | What it installs | System deps | Works on |
|-------|-----------------|-------------|----------|
| `[geo]` | geopandas, fiona, shapely, pyproj, rtree, mapclassify, tobler, osmnx, pysal, censusgeocode | **None** (bundled in wheels) | Everywhere, incl. Databricks / Colab / SageMaker |
| `[gdal]` | native OSGeo `gdal` Python bindings (`from osgeo import gdal`) | system libgdal, **version-matched** | Hosts with system GDAL |
| `[geodjango]` | `[geo]` use + Django, DRF, DRF-GIS, PostGIS bindings | system libgdal at runtime + PostgreSQL | Full PostGIS stack |

> The native `[gdal]` wheel must match the installed libgdal exactly. Add it
> on top of `[geo]` only when you import `osgeo` directly, and pin it — the
> path CI exercises:
> `pip install siege-utilities[geo]` then `pip install "gdal==$(gdal-config --version)"`.
> A bare `pip install siege-utilities[geo,gdal]` resolves the newest `gdal` in
> `>=3.6,<4` and will fail to build against an older system libgdal.

### Which extra do I need?

| Use case | Install |
|----------|---------|
| Geocoding, coordinate transforms, GEOID validation, spatial joins, choropleths | `[geo]` |
| Importing `osgeo` (`gdal`/`ogr`/`osr`) directly | `[geo]` + version-matched `[gdal]` |
| Django models with PostGIS geometry fields | `[geodjango]` (+ system libgdal) |
| Everything | `[all]` (no system GDAL; add `[gdal]` separately if you need osgeo) |

### Runtime detection

`geo_capabilities()` reports a runtime *capability* tier based on what is
actually importable — distinct from the pip extras above. The `"geo-lite"`
tier means the lightweight subset (shapely/pyproj) is present but GeoPandas
is not; it is not a pip extra, just a detected capability level.

```python
from siege_utilities.geo import geo_capabilities

caps = geo_capabilities()
print(caps["tier"])      # "geodjango", "geo", "geo-lite", or "none"
print(caps["geopandas"]) # True / False
```

## Azure Databricks

Databricks runtimes include numpy, pandas, and scipy but **not** system
GDAL/GEOS/PROJ. Because `[geo]` no longer requires system GDAL, install it
directly — no init script needed:

```bash
# In a notebook cell or init script:
%pip install siege-utilities[geo,data]
```

You only need a system-GDAL init script if you import `osgeo` directly or
use GeoDjango/PostGIS:

```bash
#!/bin/bash
apt-get update && apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
pip install siege-utilities[geo,data]
pip install "gdal==$(gdal-config --version)"   # only if you import osgeo
```

### Spark integration

PySpark and Apache Sedona are pure Python packages — install them with:

```bash
%pip install siege-utilities[distributed]
```

## Google Colab

Colab includes most Python data science packages but not system GDAL.
`[geo]` works out of the box:

```bash
!pip install siege-utilities[geo,data,reporting]

# Only if you import osgeo directly:
!apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
!pip install "gdal==$(gdal-config --version)"
```

## AWS SageMaker

SageMaker conda environments include numpy/pandas but not system GDAL.
`[geo]` installs without it:

```bash
# In a lifecycle config or notebook:
pip install siege-utilities[geo,data]

# Only if you import osgeo directly:
conda install -c conda-forge gdal
pip install "gdal==$(gdal-config --version)"
```

## Functions by Capability Tier

### geo-lite tier — no GDAL, no GeoPandas (lightweight subset)

- `validate_geoid()`, `normalize_geoid()`, `parse_geoid()` — GEOID utilities
- `geocode_single()`, `geocode_batch()` — Census geocoder
- `concatenate_addresses()`, `use_nominatim_geocoder()` — Nominatim geocoding
- `get_default_crs()`, `set_default_crs()` — CRS management
- `geo_capabilities()` — runtime detection
- Census constants, FIPS lookups, state normalization

### geo tier — `[geo]`, no system GDAL required

- `get_census_boundaries()`, `download_data()` — boundary downloads
- `interpolate_areal()` — areal interpolation
- `create_choropleth()` — map creation
- `SpatialDataTransformer` — format conversion
- All Django boundary models and services

### geodjango tier — `[geodjango]` (system libgdal + PostgreSQL)

- All geo models (`CongressionalDistrict`, `CensusTract`, etc.)
- Population services, management commands
- DRF GeoJSON serializers
