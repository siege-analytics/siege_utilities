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
from typing import Callable, List, Optional, Union

import pandas as pd
import numpy as np

from .relationship_types import (
    RelationshipType,
    WeightMethod,
    GeographyChange,
)
from .crosswalk_client import get_crosswalk

__all__ = [
    'CrosswalkProcessor',
    'apply_crosswalk',
    'normalize_to_year',
    'identify_boundary_changes',
    'get_split_tracts',
    'get_merged_tracts',
]

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
        aggregation_func: Union[str, Callable] = 'sum',
        intensive_variables: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Transform data from source boundaries to target boundaries.

        Args:
            df: DataFrame with data in source boundary vintage
            geoid_column: Name of the GEOID column
            value_columns: List of columns to transform. If None, all numeric columns.
            weight_method: How to weight data for splits/merges
            aggregation_func: How to aggregate merged data ('sum', 'mean', 'weighted_mean')
            intensive_variables: Columns that are intensive (rates, ratios,
                medians, densities, per-capita values). These are area-weighted
                averaged rather than disaggregated by weight, so a split
                preserves the value instead of scaling it down. Columns not
                listed here are treated as extensive (disaggregated).

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

        intensive_set = set(intensive_variables or [])

        # All internal columns use a reserved prefix so they can never collide
        # with user input columns. A caller's data may legitimately contain a
        # column named 'overlap_area', 'source_area', or even '_inum_rate' /
        # '_iden_rate'; merging crosswalk metadata or creating helper columns
        # under those bare names silently drops the user's columns (or raises a
        # merge-suffix KeyError). Routing every internal name through this
        # prefix isolates crosswalk metadata and computation helpers.
        R = '__xwalk__'
        c_src, c_tgt, c_aw = f'{R}source_geoid', f'{R}target_geoid', f'{R}area_weight'
        c_ov, c_sa = f'{R}overlap_area', f'{R}source_area'
        c_weight, c_total_weight = f'{R}weight', f'{R}total_weight'

        # Pull the crosswalk columns under reserved names. For intensive columns
        # we also pull whichever absolute-area columns exist so the actual
        # OVERLAP (intersection) area can be reconstructed -- ``area_weight``
        # alone (an overlap/source allocation factor) cannot express an
        # area-weighted mean on a merge (sources of area 1 and 9 can both have
        # area_weight 1). ``overlap_area`` is the intersection area directly;
        # ``source_area * area_weight`` reconstructs it when overlap_area is
        # absent or has gaps (findings: intensive overlap weighting).
        rename_map = {
            'source_geoid': c_src,
            'target_geoid': c_tgt,
            'area_weight': c_aw,
        }
        sel = ['source_geoid', 'target_geoid', 'area_weight']
        has_overlap = 'overlap_area' in self.crosswalk_df.columns
        has_source_area = 'source_area' in self.crosswalk_df.columns
        if intensive_set:
            if has_overlap:
                sel.append('overlap_area')
                rename_map['overlap_area'] = c_ov
            if has_source_area:
                sel.append('source_area')
                rename_map['source_area'] = c_sa

        xwalk = self.crosswalk_df[sel].rename(columns=rename_map)
        merged = df.merge(
            xwalk,
            left_on=geoid_column,
            right_on=c_src,
            how='left',
        )

        # Handle unmatched rows (keep original GEOID).
        unmatched = merged[c_tgt].isna()
        if unmatched.any():
            log.warning(
                f"{unmatched.sum()} rows not found in crosswalk, keeping original GEOIDs"
            )
            merged.loc[unmatched, c_tgt] = merged.loc[unmatched, geoid_column]
            merged.loc[unmatched, c_src] = merged.loc[unmatched, geoid_column]
            merged.loc[unmatched, c_aw] = 1.0

        # Get weight column based on method
        if weight_method == WeightMethod.EQUAL:
            merged[c_weight] = 1.0
        else:
            merged[c_weight] = merged[c_aw].fillna(1.0)

        # Split the value columns into extensive (disaggregated by weight) and
        # intensive (area-weighted averaged). They need fundamentally different
        # math, so handle them on separate paths rather than dividing an
        # already-aggregated extensive result.
        extensive_cols = [
            c for c in value_columns if c in merged.columns and c not in intensive_set
        ]
        intensive_cols = [
            c for c in value_columns if c in merged.columns and c in intensive_set
        ]

        # Apply weights to extensive value columns (for splits/merges).
        for col in extensive_cols:
            merged[f'{R}weighted_{col}'] = merged[col] * merged[c_weight]

        # Build the area-weighted numerator/denominator for intensive columns.
        # The area-weighted mean is Sum(value_i * overlap_i) / Sum(overlap_i),
        # computed only over rows with a non-null VALUE so a missing value does
        # not dilute the rate (e.g. [.2, NaN] -> .2, not .1). This matches the
        # areal/tobler intensive formula exactly (see geo.interpolation.areal).
        if intensive_cols:
            overlap_area = self._reconstruct_overlap_area(
                merged, c_ov, c_sa, c_aw, has_overlap, has_source_area,
            )

            # Refusal policy triggers on a true merge -- 2+ DISTINCT source
            # geographies feeding one target -- not on row count. A single
            # source with duplicate rows, or a split, is unambiguous and must
            # never refuse. Count distinct sources per target.
            distinct_src = merged.groupby(c_tgt)[c_src].nunique(dropna=False)
            merge_targets = set(distinct_src.index[distinct_src > 1])
            is_merge = merged[c_tgt].isin(merge_targets)

            if overlap_area is None:
                # No absolute-area column available. A merge of 2+ distinct
                # sources CANNOT be area-weighted from the allocation factor,
                # so refuse rather than return a wrong number. A split / 1:1 /
                # single-source (even with duplicate rows) preserves the
                # intensive value regardless of weight, so proceed with unit
                # weights.
                if is_merge.any():
                    raise ValueError(
                        "Cannot area-weight intensive columns "
                        f"{sorted(intensive_set)} on a merge: the crosswalk "
                        "carries only the allocation factor 'area_weight', "
                        "which cannot express an area-weighted mean (sources "
                        "of area 1 and 9 both get weight 1). Supply a crosswalk "
                        "with an 'overlap_area' or 'source_area' column, or "
                        "route intensive columns through areal interpolation "
                        "(LongitudinalAligner falls back to tobler "
                        "automatically on a crosswalk failure)."
                    )
                areal_w = pd.Series(1.0, index=merged.index)
            else:
                areal_w = overlap_area.astype(float)
                # An unmatched row is a lone self-mapped source; weight 1.0
                # preserves its intensive value.
                areal_w = areal_w.where(~unmatched, 1.0)
                # Do NOT coerce a missing/invalid overlap area to a zero
                # contribution -- that silently drops a source and bypasses the
                # refusal policy. If a matched merge row still has an invalid
                # area after reconstruction (no overlap_area and no recoverable
                # source_area*area_weight), reject with a clear error.
                bad_area = areal_w.isna() | (areal_w < 0)
                if (bad_area & is_merge & ~unmatched).any():
                    raise ValueError(
                        "Cannot area-weight intensive columns "
                        f"{sorted(intensive_set)} on a merge: missing or invalid "
                        "overlap area for one or more sources and no recoverable "
                        "'source_area' x 'area_weight' fallback. Supply a valid "
                        "'overlap_area' (or 'source_area') for every merging "
                        "source, or route intensive columns through areal "
                        "interpolation."
                    )
                # A single source feeding a target preserves its intensive value
                # regardless of area (there is nothing to weight it against), so
                # a non-merge row with an invalid area gets unit weight rather
                # than producing a silent NaN.
                areal_w = areal_w.where(~(bad_area & ~is_merge), 1.0)

            for col in intensive_cols:
                vals = pd.to_numeric(merged[col], errors='coerce')
                valid = vals.notna()
                merged[f'{R}inum_{col}'] = np.where(valid, vals.fillna(0.0) * areal_w, 0.0)
                merged[f'{R}iden_{col}'] = np.where(valid, areal_w, 0.0)

        # Aggregate by target GEOID.
        agg_dict = {}
        for col in extensive_cols:
            weighted_col = f'{R}weighted_{col}'
            if aggregation_func == 'sum':
                agg_dict[col] = (weighted_col, 'sum')
            elif aggregation_func == 'mean':
                agg_dict[col] = (weighted_col, 'mean')
            elif aggregation_func == 'weighted_mean':
                # Will be divided by total weight below.
                agg_dict[col] = (weighted_col, 'sum')
            else:
                agg_dict[col] = (weighted_col, aggregation_func)
        for col in intensive_cols:
            agg_dict[f'{R}inum_{col}'] = (f'{R}inum_{col}', 'sum')
            agg_dict[f'{R}iden_{col}'] = (f'{R}iden_{col}', 'sum')

        # Also aggregate weights for weighted_mean calculation.
        agg_dict[c_total_weight] = (c_weight, 'sum')

        # Group and aggregate
        result = merged.groupby(c_tgt).agg(**agg_dict).reset_index()

        # Rename target_geoid back to original column name
        result = result.rename(columns={c_tgt: geoid_column})

        # Extensive weighted_mean normalization (intensive columns are never
        # touched here -- they are computed from their own numerator/denominator
        # below, so 'mean'/'weighted_mean' cannot double-divide a rate).
        if aggregation_func == 'weighted_mean':
            for col in extensive_cols:
                if col in result.columns:
                    result[col] = result[col] / result[c_total_weight]

        # Intensive area-weighted mean: numerator / denominator.
        drop_cols = [c_total_weight]
        for col in intensive_cols:
            inum, iden = f'{R}inum_{col}', f'{R}iden_{col}'
            if inum in result.columns and iden in result.columns:
                with np.errstate(invalid='ignore', divide='ignore'):
                    result[col] = result[inum] / result[iden].replace(0, np.nan)
                drop_cols += [inum, iden]

        # Drop helper columns
        result = result.drop(columns=drop_cols, errors='ignore')

        log.info(f"Transformed to {len(result)} rows in target vintage")
        return result

    @staticmethod
    def _reconstruct_overlap_area(
        merged: pd.DataFrame,
        c_ov: str,
        c_sa: str,
        c_aw: str,
        has_overlap: bool,
        has_source_area: bool,
    ) -> Optional[pd.Series]:
        """Reconstruct the per-row overlap (intersection) area for intensive
        area-weighting.

        The area-weighted mean weights each source by its ACTUAL overlap with
        the target. Precedence:

        1. ``overlap_area`` (the intersection area) is used directly.
        2. Where ``overlap_area`` is missing -- or absent entirely -- fall back
           to ``source_area * area_weight``: ``area_weight`` is the
           overlap/source allocation fraction, so the product reconstructs the
           intersection area. This is what makes a partial overlap (area_weight
           < 1) weight correctly instead of using the whole source area.

        Returns a float Series of overlap areas, or ``None`` when neither an
        overlap area nor a reconstructible source_area x area_weight is
        available (the caller then applies the distinct-source refusal policy).
        """
        aw = pd.to_numeric(merged[c_aw], errors='coerce') if c_aw in merged.columns else None
        sa = (
            pd.to_numeric(merged[c_sa], errors='coerce')
            if (has_source_area and c_sa in merged.columns)
            else None
        )
        fallback = (sa * aw) if (sa is not None and aw is not None) else None

        if has_overlap and c_ov in merged.columns:
            ov = pd.to_numeric(merged[c_ov], errors='coerce')
            if fallback is not None:
                # Fill only the gaps in overlap_area from the reconstruction;
                # a present overlap_area always wins.
                ov = ov.where(ov.notna(), fallback)
            return ov

        if fallback is not None:
            return fallback

        return None


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
    aggregation_func: Union[str, Callable] = 'sum',
    intensive_variables: Optional[List[str]] = None,
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
        aggregation_func=aggregation_func,
        intensive_variables=intensive_variables,
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
