"""Tests for siege_utilities.analytics.pricing."""

import warnings

import numpy as np
import pytest

from siege_utilities.analytics.pricing import (
    PricePoint,
    PricingCorridor,
    analyze_price_sensitivity,
)


def _synthetic_responses(n=50, seed=42):
    """Generate synthetic Van Westendorp survey responses."""
    rng = np.random.RandomState(seed)
    too_cheap = rng.normal(20, 5, n).clip(1)
    cheap = rng.normal(35, 5, n).clip(1)
    expensive = rng.normal(65, 5, n).clip(1)
    too_expensive = rng.normal(80, 5, n).clip(1)
    return too_cheap.tolist(), cheap.tolist(), expensive.tolist(), too_expensive.tolist()


class TestValidation:
    def test_empty_responses_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            analyze_price_sensitivity([], [], [], [])

    def test_unequal_lengths_raises(self):
        with pytest.raises(ValueError, match="same number of responses"):
            analyze_price_sensitivity([10, 20], [30], [50, 60], [70, 80])

    def test_negative_prices_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            analyze_price_sensitivity([-5, 10], [20, 30], [50, 60], [70, 80])

    def test_min_sample_zero_raises(self):
        with pytest.raises(ValueError, match="min_sample must be at least 1"):
            analyze_price_sensitivity(
                [10], [20], [50], [70], min_sample=0,
            )

    def test_small_sample_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            analyze_price_sensitivity(
                [10, 20, 30], [20, 30, 40],
                [50, 60, 70], [70, 80, 90],
                min_sample=10,
            )
            sample_warnings = [
                x for x in w if "responses" in str(x.message)
            ]
            assert len(sample_warnings) == 1
            assert "Only 3 responses" in str(sample_warnings[0].message)

    def test_no_warning_above_threshold(self):
        tc, ch, ex, te = _synthetic_responses(n=20)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            analyze_price_sensitivity(tc, ch, ex, te, min_sample=10)
            sample_warnings = [
                x for x in w if "responses" in str(x.message)
            ]
            assert len(sample_warnings) == 0

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="finite"):
            analyze_price_sensitivity(
                [10, float("nan")], [20, 30], [50, 60], [70, 80],
            )

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="finite"):
            analyze_price_sensitivity(
                [10, 20], [20, float("inf")], [50, 60], [70, 80],
            )

    def test_grid_points_zero_raises(self):
        with pytest.raises(ValueError, match="grid_points must be at least 2"):
            analyze_price_sensitivity(
                [10, 20], [20, 30], [50, 60], [70, 80],
                min_sample=1, grid_points=0,
            )

    def test_grid_points_one_raises(self):
        with pytest.raises(ValueError, match="grid_points must be at least 2"):
            analyze_price_sensitivity(
                [10, 20], [20, 30], [50, 60], [70, 80],
                min_sample=1, grid_points=1,
            )


class TestHappyPath:
    def test_basic_corridor(self):
        tc, ch, ex, te = _synthetic_responses(n=100)
        corridor = analyze_price_sensitivity(tc, ch, ex, te)
        assert isinstance(corridor, PricingCorridor)
        assert corridor.sample_size == 100
        assert len(corridor.price_grid) == 200

    def test_all_intersections_found(self):
        tc, ch, ex, te = _synthetic_responses(n=100)
        corridor = analyze_price_sensitivity(tc, ch, ex, te)
        assert corridor.pmc is not None
        assert corridor.pme is not None
        assert corridor.opp is not None
        assert corridor.idp is not None

    def test_corridor_ordering(self):
        tc, ch, ex, te = _synthetic_responses(n=100)
        corridor = analyze_price_sensitivity(tc, ch, ex, te)
        assert corridor.pmc.price < corridor.pme.price

    def test_acceptable_range(self):
        tc, ch, ex, te = _synthetic_responses(n=100)
        corridor = analyze_price_sensitivity(tc, ch, ex, te)
        rng = corridor.acceptable_range
        assert rng is not None
        low, high = rng
        assert low < high

    def test_price_point_labels(self):
        tc, ch, ex, te = _synthetic_responses(n=100)
        corridor = analyze_price_sensitivity(tc, ch, ex, te)
        assert corridor.pmc.label == "PMC"
        assert corridor.pme.label == "PME"
        assert corridor.opp.label == "OPP"
        assert corridor.idp.label == "IDP"

    def test_custom_grid_points(self):
        tc, ch, ex, te = _synthetic_responses(n=50)
        corridor = analyze_price_sensitivity(
            tc, ch, ex, te, grid_points=500,
        )
        assert len(corridor.price_grid) == 500


class TestNonMonotonic:
    def test_monotonicity_check_exists(self):
        """Cumulative distributions from raw responses are monotonic by
        construction. The monotonicity guard is defensive code for future
        pre-computed distribution support. Verify clean data passes."""
        tc, ch, ex, te = _synthetic_responses(n=50)
        corridor = analyze_price_sensitivity(tc, ch, ex, te)
        assert corridor is not None


class TestNoIntersection:
    def test_warns_on_missing_intersection(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            corridor = analyze_price_sensitivity(
                [100] * 20, [100] * 20,
                [100] * 20, [100] * 20,
                min_sample=10,
            )
            intersection_warnings = [
                x for x in w if "intersection" in str(x.message).lower()
            ]
        assert corridor.sample_size == 20
        assert len(intersection_warnings) >= 1


class TestAcceptableRange:
    def test_none_when_pmc_missing(self):
        corridor = PricingCorridor(
            pmc=None,
            pme=PricePoint("PME", 80.0, "test"),
            opp=None,
            idp=None,
            price_grid=[],
            sample_size=0,
        )
        assert corridor.acceptable_range is None

    def test_none_when_pme_missing(self):
        corridor = PricingCorridor(
            pmc=PricePoint("PMC", 20.0, "test"),
            pme=None,
            opp=None,
            idp=None,
            price_grid=[],
            sample_size=0,
        )
        assert corridor.acceptable_range is None


class TestEdgeCases:
    def test_single_response_with_low_threshold(self):
        corridor = analyze_price_sensitivity(
            [10], [20], [50], [70], min_sample=1,
        )
        assert corridor.sample_size == 1

    def test_identical_responses(self):
        corridor = analyze_price_sensitivity(
            [10] * 20, [30] * 20, [50] * 20, [70] * 20,
        )
        assert corridor.sample_size == 20
