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
    │   │   ├── PlanDistrict (redistricting plan districts)
    │   │   └── SchoolDistrictElementary, Secondary, Unified
    │   ├── GADMBoundary (abstract)
    │   │   └── GADMCountry, GADMAdmin1-5
    │   ├── NLRBRegion, FederalJudicialDistrict
    │   ├── TimezoneGeometry
    │   ├── IsochroneResult
    │   └── (intersections — 14.7)
    ├── TemporalLinearFeature (abstract — MultiLineString)
    ├── TemporalPointFeature (abstract — Point)
    └── SpatioTemporalEvent (GeometryCollection — discrete events)

Non-spatial temporal models:
    CongressionalTerm, Seat, StateElectionCalendar (Phase A)
    Race, RaceEvent, ReturnSnapshot (Phase B)
    PlanDistrictAssignment (Phase C — GenericFK to boundary)
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
    NCESLocaleBoundary,
    SchoolLocation,
)
from .federal import (
    NLRBRegion,
    FederalJudicialDistrict,
)
from .timezone import (
    TimezoneGeometry,
)
from .isochrone import (
    IsochroneResult,
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
from .redistricting import (
    RedistrictingPlan,
    PlanDistrict,
    DistrictDemographics,
    PrecinctElectionResult,
    PlanDistrictAssignment,
)
from .temporal_political import (
    CongressionalTerm,
    Seat,
    StateElectionCalendar,
)
from .temporal_events import (
    Race,
    RaceEvent,
    SpatioTemporalEvent,
    ReturnSnapshot,
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
    "NCESLocaleBoundary",
    "SchoolLocation",
    # Federal
    "NLRBRegion",
    "FederalJudicialDistrict",
    # Timezone
    "TimezoneGeometry",
    # Isochrone
    "IsochroneResult",
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
    # Redistricting
    "RedistrictingPlan",
    "PlanDistrict",
    "DistrictDemographics",
    "PrecinctElectionResult",
    "PlanDistrictAssignment",
    # Temporal Political (Phase A)
    "CongressionalTerm",
    "Seat",
    "StateElectionCalendar",
    # Temporal Events (Phase B)
    "Race",
    "RaceEvent",
    "SpatioTemporalEvent",
    "ReturnSnapshot",
]
