"""
Geographic boundary Django models.

Provides GeoDjango models for storing temporal geographic features at
multiple levels — Census TIGER/Line, GADM, political, education, federal,
and intersection/crosswalk relationships.

Model hierarchy:
    TemporalGeographicFeature (root abstract — no geometry)
    ├── TemporalBoundary (abstract — MultiPolygon)
    │   └── CensusTIGERBoundary (abstract — GEOID + TIGER metadata)
    │       ├── State, County, Tract, BlockGroup, Block
    │       ├── Place, ZCTA, CongressionalDistrict
    │       └── (political, education, census_extended models)
    ├── TemporalLinearFeature (abstract — MultiLineString)
    └── TemporalPointFeature (abstract — Point)
"""

from .base import (
    TemporalGeographicFeature,
    TemporalBoundary,
    CensusTIGERBoundary,
    TemporalLinearFeature,
    TemporalPointFeature,
    CensusBoundary,  # deprecated alias
)
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
from .demographics import (
    DemographicVariable,
    DemographicSnapshot,
    DemographicTimeSeries,
)
from .crosswalks import (
    BoundaryCrosswalk,
    CrosswalkDataset,
)

__all__ = [
    # Base abstracts
    "TemporalGeographicFeature",
    "TemporalBoundary",
    "CensusTIGERBoundary",
    "TemporalLinearFeature",
    "TemporalPointFeature",
    # Deprecated alias
    "CensusBoundary",
    # Census TIGER boundaries
    "State",
    "County",
    "Tract",
    "BlockGroup",
    "Block",
    "Place",
    "ZCTA",
    "CongressionalDistrict",
    # Demographics
    "DemographicVariable",
    "DemographicSnapshot",
    "DemographicTimeSeries",
    # Crosswalks
    "BoundaryCrosswalk",
    "CrosswalkDataset",
]
