"""
Unit tests for UrbanicityClassificationService and classify_urbanicity command.

Tests service class structure, classification logic, and result dataclass
without requiring a full Django database.
"""

import pytest

# Configure Django for model-dependent tests
try:
    import django
    from django.conf import settings as django_settings

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
    _DJANGO_AVAILABLE = True
except Exception as e:
    _DJANGO_AVAILABLE = False
    _DJANGO_SKIP_REASON = str(e)


# ---- Tests that don't require Django ----


class TestClassifyUrbanicityFunction:
    """Test the pure classify_urbanicity function from nces_constants."""

    def test_large_city(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=300000, distance_to_urban=2.0)
        assert result == "city_large"

    def test_large_suburb(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=300000, distance_to_urban=10.0)
        assert result == "suburb_large"

    def test_midsize_city(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=150000, distance_to_urban=3.0)
        assert result == "city_midsize"

    def test_midsize_suburb(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=150000, distance_to_urban=8.0)
        assert result == "suburb_midsize"

    def test_small_city(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=30000, distance_to_urban=2.0)
        assert result == "city_small"

    def test_small_suburb(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=30000, distance_to_urban=15.0)
        assert result == "suburb_small"

    def test_town_fringe(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=5000, distance_to_urban=3.0)
        assert result == "town_fringe"

    def test_town_distant(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=5000, distance_to_urban=15.0)
        assert result == "town_distant"

    def test_town_remote(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=5000, distance_to_urban=30.0)
        assert result == "town_remote"

    def test_rural_fringe(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=500, distance_to_urban=3.0)
        assert result == "rural_fringe"

    def test_rural_distant(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=500, distance_to_urban=15.0)
        assert result == "rural_distant"

    def test_rural_remote(self):
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=500, distance_to_urban=30.0)
        assert result == "rural_remote"

    def test_boundary_large_city_threshold(self):
        """250,000 is the large city/suburb threshold."""
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=250000, distance_to_urban=1.0)
        assert result == "city_large"

    def test_boundary_town_threshold(self):
        """2,500 is the town/rural boundary."""
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=2500, distance_to_urban=10.0)
        assert result == "town_distant"

    def test_boundary_below_town(self):
        """Below 2,500 is rural."""
        from siege_utilities.config.nces_constants import classify_urbanicity

        result = classify_urbanicity(population=2499, distance_to_urban=10.0)
        assert result == "rural_distant"


class TestLocaleCodeMapping:
    """Test subcategory string ↔ numeric code round-trip."""

    def test_all_subcategories_have_numeric_codes(self):
        from siege_utilities.config.nces_constants import (
            LOCALE_CODE_TO_NUMERIC,
            LOCALE_NUMERIC_CODES,
        )

        for code, subcategory in LOCALE_NUMERIC_CODES.items():
            assert LOCALE_CODE_TO_NUMERIC[subcategory] == code

    def test_classify_all_produce_valid_codes(self):
        """Every classify_urbanicity result maps to a valid numeric code."""
        from siege_utilities.config.nces_constants import (
            LOCALE_CODE_TO_NUMERIC,
            classify_urbanicity,
        )

        test_cases = [
            (300000, 2.0),
            (300000, 10.0),
            (150000, 2.0),
            (150000, 10.0),
            (30000, 2.0),
            (30000, 10.0),
            (5000, 2.0),
            (5000, 15.0),
            (5000, 30.0),
            (500, 2.0),
            (500, 15.0),
            (500, 30.0),
        ]
        for pop, dist in test_cases:
            subcategory = classify_urbanicity(pop, dist)
            assert subcategory in LOCALE_CODE_TO_NUMERIC, (
                f"classify_urbanicity({pop}, {dist}) = '{subcategory}' "
                f"has no numeric code"
            )
            code = LOCALE_CODE_TO_NUMERIC[subcategory]
            assert 11 <= code <= 43


# ---- Tests that require Django ----


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason=f"Django not available: {globals().get('_DJANGO_SKIP_REASON', 'unknown')}",
)
class TestUrbanicityClassificationService:
    """Tests for UrbanicityClassificationService (structure and config)."""

    def test_import(self):
        from siege_utilities.geo.django.services.urbanicity_service import (
            UrbanicityClassificationService,
        )

        assert UrbanicityClassificationService is not None

    def test_import_from_init(self):
        from siege_utilities.geo.django.services import (
            UrbanicityClassificationService,
        )

        assert UrbanicityClassificationService is not None

    def test_instantiation(self):
        from siege_utilities.geo.django.services.urbanicity_service import (
            UrbanicityClassificationService,
        )

        svc = UrbanicityClassificationService()
        assert hasattr(svc, "classify")

    def test_classify_method_signature(self):
        """classify() accepts year, state_fips, and other kwargs."""
        import inspect

        from siege_utilities.geo.django.services.urbanicity_service import (
            UrbanicityClassificationService,
        )

        sig = inspect.signature(UrbanicityClassificationService.classify)
        params = list(sig.parameters.keys())
        assert "year" in params
        assert "state_fips" in params
        assert "urban_area_year" in params
        assert "dataset" in params
        assert "batch_size" in params
        assert "overwrite" in params
        assert "srid" in params


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason=f"Django not available: {globals().get('_DJANGO_SKIP_REASON', 'unknown')}",
)
class TestClassificationResult:
    """Tests for the ClassificationResult dataclass."""

    def test_defaults(self):
        from siege_utilities.geo.django.services.urbanicity_service import (
            ClassificationResult,
        )

        result = ClassificationResult()
        assert result.classified == 0
        assert result.skipped_no_population == 0
        assert result.skipped_no_urban_area == 0
        assert result.skipped_no_point == 0
        assert result.errors == []

    def test_total_processed(self):
        from siege_utilities.geo.django.services.urbanicity_service import (
            ClassificationResult,
        )

        result = ClassificationResult(
            classified=10,
            skipped_no_population=3,
            skipped_no_urban_area=2,
            skipped_no_point=1,
        )
        assert result.total_processed == 16

    def test_errors_list_independence(self):
        """Each result has its own errors list (no shared default)."""
        from siege_utilities.geo.django.services.urbanicity_service import (
            ClassificationResult,
        )

        r1 = ClassificationResult()
        r2 = ClassificationResult()
        r1.errors.append("test")
        assert len(r2.errors) == 0


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason=f"Django not available: {globals().get('_DJANGO_SKIP_REASON', 'unknown')}",
)
class TestMetersPerMileConstant:
    """Verify the conversion constant is correct."""

    def test_meters_per_mile(self):
        from siege_utilities.geo.django.services.urbanicity_service import (
            _METERS_PER_MILE,
        )

        assert abs(_METERS_PER_MILE - 1609.344) < 0.001
