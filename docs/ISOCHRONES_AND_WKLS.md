# Isochrones and WKL Guidance

## Current Position

- Use open-source isochrone providers by default.
- Allow custom server URLs for hosted/self-managed deployments.
- Keep proprietary backends optional and adapter-based.

## Isochrones

The library exposes:

- `siege_utilities.get_isochrone(...)` — fetch isochrone GeoJSON from a provider
- `siege_utilities.build_isochrone_request(...)` — build the HTTP request without sending it
- `siege_utilities.isochrone_to_geodataframe(...)` — convert GeoJSON to GeoDataFrame

Exception classes:

- `siege_utilities.IsochroneError` — base exception
- `siege_utilities.IsochroneNetworkError` — timeout, connection failure
- `siege_utilities.IsochroneProviderError` — HTTP error, invalid response

Supported providers:

- `openrouteservice` (`ors`) — default
- `valhalla`

Both providers support `base_url` so you can point to custom servers.

### OpenRouteService (default or custom)

```python
import siege_utilities as su

# Hosted ORS
geojson = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=15,
    provider="openrouteservice",
    api_key="<ors-key>",
)

# Self-hosted ORS
geojson_custom = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=15,
    provider="openrouteservice",
    base_url="https://ors.internal.example.com",
)
```

### Valhalla (custom server)

```python
geojson = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=20,
    provider="valhalla",
    base_url="http://valhalla.svc.cluster.local:8002",
    profile="driving-car",
)
```

### Timeout, retries, and extra parameters

```python
# Custom timeout (default 30s) and retry count (default 3)
geojson = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=15,
    timeout_seconds=60,
    max_retries=5,
)

# Provider-specific extra parameters
geojson = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=15,
    provider="valhalla",
    base_url="http://valhalla.svc.cluster.local:8002",
    extra_params={"denoise": 0.5, "generalize": 50},
)
```

### Error handling

```python
from siege_utilities.geo.isochrones import (
    IsochroneNetworkError,
    IsochroneProviderError,
)

try:
    geojson = su.get_isochrone(
        latitude=41.8781, longitude=-87.6298,
        travel_time_minutes=15,
    )
except IsochroneNetworkError as e:
    print(f"Network issue (will retry automatically): {e}")
except IsochroneProviderError as e:
    print(f"Provider returned error: {e}")
```

### Converting to GeoDataFrame

```python
# Default CRS (uses get_default_crs(), initially EPSG:4326)
gdf = su.isochrone_to_geodataframe(geojson)

# Explicit CRS
gdf = su.isochrone_to_geodataframe(geojson, crs="EPSG:3857")
```

## WKL — Well-Known Linestrings (Future Work)

**WKL (Well-Known Linestrings)** refers to the use of standardized
linestring representations (WKT/WKB) as a portable interchange format
for spatial operations across heterogeneous compute environments
(PostGIS, Sedona, Databricks native, DuckDB Spatial).

WKL can be valuable for enterprise-scale geospatial workloads, but
should be integrated behind a narrow abstraction rather than as a hard
dependency.

Recommended implementation model:

1. Define a stable internal adapter interface (`compute_isochrone`, `run_spatial_join`, `resolve_geometry_column`).
2. Keep `python` and `sedona` backends as baseline open-source paths.
3. Add a `wkl` adapter as an optional backend selected by runtime config.
4. Require contract tests so backend swaps preserve output schema and semantics.
5. For Databricks, prefer WKT/WKB interchange for portability when native spatial support differs by workspace/runtime.

This keeps contributors unblocked in open-source environments while
allowing performance-oriented deployments to opt into WKL-based
spatial operations.
