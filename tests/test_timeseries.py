"""
Unit tests for Census time-series analysis module.

Tests longitudinal data fetching, change metrics, and trend classification.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from siege_utilities.geo.timeseries import (
    # Longitudinal data
    get_longitudinal_data,
    get_available_years,
    validate_longitudinal_years,
    ACS5_AVAILABLE_YEARS,
    DECENNIAL_YEARS,
    # Change metrics
    calculate_change_metrics,
    calculate_multi_period_changes,
    calculate_index,
    get_change_summary,
    # Trend classification
    TrendCategory,
    TrendThresholds,
    classify_trends,
    classify_by_zscore,
    classify_by_quantiles,
    get_trend_summary,
    identify_outliers,
    compare_trends,
    THRESHOLD_PRESETS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def wide_format_data():
    """Create wide-format longitudinal data for testing."""
    return pd.DataFrame({
        'GEOID': ['06037010100', '06037010200', '06037010300', '06037010400', '06037010500'],
        'NAME': ['Tract 101', 'Tract 102', 'Tract 103', 'Tract 104', 'Tract 105'],
        'B19013_001E_2010': [50000, 60000, 45000, 70000, 55000],
        'B19013_001E_2015': [55000, 58000, 48000, 72000, 52000],
        'B19013_001E_2020': [65000, 55000, 50000, 75000, 45000],
    })


@pytest.fixture
def wide_format_multi_var():
    """Create wide-format data with multiple variables."""
    return pd.DataFrame({
        'GEOID': ['06037010100', '06037010200', '06037010300'],
        'NAME': ['Tract 101', 'Tract 102', 'Tract 103'],
        'B19013_001E_2010': [50000, 60000, 45000],
        'B19013_001E_2020': [65000, 55000, 50000],
        'B01001_001E_2010': [5000, 3000, 4000],
        'B01001_001E_2020': [5500, 2800, 4200],
    })


@pytest.fixture
def data_with_trends():
    """Create data with clear trend patterns."""
    return pd.DataFrame({
        'GEOID': ['g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7'],
        'change_pct': [25.0, 10.0, 0.0, -3.0, -10.0, -25.0, 50.0],  # Various trends
    })


@pytest.fixture
def mock_census_client():
    """Create a mock CensusAPIClient."""
    mock = MagicMock()
    return mock


# =============================================================================
# LONGITUDINAL DATA TESTS
# =============================================================================

class TestLongitudinalData:
    """Tests for longitudinal data functions."""

    def test_get_available_years_acs5(self):
        """Test getting available years for ACS5."""
        years = get_available_years(dataset='acs5')
        assert len(years) > 0
        assert 2020 in years

    def test_get_available_years_decennial(self):
        """Test getting available years for decennial."""
        years = get_available_years(dataset='dec')
        assert 2010 in years
        assert 2020 in years

    def test_validate_longitudinal_years_valid(self):
        """Test validating valid years."""
        years = validate_longitudinal_years([2015, 2020], dataset='acs5')
        assert 2015 in years
        assert 2020 in years

    def test_validate_longitudinal_years_invalid(self):
        """Test validating with no valid years."""
        with pytest.raises(ValueError, match="No valid years"):
            validate_longitudinal_years([1900, 1901], dataset='acs5')

    def test_validate_longitudinal_years_mixed(self):
        """Test validating mix of valid and invalid years."""
        years = validate_longitudinal_years([2015, 2020, 1900], dataset='acs5')
        assert 2015 in years
        assert 2020 in years
        assert 1900 not in years


# =============================================================================
# CHANGE METRICS TESTS
# =============================================================================

class TestChangeMetrics:
    """Tests for change metrics calculations."""

    def test_calculate_change_metrics_basic(self, wide_format_data):
        """Test basic change metric calculation."""
        result = calculate_change_metrics(
            df=wide_format_data,
            value_column='B19013_001E',
            start_year=2010,
            end_year=2020,
            metrics=['absolute', 'percent']
        )

        assert 'B19013_001E_change_2010_2020' in result.columns
        assert 'B19013_001E_pct_change_2010_2020' in result.columns

        # Check first row: 50000 -> 65000 = 15000 change, 30% increase
        row = result[result['GEOID'] == '06037010100'].iloc[0]
        assert row['B19013_001E_change_2010_2020'] == 15000
        assert abs(row['B19013_001E_pct_change_2010_2020'] - 30.0) < 0.1

    def test_calculate_change_metrics_cagr(self, wide_format_data):
        """Test CAGR calculation."""
        result = calculate_change_metrics(
            df=wide_format_data,
            value_column='B19013_001E',
            start_year=2010,
            end_year=2020,
            metrics=['cagr']
        )

        assert 'B19013_001E_cagr_2010_2020' in result.columns

        # CAGR should be between 0 and 5% for typical income growth
        cagr_col = result['B19013_001E_cagr_2010_2020']
        assert cagr_col.notna().any()

    def test_calculate_change_metrics_annualized(self, wide_format_data):
        """Test annualized change calculation."""
        result = calculate_change_metrics(
            df=wide_format_data,
            value_column='B19013_001E',
            start_year=2010,
            end_year=2020,
            metrics=['annualized']
        )

        assert 'B19013_001E_annual_change_2010_2020' in result.columns

        # First row: 15000 change over 10 years = 1500/year
        row = result[result['GEOID'] == '06037010100'].iloc[0]
        assert row['B19013_001E_annual_change_2010_2020'] == 1500

    def test_calculate_change_metrics_auto_years(self, wide_format_data):
        """Test automatic year detection."""
        result = calculate_change_metrics(
            df=wide_format_data,
            value_column='B19013_001E',
            metrics=['absolute']
        )

        # Should auto-detect 2010 and 2020
        assert 'B19013_001E_change_2010_2020' in result.columns

    def test_calculate_change_metrics_missing_column(self, wide_format_data):
        """Test error for non-existent variable."""
        with pytest.raises(ValueError, match="No year-suffixed columns found"):
            calculate_change_metrics(
                df=wide_format_data,
                value_column='NONEXISTENT',
                metrics=['absolute']
            )

    def test_calculate_change_metrics_missing_year(self, wide_format_data):
        """Test error for missing year."""
        with pytest.raises(ValueError, match="Start year .* not found"):
            calculate_change_metrics(
                df=wide_format_data,
                value_column='B19013_001E',
                start_year=2005,
                end_year=2020
            )


class TestMultiPeriodChanges:
    """Tests for multi-period change calculations."""

    def test_calculate_multi_period_changes(self, wide_format_data):
        """Test calculating changes between consecutive periods."""
        result = calculate_multi_period_changes(
            df=wide_format_data,
            value_column='B19013_001E',
            metrics=['absolute', 'percent']
        )

        # Should have 2010-2015 and 2015-2020 changes
        assert 'B19013_001E_change_2010_2015' in result.columns
        assert 'B19013_001E_change_2015_2020' in result.columns
        assert 'B19013_001E_pct_change_2010_2015' in result.columns
        assert 'B19013_001E_pct_change_2015_2020' in result.columns


class TestCalculateIndex:
    """Tests for index calculation."""

    def test_calculate_index_default_base(self, wide_format_data):
        """Test index calculation with default base year."""
        result = calculate_index(
            df=wide_format_data,
            value_column='B19013_001E',
            base_year=2010
        )

        # Base year should be 100
        assert 'B19013_001E_index_2010' in result.columns
        assert (result['B19013_001E_index_2010'] == 100.0).all()

        # 2020 values should be relative to 2010
        assert 'B19013_001E_index_2020' in result.columns

        # First row: 65000/50000 * 100 = 130
        row = result[result['GEOID'] == '06037010100'].iloc[0]
        assert abs(row['B19013_001E_index_2020'] - 130.0) < 0.1


class TestChangeSummary:
    """Tests for change summary statistics."""

    def test_get_change_summary(self, wide_format_data):
        """Test getting change summary statistics."""
        summary = get_change_summary(
            df=wide_format_data,
            value_column='B19013_001E',
            start_year=2010,
            end_year=2020
        )

        assert summary['variable'] == 'B19013_001E'
        assert summary['start_year'] == 2010
        assert summary['end_year'] == 2020
        assert summary['n_geographies'] == 5
        assert 'absolute_change' in summary
        assert 'percent_change' in summary
        assert 'cagr' in summary
        assert 'increasing' in summary
        assert 'decreasing' in summary


# =============================================================================
# TREND CLASSIFICATION TESTS
# =============================================================================

class TestTrendCategory:
    """Tests for TrendCategory enum."""

    def test_trend_category_values(self):
        """Test TrendCategory enum values."""
        assert TrendCategory.RAPID_GROWTH.value == "rapid_growth"
        assert TrendCategory.MODERATE_GROWTH.value == "moderate_growth"
        assert TrendCategory.STABLE.value == "stable"
        assert TrendCategory.MODERATE_DECLINE.value == "moderate_decline"
        assert TrendCategory.RAPID_DECLINE.value == "rapid_decline"


class TestTrendThresholds:
    """Tests for TrendThresholds data class."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresh = TrendThresholds()
        assert thresh.rapid_growth == 20.0
        assert thresh.moderate_growth == 5.0
        assert thresh.stable_lower == -5.0
        assert thresh.moderate_decline == -20.0

    def test_custom_thresholds(self):
        """Test creating custom thresholds."""
        thresh = TrendThresholds(
            rapid_growth=30.0,
            moderate_growth=10.0,
            stable_lower=-10.0,
            moderate_decline=-30.0
        )
        assert thresh.rapid_growth == 30.0
        assert thresh.moderate_decline == -30.0

    def test_to_dict(self):
        """Test threshold dict conversion."""
        thresh = TrendThresholds()
        d = thresh.to_dict()
        assert 'rapid_growth' in d
        assert 'stable' in d


