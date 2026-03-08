"""Isochrone utilities with open-source-first providers and custom server support."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import requests

DEFAULT_ORS_BASE_URL = "https://api.openrouteservice.org"
DEFAULT_VALHALLA_BASE_URL = "http://localhost:8002"

_PROVIDER_ORS = "openrouteservice"
_PROVIDER_VALHALLA = "valhalla"


def _normalize_provider(provider: str) -> str:
    normalized = (provider or "").strip().lower()
    if normalized in {"ors", "openrouteservice"}:
        return _PROVIDER_ORS
    if normalized in {"valhalla"}:
        return _PROVIDER_VALHALLA
    raise ValueError(
        "provider must be one of: openrouteservice (ors), valhalla"
    )


def _validate_inputs(latitude: float, longitude: float, travel_time_minutes: int) -> None:
    if not (-90 <= latitude <= 90):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise ValueError("longitude must be between -180 and 180")
    if travel_time_minutes <= 0:
        raise ValueError("travel_time_minutes must be > 0")


def _valhalla_costing(profile: str) -> str:
    profile_norm = (profile or "").strip().lower()
    mapping = {
        "driving-car": "auto",
        "driving-hgv": "truck",
        "cycling-regular": "bicycle",
        "foot-walking": "pedestrian",
        "auto": "auto",
        "truck": "truck",
        "bicycle": "bicycle",
        "pedestrian": "pedestrian",
    }
    return mapping.get(profile_norm, "auto")


def build_isochrone_request(
    latitude: float,
    longitude: float,
    travel_time_minutes: int,
    *,
    provider: str = _PROVIDER_ORS,
    base_url: Optional[str] = None,
    profile: str = "driving-car",
    api_key: Optional[str] = None,
    extra_params: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a provider-specific HTTP request definition for an isochrone call.

    This supports open-source providers and self-hosted/custom endpoints.
    """
    _validate_inputs(latitude, longitude, travel_time_minutes)
    provider_norm = _normalize_provider(provider)

    if provider_norm == _PROVIDER_ORS:
        root = (base_url or DEFAULT_ORS_BASE_URL).rstrip("/")
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = api_key
        return {
            "provider": _PROVIDER_ORS,
            "method": "POST",
            "url": f"{root}/v2/isochrones/{profile}",
            "headers": headers,
            "params": dict(extra_params or {}),
            "json": {
                "locations": [[float(longitude), float(latitude)]],
                "range": [int(travel_time_minutes) * 60],
            },
        }

    root = (base_url or DEFAULT_VALHALLA_BASE_URL).rstrip("/")
    payload: Dict[str, Any] = {
        "locations": [{"lat": float(latitude), "lon": float(longitude)}],
        "costing": _valhalla_costing(profile),
        "contours": [{"time": int(travel_time_minutes)}],
        "polygons": True,
    }
    if extra_params:
        payload.update(dict(extra_params))
    return {
        "provider": _PROVIDER_VALHALLA,
        "method": "POST",
        "url": f"{root}/isochrone",
        "headers": {"Accept": "application/json", "Content-Type": "application/json"},
        "params": {},
        "json": payload,
    }


def get_isochrone(
    latitude: float,
    longitude: float,
    travel_time_minutes: int,
    *,
    provider: str = _PROVIDER_ORS,
    base_url: Optional[str] = None,
    profile: str = "driving-car",
    api_key: Optional[str] = None,
    timeout_seconds: int = 30,
    extra_params: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Fetch an isochrone GeoJSON response.

    Args:
        latitude: Center latitude.
        longitude: Center longitude.
        travel_time_minutes: Travel-time contour in minutes.
        provider: `openrouteservice` (default) or `valhalla`.
        base_url: Custom server root for self-hosted providers.
        profile: Travel profile (`driving-car`, `cycling-regular`, `foot-walking`, etc.).
        api_key: Optional API key (commonly used for hosted ORS).
        timeout_seconds: HTTP timeout.
        extra_params: Provider-specific extra request fields.

    Returns:
        Provider response parsed as JSON (typically GeoJSON FeatureCollection).
    """
    request_def = build_isochrone_request(
        latitude,
        longitude,
        travel_time_minutes,
        provider=provider,
        base_url=base_url,
        profile=profile,
        api_key=api_key,
        extra_params=extra_params,
    )

    response = requests.post(
        request_def["url"],
        headers=request_def["headers"],
        params=request_def["params"],
        json=request_def["json"],
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("isochrone response must be a JSON object")
    return data


def isochrone_to_geodataframe(isochrone_geojson: Mapping[str, Any]):
    """Convert an isochrone GeoJSON object to GeoDataFrame when geopandas is available."""
    try:
        import geopandas as gpd
    except ImportError as exc:  # pragma: no cover
        raise ImportError("geopandas is required for isochrone_to_geodataframe") from exc

    return gpd.GeoDataFrame.from_features(isochrone_geojson.get("features", []), crs="EPSG:4326")
