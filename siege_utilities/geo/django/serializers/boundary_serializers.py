"""
Django REST Framework GeoJSON serializers for geographic boundary models.

Requires djangorestframework-gis for GeoJSON serialization.
"""

from rest_framework import serializers

try:
    from rest_framework_gis.serializers import GeoFeatureModelSerializer
except ImportError:
    # Fallback if rest_framework_gis is not installed
    GeoFeatureModelSerializer = serializers.ModelSerializer

try:
    from ..models import (
        State, County, Tract, BlockGroup, Place, ZCTA,
        CongressionalDistrict, DemographicSnapshot, BoundaryCrosswalk,
    )
except ImportError:
    State = County = Tract = BlockGroup = Place = ZCTA = None
    CongressionalDistrict = DemographicSnapshot = BoundaryCrosswalk = None


class TemporalBoundarySerializer(GeoFeatureModelSerializer):
    """Base serializer for all temporal boundary models."""

    total_area = serializers.ReadOnlyField()
    land_percentage = serializers.ReadOnlyField()
    is_current = serializers.ReadOnlyField()

    class Meta:
        abstract = True
        geo_field = "geometry"
        fields = [
            "id",
            "feature_id",
            "boundary_id",
            "name",
            "vintage_year",
            "valid_from",
            "valid_to",
            "source",
            "area_land",
            "area_water",
            "internal_point",
            "total_area",
            "land_percentage",
            "is_current",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CensusTIGERSerializer(TemporalBoundarySerializer):
    """Base serializer for Census TIGER/Line boundary models."""

    class Meta(TemporalBoundarySerializer.Meta):
        abstract = True
        fields = TemporalBoundarySerializer.Meta.fields + [
            "geoid",
            "state_fips",
            "lsad",
            "mtfcc",
            "funcstat",
        ]


# Keep old name as alias for backwards compatibility
CensusBoundarySerializer = CensusTIGERSerializer


class StateSerializer(CensusTIGERSerializer):
    """Serializer for State boundaries."""

    class Meta(CensusTIGERSerializer.Meta):
        model = State
        fields = CensusTIGERSerializer.Meta.fields + [
            "abbreviation",
            "region",
            "division",
        ]


class CountySerializer(CensusTIGERSerializer):
    """Serializer for County boundaries."""

    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusTIGERSerializer.Meta):
        model = County
        fields = CensusTIGERSerializer.Meta.fields + [
            "county_fips",
            "county_name",
            "state_name",
        ]


class TractSerializer(CensusTIGERSerializer):
    """Serializer for Census Tract boundaries."""

    tract_number = serializers.ReadOnlyField()
    county_name = serializers.CharField(source="county.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusTIGERSerializer.Meta):
        model = Tract
        fields = CensusTIGERSerializer.Meta.fields + [
            "county_fips",
            "tract_code",
            "tract_number",
            "county_name",
            "state_name",
        ]


class BlockGroupSerializer(CensusTIGERSerializer):
    """Serializer for Block Group boundaries."""

    tract_number = serializers.CharField(source="tract.tract_number", read_only=True)

    class Meta(CensusTIGERSerializer.Meta):
        model = BlockGroup
        fields = CensusTIGERSerializer.Meta.fields + [
            "county_fips",
            "tract_code",
            "block_group",
            "tract_number",
        ]


class PlaceSerializer(CensusTIGERSerializer):
    """Serializer for Place boundaries."""

    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusTIGERSerializer.Meta):
        model = Place
        fields = CensusTIGERSerializer.Meta.fields + [
            "place_fips",
            "place_type",
            "state_name",
        ]


class ZCTASerializer(CensusTIGERSerializer):
    """Serializer for ZCTA boundaries."""

    class Meta(CensusTIGERSerializer.Meta):
        model = ZCTA
        fields = CensusTIGERSerializer.Meta.fields + ["zcta5"]


class CongressionalDistrictSerializer(CensusTIGERSerializer):
    """Serializer for Congressional District boundaries."""

    is_at_large = serializers.ReadOnlyField()
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusTIGERSerializer.Meta):
        model = CongressionalDistrict
        fields = CensusTIGERSerializer.Meta.fields + [
            "district_number",
            "congress_number",
            "session",
            "is_at_large",
            "state_name",
        ]


class DemographicSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for DemographicSnapshot."""

    geography_type = serializers.CharField(
        source="content_type.model", read_only=True
    )

    class Meta:
        model = DemographicSnapshot
        fields = [
            "id",
            "object_id",
            "geography_type",
            "year",
            "dataset",
            "vintage",
            "values",
            "moe_values",
            "total_population",
            "median_household_income",
            "median_age",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BoundaryWithDemographicsSerializer(serializers.Serializer):
    """
    Combined serializer for boundary with demographic data.

    Combines boundary geometry with demographic values
    into a single GeoJSON response.
    """

    # Boundary fields (v3 names)
    geoid = serializers.CharField()
    name = serializers.CharField()
    geometry = serializers.SerializerMethodField()
    vintage_year = serializers.IntegerField()
    area_land = serializers.IntegerField()
    area_water = serializers.IntegerField()

    # Demographic fields
    demographics = DemographicSnapshotSerializer(many=True, read_only=True)

    # Computed fields
    total_population = serializers.IntegerField(required=False)
    median_household_income = serializers.IntegerField(required=False)

    def get_geometry(self, obj):
        """Return GeoJSON geometry."""
        if hasattr(obj, "geometry") and obj.geometry:
            return obj.geometry.geojson
        return None

    class Meta:
        fields = [
            "geoid",
            "name",
            "geometry",
            "vintage_year",
            "area_land",
            "area_water",
            "demographics",
            "total_population",
            "median_household_income",
        ]


class BoundaryCrosswalkSerializer(serializers.ModelSerializer):
    """Serializer for BoundaryCrosswalk."""

    is_unchanged = serializers.ReadOnlyField()
    is_one_to_one = serializers.ReadOnlyField()

    class Meta:
        model = BoundaryCrosswalk
        fields = [
            "id",
            "source_geoid",
            "target_geoid",
            "source_year",
            "target_year",
            "geography_type",
            "relationship",
            "weight",
            "weight_type",
            "state_fips",
            "source_population",
            "target_population",
            "allocated_population",
            "area_sq_meters",
            "is_unchanged",
            "is_one_to_one",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# Inline factory functions for quick serializer access
def get_boundary_serializer(geography_type: str):
    """
    Get the appropriate serializer for a geography type.

    Args:
        geography_type: Type of geography (state, county, tract, etc.)

    Returns:
        Serializer class
    """
    serializers_map = {
        "state": StateSerializer,
        "county": CountySerializer,
        "tract": TractSerializer,
        "blockgroup": BlockGroupSerializer,
        "place": PlaceSerializer,
        "zcta": ZCTASerializer,
        "cd": CongressionalDistrictSerializer,
        "congressionaldistrict": CongressionalDistrictSerializer,
    }
    return serializers_map.get(geography_type.lower())
