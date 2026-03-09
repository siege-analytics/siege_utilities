"""
Runtime capability detection for the geo subsystem.

Reports which optional spatial packages are available so callers
can adapt gracefully (e.g. fall back to geo-lite operations when
geopandas is absent).
"""

from __future__ import annotations

import importlib
from typing import Any, Dict


def _probe(module_name: str) -> bool:
    """Return True if *module_name* can be imported."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def geo_capabilities() -> Dict[str, Any]:
    """Detect available spatial packages and report the active tier.

    Returns a dict with boolean flags for each optional package and a
    ``tier`` string (``"geodjango"``, ``"geo"``, ``"geo-lite"``, or
    ``"none"``).

    >>> caps = geo_capabilities()
    >>> caps["tier"]         # e.g. "geo-lite"
    >>> caps["shapely"]      # True / False
    """
    caps: Dict[str, Any] = {}

    # Core geo-lite packages (prebuilt wheels, no GDAL)
    caps["shapely"] = _probe("shapely")
    caps["pyproj"] = _probe("pyproj")
    caps["geopy"] = _probe("geopy")
    caps["censusgeocode"] = _probe("censusgeocode")

    # Full geo (requires GDAL/GEOS/PROJ system libs)
    caps["geopandas"] = _probe("geopandas")
    caps["fiona"] = _probe("fiona")
    caps["rtree"] = _probe("rtree")
    caps["mapclassify"] = _probe("mapclassify")

    # GeoDjango stack
    caps["django_gis"] = _probe("django.contrib.gis")

    # Optional performance / distributed
    caps["duckdb"] = _probe("duckdb")
    caps["sedona"] = _probe("sedona")

    # Determine tier
    if caps["django_gis"] and caps["geopandas"]:
        tier = "geodjango"
    elif caps["geopandas"] and caps["fiona"]:
        tier = "geo"
    elif caps["shapely"] or caps["pyproj"]:
        tier = "geo-lite"
    else:
        tier = "none"

    caps["tier"] = tier
    return caps
