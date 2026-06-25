"""Error-path coverage (SU-4b) for geo.django.services.isochrone_service."""
import pytest
from siege_utilities.geo.django.services.isochrone_service import (
    IsochroneComputeService,
)


def test_geojson_to_multipolygon_raises_on_empty_features():
    with pytest.raises(ValueError) as exc_info:
        IsochroneComputeService._geojson_to_multipolygon({"features": []})
    assert "no features" in str(exc_info.value)
