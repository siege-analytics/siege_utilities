"""Error-path tests for siege_utilities.geo.django.services (SU-4b).

Covers crosswalk_service, demographic_service, isochrone_service,
population_service. All require Django to be configured.
"""

import pytest

try:
    from django.conf import settings as _ds
    _DJANGO_CONFIGURED = _ds.configured
except Exception:
    _DJANGO_CONFIGURED = False

pytestmark = pytest.mark.skipif(
    not _DJANGO_CONFIGURED, reason="Django not configured"
)


class TestCrosswalkServiceErrors:
    """Error paths for crosswalk_service.populate."""

    def test_missing_crosswalk_data_returns_error(self):
        from siege_utilities.geo.django.services.crosswalk_service import (
            CrosswalkPopulationService,
        )
        svc = CrosswalkPopulationService()
        result = svc.populate(source_year=1800, target_year=1850)
        assert result.errors or not result.success


class TestIsochroneServiceErrors:
    """Error paths for isochrone_service."""

    def test_empty_geojson_raises(self):
        from siege_utilities.geo.django.services.isochrone_service import (
            IsochroneService,
        )
        svc = IsochroneService()
        with pytest.raises(ValueError, match="[Nn]o (features|polygon)"):
            svc._geojson_to_multipolygon({"type": "FeatureCollection", "features": []})


class TestDemographicServiceErrors:
    """Error paths for demographic_service."""

    def test_invalid_geography_type_raises(self):
        from siege_utilities.geo.django.services.demographic_service import (
            DemographicPopulationService,
        )
        svc = DemographicPopulationService()
        with pytest.raises((ValueError, KeyError)):
            svc._get_content_type("nonexistent_geography_zz")


class TestPopulationServiceErrors:
    """Error paths for population_service."""

    def test_invalid_geography_type_raises(self):
        from siege_utilities.geo.django.services.population_service import (
            PopulationService,
        )
        svc = PopulationService()
        with pytest.raises((ValueError, KeyError)):
            svc._download_boundaries("nonexistent_geography_zz", "06")
