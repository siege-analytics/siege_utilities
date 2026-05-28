"""Error-path tests for timeseries modules.

Covers: change_metrics, trend_classifier, longitudinal_data —
all error paths exercisable without network, Census API, or crosswalks.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np

from siege_utilities.geo.timeseries.change_metrics import (
    calculate_change_metrics,
    calculate_multi_period_changes,
    calculate_index,
    _find_year_columns,
)
from siege_utilities.geo.timeseries.trend_classifier import (
    TrendThresholds,
    classify_trends,
    classify_by_quantiles,
    identify_outliers,
)
from siege_utilities.geo.timeseries.longitudinal_data import (
    validate_longitudinal_years,
    get_available_years,
    inflation_factor,
    LongitudinalAligner,
    _merge_to_wide_format,
)


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def wide_df():
    """Minimal wide-format DataFrame with 2 years."""
    return pd.DataFrame({
        "GEOID": ["001", "002"],
        "NAME": ["A", "B"],
        "income_2010": [50000, 60000],
        "income_2020": [65000, 55000],
    })


@pytest.fixture
def wide_df_3years():
    """Wide-format DataFrame with 3 consecutive years."""
    return pd.DataFrame({
        "GEOID": ["001", "002"],
        "NAME": ["A", "B"],
        "pop_2010": [1000, 2000],
        "pop_2015": [1100, 1900],
        "pop_2020": [1200, 1800],
    })


@pytest.fixture
def trend_df():
    """DataFrame with a numeric change column for trend classification."""
    return pd.DataFrame({
        "GEOID": ["g1", "g2", "g3"],
        "pct_change": [25.0, 0.0, -30.0],
    })


# =========================================================================
# change_metrics: calculate_change_metrics
# =========================================================================

class TestChangeMetricsMissingColumn:
    def test_nonexistent_variable_raises(self, wide_df):
        with pytest.raises(ValueError, match="No year-suffixed columns found"):
            calculate_change_metrics(
                df=wide_df,
                value_column="BOGUS",
            )


class TestChangeMetricsInvalidStartYear:
    def test_missing_start_year_raises(self, wide_df):
        with pytest.raises(ValueError, match="Start year 2005 not found"):
            calculate_change_metrics(
                df=wide_df,
                value_column="income",
                start_year=2005,
                end_year=2020,
            )


class TestChangeMetricsInvalidEndYear:
    def test_missing_end_year_raises(self, wide_df):
        with pytest.raises(ValueError, match="End year 2025 not found"):
            calculate_change_metrics(
                df=wide_df,
                value_column="income",
                start_year=2010,
                end_year=2025,
            )


class TestChangeMetricsNoYearSuffix:
    def test_column_without_year_suffix_not_found(self):
        df = pd.DataFrame({"income": [100, 200], "GEOID": ["a", "b"]})
        with pytest.raises(ValueError, match="No year-suffixed columns found"):
            calculate_change_metrics(df=df, value_column="income")


# =========================================================================
# change_metrics: calculate_multi_period_changes
# =========================================================================

class TestMultiPeriodNeedsTwoYears:
    def test_single_year_raises(self):
        df = pd.DataFrame({
            "GEOID": ["001"],
            "val_2020": [100],
        })
        with pytest.raises(ValueError, match="Need at least 2 years"):
            calculate_multi_period_changes(df=df, value_column="val")


# =========================================================================
# change_metrics: calculate_index
# =========================================================================

class TestCalculateIndexMissingBaseYear:
    def test_invalid_base_year_raises(self, wide_df):
        with pytest.raises(ValueError, match="Base year 2000 not found"):
            calculate_index(
                df=wide_df,
                value_column="income",
                base_year=2000,
            )


# =========================================================================
# change_metrics: _find_year_columns
# =========================================================================

class TestFindYearColumns:
    def test_no_matching_columns_returns_empty(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        assert _find_year_columns(df, "income") == {}

    def test_non_year_suffix_ignored(self):
        df = pd.DataFrame({"income_abc": [1], "income_999": [2]})
        # "abc" is not a year, "999" is outside 1900-2100
        assert _find_year_columns(df, "income") == {}

    def test_valid_years_detected(self, wide_df):
        result = _find_year_columns(wide_df, "income")
        assert 2010 in result
        assert 2020 in result
        assert result[2010] == "income_2010"


# =========================================================================
# trend_classifier: classify_trends
# =========================================================================

class TestClassifyTrendsInvalidPreset:
    def test_unknown_preset_raises(self, trend_df):
        with pytest.raises(ValueError, match="Unknown threshold preset"):
            classify_trends(
                df=trend_df,
                change_column="pct_change",
                thresholds="nonexistent_preset",
            )


class TestClassifyTrendsMissingColumn:
    def test_missing_change_column_raises_key_error(self, trend_df):
        with pytest.raises(KeyError):
            classify_trends(
                df=trend_df,
                change_column="does_not_exist",
            )


# =========================================================================
# trend_classifier: classify_by_quantiles
# =========================================================================

class TestQuantilesLabelMismatch:
    def test_wrong_label_count_raises(self, trend_df):
        with pytest.raises(ValueError, match="Number of labels"):
            classify_by_quantiles(
                df=trend_df,
                change_column="pct_change",
                n_quantiles=5,
                labels=["a", "b"],
            )


class TestQuantilesMissingColumn:
    def test_missing_column_raises_key_error(self, trend_df):
        with pytest.raises(KeyError):
            classify_by_quantiles(
                df=trend_df,
                change_column="nonexistent",
            )


# =========================================================================
# trend_classifier: identify_outliers
# =========================================================================

class TestOutliersInvalidMethod:
    def test_unknown_method_raises(self, trend_df):
        with pytest.raises(ValueError, match="Unknown method"):
            identify_outliers(
                df=trend_df,
                change_column="pct_change",
                method="magic",
            )


class TestOutliersMissingColumn:
    def test_missing_column_raises_key_error(self, trend_df):
        with pytest.raises(KeyError):
            identify_outliers(
                df=trend_df,
                change_column="nope",
                method="iqr",
            )


# =========================================================================
# longitudinal_data: validate_longitudinal_years
# =========================================================================

class TestValidateYearsNoValid:
    def test_all_invalid_raises(self):
        with pytest.raises(ValueError, match="No valid years"):
            validate_longitudinal_years([1800, 1801], dataset="acs5")


class TestValidateYearsMixed:
    def test_returns_only_valid(self):
        valid = validate_longitudinal_years([2020, 1800], dataset="acs5")
        assert 2020 in valid
        assert 1800 not in valid


class TestValidateYearsEmptyInput:
    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="No valid years"):
            validate_longitudinal_years([], dataset="acs5")


# =========================================================================
# longitudinal_data: get_available_years
# =========================================================================

class TestGetAvailableYearsUnknownDataset:
    def test_unknown_dataset_returns_empty(self):
        assert get_available_years(dataset="nonexistent") == []


class TestGetAvailableYearsKnownDatasets:
    def test_acs5_returns_nonempty(self):
        years = get_available_years(dataset="acs5")
        assert len(years) > 0
        assert 2020 in years

    def test_decennial_returns_nonempty(self):
        years = get_available_years(dataset="dec")
        assert len(years) > 0
        assert 2010 in years


# =========================================================================
# longitudinal_data: inflation_factor
# =========================================================================

class TestInflationFactorMissingYear:
    def test_unknown_from_year_raises_key_error(self):
        with pytest.raises(KeyError):
            inflation_factor(1800, 2020)

    def test_unknown_to_year_raises_key_error(self):
        with pytest.raises(KeyError):
            inflation_factor(2020, 2099)


class TestInflationFactorSameYear:
    def test_same_year_returns_one(self):
        factor = inflation_factor(2020, 2020)
        assert factor == pytest.approx(1.0)


# =========================================================================
# longitudinal_data: LongitudinalAligner
# =========================================================================

class TestAlignerInvalidTargetVintage:
    def test_invalid_vintage_raises(self):
        with pytest.raises(ValueError, match="target_vintage must be"):
            LongitudinalAligner(target_vintage=2015)


class TestAlignerValidVintages:
    def test_2000_accepted(self):
        a = LongitudinalAligner(target_vintage=2000)
        assert a.target_vintage == 2000

    def test_2010_accepted(self):
        a = LongitudinalAligner(target_vintage=2010)
        assert a.target_vintage == 2010

    def test_2020_accepted(self):
        a = LongitudinalAligner(target_vintage=2020)
        assert a.target_vintage == 2020


class TestAlignerIdentityAlignment:
    def test_same_vintage_returns_identity(self):
        aligner = LongitudinalAligner(target_vintage=2020)
        df = pd.DataFrame({"GEOID": ["001"], "val": [100]})
        result = aligner.align(df, source_vintage=2020)
        assert result.method == "identity"
        assert result.rows_before == 1
        assert result.rows_after == 1
        assert result.data.equals(df)


class TestAlignerTransitionChain:
    def test_same_vintage_empty_chain(self):
        chain = LongitudinalAligner._transition_chain(2020, 2020)
        assert chain == []

    def test_direct_2010_to_2020(self):
        chain = LongitudinalAligner._transition_chain(2010, 2020)
        assert chain == [(2010, 2020)]

    def test_chained_2000_to_2020(self):
        chain = LongitudinalAligner._transition_chain(2000, 2020)
        assert chain == [(2000, 2010), (2010, 2020)]

    def test_reverse_chained_2020_to_2000(self):
        chain = LongitudinalAligner._transition_chain(2020, 2000)
        assert chain == [(2020, 2010), (2010, 2000)]

    def test_unsupported_vintage_raises(self):
        with pytest.raises(ValueError, match="No supported crosswalk path"):
            LongitudinalAligner._transition_chain(1990, 2020)


# =========================================================================
# longitudinal_data: _merge_to_wide_format
# =========================================================================

class TestMergeToWideFormatEmpty:
    def test_empty_dict_raises(self):
        with pytest.raises(ValueError, match="No yearly data to merge"):
            _merge_to_wide_format(
                yearly_data={},
                var_list=["income"],
                include_moe=False,
            )


class TestMergeToWideFormatSingleYear:
    def test_single_year_produces_one_suffixed_column(self):
        df = pd.DataFrame({
            "GEOID": ["001", "002"],
            "NAME": ["A", "B"],
            "income": [100, 200],
        })
        result = _merge_to_wide_format(
            yearly_data={2020: df},
            var_list=["income"],
            include_moe=False,
        )
        assert "income_2020" in result.columns
        assert len(result) == 2


# =========================================================================
# Edge cases: NaN / inf handling
# =========================================================================

class TestChangeMetricsZeroDivision:
    def test_zero_start_value_produces_nan_not_inf(self):
        df = pd.DataFrame({
            "GEOID": ["001"],
            "val_2010": [0],
            "val_2020": [100],
        })
        result = calculate_change_metrics(
            df=df, value_column="val",
            start_year=2010, end_year=2020,
            metrics=["percent"],
        )
        pct_col = "val_pct_change_2010_2020"
        assert pct_col in result.columns
        # Division by zero should produce NaN, not inf
        assert pd.isna(result[pct_col].iloc[0])


class TestChangeMetricsNegativeValuesCAGR:
    def test_negative_start_cagr_produces_nan(self):
        df = pd.DataFrame({
            "GEOID": ["001"],
            "val_2010": [-100],
            "val_2020": [100],
        })
        result = calculate_change_metrics(
            df=df, value_column="val",
            start_year=2010, end_year=2020,
            metrics=["cagr"],
        )
        cagr_col = "val_cagr_2010_2020"
        assert cagr_col in result.columns
        # Negative ratio -> NaN
        assert pd.isna(result[cagr_col].iloc[0])


class TestClassifyByZscoreAllSameValue:
    def test_zero_std_produces_average(self):
        from siege_utilities.geo.timeseries.trend_classifier import classify_by_zscore

        df = pd.DataFrame({
            "GEOID": ["g1", "g2", "g3"],
            "change": [5.0, 5.0, 5.0],
        })
        result = classify_by_zscore(df, change_column="change")
        assert (result["trend_zscore_category"] == "average").all()
        assert (result["change_zscore"] == 0.0).all()


class TestAlignerAdjustInflation:
    def test_adjusts_dollar_columns(self):
        df = pd.DataFrame({
            "GEOID": ["001"],
            "income": [50000.0],
            "population": [1000],
        })
        result = LongitudinalAligner.adjust_inflation(
            df, dollar_columns=["income"],
            from_year=2010, to_year=2020,
        )
        factor = inflation_factor(2010, 2020)
        assert result["income"].iloc[0] == pytest.approx(50000.0 * factor)
        # Non-dollar column unchanged
        assert result["population"].iloc[0] == 1000

    def test_missing_column_silently_skipped(self):
        df = pd.DataFrame({"GEOID": ["001"], "income": [50000.0]})
        # "bonus" not in columns -- should not raise
        result = LongitudinalAligner.adjust_inflation(
            df, dollar_columns=["income", "bonus"],
            from_year=2010, to_year=2020,
        )
        assert "income" in result.columns
