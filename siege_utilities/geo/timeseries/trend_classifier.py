"""
Trend classification for Census time-series analysis.

This module provides functions to classify and categorize trends
in longitudinal Census data. It supports:

- Threshold-based classification (rapid growth, stable, decline, etc.)
- Statistical classification (z-score based)
- Custom classification schemes

Example usage:
    from siege_utilities.geo.timeseries import classify_trends

    # Classify income changes
    df = classify_trends(
        df=income_data,
        change_column='B19013_001E_pct_change_2010_2020'
    )

    # Result includes 'trend_category' column
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)


# =============================================================================
# TREND CATEGORIES
# =============================================================================

class TrendCategory(Enum):
    """Standard trend categories for classification."""

    RAPID_GROWTH = "rapid_growth"
    MODERATE_GROWTH = "moderate_growth"
    STABLE = "stable"
    MODERATE_DECLINE = "moderate_decline"
    RAPID_DECLINE = "rapid_decline"


# Default thresholds for percentage change classification
DEFAULT_THRESHOLDS = {
    TrendCategory.RAPID_GROWTH: 20.0,      # > 20% growth
    TrendCategory.MODERATE_GROWTH: 5.0,    # 5% to 20% growth
    TrendCategory.STABLE: -5.0,            # -5% to 5%
    TrendCategory.MODERATE_DECLINE: -20.0, # -20% to -5%
    TrendCategory.RAPID_DECLINE: None,     # < -20%
}


@dataclass
class TrendThresholds:
    """
    Threshold configuration for trend classification.

    Attributes:
        rapid_growth: Threshold for rapid growth (values >= this)
        moderate_growth: Threshold for moderate growth
        stable_lower: Lower bound for stable category
        moderate_decline: Threshold for moderate decline
        rapid_decline: Values below this (or moderate_decline if None)
    """

    rapid_growth: float = 20.0
    moderate_growth: float = 5.0
    stable_lower: float = -5.0
    moderate_decline: float = -20.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for display."""
        return {
            'rapid_growth': f'>= {self.rapid_growth}%',
            'moderate_growth': f'{self.moderate_growth}% to {self.rapid_growth}%',
            'stable': f'{self.stable_lower}% to {self.moderate_growth}%',
            'moderate_decline': f'{self.moderate_decline}% to {self.stable_lower}%',
            'rapid_decline': f'< {self.moderate_decline}%',
        }


# Preset threshold configurations
THRESHOLD_PRESETS = {
    'default': TrendThresholds(),
    'conservative': TrendThresholds(
        rapid_growth=30.0,
        moderate_growth=10.0,
        stable_lower=-10.0,
        moderate_decline=-30.0
    ),
    'sensitive': TrendThresholds(
        rapid_growth=10.0,
        moderate_growth=2.0,
        stable_lower=-2.0,
        moderate_decline=-10.0
    ),
    'housing': TrendThresholds(
        rapid_growth=25.0,
        moderate_growth=10.0,
        stable_lower=-5.0,
        moderate_decline=-15.0
    ),
    'population': TrendThresholds(
        rapid_growth=15.0,
        moderate_growth=5.0,
        stable_lower=-2.0,
        moderate_decline=-10.0
    ),
}


# =============================================================================
# TREND CLASSIFICATION FUNCTIONS
# =============================================================================

