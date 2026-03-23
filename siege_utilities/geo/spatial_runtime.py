"""Spatial runtime capability planning across Databricks/Spark/Python contexts.

Includes ``GeometryPayload`` for Spark-safe geometry transport and codec helpers
(``encode_geometry``, ``decode_geometry``, ``payload_to_spark_row``,
``spark_row_to_payload``) that round-trip shapely geometries through WKT / WKB /
GeoJSON representations.
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import shapely.geometry.base  # noqa: F401
    import shapely.wkt as _swkt
    import shapely.wkb as _swkb

    _SHAPELY_AVAILABLE = True
except ImportError:  # pragma: no cover – optional dependency
    _SHAPELY_AVAILABLE = False


@dataclass(frozen=True)
class SpatialRuntimePlan:
    """Execution plan for spatial operations with deterministic fallback order."""

    runtime: str
    native_spatial_available: bool
    sedona_available: bool
    loader_order: List[str]
    reason: str


def _parse_databricks_runtime_version(version: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse Databricks runtime version like `17.1.x-scala2.12`."""
    if not version:
        return None
    match = re.match(r"^\s*(\d+)\.(\d+)", str(version))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _detect_databricks_runtime() -> Optional[str]:
    """Read Databricks runtime version from environment when available."""
    return os.getenv("DATABRICKS_RUNTIME_VERSION")


def _infer_native_spatial_support(runtime_version: Optional[str]) -> bool:
    """
    Infer native Databricks spatial support from runtime version.

    Databricks SQL GEOGRAPHY/GEOMETRY support starts in Runtime 17.1+ (preview).
    """
    parsed = _parse_databricks_runtime_version(runtime_version)
    if parsed is None:
        return False
    major, minor = parsed
    return (major, minor) >= (17, 1)


def _detect_sedona_available() -> bool:
    """Best-effort Sedona availability detection via import."""
    try:
        import sedona  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def resolve_spatial_runtime_plan(
    *,
    databricks_runtime_version: Optional[str] = None,
    native_spatial_available: Optional[bool] = None,
    sedona_available: Optional[bool] = None,
) -> SpatialRuntimePlan:
    """
    Resolve spatial runtime execution plan.

    Priority order:
    1. databricks_native
    2. sedona
    3. python
    """
    runtime_version = databricks_runtime_version or _detect_databricks_runtime()
    native_available = (
        _infer_native_spatial_support(runtime_version)
        if native_spatial_available is None
        else bool(native_spatial_available)
    )
    sedona_ready = _detect_sedona_available() if sedona_available is None else bool(sedona_available)

    if native_available:
        return SpatialRuntimePlan(
            runtime="databricks_native",
            native_spatial_available=True,
            sedona_available=sedona_ready,
            loader_order=["databricks_native", "sedona", "python"],
            reason="native Databricks spatial support available",
        )
    if sedona_ready:
        return SpatialRuntimePlan(
            runtime="sedona",
            native_spatial_available=False,
            sedona_available=True,
            loader_order=["sedona", "python"],
            reason="native Databricks spatial unavailable, Sedona available",
        )
    return SpatialRuntimePlan(
        runtime="python",
        native_spatial_available=False,
        sedona_available=False,
        loader_order=["python"],
        reason="no native Databricks spatial or Sedona support detected",
    )


# ---------------------------------------------------------------------------
# Geometry payload – Spark-safe transport container
# ---------------------------------------------------------------------------


@dataclass
class GeometryPayload:
    """Spark-safe container for a single geometry with optional multi-format encoding.

    At least one of ``geometry_wkt``, ``geometry_wkb``, or ``geometry_geojson``
    should be populated for the payload to be useful.
    """

    geometry_wkt: Optional[str] = None
    geometry_wkb: Optional[bytes] = None
    geometry_geojson: Optional[Dict[str, Any]] = None
    crs: str = "EPSG:4326"
    geometry_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Codec helpers
