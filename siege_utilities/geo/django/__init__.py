"""
GeoDjango integration for temporal geographic feature data.

This module provides Django models for storing and querying geographic
boundaries with full GeoDjango spatial support and temporal validity tracking.

Requirements:
    - Django >= 4.2
    - djangorestframework-gis >= 1.0
    - PostGIS database

Usage:
    Add 'siege_utilities.geo.django' to INSTALLED_APPS.

Example:
    >>> from siege_utilities.geo.django.models import State, County, Tract
    >>> from siege_utilities.geo.django.services import BoundaryPopulationService

    # Fetch boundaries containing a point
    >>> from django.contrib.gis.geos import Point
    >>> point = Point(-122.4194, 37.7749, srid=4326)
    >>> tract = Tract.objects.filter(geometry__contains=point).first()

    # Populate boundaries from TIGER/Line
    >>> service = BoundaryPopulationService()
    >>> service.populate_counties(year=2020, state_fips='06')
"""

from __future__ import annotations

import importlib.util
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

# Check for Django availability
_django_available = importlib.util.find_spec("django") is not None
_gis_available = False

# Auto-detect GDAL library on macOS if not already set.
# Django's libgdal.py reads GDAL_LIBRARY_PATH from django.conf.settings,
# but that only works when DJANGO_SETTINGS_MODULE is configured.
# Setting the env var ensures GDAL is found in all contexts (notebooks, tests, CLI).
if "GDAL_LIBRARY_PATH" not in os.environ and platform.system() == "Darwin":
    for _candidate in (
        "/opt/homebrew/lib/libgdal.dylib",   # Apple Silicon Homebrew
        "/usr/local/lib/libgdal.dylib",       # Intel Homebrew
    ):
        if Path(_candidate).exists():
            os.environ["GDAL_LIBRARY_PATH"] = _candidate
            break

if "GEOS_LIBRARY_PATH" not in os.environ and platform.system() == "Darwin":
    for _candidate in (
        "/opt/homebrew/lib/libgeos_c.dylib",
        "/usr/local/lib/libgeos_c.dylib",
    ):
        if Path(_candidate).exists():
            os.environ["GEOS_LIBRARY_PATH"] = _candidate
            break

if _django_available:
    try:
        from django.contrib.gis.db import models as gis_models
        _gis_available = True
    except Exception:
        # ImportError: django.contrib.gis not installed
        # ImproperlyConfigured: GDAL C library not found on system
        _gis_available = False

# Lazy imports to avoid import errors when Django is not installed
if TYPE_CHECKING:
    from .models import (
        TemporalGeographicFeature,
        TemporalBoundary,
        CensusTIGERBoundary,
        TemporalLinearFeature,
        TemporalPointFeature,
        CensusBoundary,
        State,
        County,
        Tract,
        BlockGroup,
        Block,
        Place,
        ZCTA,
        CongressionalDistrict,
        StateLegislativeUpper,
        StateLegislativeLower,
        VTD,
        Precinct,
        GADMBoundary,
        GADMCountry,
        GADMAdmin1,
        GADMAdmin2,
        GADMAdmin3,
        GADMAdmin4,
        GADMAdmin5,
        SchoolDistrictBase,
        SchoolDistrictElementary,
        SchoolDistrictSecondary,
        SchoolDistrictUnified,
        NLRBRegion,
        FederalJudicialDistrict,
        CBSA,
        UrbanArea,
        BoundaryIntersection,
        CountyCDIntersection,
        VTDCDIntersection,
        TractCDIntersection,
        TemporalCrosswalk,
        BoundaryCrosswalk,
        CrosswalkDataset,
        DemographicSnapshot,
        DemographicVariable,
        DemographicTimeSeries,
    )
    from .services import (
        BoundaryPopulationService,
        DemographicPopulationService,
        CrosswalkPopulationService,
    )
    from .serializers import (
        TemporalBoundarySerializer,
        CensusTIGERSerializer,
        StateSerializer,
        CountySerializer,
        TractSerializer,
        BoundaryWithDemographicsSerializer,
    )


def _check_dependencies():
    """Check that Django and GeoDjango are available."""
    if not _django_available:
        raise ImportError(
            "Django is not installed. Install it with: pip install django>=4.2"
        )
    if not _gis_available:
        raise ImportError(
            "GeoDjango is not available. Ensure you have a spatial database "
            "(PostGIS, SpatiaLite) configured and django.contrib.gis installed."
        )


def get_model(model_name: str):
    """
    Lazily import a model by name.

    Args:
        model_name: Name of the model (e.g., 'State', 'County', 'Tract')

    Returns:
        The Django model class

    Raises:
        ImportError: If Django/GeoDjango is not available
        ValueError: If the model name is not recognized
    """
    _check_dependencies()
    from . import models as model_module

    if not hasattr(model_module, model_name):
        raise ValueError(f"Unknown model: {model_name}")
    return getattr(model_module, model_name)


def get_service(service_name: str):
    """
    Lazily import a service by name.

    Args:
        service_name: Name of the service (e.g., 'BoundaryPopulationService')

    Returns:
        The service class

    Raises:
        ImportError: If Django/GeoDjango is not available
    """
    _check_dependencies()
    from . import services as services_module

    if not hasattr(services_module, service_name):
        raise ValueError(f"Unknown service: {service_name}")
    return getattr(services_module, service_name)


# Version info — matches package version
__version__ = "3.0.0"

__all__ = [
    # Models (lazy)
    "get_model",
    "get_service",
    # Version
    "__version__",
    # Availability checks
    "_django_available",
    "_gis_available",
]
