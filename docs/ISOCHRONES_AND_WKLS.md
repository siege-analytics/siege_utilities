# Isochrones and WKLS Guidance

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

## WKLS -- Well Known Locations gazetteer

**WKLS (Well Known Locations)** is a global admin-boundary gazetteer
that ships as an optional backend of siege_utilities. It is not future
work; it is available today.

Install the extra and use the `WklsGazetteer` class:

```bash
pip install siege-utilities[wkls]
```

```python
from siege_utilities.geo.gazetteers.wkls_gazetteer import WklsGazetteer

gazetteer = WklsGazetteer()
```

The WKLS gazetteer is selected as the default gazetteer backend when the
`wkls` extra is installed. It provides global administrative boundary
lookups behind the standard gazetteer interface, so callers do not need
to know which backend is resolving a location.
