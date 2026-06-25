"""Error-path coverage (SU-4b) for siege_utilities.geo.crosswalk.relationship_types.

Forces the ValueError guards in CrosswalkRelationship.get_weight when a
requested weight is unavailable or the method is unknown.
"""

import pytest

from siege_utilities.geo.crosswalk.relationship_types import (
    CrosswalkRelationship,
    WeightMethod,
)


def _rel():
    # population_weight / housing_weight left as None (the default).
    return CrosswalkRelationship(source_geoid="06001", target_geoid="06002")


def test_get_weight_raises_when_population_weight_missing():
    with pytest.raises(ValueError) as exc_info:
        _rel().get_weight(WeightMethod.POPULATION)
    assert "Population weight not available" in str(exc_info.value)


def test_get_weight_raises_when_housing_weight_missing():
    with pytest.raises(ValueError) as exc_info:
        _rel().get_weight(WeightMethod.HOUSING)
    assert "Housing weight not available" in str(exc_info.value)


def test_get_weight_raises_on_unknown_method():
    with pytest.raises(ValueError) as exc_info:
        _rel().get_weight("not-a-weight-method")
    assert "Unknown weight method" in str(exc_info.value)


def test_get_weight_returns_area_weight_for_valid_method():
    # Sanity anchor so the guard tests cannot pass vacuously.
    assert _rel().get_weight(WeightMethod.AREA) == 1.0
