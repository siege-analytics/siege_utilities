"""
Tests for the temporal geographic feature model hierarchy.

Tests the abstract base classes: TemporalGeographicFeature, TemporalBoundary,
CensusTIGERBoundary, TemporalLinearFeature, TemporalPointFeature.

Since these are abstract models, we test their fields, properties, and methods
by inspecting the class definitions rather than instantiating them directly.
"""

import os
import warnings
from datetime import date

import django
from django.conf import settings as django_settings

# Configure Django before any model imports
if not django_settings.configured:
    django_settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.postgis",
                "NAME": "test_siege_geo",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.gis",
            "siege_utilities.geo.django",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()

import pytest


class TestTemporalGeographicFeature:
    """Tests for the root abstract model."""

    def test_import(self):
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        assert TemporalGeographicFeature is not None

    def test_is_abstract(self):
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        assert TemporalGeographicFeature._meta.abstract is True

    def test_has_required_fields(self):
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        field_names = {f.name for f in TemporalGeographicFeature._meta.get_fields()}
        expected = {"feature_id", "name", "vintage_year", "valid_from", "valid_to", "source"}
        assert expected.issubset(field_names)

    def test_has_timestamps(self):
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        field_names = {f.name for f in TemporalGeographicFeature._meta.get_fields()}
        assert "created_at" in field_names
        assert "updated_at" in field_names

    def test_vintage_year_validators(self):
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        field = TemporalGeographicFeature._meta.get_field("vintage_year")
        min_vals = [v.limit_value for v in field.validators if hasattr(v, "limit_value") and v.code == "min_value"]
        max_vals = [v.limit_value for v in field.validators if hasattr(v, "limit_value") and v.code == "max_value"]
        assert 1790 in min_vals
        assert 2100 in max_vals

    def test_ordering(self):
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        assert TemporalGeographicFeature._meta.ordering == ["feature_id"]

    def test_no_geometry_field(self):
        """Root abstract should NOT have a geometry field."""
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature
        field_names = {f.name for f in TemporalGeographicFeature._meta.get_fields()}
        assert "geometry" not in field_names


