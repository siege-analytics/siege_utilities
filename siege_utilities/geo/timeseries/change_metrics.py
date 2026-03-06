"""
Change metrics calculations for Census time-series analysis.

This module provides functions to calculate various change metrics
from longitudinal Census data, including:

- Absolute change
- Percentage change
- Compound Annual Growth Rate (CAGR)
- Per-period change rates

Example usage:
    from siege_utilities.geo.timeseries import calculate_change_metrics

    # Calculate metrics for income data
    df = calculate_change_metrics(
        df=longitudinal_data,
        value_column='B19013_001E',
        metrics=['absolute', 'percent', 'cagr']
    )
"""

import logging
from typing import List, Optional

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)


# =============================================================================
# CHANGE METRIC CALCULATIONS
# =============================================================================

def calculate_change_metrics(
    df: pd.DataFrame,
    value_column: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    metrics: List[str] = None
) -> pd.DataFrame:
    """
    Calculate change metrics for a variable across time.

    This function expects wide-format data with year-suffixed columns
    (e.g., B19013_001E_2010, B19013_001E_2020).

    Args:
        df: DataFrame with year-suffixed columns
        value_column: Base variable name (without year suffix)
        start_year: Start year for comparison. If None, uses earliest year found.
        end_year: End year for comparison. If None, uses latest year found.
        metrics: List of metrics to calculate. Options:
            - 'absolute': Raw change (end - start)
            - 'percent': Percentage change ((end - start) / start * 100)
            - 'cagr': Compound Annual Growth Rate
            - 'annualized': Annualized change (absolute change / years)
            Default: ['absolute', 'percent', 'cagr']

    Returns:
        DataFrame with original columns plus new metric columns:
        - {value_column}_change_{start}_{end}: Absolute change
        - {value_column}_pct_change_{start}_{end}: Percentage change
        - {value_column}_cagr_{start}_{end}: CAGR

    Example:
        df = calculate_change_metrics(
            df=income_data,
            value_column='B19013_001E',
            start_year=2010,
            end_year=2020,
            metrics=['absolute', 'percent', 'cagr']
        )
    """
    if metrics is None:
        metrics = ['absolute', 'percent', 'cagr']

    df = df.copy()

    # Find year columns for this variable
    year_cols = _find_year_columns(df, value_column)
    if not year_cols:
        raise ValueError(
            f"No year-suffixed columns found for '{value_column}'. "
            f"Expected columns like '{value_column}_2010', '{value_column}_2020'."
        )

    years = sorted(year_cols.keys())

    # Determine start and end years
    if start_year is None:
        start_year = min(years)
    if end_year is None:
        end_year = max(years)

    if start_year not in year_cols:
        raise ValueError(f"Start year {start_year} not found. Available: {years}")
    if end_year not in year_cols:
        raise ValueError(f"End year {end_year} not found. Available: {years}")

    start_col = year_cols[start_year]
    end_col = year_cols[end_year]
    num_years = end_year - start_year

    log.info(f"Calculating change metrics for {value_column}: {start_year} -> {end_year}")

    # Get values
    start_values = df[start_col].astype(float)
    end_values = df[end_col].astype(float)

    # Calculate absolute change
    if 'absolute' in metrics:
        col_name = f"{value_column}_change_{start_year}_{end_year}"
        df[col_name] = end_values - start_values

    # Calculate percentage change
    if 'percent' in metrics:
        col_name = f"{value_column}_pct_change_{start_year}_{end_year}"
        # Handle division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            pct_change = ((end_values - start_values) / start_values) * 100
            pct_change = pct_change.replace([np.inf, -np.inf], np.nan)
        df[col_name] = pct_change

    # Calculate CAGR
    if 'cagr' in metrics and num_years > 0:
        col_name = f"{value_column}_cagr_{start_year}_{end_year}"
        df[col_name] = _calculate_cagr(start_values, end_values, num_years)

    # Calculate annualized change
    if 'annualized' in metrics and num_years > 0:
        col_name = f"{value_column}_annual_change_{start_year}_{end_year}"
        df[col_name] = (end_values - start_values) / num_years

    return df


def _find_year_columns(df: pd.DataFrame, value_column: str) -> dict:
    """
    Find year-suffixed columns for a variable.

    Args:
        df: DataFrame
        value_column: Base variable name

    Returns:
        Dictionary mapping year to column name
    """
    year_cols = {}
    for col in df.columns:
        if col.startswith(f"{value_column}_"):
            suffix = col[len(value_column) + 1:]
            try:
                year = int(suffix)
                if 1900 <= year <= 2100:  # Reasonable year range
                    year_cols[year] = col
            except ValueError:
                continue
    return year_cols


