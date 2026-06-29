"""Error-path coverage (SU-4b) for geo.django.services.population_service."""
import pytest
from siege_utilities.geo.django.services.population_service import (
    BoundaryPopulationService,
)


def test_download_boundaries_raises_on_unknown_geography_type():
    with pytest.raises(ValueError) as exc_info:
        BoundaryPopulationService()._download_boundaries("not_a_geography", 2020)
    assert "Unknown geography type" in str(exc_info.value)