class TestClassifyTrends:
    """Tests for trend classification functions."""

    def test_classify_trends_default(self, data_with_trends):
        """Test trend classification with default thresholds."""
        result = classify_trends(
            df=data_with_trends,
            change_column='change_pct'
        )

        assert 'trend_category' in result.columns

        # Check specific classifications
        row_rapid_growth = result[result['GEOID'] == 'g1'].iloc[0]  # 25%
        assert row_rapid_growth['trend_category'] == 'rapid_growth'

        row_moderate_growth = result[result['GEOID'] == 'g2'].iloc[0]  # 10%
        assert row_moderate_growth['trend_category'] == 'moderate_growth'

        row_stable = result[result['GEOID'] == 'g3'].iloc[0]  # 0%
        assert row_stable['trend_category'] == 'stable'

        row_rapid_decline = result[result['GEOID'] == 'g6'].iloc[0]  # -25%
        assert row_rapid_decline['trend_category'] == 'rapid_decline'

    def test_classify_trends_preset(self, data_with_trends):
        """Test trend classification with preset thresholds."""
        result = classify_trends(
            df=data_with_trends,
            change_column='change_pct',
            thresholds='conservative'
        )

        assert 'trend_category' in result.columns

    def test_classify_trends_custom_thresholds(self, data_with_trends):
        """Test trend classification with custom thresholds."""
        result = classify_trends(
            df=data_with_trends,
            change_column='change_pct',
            thresholds={
                'rapid_growth': 40.0,
                'moderate_growth': 15.0,
                'stable_lower': -15.0,
                'moderate_decline': -40.0
            }
        )

        # With threshold of 40%, only 50% should be rapid growth
        row_50pct = result[result['GEOID'] == 'g7'].iloc[0]
        assert row_50pct['trend_category'] == 'rapid_growth'

        row_25pct = result[result['GEOID'] == 'g1'].iloc[0]
        assert row_25pct['trend_category'] == 'moderate_growth'

    def test_classify_trends_custom_output_column(self, data_with_trends):
        """Test trend classification with custom output column name."""
        result = classify_trends(
            df=data_with_trends,
            change_column='change_pct',
            output_column='my_trend'
        )

        assert 'my_trend' in result.columns
        assert 'trend_category' not in result.columns

    def test_classify_trends_invalid_preset(self, data_with_trends):
        """Test error for invalid preset name."""
        with pytest.raises(ValueError, match="Unknown threshold preset"):
            classify_trends(
                df=data_with_trends,
                change_column='change_pct',
                thresholds='invalid_preset'
            )