def classify_trends(
    df: pd.DataFrame,
    change_column: str,
    thresholds: Union[TrendThresholds, str, Dict[str, float], None] = None,
    output_column: str = 'trend_category'
) -> pd.DataFrame:
    """
    Classify changes into trend categories.

    Args:
        df: DataFrame with change metrics
        change_column: Column containing change values (typically percentage change)
        thresholds: Threshold configuration. Can be:
            - TrendThresholds object
            - Preset name ('default', 'conservative', 'sensitive', 'housing', 'population')
            - Dict with keys: rapid_growth, moderate_growth, stable_lower, moderate_decline
            - None (uses default thresholds)
        output_column: Name for the category column

    Returns:
        DataFrame with new trend_category column

    Example:
        df = classify_trends(
            df=income_changes,
            change_column='B19013_001E_pct_change_2010_2020',
            thresholds='conservative'
        )
    """
    df = df.copy()

    # Resolve thresholds
    if thresholds is None:
        thresh = THRESHOLD_PRESETS['default']
    elif isinstance(thresholds, str):
        if thresholds not in THRESHOLD_PRESETS:
            raise ValueError(
                f"Unknown threshold preset: '{thresholds}'. "
                f"Available: {list(THRESHOLD_PRESETS.keys())}"
            )
        thresh = THRESHOLD_PRESETS[thresholds]
    elif isinstance(thresholds, dict):
        thresh = TrendThresholds(**thresholds)
    else:
        thresh = thresholds

    log.info(f"Classifying trends in '{change_column}' using thresholds: {thresh.to_dict()}")

    # Get values
    values = df[change_column].astype(float)

    # Classify
    conditions = [
        values >= thresh.rapid_growth,
        (values >= thresh.moderate_growth) & (values < thresh.rapid_growth),
        (values >= thresh.stable_lower) & (values < thresh.moderate_growth),
        (values >= thresh.moderate_decline) & (values < thresh.stable_lower),
        values < thresh.moderate_decline,
    ]

    choices = [
        TrendCategory.RAPID_GROWTH.value,
        TrendCategory.MODERATE_GROWTH.value,
        TrendCategory.STABLE.value,
        TrendCategory.MODERATE_DECLINE.value,
        TrendCategory.RAPID_DECLINE.value,
    ]

    df[output_column] = np.select(conditions, choices, default='unknown')

    # Log distribution
    counts = df[output_column].value_counts()
    log.info(f"Trend distribution:\n{counts.to_string()}")

    return df


def classify_by_zscore(
    df: pd.DataFrame,
    change_column: str,
    output_column: str = 'trend_zscore_category'
) -> pd.DataFrame:
    """
    Classify trends using z-scores (statistical approach).

    This method classifies based on how many standard deviations
    a geography's change is from the mean, providing a relative
    classification within the dataset.

    Categories:
    - extreme_positive: z >= 2
    - high_positive: 1 <= z < 2
    - average: -1 < z < 1
    - high_negative: -2 < z <= -1
    - extreme_negative: z <= -2

    Args:
        df: DataFrame with change metrics
        change_column: Column containing change values
        output_column: Name for the category column

    Returns:
        DataFrame with z-score category column and z-score values
    """
    df = df.copy()

    values = df[change_column].astype(float)
    mean = values.mean()
    std = values.std()

    if std == 0 or pd.isna(std):
        log.warning("Standard deviation is zero or NaN, all values will be 'average'")
        df[output_column] = 'average'
        df[f'{change_column}_zscore'] = 0.0
        return df

    # Calculate z-scores
    zscores = (values - mean) / std
    df[f'{change_column}_zscore'] = zscores

    # Classify
    conditions = [
        zscores >= 2,
        (zscores >= 1) & (zscores < 2),
        (zscores > -1) & (zscores < 1),
        (zscores > -2) & (zscores <= -1),
        zscores <= -2,
    ]

    choices = [
        'extreme_positive',
        'high_positive',
        'average',
        'high_negative',
        'extreme_negative',
    ]

    df[output_column] = np.select(conditions, choices, default='average')

    return df


def classify_by_quantiles(
    df: pd.DataFrame,
    change_column: str,
    n_quantiles: int = 5,
    labels: Optional[List[str]] = None,
    output_column: str = 'trend_quantile'
) -> pd.DataFrame:
    """
    Classify trends into quantile-based categories.

    This method divides the data into equal-sized groups (quintiles,
    deciles, etc.) which is useful when you want balanced category sizes.

    Args:
        df: DataFrame with change metrics
        change_column: Column containing change values
        n_quantiles: Number of quantiles (default: 5 for quintiles)
        labels: Custom labels for quantiles. If None, uses:
            - 5 quantiles: ['lowest', 'low', 'middle', 'high', 'highest']
            - Other: numeric labels 1 to n
        output_column: Name for the category column

    Returns:
        DataFrame with quantile category column
    """
    df = df.copy()

    # Default labels for quintiles
    if labels is None:
        if n_quantiles == 5:
            labels = ['lowest', 'low', 'middle', 'high', 'highest']
        elif n_quantiles == 4:
            labels = ['lowest', 'low', 'high', 'highest']
        elif n_quantiles == 3:
            labels = ['low', 'middle', 'high']
        else:
            labels = [str(i + 1) for i in range(n_quantiles)]

    if len(labels) != n_quantiles:
        raise ValueError(
            f"Number of labels ({len(labels)}) must match n_quantiles ({n_quantiles})"
        )

    df[output_column] = pd.qcut(
        df[change_column],
        q=n_quantiles,
        labels=labels,
        duplicates='drop'
    )

    return df


