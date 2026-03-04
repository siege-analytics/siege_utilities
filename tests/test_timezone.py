"""
Tests for TimezoneGeometry model and TimezonePopulationService.
"""

import pytest

try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401

    _DJANGO_AVAILABLE = True
except Exception:
    _DJANGO_AVAILABLE = False


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="GeoDjango/GDAL not available")
class TestTimezoneGeometryModel:
    """Tests for TimezoneGeometry model definition."""

    def test_import(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        assert TimezoneGeometry is not None

    def test_has_timezone_id(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        field = TimezoneGeometry._meta.get_field("timezone_id")
        assert field is not None
        assert field.max_length == 100

    def test_has_utc_offset_std(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        field = TimezoneGeometry._meta.get_field("utc_offset_std")
        assert field is not None

    def test_has_utc_offset_dst(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        field = TimezoneGeometry._meta.get_field("utc_offset_dst")
        assert field is not None

    def test_has_observes_dst(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        field = TimezoneGeometry._meta.get_field("observes_dst")
        assert field is not None

    def test_inherits_temporal_boundary(self):
        from siege_utilities.geo.django.models.base import TemporalBoundary
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        assert issubclass(TimezoneGeometry, TemporalBoundary)

    def test_unique_together(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry

        unique = TimezoneGeometry._meta.unique_together
        assert ("timezone_id", "vintage_year") in unique

    def test_str_representation(self):
        from siege_utilities.geo.django.models.timezone import TimezoneGeometry
        from decimal import Decimal

        tz = TimezoneGeometry(
            timezone_id="America/New_York",
            utc_offset_std=Decimal("-5.0"),
            vintage_year=2024,
        )
        result = str(tz)
        assert "America/New_York" in result


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="GeoDjango/GDAL not available")
class TestTimezonePopulationService:
    """Tests for TimezonePopulationService."""

    def test_import(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationService,
        )

        assert TimezonePopulationService is not None

    def test_service_instantiation(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationService,
        )

        svc = TimezonePopulationService()
        assert hasattr(svc, "populate_from_geojson")

    def test_populate_method_signature(self):
        import inspect
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationService,
        )

        sig = inspect.signature(TimezonePopulationService.populate_from_geojson)
        assert "geojson_path" in sig.parameters
        assert "vintage_year" in sig.parameters
        assert "update_existing" in sig.parameters

    def test_population_result(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationResult,
        )

        result = TimezonePopulationResult(records_created=10)
        assert result.success is True
        assert result.records_created == 10

    def test_population_result_with_errors(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationResult,
        )

        result = TimezonePopulationResult(errors=["file not found"])
        assert result.success is False

    def test_populate_nonexistent_file(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationService,
        )

        svc = TimezonePopulationService()
        result = svc.populate_from_geojson("/nonexistent/path.geojson")
        assert not result.success
        assert len(result.errors) > 0

    def test_timezone_offsets_data(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TIMEZONE_OFFSETS,
        )

        assert "America/New_York" in TIMEZONE_OFFSETS
        std, dst, obs = TIMEZONE_OFFSETS["America/New_York"]
        assert std == -5.0
        assert dst == -4.0
        assert obs is True

    def test_phoenix_no_dst(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TIMEZONE_OFFSETS,
        )

        std, dst, obs = TIMEZONE_OFFSETS["America/Phoenix"]
        assert std == -7.0
        assert dst == -7.0
        assert obs is False

    def test_lookup_offset_fallback(self):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationService,
        )

        svc = TimezonePopulationService()
        std, dst, obs = svc._lookup_offset("America/New_York")
        assert std == -5.0
        assert dst == -4.0
        assert obs is True


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="GeoDjango/GDAL not available")
class TestTimezoneManagementCommand:
    """Tests for populate_timezones management command."""

    def test_command_import(self):
        from siege_utilities.geo.django.management.commands.populate_timezones import (
            Command,
        )

        assert Command is not None

    def test_command_has_help(self):
        from siege_utilities.geo.django.management.commands.populate_timezones import (
            Command,
        )

        cmd = Command()
        assert cmd.help is not None
        assert len(cmd.help) > 0
