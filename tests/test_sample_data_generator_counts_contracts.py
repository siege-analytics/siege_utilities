"""Contracts for synthetic sample-data generators (row-count fidelity).

Regression for the defect where generate_synthetic_population /
generate_synthetic_businesses / generate_synthetic_housing returned fewer
rows than requested because a floored ``int(count * percentage)`` dropped the
fractional remainder. The generators must now return exactly the requested
count via largest-remainder apportionment.
"""

import pytest

from siege_utilities import generate_synthetic_population
from siege_utilities import generate_synthetic_businesses
from siege_utilities import generate_synthetic_housing
from siege_utilities.reference.sample_data import _apportion

pytest.importorskip(
    "faker", reason="Faker is required to generate synthetic sample data"
)


class TestGeneratorRowCounts:
    @pytest.mark.parametrize("size", [1, 2, 5, 7, 10, 100])
    def test_population_returns_exact_size(self, size):
        df = generate_synthetic_population(size=size)
        assert df.shape[0] == size

    @pytest.mark.parametrize("count", [1, 3, 8, 50])
    def test_businesses_returns_exact_count(self, count):
        df = generate_synthetic_businesses(business_count=count)
        assert df.shape[0] == count

    @pytest.mark.parametrize("count", [1, 7, 13, 40])
    def test_housing_returns_exact_count(self, count):
        df = generate_synthetic_housing(housing_count=count)
        assert df.shape[0] == count

    def test_custom_distribution_not_summing_to_one_still_exact(self):
        # Weights sum to 0.6; normalization must still yield exactly N.
        df = generate_synthetic_businesses(
            business_count=10,
            industry_distribution={"a": 0.3, "b": 0.3},
        )
        assert df.shape[0] == 10

    def test_zero_size_is_empty(self):
        assert generate_synthetic_population(size=0).shape[0] == 0


class TestApportion:
    def test_sums_to_total_with_default_like_weights(self):
        dist = {"a": 0.35, "b": 0.30, "c": 0.25, "d": 0.10}
        counts = _apportion(10, dist)
        assert sum(counts.values()) == 10
        assert set(counts) == set(dist)

    def test_largest_remainder_gets_the_leftover(self):
        # size=10 over these weights: real shares 3.5, 3.0, 2.5, 1.0;
        # floors 3+3+2+1 = 9; the single leftover unit goes to the largest
        # fractional remainder (0.5), i.e. "a" or "c" -- both at 0.5, ties
        # broken by iteration order, so "a" (first) receives it.
        dist = {"a": 0.35, "b": 0.30, "c": 0.25, "d": 0.10}
        counts = _apportion(10, dist)
        assert counts == {"a": 4, "b": 3, "c": 2, "d": 1}

    def test_normalizes_non_summing_weights(self):
        counts = _apportion(10, {"a": 0.3, "b": 0.3})
        assert sum(counts.values()) == 10
        assert counts["a"] == 5 and counts["b"] == 5

    def test_zero_total_and_empty_distribution(self):
        assert _apportion(0, {"a": 1.0}) == {"a": 0}
        assert _apportion(10, {}) == {}
        assert _apportion(10, {"a": 0.0}) == {"a": 0}