class TestClassifyByZscore:
    """Tests for z-score based classification."""

    def test_classify_by_zscore(self, data_with_trends):
        """Test z-score classification."""
        result = classify_by_zscore(
            df=data_with_trends,
            change_column='change_pct'
        )

        assert 'trend_zscore_category' in result.columns
        assert 'change_pct_zscore' in result.columns

        # Check that categories are present
        categories = result['trend_zscore_category'].unique()
        assert len(categories) > 0


class TestClassifyByQuantiles:
    """Tests for quantile-based classification."""

    def test_classify_by_quantiles_default(self, data_with_trends):
        """Test quintile classification."""
        result = classify_by_quantiles(
            df=data_with_trends,
            change_column='change_pct',
            n_quantiles=5
        )

        assert 'trend_quantile' in result.columns
        # Should have labels: lowest, low, middle, high, highest
        unique_labels = result['trend_quantile'].unique()
        assert len(unique_labels) <= 5

    def test_classify_by_quantiles_custom_labels(self, data_with_trends):
        """Test quantile classification with custom labels."""
        result = classify_by_quantiles(
            df=data_with_trends,
            change_column='change_pct',
            n_quantiles=3,
            labels=['bottom', 'middle', 'top']
        )

        assert 'trend_quantile' in result.columns

    def test_classify_by_quantiles_wrong_labels(self, data_with_trends):
        """Test error when label count doesn't match quantiles."""
        with pytest.raises(ValueError, match="Number of labels"):
            classify_by_quantiles(
                df=data_with_trends,
                change_column='change_pct',
                n_quantiles=5,
                labels=['a', 'b']  # Wrong count
            )


