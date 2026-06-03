"""Tests for the pure-numpy choropleth classification module.

Tests classification independently of rendering — no geopandas or
matplotlib required for the core classify_series tests.
"""

import pytest
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# ClassificationResult and classify_series
# ---------------------------------------------------------------------------

class TestClassifySeriesBasic:
    """Core classify_series behavior."""

    def test_returns_classification_result(self):
        from siege_utilities.geo.classification import classify_series, ClassificationResult

        result = classify_series([1, 2, 3, 4, 5], scheme="quantiles", k=3)
        assert isinstance(result, ClassificationResult)

    def test_bins_length_matches_input(self):
        from siege_utilities.geo.classification import classify_series

        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = classify_series(values, scheme="quantiles", k=4)
        assert len(result.bins) == len(values)

    def test_bins_in_range(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series(list(range(1, 101)), scheme="quantiles", k=5)
        assert result.bins.min() >= 0
        assert result.bins.max() < result.k

    def test_breaks_length_is_k_plus_one(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series(list(range(1, 101)), scheme="equal_interval", k=5)
        assert len(result.breaks) == result.k + 1

    def test_breaks_monotonic(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series(list(range(1, 101)), scheme="quantiles", k=5)
        assert np.all(np.diff(result.breaks) >= 0)

    def test_reports_backend(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series([1, 2, 3, 4, 5], scheme="quantiles", k=3)
        assert result.backend in ("numpy", "mapclassify")

    def test_empty_raises(self):
        from siege_utilities.geo.classification import classify_series

        with pytest.raises(ValueError, match="empty"):
            classify_series([], scheme="quantiles", k=3)

    def test_all_nan_raises(self):
        from siege_utilities.geo.classification import classify_series

        with pytest.raises(ValueError, match="empty"):
            classify_series([np.nan, np.nan], scheme="quantiles", k=3)

    def test_nan_values_get_minus_one(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series([1, 2, np.nan, 4, 5], scheme="quantiles", k=3)
        assert result.bins[2] == -1
        assert result.bins[0] >= 0

    def test_constant_value_single_bin(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series([5, 5, 5, 5], scheme="quantiles", k=3)
        assert result.k == 1
        assert np.all(result.bins == 0)

    def test_k_exceeds_data_size(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series([1, 2, 3], scheme="equal_interval", k=10)
        assert result.k <= 3

    def test_invalid_k_raises(self):
        from siege_utilities.geo.classification import classify_series

        with pytest.raises(ValueError, match="k must be"):
            classify_series([1, 2, 3], scheme="quantiles", k=0)

    def test_unknown_scheme_raises(self):
        from siege_utilities.geo.classification import classify_series

        with pytest.raises(ValueError, match="Unknown classification scheme"):
            classify_series([1, 2, 3], scheme="nonexistent_scheme", k=3)

    def test_accepts_pandas_series(self):
        from siege_utilities.geo.classification import classify_series

        s = pd.Series([10, 20, 30, 40, 50])
        result = classify_series(s, scheme="quantiles", k=3)
        assert len(result.bins) == 5

    def test_accepts_numpy_array(self):
        from siege_utilities.geo.classification import classify_series

        arr = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = classify_series(arr, scheme="quantiles", k=3)
        assert len(result.bins) == 5


# ---------------------------------------------------------------------------
# Individual scheme correctness
# ---------------------------------------------------------------------------

class TestQuantilesScheme:

    def test_even_split(self):
        from siege_utilities.geo.classification import classify_series

        values = list(range(1, 101))
        result = classify_series(values, scheme="quantiles", k=4)
        counts = np.bincount(result.bins[result.bins >= 0])
        assert all(c >= 20 for c in counts)

    def test_breaks_cover_range(self):
        from siege_utilities.geo.classification import classify_series

        values = [10, 20, 30, 40, 50]
        result = classify_series(values, scheme="quantiles", k=3)
        assert result.breaks[0] <= 10
        assert result.breaks[-1] >= 50


class TestEqualIntervalScheme:

    def test_uniform_bin_widths(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series(list(range(0, 100)), scheme="equal_interval", k=5)
        widths = np.diff(result.breaks)
        np.testing.assert_allclose(widths, widths[0], atol=0.01)

    def test_breaks_span_data(self):
        from siege_utilities.geo.classification import classify_series

        values = [5, 15, 25, 35, 45]
        result = classify_series(values, scheme="equal_interval", k=4)
        assert result.breaks[0] == pytest.approx(5.0)
        assert result.breaks[-1] == pytest.approx(45.0)


class TestNaturalBreaksScheme:

    def test_produces_expected_k(self):
        from siege_utilities.geo.classification import classify_series

        values = list(range(1, 51))
        result = classify_series(values, scheme="natural_breaks", k=5)
        assert result.k >= 2

    def test_fisher_jenks_alias(self):
        from siege_utilities.geo.classification import classify_series

        values = list(range(1, 51))
        r1 = classify_series(values, scheme="natural_breaks", k=5)
        r2 = classify_series(values, scheme="fisher_jenks", k=5)
        np.testing.assert_array_equal(r1.bins, r2.bins)

    def test_clustered_data_finds_gaps(self):
        from siege_utilities.geo.classification import classify_series

        values = [1, 2, 3, 100, 101, 102, 200, 201, 202]
        result = classify_series(values, scheme="natural_breaks", k=3)
        assert result.bins[0] == result.bins[1] == result.bins[2]
        assert result.bins[3] == result.bins[4] == result.bins[5]


class TestStdMeanScheme:

    def test_breaks_centered_on_mean(self):
        from siege_utilities.geo.classification import classify_series

        np.random.seed(42)
        values = np.random.normal(100, 15, 200)
        result = classify_series(values, scheme="std_mean", k=6)
        assert any(abs(b - 100) < 20 for b in result.breaks)

    def test_constant_std_returns_single_bin(self):
        from siege_utilities.geo.classification import classify_series

        result = classify_series([5, 5, 5], scheme="std_mean", k=4)
        assert result.k == 1


class TestHeadTailBreaksScheme:

    def test_produces_bins(self):
        from siege_utilities.geo.classification import classify_series

        np.random.seed(42)
        values = np.random.exponential(10, 100)
        result = classify_series(values, scheme="headtailbreaks", k=10)
        assert result.k >= 1

    def test_uniform_data_few_bins(self):
        from siege_utilities.geo.classification import classify_series

        values = list(range(1, 101))
        result = classify_series(values, scheme="headtailbreaks", k=10)
        assert result.k <= 10


class TestBoxPlotScheme:

    def test_produces_expected_structure(self):
        from siege_utilities.geo.classification import classify_series

        np.random.seed(42)
        values = np.random.normal(50, 10, 200)
        result = classify_series(values, scheme="boxplot", k=6)
        assert result.k >= 2
        assert result.breaks[0] <= values.min()
        assert result.breaks[-1] >= values.max()


class TestPercentilesScheme:

    def test_fixed_percentile_breaks(self):
        from siege_utilities.geo.classification import classify_series

        values = list(range(1, 1001))
        result = classify_series(values, scheme="percentiles", k=6)
        assert result.k >= 2


# ---------------------------------------------------------------------------
# classify_choropleth
# ---------------------------------------------------------------------------

class TestClassifyChoropleth:

    def test_adds_bin_column(self):
        from siege_utilities.geo.classification import classify_choropleth

        df = pd.DataFrame({"pop": [100, 200, 300, 400, 500]})
        result = classify_choropleth(df, "pop", scheme="quantiles", k=3)
        assert "_bin" in result.columns
        assert "_break_low" in result.columns
        assert "_break_high" in result.columns

    def test_does_not_modify_input(self):
        from siege_utilities.geo.classification import classify_choropleth

        df = pd.DataFrame({"pop": [100, 200, 300, 400, 500]})
        original_cols = set(df.columns)
        classify_choropleth(df, "pop", scheme="quantiles", k=3)
        assert set(df.columns) == original_cols

    def test_missing_column_raises(self):
        from siege_utilities.geo.classification import classify_choropleth

        df = pd.DataFrame({"pop": [100, 200, 300]})
        with pytest.raises(ValueError, match="not found"):
            classify_choropleth(df, "nonexistent", scheme="quantiles", k=3)

    def test_color_column_when_matplotlib_available(self):
        from siege_utilities.geo.classification import classify_choropleth

        pytest.importorskip("matplotlib")
        df = pd.DataFrame({"val": [10, 20, 30, 40, 50]})
        result = classify_choropleth(df, "val", scheme="quantiles", k=3, cmap="YlOrRd")
        assert "_color" in result.columns
        colors = result["_color"]
        assert all(c.startswith("#") for c in colors if c)

    def test_break_bounds_bracket_values(self):
        from siege_utilities.geo.classification import classify_choropleth

        df = pd.DataFrame({"val": [10, 20, 30, 40, 50]})
        result = classify_choropleth(df, "val", scheme="equal_interval", k=3)
        for _, row in result.iterrows():
            if row["_bin"] >= 0:
                assert row["_break_low"] <= row["val"]
                assert row["_break_high"] >= row["val"]

    def test_nan_bin_has_nan_bounds(self):
        from siege_utilities.geo.classification import classify_choropleth

        df = pd.DataFrame({"val": [10, np.nan, 30, 40, 50]})
        result = classify_choropleth(df, "val", scheme="quantiles", k=3)
        nan_row = result.iloc[1]
        assert nan_row["_bin"] == -1
        assert np.isnan(nan_row["_break_low"])
        assert np.isnan(nan_row["_break_high"])


# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------

class TestBackendDispatch:

    def test_numpy_backend_forced(self):
        from unittest.mock import patch
        from siege_utilities.geo import classification as mod

        with patch.object(mod, "_MAPCLASSIFY_AVAILABLE", False):
            result = mod.classify_series([1, 2, 3, 4, 5], scheme="quantiles", k=3)
        assert result.backend == "numpy"

    def test_all_numpy_schemes_work_without_mapclassify(self):
        from unittest.mock import patch
        from siege_utilities.geo import classification as mod

        values = list(range(1, 101))
        with patch.object(mod, "_MAPCLASSIFY_AVAILABLE", False):
            for scheme in mod.AVAILABLE_SCHEMES:
                result = mod.classify_series(values, scheme=scheme, k=5)
                assert result.backend == "numpy"
                assert len(result.bins) == 100
                assert result.k >= 1


# ---------------------------------------------------------------------------
# AVAILABLE_SCHEMES constant
# ---------------------------------------------------------------------------

class TestAvailableSchemes:

    def test_has_core_schemes(self):
        from siege_utilities.geo.classification import AVAILABLE_SCHEMES

        for scheme in ("quantiles", "equal_interval", "natural_breaks",
                       "fisher_jenks", "headtailbreaks", "boxplot"):
            assert scheme in AVAILABLE_SCHEMES

    def test_values_are_human_readable(self):
        from siege_utilities.geo.classification import AVAILABLE_SCHEMES

        for key, label in AVAILABLE_SCHEMES.items():
            assert isinstance(label, str)
            assert len(label) > 3
