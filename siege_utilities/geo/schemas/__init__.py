"""
Pydantic schema layer for geographic models.

Provides validation schemas that mirror the Django models but without geometry
(geometry handled via GeoDataFrame/WKT).  Designed for:
- API serialization/validation
- Data pipeline intermediate representations
- Round-trip conversion: GeoDataFrame ↔ Schema ↔ ORM

Usage:
    from siege_utilities.geo.schemas import StateSchema, CountySchema
    from siege_utilities.geo.schemas.converters import gdf_to_schemas, schemas_to_orm
"""

from .base import (
    TemporalGeographicFeatureSchema,
    TemporalBoundarySchema,
    CensusTIGERSchema,
)
from .boundaries import (
    StateSchema,
    CountySchema,
    TractSchema,
    BlockGroupSchema,
    BlockSchema,
    PlaceSchema,
    ZCTASchema,
    CongressionalDistrictSchema,
)
from .political import (
    StateLegislativeUpperSchema,
    StateLegislativeLowerSchema,
    VTDSchema,
    PrecinctSchema,
)
from .gadm import (
    GADMBoundarySchema,
    GADMCountrySchema,
    GADMAdmin1Schema,
    GADMAdmin2Schema,
    GADMAdmin3Schema,
    GADMAdmin4Schema,
    GADMAdmin5Schema,
)
from .education import (
    SchoolDistrictBaseSchema,
    SchoolDistrictElementarySchema,
    SchoolDistrictSecondarySchema,
    SchoolDistrictUnifiedSchema,
)
from .federal import (
    NLRBRegionSchema,
    FederalJudicialDistrictSchema,
)
from .intersections import (
    BoundaryIntersectionSchema,
    CountyCDIntersectionSchema,
    VTDCDIntersectionSchema,
    TractCDIntersectionSchema,
)
from .crosswalks import (
    TemporalCrosswalkSchema,
)

__all__ = [
    # Base
    "TemporalGeographicFeatureSchema",
    "TemporalBoundarySchema",
    "CensusTIGERSchema",
    # Census boundaries
    "StateSchema",
    "CountySchema",
    "TractSchema",
    "BlockGroupSchema",
    "BlockSchema",
    "PlaceSchema",
    "ZCTASchema",
    "CongressionalDistrictSchema",
    # Political
    "StateLegislativeUpperSchema",
    "StateLegislativeLowerSchema",
    "VTDSchema",
    "PrecinctSchema",
    # GADM
    "GADMBoundarySchema",
    "GADMCountrySchema",
    "GADMAdmin1Schema",
    "GADMAdmin2Schema",
    "GADMAdmin3Schema",
    "GADMAdmin4Schema",
    "GADMAdmin5Schema",
    # Education
    "SchoolDistrictBaseSchema",
    "SchoolDistrictElementarySchema",
    "SchoolDistrictSecondarySchema",
    "SchoolDistrictUnifiedSchema",
    # Federal
    "NLRBRegionSchema",
    "FederalJudicialDistrictSchema",
    # Intersections
    "BoundaryIntersectionSchema",
    "CountyCDIntersectionSchema",
    "VTDCDIntersectionSchema",
    "TractCDIntersectionSchema",
    # Crosswalks
    "TemporalCrosswalkSchema",
]
