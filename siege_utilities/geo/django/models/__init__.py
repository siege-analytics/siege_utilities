"""
Census boundary Django models.

This module provides GeoDjango models for storing Census geographic boundaries
at multiple levels (state, county, tract, block group, block, place, ZCTA, CD).

Each model includes:
- GEOID (unique identifier)
- Name
- Geometry (MultiPolygon)
- Census year
- Land and water area
- Parent relationships (where applicable)
"""

from .base import CensusBoundary
from .boundaries import (
    State,
    County,
    Tract,
    BlockGroup,
    Block,
    Place,
    ZCTA,
    CongressionalDistrict,
)
from .demographics import DemographicSnapshot, DemographicVariable
from .crosswalks import BoundaryCrosswalk

__all__ = [
    # Base
    "CensusBoundary",
    # Boundaries
    "State",
    "County",
    "Tract",
    "BlockGroup",
    "Block",
    "Place",
    "ZCTA",
    "CongressionalDistrict",
    # Demographics
    "DemographicSnapshot",
    "DemographicVariable",
    # Crosswalks
    "BoundaryCrosswalk",
]