class TestTrendSummary:
    """Tests for trend summary functions."""

    def test_get_trend_summary(self, data_with_trends):
        """Test getting trend summary statistics."""
        # First classify
        df = classify_trends(data_with_trends, 'change_pct')

        summary = get_trend_summary(df, 'trend_category')

        assert summary['total_geographies'] == 7
        assert 'categories' in summary
        assert 'overview' in summary
        assert 'growing' in summary['overview']
        assert 'declining' in summary['overview']


class TestIdentifyOutliers:
    """Tests for outlier identification."""

    def test_identify_outliers_iqr(self, data_with_trends):
        """Test outlier identification using IQR method."""
        result = identify_outliers(
            df=data_with_trends,
            change_column='change_pct',
            method='iqr'
        )

        assert 'is_outlier' in result.columns
        assert 'outlier_type' in result.columns

    def test_identify_outliers_zscore(self, data_with_trends):
        """Test outlier identification using z-score method."""
        result = identify_outliers(
            df=data_with_trends,
            change_column='change_pct',
            method='zscore'
        )

        assert 'is_outlier' in result.columns
        assert 'outlier_type' in result.columns

    def test_identify_outliers_invalid_method(self, data_with_trends):
        """Test error for invalid method."""
        with pytest.raises(ValueError, match="Unknown method"):
            identify_outliers(
                df=data_with_trends,
                change_column='change_pct',
                method='invalid'
            )


class TestCompareTrends:
    """Tests for trend comparison."""

    def test_compare_trends(self, data_with_trends):
        """Test comparing trends between two DataFrames."""
        df1 = classify_trends(data_with_trends.copy(), 'change_pct')
        df2 = classify_trends(data_with_trends.copy(), 'change_pct')

        # Modify some trends in df2
        df2.loc[df2['GEOID'] == 'g1', 'trend_category'] = 'moderate_growth'

        comparison = compare_trends(df1, df2)

        assert 'trend_changed' in comparison.columns
        assert 'trend_transition' in comparison.columns

        # Check that g1 shows as changed
        g1_row = comparison[comparison['GEOID'] == 'g1'].iloc[0]
        assert g1_row['trend_changed'] == True


# =============================================================================
# THRESHOLD PRESETS TESTS
# =============================================================================

class TestThresholdPresets:
    """Tests for threshold preset configurations."""

    def test_default_preset(self):
        """Test default preset exists and has correct values."""
        assert 'default' in THRESHOLD_PRESETS
        default = THRESHOLD_PRESETS['default']
        assert default.rapid_growth == 20.0

    def test_conservative_preset(self):
        """Test conservative preset has higher thresholds."""
        assert 'conservative' in THRESHOLD_PRESETS
        conservative = THRESHOLD_PRESETS['conservative']
        assert conservative.rapid_growth > THRESHOLD_PRESETS['default'].rapid_growth

    def test_sensitive_preset(self):
        """Test sensitive preset has lower thresholds."""
        assert 'sensitive' in THRESHOLD_PRESETS
        sensitive = THRESHOLD_PRESETS['sensitive']
        assert sensitive.rapid_growth < THRESHOLD_PRESETS['default'].rapid_growth

    def test_all_presets_valid(self):
        """Test all presets have required attributes."""
        for name, preset in THRESHOLD_PRESETS.items():
            assert hasattr(preset, 'rapid_growth')
            assert hasattr(preset, 'moderate_growth')
            assert hasattr(preset, 'stable_lower')
            assert hasattr(preset, 'moderate_decline')
