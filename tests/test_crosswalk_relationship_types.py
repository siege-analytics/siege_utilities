"""Error-path tests for siege_utilities.geo.crosswalk.relationship_types (SU-4b)."""

import pytest

try:
    from siege_utilities.geo.crosswalk.relationship_types import (
        CrosswalkRelationship,
        RelationshipType,
        WeightMethod,
    )
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or crosswalk deps missing")


class TestGetWeightErrors:
    """Error paths for CrosswalkRelationship.get_weight."""

    def test_missing_population_weight_raises(self):
        """Requesting population weight when not set must raise ValueError."""
        rel = CrosswalkRelationship(
            source_geoid="01001",
            target_geoid="01002",
            population_weight=None,
        )
        with pytest.raises(ValueError, match="Population weight not available"):
            rel.get_weight(WeightMethod.POPULATION)

    def test_missing_housing_weight_raises(self):
        """Requesting housing weight when not set must raise ValueError."""
        rel = CrosswalkRelationship(
            source_geoid="01001",
            target_geoid="01002",
            housing_weight=None,
        )
        with pytest.raises(ValueError, match="Housing weight not available"):
            rel.get_weight(WeightMethod.HOUSING)


class TestGetWeightHappyPath:
    """Sanity checks for get_weight."""

    def test_area_weight_returns_default(self):
        """Area weight returns the default 1.0."""
        rel = CrosswalkRelationship(source_geoid="01001", target_geoid="01002")
        assert rel.get_weight(WeightMethod.AREA) == 1.0

    def test_equal_weight_always_one(self):
        """Equal weight method always returns 1.0."""
        rel = CrosswalkRelationship(
            source_geoid="01001", target_geoid="01002", area_weight=0.5
        )
        assert rel.get_weight(WeightMethod.EQUAL) == 1.0

    def test_population_weight_when_set(self):
        """Population weight returns set value."""
        rel = CrosswalkRelationship(
            source_geoid="01001", target_geoid="01002", population_weight=0.75
        )
        assert rel.get_weight(WeightMethod.POPULATION) == 0.75