# ---------------------------------------------------------------------------


def _require_shapely(fn_name: str) -> None:
    if not _SHAPELY_AVAILABLE:
        raise ImportError(
            f"{fn_name} requires shapely, which is not installed. "
            "Install it with: pip install shapely"
        )


def encode_geometry(
    geom: Any,
    fmt: str = "wkt",
    crs: str = "EPSG:4326",
) -> GeometryPayload:
    """Encode a shapely geometry into a :class:`GeometryPayload`.

    Parameters
    ----------
    geom:
        A ``shapely.geometry.base.BaseGeometry`` instance.
    fmt:
        Primary serialisation format – ``"wkt"``, ``"wkb"``, or ``"geojson"``.
        All three representations are always populated; *fmt* only controls
        validation of the primary path.
    crs:
        Coordinate reference system identifier stored on the payload.

    Returns
    -------
    GeometryPayload
    """
    _require_shapely("encode_geometry")
    import shapely.geometry  # local import – already guarded

    if not isinstance(geom, shapely.geometry.base.BaseGeometry):
        raise TypeError(
            f"Expected a shapely BaseGeometry, got {type(geom).__name__}"
        )

    wkt = geom.wkt
    wkb = geom.wkb
    geojson = shapely.geometry.mapping(geom)

    return GeometryPayload(
        geometry_wkt=wkt,
        geometry_wkb=wkb,
        geometry_geojson=geojson,
        crs=crs,
        geometry_type=geom.geom_type,
    )


def decode_geometry(payload: GeometryPayload) -> Any:
    """Decode a :class:`GeometryPayload` back to a shapely geometry.

    Tries WKT first, then WKB, then GeoJSON.

    Returns
    -------
    shapely.geometry.base.BaseGeometry
    """
    _require_shapely("decode_geometry")
    import shapely.geometry  # local import – already guarded

    if payload.geometry_wkt is not None:
        return _swkt.loads(payload.geometry_wkt)
    if payload.geometry_wkb is not None:
        return _swkb.loads(payload.geometry_wkb)
    if payload.geometry_geojson is not None:
        return shapely.geometry.shape(payload.geometry_geojson)
    raise ValueError("GeometryPayload has no geometry data (wkt, wkb, and geojson are all None)")


def payload_to_spark_row(payload: GeometryPayload) -> Dict[str, Any]:
    """Convert a :class:`GeometryPayload` to a Spark-safe ``dict``.

    Binary ``geometry_wkb`` is base64-encoded to a string; ``geometry_geojson``
    is JSON-serialised.  All resulting values are plain strings (or ``None``).
    """
    row: Dict[str, Any] = {
        "geometry_wkt": payload.geometry_wkt,
        "geometry_wkb_b64": (
            base64.b64encode(payload.geometry_wkb).decode("ascii")
            if payload.geometry_wkb is not None
            else None
        ),
        "geometry_geojson": (
            json.dumps(payload.geometry_geojson)
            if payload.geometry_geojson is not None
            else None
        ),
        "crs": payload.crs,
        "geometry_type": payload.geometry_type,
    }
    return row


def spark_row_to_payload(row: Dict[str, Any]) -> GeometryPayload:
    """Reconstruct a :class:`GeometryPayload` from a Spark-row ``dict``.

    Reverses the encoding performed by :func:`payload_to_spark_row`.
    """
    wkb_b64 = row.get("geometry_wkb_b64")
    geojson_str = row.get("geometry_geojson")

    return GeometryPayload(
        geometry_wkt=row.get("geometry_wkt"),
        geometry_wkb=(
            base64.b64decode(wkb_b64) if wkb_b64 is not None else None
        ),
        geometry_geojson=(
            json.loads(geojson_str) if geojson_str is not None else None
        ),
        crs=row.get("crs", "EPSG:4326"),
        geometry_type=row.get("geometry_type"),
    )
