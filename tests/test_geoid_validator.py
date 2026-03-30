"""
Unit tests for GEOIDValidator and GEOID CheckConstraints.

Tests the GEOIDValidator class in geoid_utils.py and verifies that all
concrete boundary models have CheckConstraints on their GEOID fields.
"""

import pytest

from siege_utilities.geo.geoid_utils import GEOIDValidator

# Skip Django-dependent tests if GDAL is not available (CI without geospatial libs)
try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401

    _DJANGO_AVAILABLE = True
except Exception:
    _DJANGO_AVAILABLE = False


class TestGEOIDValidator:
    """Tests for the GEOIDValidator callable."""

    def test_valid_state_geoid(self):
        """A 2-digit state GEOID should pass validation."""
        validator = GEOIDValidator("state")
        # Django validators return None on success, raise ValidationError on failure
        assert validator("06") is None  # California

    def test_valid_county_geoid(self):
        """A 5-digit county GEOID should pass validation."""
        validator = GEOIDValidator("county")
        assert validator("06037") is None  # LA County

    def test_valid_tract_geoid(self):
        """An 11-digit tract GEOID should pass validation."""
        validator = GEOIDValidator("tract")
        assert validator("06037101100") is None

    def test_invalid_geoid_wrong_length(self):
        """GEOID with wrong length should raise ValidationError."""
        from django.core.exceptions import ValidationError

        validator = GEOIDValidator("state")
        with pytest.raises(ValidationError, match="2 digits"):
            validator("123")  # 3 digits, expected 2

    def test_invalid_geoid_non_digits(self):
        """GEOID with non-digit characters should raise ValidationError."""
        from django.core.exceptions import ValidationError

        validator = GEOIDValidator("county")
        with pytest.raises(ValidationError, match="only digits"):
            validator("CA037")

    def test_invalid_geoid_empty(self):
        """Empty GEOID should raise ValidationError."""
        from django.core.exceptions import ValidationError

        validator = GEOIDValidator("state")
        with pytest.raises(ValidationError, match="non-empty string"):
            validator("")

    def test_invalid_geoid_none(self):
        """None GEOID should raise ValidationError."""
        from django.core.exceptions import ValidationError

        validator = GEOIDValidator("state")
        with pytest.raises(ValidationError, match="non-empty string"):
            validator(None)

    def test_equality(self):
        """Two validators with same geography_level should be equal."""
        v1 = GEOIDValidator("tract")
        v2 = GEOIDValidator("tract")
        assert v1 == v2

    def test_inequality(self):
        """Two validators with different geography_levels should not be equal."""
        v1 = GEOIDValidator("tract")
        v2 = GEOIDValidator("county")
        assert v1 != v2

    def test_repr(self):
        """Validator repr should include geography_level."""
        v = GEOIDValidator("county")
        assert "county" in repr(v)

    def test_deconstruct(self):
        """Validator should be deconstructable for Django migrations."""
        v = GEOIDValidator("tract")
        path, args, kwargs = v.deconstruct()
        assert "GEOIDValidator" in path
        assert args == ("tract",)
        assert kwargs == {}


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="GeoDjango/GDAL not available",
)
class TestBoundaryModelConstraints:
    """Verify CheckConstraints exist on all concrete boundary models."""

    EXPECTED_CONSTRAINTS = {
        "State": ("state_geoid_2_digits", r"^\d{2}$"),
        "County": ("county_geoid_5_digits", r"^\d{5}$"),
        "Tract": ("tract_geoid_11_digits", r"^\d{11}$"),
        "BlockGroup": ("blockgroup_geoid_12_digits", r"^\d{12}$"),
        "Block": ("block_geoid_15_digits", r"^\d{15}$"),
        "Place": ("place_geoid_7_digits", r"^\d{7}$"),
        "ZCTA": ("zcta_geoid_5_digits", r"^\d{5}$"),
        "CongressionalDistrict": ("cd_geoid_4_digits", r"^\d{4}$"),
        "StateLegislativeUpper": ("sldu_geoid_5_digits", r"^\d{5}$"),
        "StateLegislativeLower": ("sldl_geoid_5_digits", r"^\d{5}$"),
        "VTD": ("vtd_geoid_8_digits", r"^\d{8}$"),
    }

    @pytest.mark.parametrize(
        "model_name,expected",
        list(EXPECTED_CONSTRAINTS.items()),
        ids=list(EXPECTED_CONSTRAINTS.keys()),
    )
    def test_model_has_geoid_constraint(self, model_name, expected):
        """Each concrete boundary model should have a GEOID CheckConstraint."""
        from siege_utilities.geo.django import models as geo_models

        model_cls = getattr(geo_models, model_name)
        constraint_names = [c.name for c in model_cls._meta.constraints]
        expected_name, _ = expected
        assert expected_name in constraint_names, (
            f"{model_name} missing constraint '{expected_name}'. "
            f"Found: {constraint_names}"
        )


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason="GeoDjango/GDAL not available",
)
class TestTractUrbanicity:
    """Tests for Tract urbanicity field and properties."""

    def test_tract_has_urbanicity_code_field(self):
        """Tract model should have urbanicity_code field."""
        from siege_utilities.geo.django.models import Tract

        field_names = [f.name for f in Tract._meta.get_fields()]
        assert "urbanicity_code" in field_names

    def test_tract_urbanicity_code_is_nullable(self):
        """urbanicity_code should be nullable (not all tracts classified)."""
        from siege_utilities.geo.django.models import Tract

        field = Tract._meta.get_field("urbanicity_code")
        assert field.null is True
        assert field.blank is True

    def test_tract_urbanicity_code_is_indexed(self):
        """urbanicity_code should have a database index."""
        from siege_utilities.geo.django.models import Tract

        field = Tract._meta.get_field("urbanicity_code")
        assert field.db_index is True

    def test_tract_has_urbanicity_category_property(self):
        """Tract should have urbanicity_category property."""
        from siege_utilities.geo.django.models import Tract

        assert hasattr(Tract, "urbanicity_category")
        assert isinstance(Tract.__dict__["urbanicity_category"], property)

    def test_tract_has_urbanicity_subcategory_property(self):
        """Tract should have urbanicity_subcategory property."""
        from siege_utilities.geo.django.models import Tract

        assert hasattr(Tract, "urbanicity_subcategory")
        assert isinstance(Tract.__dict__["urbanicity_subcategory"], property)
