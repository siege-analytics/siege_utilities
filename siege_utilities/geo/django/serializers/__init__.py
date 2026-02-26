"""
Django REST Framework serializers for geographic boundary data.
"""

from .boundary_serializers import (
    TemporalBoundarySerializer,
    CensusTIGERSerializer,
    CensusBoundarySerializer,  # deprecated alias
    StateSerializer,
    CountySerializer,
    TractSerializer,
    BlockGroupSerializer,
    PlaceSerializer,
    ZCTASerializer,
    CongressionalDistrictSerializer,
    BoundaryWithDemographicsSerializer,
    DemographicSnapshotSerializer,
    BoundaryCrosswalkSerializer,
    get_boundary_serializer,
)

__all__ = [
    "TemporalBoundarySerializer",
    "CensusTIGERSerializer",
    "CensusBoundarySerializer",
    "StateSerializer",
    "CountySerializer",
    "TractSerializer",
    "BlockGroupSerializer",
    "PlaceSerializer",
    "ZCTASerializer",
    "CongressionalDistrictSerializer",
    "BoundaryWithDemographicsSerializer",
    "DemographicSnapshotSerializer",
    "BoundaryCrosswalkSerializer",
    "get_boundary_serializer",
]
