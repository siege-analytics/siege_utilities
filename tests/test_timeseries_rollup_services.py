"""
Unit tests for TimeseriesService and DemographicRollupService.

Tests service class structure, statistics helpers, and configuration
without requiring a full Django database.
"""

import math

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


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason=f"Django not available: {globals().get('_DJANGO_SKIP_REASON', 'unknown')}",
)
class TestTimeseriesService:
    """Tests for TimeseriesService."""

    def test_import(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        assert TimeseriesService is not None

    def test_init_default_dataset(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        svc = TimeseriesService()
        assert svc.dataset == "acs5"

    def test_init_custom_dataset(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        svc = TimeseriesService(dataset="acs1")
        assert svc.dataset == "acs1"

    def test_std_dev(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        values = [10, 20, 30]
        mean = 20
        sd = TimeseriesService._std_dev(values, mean)
        assert abs(sd - 8.1649658) < 0.001

    def test_cagr_positive_growth(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        # 100 → 200 over 5 periods ≈ 14.87% CAGR
        cagr = TimeseriesService._cagr(100, 200, 5)
        assert cagr is not None
        assert abs(cagr - 0.1487) < 0.001

    def test_cagr_zero_start_returns_none(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        assert TimeseriesService._cagr(0, 100, 5) is None

    def test_trend_direction_increasing(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        assert TimeseriesService._trend_direction([10, 20, 30, 40]) == "increasing"

    def test_trend_direction_decreasing(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        assert TimeseriesService._trend_direction([40, 30, 20, 10]) == "decreasing"

    def test_trend_direction_stable(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        assert TimeseriesService._trend_direction([100, 100, 100, 100]) == "stable"

    def test_resolve_model_known_level(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService
        from siege_utilities.geo.django.models import Tract

        svc = TimeseriesService()
        model = svc._resolve_model("tract")
        assert model is Tract

    def test_resolve_model_unknown_level(self):
        from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

        svc = TimeseriesService()
        assert svc._resolve_model("galaxy") is None


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason=f"Django not available: {globals().get('_DJANGO_SKIP_REASON', 'unknown')}",
)
class TestDemographicRollupService:
    """Tests for DemographicRollupService."""

    def test_import(self):
        from siege_utilities.geo.django.services.rollup_service import DemographicRollupService

        assert DemographicRollupService is not None

    def test_init_default_dataset(self):
        from siege_utilities.geo.django.services.rollup_service import DemographicRollupService

        svc = DemographicRollupService()
        assert svc.dataset == "acs5"

    def test_geoid_prefix_lengths(self):
        from siege_utilities.geo.django.services.rollup_service import DemographicRollupService

        assert DemographicRollupService.GEOID_PREFIX_LENGTHS["state"] == 2
        assert DemographicRollupService.GEOID_PREFIX_LENGTHS["county"] == 5
        assert DemographicRollupService.GEOID_PREFIX_LENGTHS["tract"] == 11

    def test_resolve_model_county(self):
        from siege_utilities.geo.django.services.rollup_service import DemographicRollupService
        from siege_utilities.geo.django.models import County

        svc = DemographicRollupService()
        assert svc._resolve_model("county") is County

    def test_resolve_model_unknown(self):
        from siege_utilities.geo.django.services.rollup_service import DemographicRollupService

        svc = DemographicRollupService()
        assert svc._resolve_model("galaxy") is None


@pytest.mark.skipif(
    not _DJANGO_AVAILABLE,
    reason=f"Django not available: {globals().get('_DJANGO_SKIP_REASON', 'unknown')}",
)
class TestServiceExports:
    """Tests for service module exports."""

    def test_timeseries_service_exported(self):
        from siege_utilities.geo.django.services import TimeseriesService

        assert TimeseriesService is not None

    def test_rollup_service_exported(self):
        from siege_utilities.geo.django.services import DemographicRollupService

        assert DemographicRollupService is not None
