"""
Time-series analysis for Census longitudinal data.

This module provides tools for analyzing Census data across multiple years,
including change metrics, trend classification, and multi-year data fetching.

Key features:
- Fetch data for multiple years with automatic boundary normalization
- Calculate change metrics (absolute, percent, CAGR)
- Classify trends into categories (rapid growth, stable, decline, etc.)
- Support for various analysis approaches

Example usage:
    from siege_utilities.geo.timeseries import (
        get_longitudinal_data,
        calculate_change_metrics,
        classify_trends
    )

    # Fetch income data for multiple years
    df = get_longitudinal_data(
        variables='B19013_001E',
        years=[2010, 2015, 2020],
        geography='tract',
        state='California',
        target_year=2020  # Normalize all to 2020 boundaries
    )

    # Calculate change metrics
    df = calculate_change_metrics(
        df=df,
        value_column='B19013_001E',
        start_year=2010,
        end_year=2020,
        metrics=['absolute', 'percent', 'cagr']
    )

    # Classify trends
    df = classify_trends(
        df=df,
        change_column='B19013_001E_pct_change_2010_2020'
    )
"""

from .longitudinal_data import (
    # Main function
    get_longitudinal_data,
    # Utility functions
    get_available_years,
    validate_longitudinal_years,
    # Constants
    ACS5_AVAILABLE_YEARS,
    DECENNIAL_YEARS,
    BOUNDARY_CHANGE_YEARS,
)

from .change_metrics import (
    # Main functions
    calculate_change_metrics,
    calculate_multi_period_changes,
    calculate_index,
    get_change_summary,
)

from .trend_classifier import (
    # Enums and classes
    TrendCategory,
    TrendThresholds,
    # Main functions
    classify_trends,
    classify_by_zscore,
    classify_by_quantiles,
    # Analysis functions
    get_trend_summary,
    identify_outliers,
    compare_trends,
    # Presets
    THRESHOLD_PRESETS,
    DEFAULT_THRESHOLDS,
)

__all__ = [
    # Longitudinal data
    'get_longitudinal_data',
    'get_available_years',
    'validate_longitudinal_years',
    'ACS5_AVAILABLE_YEARS',
    'DECENNIAL_YEARS',
    'BOUNDARY_CHANGE_YEARS',
    # Change metrics
    'calculate_change_metrics',
    'calculate_multi_period_changes',
    'calculate_index',
    'get_change_summary',
    # Trend classification
    'TrendCategory',
    'TrendThresholds',
    'classify_trends',
    'classify_by_zscore',
    'classify_by_quantiles',
    'get_trend_summary',
    'identify_outliers',
    'compare_trends',
    'THRESHOLD_PRESETS',
    'DEFAULT_THRESHOLDS',
]