def get_trend_summary(
    df: pd.DataFrame,
    trend_column: str = 'trend_category',
    geoid_column: str = 'GEOID'
) -> Dict:
    """
    Get summary statistics for trend classification.

    Args:
        df: DataFrame with trend categories
        trend_column: Name of the trend category column
        geoid_column: Name of the GEOID column

    Returns:
        Dictionary with summary statistics
    """
    counts = df[trend_column].value_counts()
    percentages = df[trend_column].value_counts(normalize=True) * 100

    summary = {
        'total_geographies': len(df),
        'categories': {},
    }

    for category in counts.index:
        summary['categories'][category] = {
            'count': int(counts[category]),
            'percentage': round(percentages[category], 1),
        }

    # Calculate growth vs decline
    growth_cats = [TrendCategory.RAPID_GROWTH.value, TrendCategory.MODERATE_GROWTH.value]
    decline_cats = [TrendCategory.RAPID_DECLINE.value, TrendCategory.MODERATE_DECLINE.value]

    growth_count = df[df[trend_column].isin(growth_cats)].shape[0]
    decline_count = df[df[trend_column].isin(decline_cats)].shape[0]
    stable_count = df[df[trend_column] == TrendCategory.STABLE.value].shape[0]

    summary['overview'] = {
        'growing': growth_count,
        'declining': decline_count,
        'stable': stable_count,
        'growth_to_decline_ratio': round(growth_count / max(decline_count, 1), 2),
    }

    return summary


def identify_outliers(
    df: pd.DataFrame,
    change_column: str,
    method: str = 'iqr',
    threshold: float = 1.5
) -> pd.DataFrame:
    """
    Identify outlier geographies based on change values.

    Args:
        df: DataFrame with change metrics
        change_column: Column containing change values
        method: Outlier detection method:
            - 'iqr': Interquartile range method
            - 'zscore': Z-score method
        threshold: Threshold for outlier detection:
            - For IQR: multiplier (default 1.5)
            - For zscore: number of standard deviations (default 1.5)

    Returns:
        DataFrame with is_outlier and outlier_type columns
    """
    df = df.copy()
    values = df[change_column].astype(float)

    if method == 'iqr':
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        df['is_outlier'] = (values < lower_bound) | (values > upper_bound)
        df['outlier_type'] = np.where(
            values < lower_bound, 'low_outlier',
            np.where(values > upper_bound, 'high_outlier', 'normal')
        )

    elif method == 'zscore':
        mean = values.mean()
        std = values.std()
        zscores = (values - mean) / std

        df['is_outlier'] = abs(zscores) > threshold
        df['outlier_type'] = np.where(
            zscores < -threshold, 'low_outlier',
            np.where(zscores > threshold, 'high_outlier', 'normal')
        )

    else:
        raise ValueError(f"Unknown method: '{method}'. Use 'iqr' or 'zscore'.")

    outlier_count = df['is_outlier'].sum()
    log.info(f"Identified {outlier_count} outliers using {method} method")

    return df


def compare_trends(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    trend_column: str = 'trend_category',
    geoid_column: str = 'GEOID'
) -> pd.DataFrame:
    """
    Compare trend classifications between two DataFrames.

    Useful for comparing trend patterns between different:
    - Time periods
    - Variables
    - Geographic subsets

    Args:
        df1: First DataFrame with trend classification
        df2: Second DataFrame with trend classification
        trend_column: Name of trend category column
        geoid_column: Name of GEOID column

    Returns:
        DataFrame with comparison columns
    """
    merged = df1[[geoid_column, trend_column]].merge(
        df2[[geoid_column, trend_column]],
        on=geoid_column,
        how='outer',
        suffixes=('_1', '_2')
    )

    col1 = f'{trend_column}_1'
    col2 = f'{trend_column}_2'

    merged['trend_changed'] = merged[col1] != merged[col2]

    # Create transition label
    merged['trend_transition'] = merged[col1].astype(str) + ' -> ' + merged[col2].astype(str)

    return merged
