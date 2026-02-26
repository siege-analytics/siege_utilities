"""
Geographic boundary Django models.

Provides GeoDjango models for storing temporal geographic features at
multiple levels — Census TIGER/Line, GADM, political, education, federal,
and intersection/crosswalk relationships.

Model hierarchy:
    TemporalGeographicFeature (root abstract — no geometry)
    ├── TemporalBoundary (abstract — MultiPolygon)
    │   ├── CensusTIGERBoundary (abstract — GEOID + TIGER metadata)
    │   │   ├── State, County, Tract, BlockGroup, Block, Place, ZCTA, CD
    │   │   ├── StateLegislativeUpper, StateLegislativeLower, VTD, Precinct
    │   │   └── SchoolDistrictElementary, Secondary, Unified
    │   ├── GADMBoundary (abstract)
    │   │   └── GADMCountry, GADMAdmin1-5
    │   ├── NLRBRegion, FederalJudicialDistrict
    │   └── (intersections — 14.7)
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
from .political import (
    StateLegislativeUpper,
    StateLegislativeLower,
    VTD,
    Precinct,
)
from .gadm import (
    GADMBoundary,
    GADMCountry,
    GADMAdmin1,
    GADMAdmin2,
    GADMAdmin3,
    GADMAdmin4,
    GADMAdmin5,
)
from .education import (
    SchoolDistrictBase,
    SchoolDistrictElementary,
    SchoolDistrictSecondary,
    SchoolDistrictUnified,
)
from .federal import (
    NLRBRegion,
    FederalJudicialDistrict,
)
from .census_extended import (
    CBSA,
    UrbanArea,
)
from .intersections import (
    BoundaryIntersection,
    CountyCDIntersection,
    VTDCDIntersection,
    TractCDIntersection,
)
from .demographics import (
    DemographicVariable,
    DemographicSnapshot,
    DemographicTimeSeries,
)
from .crosswalks import (
    TemporalCrosswalk,
    BoundaryCrosswalk,  # deprecated alias
    CrosswalkDataset,
)

__all__ = [
    # Base abstracts
    "TemporalGeographicFeature",
    "TemporalBoundary",
    "CensusTIGERBoundary",
    "TemporalLinearFeature",
    "TemporalPointFeature",
    "CensusBoundary",  # deprecated alias
    # Census TIGER boundaries
    "State",
    "County",
    "Tract",
    "BlockGroup",
    "Block",
    "Place",
    "ZCTA",
    "CongressionalDistrict",
    # Political
    "StateLegislativeUpper",
    "StateLegislativeLower",
    "VTD",
    "Precinct",
    # GADM
    "GADMBoundary",
    "GADMCountry",
    "GADMAdmin1",
    "GADMAdmin2",
    "GADMAdmin3",
    "GADMAdmin4",
    "GADMAdmin5",
    # Education (NCES)
    "SchoolDistrictBase",
    "SchoolDistrictElementary",
    "SchoolDistrictSecondary",
    "SchoolDistrictUnified",
    # Federal
    "NLRBRegion",
    "FederalJudicialDistrict",
    # Census Extended
    "CBSA",
    "UrbanArea",
    # Intersections
    "BoundaryIntersection",
    "CountyCDIntersection",
    "VTDCDIntersection",
    "TractCDIntersection",
    # Demographics
    "DemographicVariable",
    "DemographicSnapshot",
    "DemographicTimeSeries",
    # Crosswalks
    "TemporalCrosswalk",
    "BoundaryCrosswalk",  # deprecated alias
    "CrosswalkDataset",
]
