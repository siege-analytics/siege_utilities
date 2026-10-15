"""
Unit tests for GEOIDValidator and GEOID CheckConstraints.

Tests the GEOIDValidator class in geoid_utils.py and verifies that all
concrete boundary models have CheckConstraints on their GEOID fields.
"""

import re

import pytest

from siege_utilities.geo.geoid_utils import GEOID_LENGTHS, GEOIDValidator

# Skip Django-dependent tests if GDAL is not available (CI without geospatial libs)
try:
    from django.core.exceptions import ImproperlyConfigured
except ImportError:  # Django absent; the gis import below raises ImportError
    ImproperlyConfigured = ImportError
try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401

    _DJANGO_AVAILABLE = True
except (ImportError, RuntimeError, ImproperlyConfigured, OSError):
    # GeoDjango without system libgdal raises ImproperlyConfigured (or
    # OSError for an unloadable GDAL_LIBRARY_PATH); django(.contrib.gis)
    # absent raises ImportError. Narrowed so an UNRELATED error fails
    # loudly instead of silently skipping these tests (writing-code:7).
    _DJANGO_AVAILABLE = False


def _constraint_geoid_regex(constraint):
    """Extract the ``geoid__regex`` pattern from a CheckConstraint's condition.

    The constraint's ``condition`` (``check`` on older Django) is a ``Q``
    object such as ``Q(geoid__regex=r"^\\d{11}$")``. Walk its children
    (including nested ``Q`` nodes) and return the regex bound to a
    ``*regex`` lookup, or ``None`` if there isn't one.
    """
    condition = getattr(constraint, "condition", None)
    if condition is None:
        condition = getattr(constraint, "check", None)
    if condition is None:
        return None

    stack = list(getattr(condition, "children", []))
    while stack:
        node = stack.pop()
        if isinstance(node, tuple) and len(node) == 2:
            lookup, value = node
            if str(lookup).endswith("regex"):
                return value
        else:
            stack.extend(getattr(node, "children", []))
    return None


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

    @pytest.mark.parametrize(
        "geoid",
        [
            "0100500008A", "010110001-1", "01001000001", "0100500008a",
            "01001ZZZZZZ", "010130012.2", "05081000L/C",
        ],
    )
    def test_vtd_validator_accepts_tiger_codes(self, geoid):
        """Real VTDST codes include letters, hyphens, periods, and slashes."""
        assert GEOIDValidator("vtd")(geoid) is None

    @pytest.mark.parametrize(
        "geoid",
        [
            "010050008A", "01005000008A", "0100500008_", "0100500008 ",
            "A100500008A", "01A0500008A", "0100500008\u00e9",
        ],
    )
    def test_vtd_validator_rejects_invalid_codes(self, geoid):
        """Widening VTDST must preserve length, prefix, and alphabet checks."""
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="VTD GEOID must contain"):
            GEOIDValidator("vtd")(geoid)

    @pytest.mark.parametrize(
        "level,length",
        [(level, length) for level, length in GEOID_LENGTHS.items() if level != "vtd"],
    )
    def test_non_vtd_validator_rejects_letters(self, level, length):
        """The VTD exception must not relax any other geography level."""
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="only digits"):
            GEOIDValidator(level)("0" * (length - 1) + "A")

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
        "CongressionalDistrict": ("cd_geoid_format", r"^\d{2}([0-9A-Za-z]{2}|112[0-9]{2})$"),
        "StateLegislativeUpper": ("sldu_geoid_format", r"^\d{2}[0-9A-Za-z-]{3}$"),
        "StateLegislativeLower": ("sldl_geoid_format", r"^\d{2}[0-9A-Za-z-]{3}$"),
        "VTD": ("vtd_geoid_format", r"^\d{5}[0-9A-Za-z./-]{6}$"),
    }

    @pytest.mark.parametrize(
        "model_name,expected",
        list(EXPECTED_CONSTRAINTS.items()),
        ids=list(EXPECTED_CONSTRAINTS.keys()),
    )
    def test_model_has_geoid_constraint(self, model_name, expected):
        """Each model's GEOID constraint must enforce its length and alphabet."""
        from siege_utilities.geo.django import models as geo_models

        model_cls = getattr(geo_models, model_name)
        expected_name, expected_regex = expected

        constraint = next(
            (c for c in model_cls._meta.constraints if c.name == expected_name),
            None,
        )
        constraint_names = [c.name for c in model_cls._meta.constraints]
        assert constraint is not None, (
            f"{model_name} missing constraint '{expected_name}'. "
            f"Found: {constraint_names}"
        )

        actual_regex = _constraint_geoid_regex(constraint)
        assert actual_regex == expected_regex, (
            f"{model_name} constraint '{expected_name}' enforces regex "
            f"{actual_regex!r}, expected {expected_regex!r}."
        )

    @pytest.mark.parametrize(
        "geoid,accepted",
        [
            ("0100500008A", True),
            ("010110001-1", True),
            ("01001000001", True),
            ("0100500008a", True),
            ("01001ZZZZZZ", True),
            ("010130012.2", True),
            ("05081000L/C", True),
            ("010050008A", False),
            ("01005000008A", False),
            ("0100500008_", False),
            ("0100500008 ", False),
            ("A100500008A", False),
            ("01A0500008A", False),
        ],
    )
    def test_vtd_geoid_constraint_accepts_tiger_codes(self, geoid, accepted):
        """Exercise the model's regex without querying a database."""
        from siege_utilities.geo.django.models import VTD

        patterns = [
            pattern
            for constraint in VTD._meta.constraints
            if (pattern := _constraint_geoid_regex(constraint)) is not None
        ]
        assert len(patterns) == 1, patterns
        pattern = patterns[0]
        assert (re.fullmatch(pattern, geoid) is not None) is accepted, (
            f"VTD constraint {pattern!r}: {geoid!r}, expected accepted={accepted}"
        )

    @pytest.mark.postgis
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "geoid,accepted",
        [
            ("010130012.2", True),
            ("05081000L/C", True),
            ("0100500008_", False),
            ("A100500008A", False),
        ],
    )
    def test_vtd_live_database_constraint_accepts_tiger_codes(self, geoid, accepted):
        """Prove the migrated PostgreSQL CHECK accepts and rejects real writes."""
        from django.contrib.gis.geos import MultiPolygon, Polygon
        from django.db import IntegrityError, transaction

        from siege_utilities.geo.django.models import VTD

        values = {
            "geoid": geoid,
            "name": "VTD check probe",
            "vintage_year": 2020,
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "vtd_code": geoid[5:],
            "geometry": MultiPolygon(Polygon(((0, 0), (1, 0), (1, 1), (0, 0)))),
        }
        if accepted:
            row = VTD.objects.create(**values)
            assert VTD.objects.filter(pk=row.pk, geoid=geoid).exists()
        else:
            with pytest.raises(IntegrityError, match="vtd_geoid_format"):
                with transaction.atomic():
                    VTD.objects.create(**values)

    def test_vtd_migration_state_matches_model(self):
        """The migration graph must end with the model's corrected constraint."""
        from django.db.migrations.loader import MigrationLoader

        from siege_utilities.geo.django.models import VTD

        loader = MigrationLoader(None)
        state = loader.project_state(loader.graph.leaf_nodes("siege_geo"))
        constraints = state.models["siege_geo", "vtd"].options["constraints"]
        assert constraints == VTD._meta.constraints

    @pytest.mark.parametrize(
        "migration_name,direction,removed,added,pattern",
        [
            (
                "0013_vtd_geoid_charclass", "apply",
                "vtd_geoid_11_digits", "vtd_geoid_format", r"^\d{5}[0-9A-Za-z-]{6}$",
            ),
            (
                "0013_vtd_geoid_charclass", "unapply",
                "vtd_geoid_format", "vtd_geoid_11_digits", r"^\d{11}$",
            ),
            (
                "0016_vtd_geoid_period_slash", "apply",
                "vtd_geoid_format", "vtd_geoid_format", r"^\d{5}[0-9A-Za-z./-]{6}$",
            ),
            (
                "0016_vtd_geoid_period_slash", "unapply",
                "vtd_geoid_format", "vtd_geoid_format", r"^\d{5}[0-9A-Za-z-]{6}$",
            ),
        ],
    )
    def test_vtd_migration_validates_after_constraint_swap(
        self, migration_name, direction, removed, added, pattern
    ):
        """Forward and reverse SQL release the swap lock before scanning rows."""
        from django.db import connection
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(None)
        migration = loader.disk_migrations["siege_geo", migration_name]
        state = loader.project_state(migration.dependencies)
        assert migration.atomic is False
        with connection.schema_editor(collect_sql=True, atomic=migration.atomic) as editor:
            getattr(migration, direction)(state, editor)

        swap, validate = editor.collected_sql
        assert 'ALTER TABLE "siege_geo_vtd"' in swap
        assert f'DROP CONSTRAINT IF EXISTS "{removed}"' in swap
        assert f'DROP CONSTRAINT IF EXISTS "{added}"' in swap
        assert f'ADD CONSTRAINT "{added}"' in swap
        assert f'CHECK ("geoid" ~ \'{pattern}\') NOT VALID' in swap
        assert validate == (
            f'ALTER TABLE "siege_geo_vtd" VALIDATE CONSTRAINT "{added}";'
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
