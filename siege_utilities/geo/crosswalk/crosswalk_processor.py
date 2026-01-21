"""
Crosswalk processor for transforming data between Census boundary years.

This module provides functions to apply crosswalk relationships to transform
data from one Census boundary vintage to another. It handles:

- One-to-one mappings: Simple GEOID rename
- One-to-many (splits): Disaggregate data using weights
- Many-to-one (merges): Aggregate data using weights

Example usage:
    from siege_utilities.geo.crosswalk import apply_crosswalk, WeightMethod

    # Transform 2010 data to 2020 boundaries
    df_2020 = apply_crosswalk(
        df=df_2010,
        source_year=2010,
        target_year=2020,
        weight_method=WeightMethod.AREA,
        aggregation_func='sum'
    )
"""

import logging
from typing import Callable, Dict, List, Optional, Union

import pandas as pd
import numpy as np

from .relationship_types import (
    RelationshipType,
    WeightMethod,
    CrosswalkRelationship,
    GeographyChange,
)
from .crosswalk_client import get_crosswalk

log = logging.getLogger(__name__)


# =============================================================================
# CROSSWALK PROCESSOR
# =============================================================================

class CrosswalkProcessor:
    """
    Processor for applying crosswalks to transform data between Census years.

    This class handles the logic of transforming data from one boundary
    vintage to another, accounting for splits, merges, and complex changes.

    Attributes:
        crosswalk_df: The crosswalk DataFrame with relationships
        source_year: Source boundary year
        target_year: Target boundary year
        geography_level: Geographic level being processed
    """

    def __init__(
        self,
        crosswalk_df: pd.DataFrame,
        source_year: int,
        target_year: int,
        geography_level: str
    ):
        """
        Initialize the processor with a crosswalk.

        Args:
            crosswalk_df: DataFrame from get_crosswalk()
            source_year: Source Census year
            target_year: Target Census year
            geography_level: Geographic level ('tract', 'county', etc.)
        """
        self.crosswalk_df = crosswalk_df
        self.source_year = source_year
        self.target_year = target_year
        self.geography_level = geography_level

        # Build lookup dictionaries for efficient processing
        self._build_lookups()

    def _build_lookups(self) -> None:
        """Build lookup dictionaries for efficient crosswalk processing."""
        # Source to targets mapping
        self.source_to_targets = {}
        for _, row in self.crosswalk_df.iterrows():
            source = row['source_geoid']
            target = row['target_geoid']
            weight = row.get('area_weight', 1.0)

            if source not in self.source_to_targets:
                self.source_to_targets[source] = []
            self.source_to_targets[source].append({
                'target_geoid': target,
                'area_weight': weight
            })

        # Target to sources mapping (for aggregation)
        self.target_to_sources = {}
        for _, row in self.crosswalk_df.iterrows():
            source = row['source_geoid']
            target = row['target_geoid']
            weight = row.get('area_weight', 1.0)

            if target not in self.target_to_sources:
                self.target_to_sources[target] = []
            self.target_to_sources[target].append({
                'source_geoid': source,
                'area_weight': weight
            })

        log.info(
            f"Built crosswalk lookups: {len(self.source_to_targets)} sources, "
            f"{len(self.target_to_sources)} targets"
        )

    def get_relationship_type(self, source_geoid: str) -> RelationshipType:
        """
        Determine the relationship type for a source geography.

        Args:
            source_geoid: GEOID in source year

        Returns:
            RelationshipType indicating how this geography changed
        """
        if source_geoid not in self.source_to_targets:
            log.warning(f"Source GEOID {source_geoid} not found in crosswalk")
            return RelationshipType.ONE_TO_ONE

        targets = self.source_to_targets[source_geoid]

        if len(targets) == 1:
            target_geoid = targets[0]['target_geoid']
            # Check if target has multiple sources (merge case)
            if len(self.target_to_sources.get(target_geoid, [])) > 1:
                return RelationshipType.MERGED
            return RelationshipType.ONE_TO_ONE
        else:
            return RelationshipType.SPLIT

    def get_geography_change(self, source_geoid: str) -> GeographyChange:
        """
        Get detailed change information for a source geography.

        Args:
            source_geoid: GEOID in source year

        Returns:
            GeographyChange object with relationship details
        """
        relationship_type = self.get_relationship_type(source_geoid)
        targets = self.source_to_targets.get(source_geoid, [])

        return GeographyChange(
            source_geoid=source_geoid,
            relationship_type=relationship_type,
            target_geoids=[t['target_geoid'] for t in targets],
            weights={t['target_geoid']: t['area_weight'] for t in targets}
        )

    def transform(
        self,
        df: pd.DataFrame,
        geoid_column: str = 'GEOID',
        value_columns: Optional[List[str]] = None,
        weight_method: WeightMethod = WeightMethod.AREA,
        aggregation_func: Union[str, Callable] = 'sum'
    ) -> pd.DataFrame:
        """
        Transform data from source boundaries to target boundaries.

        Args:
            df: DataFrame with data in source boundary vintage
            geoid_column: Name of the GEOID column
            value_columns: List of columns to transform. If None, all numeric columns.
            weight_method: How to weight data for splits/merges
            aggregation_func: How to aggregate merged data ('sum', 'mean', 'weighted_mean')

        Returns:
            DataFrame with data in target boundary vintage

        Raises:
            ValueError: If geoid_column not found in DataFrame
        """
        if geoid_column not in df.columns:
            raise ValueError(f"GEOID column '{geoid_column}' not found in DataFrame")

        # Identify value columns
        if value_columns is None:
            value_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            # Remove GEOID if it's numeric
            if geoid_column in value_columns:
                value_columns.remove(geoid_column)

        log.info(f"Transforming {len(df)} rows with {len(value_columns)} value columns")

        # Merge with crosswalk
        merged = df.merge(
            self.crosswalk_df[['source_geoid', 'target_geoid', 'area_weight']],
            left_on=geoid_column,
            right_on='source_geoid',
            how='left'
        )

        # Handle unmatched rows (keep original GEOID)
        unmatched = merged['target_geoid'].isna()
        if unmatched.any():
            log.warning(
                f"{unmatched.sum()} rows not found in crosswalk, keeping original GEOIDs"
            )
            merged.loc[unmatched, 'target_geoid'] = merged.loc[unmatched, geoid_column]
            merged.loc[unmatched, 'area_weight'] = 1.0

        # Get weight column based on method
        if weight_method == WeightMethod.EQUAL:
            merged['_weight'] = 1.0
        else:
            merged['_weight'] = merged['area_weight'].fillna(1.0)

        # Apply weights to value columns (for splits)
        for col in value_columns:
            if col in merged.columns:
                merged[f'_weighted_{col}'] = merged[col] * merged['_weight']

        # Aggregate by target GEOID
        agg_dict = {}
        for col in value_columns:
            weighted_col = f'_weighted_{col}'
            if weighted_col in merged.columns:
                if aggregation_func == 'sum':
                    agg_dict[col] = (weighted_col, 'sum')
                elif aggregation_func == 'mean':
                    agg_dict[col] = (weighted_col, 'mean')
                elif aggregation_func == 'weighted_mean':
                    # Will handle separately
                    agg_dict[col] = (weighted_col, 'sum')
                else:
                    agg_dict[col] = (weighted_col, aggregation_func)

        # Also aggregate weights for weighted_mean calculation
        agg_dict['_total_weight'] = ('_weight', 'sum')

        # Group and aggregate
        result = merged.groupby('target_geoid').agg(**agg_dict).reset_index()

        # Rename target_geoid back to original column name
        result = result.rename(columns={'target_geoid': geoid_column})

        # Calculate weighted mean if needed
        if aggregation_func == 'weighted_mean':
            for col in value_columns:
                if col in result.columns:
                    result[col] = result[col] / result['_total_weight']

        # Drop helper columns
        result = result.drop(columns=['_total_weight'], errors='ignore')

        log.info(f"Transformed to {len(result)} rows in target vintage")
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def apply_crosswalk(
    df: pd.DataFrame,
    source_year: int = 2010,
    target_year: int = 2020,
    geography_level: str = 'tract',
    state_fips: Optional[str] = None,
    geoid_column: str = 'GEOID',
    value_columns: Optional[List[str]] = None,
    weight_method: WeightMethod = WeightMethod.AREA,
    aggregation_func: Union[str, Callable] = 'sum'
) -> pd.DataFrame:
    """
    Apply a crosswalk to transform data from one boundary vintage to another.

    This is the main function for transforming data between Census years.
    It handles all relationship types (unchanged, splits, merges) automatically.

    Args:
        df: DataFrame with data in source boundary vintage
        source_year: Source Census year (e.g., 2010)
        target_year: Target Census year (e.g., 2020)
        geography_level: Geographic level ('tract', 'block_group', 'county')
        state_fips: Optional state FIPS to filter crosswalk
        geoid_column: Name of the GEOID column in df
        value_columns: List of columns to transform. If None, all numeric columns.
        weight_method: How to weight data for splits/merges
        aggregation_func: How to aggregate data ('sum', 'mean', 'weighted_mean')

    Returns:
        DataFrame with data transformed to target boundary vintage

    Example:
        # Transform 2010 income data to 2020 tracts
        df_2020 = apply_crosswalk(
            df=income_2010,
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            state_fips='06',  # California
            value_columns=['median_income', 'total_population']
        )
    """
    # Get crosswalk
    crosswalk_df = get_crosswalk(
        source_year=source_year,
        target_year=target_year,
        geography_level=geography_level,
        state_fips=state_fips
    )

    # Create processor
    processor = CrosswalkProcessor(
        crosswalk_df=crosswalk_df,
        source_year=source_year,
        target_year=target_year,
        geography_level=geography_level
    )

    # Transform
    return processor.transform(
        df=df,
        geoid_column=geoid_column,
        value_columns=value_columns,
        weight_method=weight_method,
        aggregation_func=aggregation_func
    )


