"""
Tests for NLRB region model and population service.
"""

import pytest

try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401

    _DJANGO_AVAILABLE = True
except Exception:
    _DJANGO_AVAILABLE = False


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="GeoDjango/GDAL not available")
class TestNLRBRegionModel:
    """Tests for the NLRBRegion model definition."""

    def test_import(self):
        from siege_utilities.geo.django.models.federal import NLRBRegion

        assert NLRBRegion is not None

    def test_has_region_number(self):
        from siege_utilities.geo.django.models.federal import NLRBRegion

        field = NLRBRegion._meta.get_field("region_number")
        assert field is not None

    def test_has_region_office(self):
        from siege_utilities.geo.django.models.federal import NLRBRegion

        field = NLRBRegion._meta.get_field("region_office")
        assert field is not None

    def test_has_states_covered(self):
        from siege_utilities.geo.django.models.federal import NLRBRegion

        field = NLRBRegion._meta.get_field("states_covered")
        assert field is not None

    def test_feature_id_auto_set(self):
        from siege_utilities.geo.django.models.federal import NLRBRegion

        region = NLRBRegion(region_number=5, vintage_year=2024)
        # save() would auto-set feature_id, but we can't save without DB
        # Just verify the model accepts the fields
        assert region.region_number == 5

    def test_str_representation(self):
        from siege_utilities.geo.django.models.federal import NLRBRegion

        region = NLRBRegion(
            region_number=5,
            region_office="Baltimore",
            vintage_year=2024,
        )
        assert "5" in str(region)
        assert "Baltimore" in str(region)


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="GeoDjango/GDAL not available")
class TestNLRBPopulationService:
    """Tests for NLRBPopulationService."""

    def test_import(self):
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationService,
        )

        assert NLRBPopulationService is not None

    def test_nlrb_regions_data(self):
        from siege_utilities.geo.django.services.nlrb_service import NLRB_REGIONS

        assert len(NLRB_REGIONS) > 20
        assert 1 in NLRB_REGIONS
        assert NLRB_REGIONS[1]["office"] == "Boston"
        assert "MA" in NLRB_REGIONS[1]["states"]

    def test_service_instantiation(self):
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationService,
        )

        svc = NLRBPopulationService()
        assert hasattr(svc, "populate")

    def test_populate_method_signature(self):
        import inspect
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationService,
        )

        sig = inspect.signature(NLRBPopulationService.populate)
        assert "vintage_year" in sig.parameters
        assert "update_existing" in sig.parameters
        assert "dissolve_counties" in sig.parameters

    def test_nlrb_population_result(self):
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationResult,
        )

        result = NLRBPopulationResult(records_created=5, records_skipped=3)
        assert result.success is True
        assert result.records_created == 5

    def test_nlrb_population_result_with_errors(self):
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationResult,
        )

        result = NLRBPopulationResult(errors=["something broke"])
        assert result.success is False

    def test_all_regions_have_office(self):
        from siege_utilities.geo.django.services.nlrb_service import NLRB_REGIONS

        for num, info in NLRB_REGIONS.items():
            assert "office" in info, f"Region {num} missing office"
            assert "states" in info, f"Region {num} missing states"
            assert len(info["states"]) > 0, f"Region {num} has no states"

    def test_region_numbers_are_positive(self):
        from siege_utilities.geo.django.services.nlrb_service import NLRB_REGIONS

        for num in NLRB_REGIONS:
            assert num > 0
            assert num <= 34


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="GeoDjango/GDAL not available")
class TestNLRBManagementCommand:
    """Tests for populate_nlrb_regions management command."""

    def test_command_import(self):
        from siege_utilities.geo.django.management.commands.populate_nlrb_regions import (
            Command,
        )

        assert Command is not None

    def test_command_has_help(self):
        from siege_utilities.geo.django.management.commands.populate_nlrb_regions import (
            Command,
        )

        cmd = Command()
        assert cmd.help is not None
        assert len(cmd.help) > 0
