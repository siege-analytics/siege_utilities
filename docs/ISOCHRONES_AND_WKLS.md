# Isochrones and WKLS Guidance

## Current Position

- Use open-source isochrone providers by default.
- Allow custom server URLs for hosted/self-managed deployments.
- Keep proprietary backends optional and adapter-based.

## Isochrones

The library now exposes:

- `siege_utilities.get_isochrone(...)`
- `siege_utilities.build_isochrone_request(...)`
- `siege_utilities.isochrone_to_geodataframe(...)`

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

## WKLS (Recommendation)

WKLS can be valuable for enterprise-scale geospatial workloads, but should be integrated behind a narrow abstraction rather than as a hard dependency.

Recommended implementation model:

1. Define a stable internal adapter interface (`compute_isochrone`, `run_spatial_join`, `resolve_geometry_column`).
2. Keep `python` and `sedona` backends as baseline open-source paths.
3. Add a `wkls` adapter as an optional backend selected by runtime config.
4. Require contract tests so backend swaps preserve output schema and semantics.
5. For Databricks, prefer WKT/WKB interchange for portability when native spatial support differs by workspace/runtime.

This keeps contributors unblocked in open-source environments while allowing performance-oriented deployments to opt into WKLS.