def normalize_to_year(
    df: pd.DataFrame,
    data_year: int,
    target_year: int = 2020,
    geography_level: str = 'tract',
    state_fips: Optional[str] = None,
    geoid_column: str = 'GEOID',
    value_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Normalize data to a specific boundary year.

    Convenience function that determines the correct crosswalk direction
    and applies it to transform data to the target year's boundaries.

    Args:
        df: DataFrame with data
        data_year: Year of the data's boundaries
        target_year: Year to normalize to (default: 2020)
        geography_level: Geographic level
        state_fips: Optional state FIPS filter
        geoid_column: Name of GEOID column
        value_columns: Columns to transform

    Returns:
        DataFrame normalized to target year boundaries

    Example:
        # Normalize mixed-year data to 2020 boundaries
        df_normalized = normalize_to_year(
            df=old_data,
            data_year=2010,
            target_year=2020,
            geography_level='tract'
        )
    """
    if data_year == target_year:
        log.info(f"Data already in {target_year} boundaries, no transformation needed")
        return df.copy()

    return apply_crosswalk(
        df=df,
        source_year=data_year,
        target_year=target_year,
        geography_level=geography_level,
        state_fips=state_fips,
        geoid_column=geoid_column,
        value_columns=value_columns
    )


def identify_boundary_changes(
    source_year: int = 2010,
    target_year: int = 2020,
    geography_level: str = 'tract',
    state_fips: Optional[str] = None
) -> pd.DataFrame:
    """
    Identify and summarize boundary changes between Census years.

    Returns a DataFrame showing how each source geography changed,
    useful for understanding the extent of boundary changes in an area.

    Args:
        source_year: Source Census year
        target_year: Target Census year
        geography_level: Geographic level
        state_fips: Optional state FIPS filter

    Returns:
        DataFrame with columns:
        - source_geoid: GEOID in source year
        - relationship_type: Type of change (unchanged, split, merged)
        - num_targets: Number of target GEOIDs this maps to
        - target_geoids: List of target GEOIDs (as string)

    Example:
        # See which California tracts changed
        changes = identify_boundary_changes(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            state_fips='06'
        )

        # Filter to just splits
        splits = changes[changes['relationship_type'] == 'split']
    """
    crosswalk_df = get_crosswalk(
        source_year=source_year,
        target_year=target_year,
        geography_level=geography_level,
        state_fips=state_fips
    )

    processor = CrosswalkProcessor(
        crosswalk_df=crosswalk_df,
        source_year=source_year,
        target_year=target_year,
        geography_level=geography_level
    )

    # Get unique source GEOIDs
    source_geoids = crosswalk_df['source_geoid'].unique()

    results = []
    for source_geoid in source_geoids:
        change = processor.get_geography_change(source_geoid)
        results.append({
            'source_geoid': source_geoid,
            'relationship_type': change.relationship_type.value,
            'num_targets': change.num_targets,
            'target_geoids': ','.join(change.target_geoids)
        })

    return pd.DataFrame(results)


def get_split_tracts(
    source_year: int = 2010,
    target_year: int = 2020,
    state_fips: Optional[str] = None
) -> pd.DataFrame:
    """
    Get a list of tracts that were split between Census years.

    Args:
        source_year: Source Census year
        target_year: Target Census year
        state_fips: Optional state FIPS filter

    Returns:
        DataFrame with split tracts and their target tracts
    """
    changes = identify_boundary_changes(
        source_year=source_year,
        target_year=target_year,
        geography_level='tract',
        state_fips=state_fips
    )

    return changes[changes['relationship_type'] == 'split'].copy()


def get_merged_tracts(
    source_year: int = 2010,
    target_year: int = 2020,
    state_fips: Optional[str] = None
) -> pd.DataFrame:
    """
    Get a list of tracts that were merged between Census years.

    Args:
        source_year: Source Census year
        target_year: Target Census year
        state_fips: Optional state FIPS filter

    Returns:
        DataFrame with merged tracts and their resulting tract
    """
    changes = identify_boundary_changes(
        source_year=source_year,
        target_year=target_year,
        geography_level='tract',
        state_fips=state_fips
    )

    return changes[changes['relationship_type'] == 'merged'].copy()
