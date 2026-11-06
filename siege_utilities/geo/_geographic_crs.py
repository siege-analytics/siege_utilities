"""Private CRS normalization for APIs that consume longitude/latitude."""

from numbers import Real
from typing import Any


def _check_coordinate(value: float, limit: int, axis: str, function: str) -> None:
    if value < -limit or value > limit:
        raise ValueError(
            f"{function}: {axis} {value} is outside [-{limit}, {limit}] "
            "with no CRS. Set the input CRS before passing projected coordinates."
        )


def _validate_geographic(geometry: Any, function: str) -> None:
    """Reject out-of-range coordinates without requiring optional geo imports."""
    if hasattr(geometry, "bounds"):
        minx, miny, maxx, maxy = geometry.bounds
        for value, limit, axis in (
            (minx, 180, "longitude"), (maxx, 180, "longitude"),
            (miny, 90, "latitude"), (maxy, 90, "latitude"),
        ):
            _check_coordinate(value, limit, axis, function)
        return

    geojson = geometry if isinstance(geometry, dict) else getattr(geometry, "__geo_interface__", {})
    pending = [geojson.get("coordinates", ())]
    while pending:
        coordinates = pending.pop()
        if len(coordinates) == 0:
            continue
        if isinstance(coordinates[0], Real):
            _check_coordinate(coordinates[0], 180, "longitude", function)
            _check_coordinate(coordinates[1], 90, "latitude", function)
        else:
            pending.extend(coordinates)


def _geographic_geometries(geometries: Any, crs: str, function: str) -> Any:
    """Return a geographic geometry series without changing caller data."""
    source_crs = getattr(geometries, "crs", None)
    if source_crs is not None:
        return geometries if source_crs == crs else geometries.to_crs(crs)
    for geometry in geometries:
        _validate_geographic(geometry, function)
    return geometries


def _geographic_polygon(geometry: Any, crs: str, function: str) -> Any:
    """Normalize a frame/series to its polygon union, or validate a bare shape."""
    if hasattr(geometry, "crs") and hasattr(geometry, "geometry"):
        # GeoPandas inputs already require Shapely; bare H3 GeoJSON does not.
        from shapely.ops import unary_union

        geometries = _geographic_geometries(geometry.geometry, crs, function)
        return unary_union(geometries)
    _validate_geographic(geometry, function)
    return geometry