def _calculate_cagr(
    start_values: pd.Series,
    end_values: pd.Series,
    num_years: int
) -> pd.Series:
    """
    Calculate Compound Annual Growth Rate.

    CAGR = ((End / Start) ^ (1 / Years)) - 1

    Args:
        start_values: Starting values
        end_values: Ending values
        num_years: Number of years between

    Returns:
        CAGR as percentage (e.g., 5.2 for 5.2% annual growth)
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        # Handle negative and zero values
        ratio = end_values / start_values

        # CAGR only makes sense for positive ratios
        ratio = ratio.where(ratio > 0, np.nan)

        cagr = (np.power(ratio, 1 / num_years) - 1) * 100
        cagr = cagr.replace([np.inf, -np.inf], np.nan)

    return cagr


def calculate_multi_period_changes(
    df: pd.DataFrame,
    value_column: str,
    metrics: List[str] = None
) -> pd.DataFrame:
    """
    Calculate change metrics between all consecutive periods.

    Args:
        df: DataFrame with year-suffixed columns
        value_column: Base variable name
        metrics: Metrics to calculate

    Returns:
        DataFrame with changes between each pair of consecutive years
    """
    if metrics is None:
        metrics = ['absolute', 'percent']

    year_cols = _find_year_columns(df, value_column)
    years = sorted(year_cols.keys())

    if len(years) < 2:
        raise ValueError(f"Need at least 2 years, found: {years}")

    df = df.copy()

    for i in range(len(years) - 1):
        start_year = years[i]
        end_year = years[i + 1]

        df = calculate_change_metrics(
            df=df,
            value_column=value_column,
            start_year=start_year,
            end_year=end_year,
            metrics=metrics
        )

    return df


def calculate_index(
    df: pd.DataFrame,
    value_column: str,
    base_year: Optional[int] = None,
    index_value: float = 100.0
) -> pd.DataFrame:
    """
    Calculate an index relative to a base year.

    This is useful for comparing changes across geographies with
    different absolute values.

    Args:
        df: DataFrame with year-suffixed columns
        value_column: Base variable name
        base_year: Year to use as index base. If None, uses earliest year.
        index_value: Value to set base year to (default: 100)

    Returns:
        DataFrame with indexed columns (e.g., B19013_001E_index_2010)

    Example:
        df = calculate_index(df, 'B19013_001E', base_year=2010)
        # Creates columns: B19013_001E_index_2010, B19013_001E_index_2015, ...
    """
    df = df.copy()

    year_cols = _find_year_columns(df, value_column)
    years = sorted(year_cols.keys())

    if base_year is None:
        base_year = min(years)

    if base_year not in year_cols:
        raise ValueError(f"Base year {base_year} not found. Available: {years}")

    base_col = year_cols[base_year]
    base_values = df[base_col].astype(float)

    for year, col in year_cols.items():
        index_col = f"{value_column}_index_{year}"
        with np.errstate(divide='ignore', invalid='ignore'):
            df[index_col] = (df[col].astype(float) / base_values) * index_value
            df[index_col] = df[index_col].replace([np.inf, -np.inf], np.nan)

    return df


def get_change_summary(
    df: pd.DataFrame,
    value_column: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
) -> dict:
    """
    Get summary statistics for changes in a variable.

    Args:
        df: DataFrame with year-suffixed columns
        value_column: Base variable name
        start_year: Start year
        end_year: End year

    Returns:
        Dictionary with summary statistics
    """
    # Calculate metrics first
    df = calculate_change_metrics(
        df=df.copy(),
        value_column=value_column,
        start_year=start_year,
        end_year=end_year,
        metrics=['absolute', 'percent', 'cagr']
    )

    year_cols = _find_year_columns(df, value_column)
    years = sorted(year_cols.keys())

    if start_year is None:
        start_year = min(years)
    if end_year is None:
        end_year = max(years)

    abs_col = f"{value_column}_change_{start_year}_{end_year}"
    pct_col = f"{value_column}_pct_change_{start_year}_{end_year}"
    cagr_col = f"{value_column}_cagr_{start_year}_{end_year}"

    return {
        'variable': value_column,
        'start_year': start_year,
        'end_year': end_year,
        'n_geographies': len(df),
        'absolute_change': {
            'mean': df[abs_col].mean(),
            'median': df[abs_col].median(),
            'std': df[abs_col].std(),
            'min': df[abs_col].min(),
            'max': df[abs_col].max(),
        },
        'percent_change': {
            'mean': df[pct_col].mean(),
            'median': df[pct_col].median(),
            'std': df[pct_col].std(),
            'min': df[pct_col].min(),
            'max': df[pct_col].max(),
        },
        'cagr': {
            'mean': df[cagr_col].mean(),
            'median': df[cagr_col].median(),
            'std': df[cagr_col].std(),
            'min': df[cagr_col].min(),
            'max': df[cagr_col].max(),
        },
        'increasing': (df[abs_col] > 0).sum(),
        'decreasing': (df[abs_col] < 0).sum(),
        'unchanged': (df[abs_col] == 0).sum(),
    }
