"""
Django REST Framework GeoJSON serializers for Census boundary models.

Requires djangorestframework-gis for GeoJSON serialization.
"""

from rest_framework import serializers

try:
    from rest_framework_gis.serializers import GeoFeatureModelSerializer
except ImportError:
    # Fallback if rest_framework_gis is not installed
    GeoFeatureModelSerializer = serializers.ModelSerializer


class CensusBoundarySerializer(GeoFeatureModelSerializer):
    """Base serializer for Census boundary models."""

    total_area = serializers.ReadOnlyField()
    land_percentage = serializers.ReadOnlyField()

    class Meta:
        abstract = True
        geo_field = "geometry"
        fields = [
            "id",
            "geoid",
            "name",
            "census_year",
            "aland",
            "awater",
            "total_area",
            "land_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StateSerializer(CensusBoundarySerializer):
    """Serializer for State boundaries."""

    from ..models import State

    class Meta(CensusBoundarySerializer.Meta):
        model = State
        fields = CensusBoundarySerializer.Meta.fields + [
            "state_fips",
            "abbreviation",
            "functional_status",
        ]


class CountySerializer(CensusBoundarySerializer):
    """Serializer for County boundaries."""

    from ..models import County

    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusBoundarySerializer.Meta):
        model = County
        fields = CensusBoundarySerializer.Meta.fields + [
            "state_fips",
            "county_fips",
            "county_name",
            "legal_statistical_area",
            "state_name",
        ]


class TractSerializer(CensusBoundarySerializer):
    """Serializer for Census Tract boundaries."""

    from ..models import Tract

    tract_number = serializers.ReadOnlyField()
    county_name = serializers.CharField(source="county.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusBoundarySerializer.Meta):
        model = Tract
        fields = CensusBoundarySerializer.Meta.fields + [
            "state_fips",
            "county_fips",
            "tract_code",
            "tract_number",
            "county_name",
            "state_name",
        ]


class BlockGroupSerializer(CensusBoundarySerializer):
    """Serializer for Block Group boundaries."""

    from ..models import BlockGroup

    tract_number = serializers.CharField(source="tract.tract_number", read_only=True)

    class Meta(CensusBoundarySerializer.Meta):
        model = BlockGroup
        fields = CensusBoundarySerializer.Meta.fields + [
            "state_fips",
            "county_fips",
            "tract_code",
            "block_group",
            "tract_number",
        ]


class PlaceSerializer(CensusBoundarySerializer):
    """Serializer for Place boundaries."""

    from ..models import Place

    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusBoundarySerializer.Meta):
        model = Place
        fields = CensusBoundarySerializer.Meta.fields + [
            "state_fips",
            "place_fips",
            "place_type",
            "functional_status",
            "state_name",
        ]


class ZCTASerializer(CensusBoundarySerializer):
    """Serializer for ZCTA boundaries."""

    from ..models import ZCTA

    class Meta(CensusBoundarySerializer.Meta):
        model = ZCTA
        fields = CensusBoundarySerializer.Meta.fields + ["zcta5"]


class CongressionalDistrictSerializer(CensusBoundarySerializer):
    """Serializer for Congressional District boundaries."""

    from ..models import CongressionalDistrict

    is_at_large = serializers.ReadOnlyField()
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta(CensusBoundarySerializer.Meta):
        model = CongressionalDistrict
        fields = CensusBoundarySerializer.Meta.fields + [
            "state_fips",
            "district_number",
            "congress_number",
            "session",
            "is_at_large",
            "state_name",
        ]


class DemographicSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for DemographicSnapshot."""

    from ..models import DemographicSnapshot

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

    This serializer combines boundary geometry with demographic values
    into a single GeoJSON response.
    """

    # Boundary fields
    geoid = serializers.CharField()
    name = serializers.CharField()
    geometry = serializers.SerializerMethodField()
    census_year = serializers.IntegerField()
    aland = serializers.IntegerField()
    awater = serializers.IntegerField()

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
            "census_year",
            "aland",
            "awater",
            "demographics",
            "total_population",
            "median_household_income",
        ]


class BoundaryCrosswalkSerializer(serializers.ModelSerializer):
    """Serializer for BoundaryCrosswalk."""

    from ..models import BoundaryCrosswalk

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