class TestTemporalBoundary:
    """Tests for the polygon/area abstract model."""

    def test_import(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        assert TemporalBoundary is not None

    def test_is_abstract(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        assert TemporalBoundary._meta.abstract is True

    def test_inherits_temporal_geographic_feature(self):
        from siege_utilities.geo.django.models.base import (
            TemporalGeographicFeature,
            TemporalBoundary,
        )
        assert issubclass(TemporalBoundary, TemporalGeographicFeature)

    def test_has_geometry_field(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        field = TemporalBoundary._meta.get_field("geometry")
        assert field.__class__.__name__ == "MultiPolygonField"

    def test_geometry_srid_4326(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        field = TemporalBoundary._meta.get_field("geometry")
        assert field.srid == 4326

    def test_has_boundary_specific_fields(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        field_names = {f.name for f in TemporalBoundary._meta.get_fields()}
        expected = {"boundary_id", "geometry", "area_land", "area_water", "internal_point"}
        assert expected.issubset(field_names)

    def test_has_internal_point(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        field = TemporalBoundary._meta.get_field("internal_point")
        assert field.__class__.__name__ == "PointField"
        assert field.null is True

    def test_inherits_temporal_fields(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        field_names = {f.name for f in TemporalBoundary._meta.get_fields()}
        assert "valid_from" in field_names
        assert "valid_to" in field_names
        assert "vintage_year" in field_names


class TestCensusTIGERBoundary:
    """Tests for the Census TIGER abstract model."""

    def test_import(self):
        from siege_utilities.geo.django.models.base import CensusTIGERBoundary
        assert CensusTIGERBoundary is not None

    def test_is_abstract(self):
        from siege_utilities.geo.django.models.base import CensusTIGERBoundary
        assert CensusTIGERBoundary._meta.abstract is True

    def test_inherits_temporal_boundary(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary, CensusTIGERBoundary
        assert issubclass(CensusTIGERBoundary, TemporalBoundary)

    def test_has_tiger_fields(self):
        from siege_utilities.geo.django.models.base import CensusTIGERBoundary
        field_names = {f.name for f in CensusTIGERBoundary._meta.get_fields()}
        expected = {"geoid", "state_fips", "lsad", "mtfcc", "funcstat"}
        assert expected.issubset(field_names)

    def test_ordering_by_geoid(self):
        from siege_utilities.geo.django.models.base import CensusTIGERBoundary
        assert CensusTIGERBoundary._meta.ordering == ["geoid"]

    def test_get_geoid_length_raises(self):
        from siege_utilities.geo.django.models.base import CensusTIGERBoundary
        with pytest.raises(NotImplementedError):
            CensusTIGERBoundary.get_geoid_length()

    def test_parse_geoid_raises(self):
        from siege_utilities.geo.django.models.base import CensusTIGERBoundary
        with pytest.raises(NotImplementedError):
            CensusTIGERBoundary.parse_geoid("06")


class TestTemporalLinearFeature:
    """Tests for the linear feature abstract model."""

    def test_import(self):
        from siege_utilities.geo.django.models.base import TemporalLinearFeature
        assert TemporalLinearFeature is not None

    def test_is_abstract(self):
        from siege_utilities.geo.django.models.base import TemporalLinearFeature
        assert TemporalLinearFeature._meta.abstract is True

    def test_inherits_temporal_geographic_feature(self):
        from siege_utilities.geo.django.models.base import (
            TemporalGeographicFeature,
            TemporalLinearFeature,
        )
        assert issubclass(TemporalLinearFeature, TemporalGeographicFeature)

    def test_has_multilinestring_geometry(self):
        from siege_utilities.geo.django.models.base import TemporalLinearFeature
        field = TemporalLinearFeature._meta.get_field("geometry")
        assert field.__class__.__name__ == "MultiLineStringField"
        assert field.srid == 4326

    def test_has_length_field(self):
        from siege_utilities.geo.django.models.base import TemporalLinearFeature
        field = TemporalLinearFeature._meta.get_field("length_meters")
        assert field.null is True


class TestTemporalPointFeature:
    """Tests for the point feature abstract model."""

    def test_import(self):
        from siege_utilities.geo.django.models.base import TemporalPointFeature
        assert TemporalPointFeature is not None

    def test_is_abstract(self):
        from siege_utilities.geo.django.models.base import TemporalPointFeature
        assert TemporalPointFeature._meta.abstract is True

    def test_inherits_temporal_geographic_feature(self):
        from siege_utilities.geo.django.models.base import (
            TemporalGeographicFeature,
            TemporalPointFeature,
        )
        assert issubclass(TemporalPointFeature, TemporalGeographicFeature)

    def test_has_point_geometry(self):
        from siege_utilities.geo.django.models.base import TemporalPointFeature
        field = TemporalPointFeature._meta.get_field("geometry")
        assert field.__class__.__name__ == "PointField"
        assert field.srid == 4326


class TestDeprecatedAlias:
    """Tests for the CensusBoundary deprecated alias."""

    def test_census_boundary_alias_exists(self):
        from siege_utilities.geo.django.models.base import CensusBoundary, CensusTIGERBoundary
        assert CensusBoundary is CensusTIGERBoundary

    def test_census_boundary_is_importable_from_models(self):
        """CensusBoundary should still be importable from models for backwards compat."""
        from siege_utilities.geo.django.models.base import CensusBoundary
        assert CensusBoundary is not None


class TestInheritanceChain:
    """Tests verifying the complete inheritance hierarchy."""

    def test_full_chain(self):
        from siege_utilities.geo.django.models.base import (
            TemporalGeographicFeature,
            TemporalBoundary,
            CensusTIGERBoundary,
            TemporalLinearFeature,
            TemporalPointFeature,
        )
        # TemporalBoundary → TemporalGeographicFeature
        assert issubclass(TemporalBoundary, TemporalGeographicFeature)
        # CensusTIGERBoundary → TemporalBoundary → TemporalGeographicFeature
        assert issubclass(CensusTIGERBoundary, TemporalBoundary)
        assert issubclass(CensusTIGERBoundary, TemporalGeographicFeature)
        # Linear and Point → TemporalGeographicFeature (NOT TemporalBoundary)
        assert issubclass(TemporalLinearFeature, TemporalGeographicFeature)
        assert not issubclass(TemporalLinearFeature, TemporalBoundary)
        assert issubclass(TemporalPointFeature, TemporalGeographicFeature)
        assert not issubclass(TemporalPointFeature, TemporalBoundary)

    def test_all_are_abstract(self):
        from siege_utilities.geo.django.models.base import (
            TemporalGeographicFeature,
            TemporalBoundary,
            CensusTIGERBoundary,
            TemporalLinearFeature,
            TemporalPointFeature,
        )
        for cls in [
            TemporalGeographicFeature,
            TemporalBoundary,
            CensusTIGERBoundary,
            TemporalLinearFeature,
            TemporalPointFeature,
        ]:
            assert cls._meta.abstract is True, f"{cls.__name__} should be abstract"
