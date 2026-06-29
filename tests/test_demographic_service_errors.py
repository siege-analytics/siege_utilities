"""Error-path coverage (SU-4b) for geo.django.services.demographic_service."""
import pytest
from siege_utilities.geo.django.services.demographic_service import (
    DemographicPopulationService,
)


def test_get_content_type_raises_on_unknown_geography_type():
    with pytest.raises(ValueError) as exc_info:
        DemographicPopulationService()._get_content_type("not_a_geography")
    assert "Unknown geography type" in str(exc_info.value)
