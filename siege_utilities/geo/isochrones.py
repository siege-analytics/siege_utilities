"""Isochrone utilities with open-source-first providers and custom server support."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Literal, Mapping, Optional

import requests

from siege_utilities.geo.crs import get_default_crs, reproject_if_needed

if TYPE_CHECKING:
    import geopandas as gpd

logger = logging.getLogger(__name__)

DEFAULT_ORS_BASE_URL = "https://api.openrouteservice.org"
DEFAULT_VALHALLA_BASE_URL = "http://localhost:8002"

ISOCHRONE_DEFAULT_RETRIES = 3
ISOCHRONE_RETRY_BACKOFF_BASE = 1  # seconds

_PROVIDER_ORS = "openrouteservice"
_PROVIDER_VALHALLA = "valhalla"

_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class IsochroneError(Exception):
    """Base exception for isochrone operations."""


class IsochroneNetworkError(IsochroneError):
    """Network failure (timeout, connection refused, DNS resolution)."""


class IsochroneProviderError(IsochroneError):
    """Provider returned an HTTP error or an unparseable response."""


# ---------------------------------------------------------------------------
# TypedDict for the request definition
# ---------------------------------------------------------------------------

try:
    from typing import TypedDict
except ImportError:  # Python <3.8 fallback; not expected on 3.11+
    from typing_extensions import TypedDict


class IsochroneRequest(TypedDict):
    """Structured request definition returned by :func:`build_isochrone_request`."""

    provider: Literal["openrouteservice", "valhalla"]
    method: Literal["POST", "GET"]
    url: str
    headers: Dict[str, str]
    params: Dict[str, Any]
    json: Dict[str, Any]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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


def _dispatch_request(
    request_def: IsochroneRequest,
    timeout_seconds: int,
) -> requests.Response:
    """Send the HTTP request described by *request_def*."""
    method = request_def["method"].upper()
    if method == "POST":
        return requests.post(
            request_def["url"],
            headers=request_def["headers"],
            params=request_def["params"],
            json=request_def["json"],
            timeout=timeout_seconds,
        )
    if method == "GET":
        return requests.get(
            request_def["url"],
            headers=request_def["headers"],
            params={**request_def["params"], **request_def["json"]},
            timeout=timeout_seconds,
        )
    raise ValueError(f"Unsupported HTTP method in request definition: {method}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
) -> IsochroneRequest:
    """Build a provider-specific HTTP request definition for an isochrone call.

    This supports open-source providers and self-hosted/custom endpoints.

    Args:
        latitude: Center latitude (-90 to 90).
        longitude: Center longitude (-180 to 180).
        travel_time_minutes: Travel-time contour in minutes (must be > 0).
        provider: ``"openrouteservice"`` (or ``"ors"``) or ``"valhalla"``.
        base_url: Custom server root for self-hosted providers.
        profile: Travel profile (``"driving-car"``, ``"cycling-regular"``,
            ``"foot-walking"``, etc.).
        api_key: Optional API key (commonly used for hosted ORS).
        extra_params: Provider-specific extra request fields merged into the
            JSON body (Valhalla) or query params (ORS).

    Returns:
        An :class:`IsochroneRequest` dict with ``provider``, ``method``,
        ``url``, ``headers``, ``params``, and ``json`` keys.

    Raises:
        ValueError: If inputs are out of range or provider is unknown.
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
        return IsochroneRequest(
            provider="openrouteservice",
            method="POST",
            url=f"{root}/v2/isochrones/{profile}",
            headers=headers,
            params=dict(extra_params or {}),
            json={
                "locations": [[float(longitude), float(latitude)]],
                "range": [int(travel_time_minutes) * 60],
            },
        )

    # Valhalla
    root = (base_url or DEFAULT_VALHALLA_BASE_URL).rstrip("/")
    payload: Dict[str, Any] = {
        "locations": [{"lat": float(latitude), "lon": float(longitude)}],
        "costing": _valhalla_costing(profile),
        "contours": [{"time": int(travel_time_minutes)}],
        "polygons": True,
    }
    if extra_params:
        payload.update(dict(extra_params))
    return IsochroneRequest(
        provider="valhalla",
        method="POST",
        url=f"{root}/isochrone",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params={},
        json=payload,
    )


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
    max_retries: int = ISOCHRONE_DEFAULT_RETRIES,
) -> Dict[str, Any]:
    """Fetch an isochrone GeoJSON response.

    Args:
        latitude: Center latitude.
        longitude: Center longitude.
        travel_time_minutes: Travel-time contour in minutes.
        provider: ``"openrouteservice"`` (default) or ``"valhalla"``.
        base_url: Custom server root for self-hosted providers.
        profile: Travel profile (``"driving-car"``, ``"cycling-regular"``,
            ``"foot-walking"``, etc.).
        api_key: Optional API key (commonly used for hosted ORS).
        timeout_seconds: HTTP timeout in seconds (default 30).
        extra_params: Provider-specific extra request fields.
        max_retries: Maximum number of attempts for transient failures
            (default 3). Set to 1 to disable retries.

    Returns:
        Provider response parsed as JSON (typically a GeoJSON
        FeatureCollection).

    Raises:
        IsochroneNetworkError: On timeout, connection, or DNS failure.
        IsochroneProviderError: On HTTP error or unparseable response.
        ValueError: If inputs are out of range or provider is unknown.
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

    last_exc: Optional[Exception] = None
    attempts = max(1, max_retries)

    for attempt in range(attempts):
        try:
            response = _dispatch_request(request_def, timeout_seconds)
        except requests.exceptions.Timeout as exc:
            last_exc = IsochroneNetworkError(
                f"Isochrone request to {request_def['url']} timed out "
                f"after {timeout_seconds}s (attempt {attempt + 1}/{attempts})"
            )
            last_exc.__cause__ = exc
            logger.warning("%s", last_exc)
            if attempt < attempts - 1:
                time.sleep(ISOCHRONE_RETRY_BACKOFF_BASE * (2 ** attempt))
            continue
        except requests.exceptions.ConnectionError as exc:
            last_exc = IsochroneNetworkError(
                f"Connection to {request_def['url']} failed "
                f"(attempt {attempt + 1}/{attempts}): {exc}"
            )
            last_exc.__cause__ = exc
            logger.warning("%s", last_exc)
            if attempt < attempts - 1:
                time.sleep(ISOCHRONE_RETRY_BACKOFF_BASE * (2 ** attempt))
            continue
        except requests.exceptions.RequestException as exc:
            raise IsochroneNetworkError(
                f"Isochrone request failed: {exc}"
            ) from exc

        # Retry on transient HTTP status codes
        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < attempts - 1:
            logger.warning(
                "Isochrone provider returned %d (attempt %d/%d), retrying",
                response.status_code, attempt + 1, attempts,
            )
            time.sleep(ISOCHRONE_RETRY_BACKOFF_BASE * (2 ** attempt))
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise IsochroneProviderError(
                f"Provider {request_def['provider']} returned HTTP "
                f"{response.status_code}: {response.text[:200]}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise IsochroneProviderError(
                f"Provider returned non-JSON response: "
                f"{response.text[:200]}"
            ) from exc

        if not isinstance(data, dict):
            raise IsochroneProviderError(
                f"Isochrone response must be a JSON object, "
                f"got {type(data).__name__}"
            )
        return data

    # All retries exhausted
    if last_exc is not None:
        raise last_exc
    raise IsochroneNetworkError("Isochrone request failed after all retry attempts")


def isochrone_to_geodataframe(
    isochrone_geojson: Mapping[str, Any],
    *,
    crs: str | None = None,
) -> "gpd.GeoDataFrame":
    """Convert an isochrone GeoJSON object to a GeoDataFrame.

    Requires ``geopandas``. Install with ``pip install siege_utilities[geo]``.

    GeoJSON is always ingested as EPSG:4326 (the GeoJSON spec mandates WGS 84).
    If *crs* differs from EPSG:4326 the result is reprojected to the
    requested CRS before returning.

    Args:
        isochrone_geojson: A GeoJSON dict (typically a FeatureCollection
            returned by :func:`get_isochrone`).
        crs: Target coordinate reference system. Defaults to
            :func:`~siege_utilities.geo.crs.get_default_crs` (initially
            ``"EPSG:4326"``).  Pass any string accepted by ``pyproj``.

    Returns:
        A GeoDataFrame with one row per feature in the requested *crs*.

    Raises:
        ImportError: If geopandas is not installed.
    """
    try:
        import geopandas as _gpd
    except ImportError as exc:
        raise ImportError(
            "geopandas is required for isochrone_to_geodataframe. "
            "Install with: pip install siege_utilities[geo]"
        ) from exc

    # GeoJSON is always WGS 84 per RFC 7946
    features = isochrone_geojson.get("features", [])
    if not features:
        return _gpd.GeoDataFrame()
    gdf = _gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return reproject_if_needed(gdf, crs)
