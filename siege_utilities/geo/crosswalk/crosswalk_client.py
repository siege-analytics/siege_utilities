"""
Client for downloading and caching Census boundary crosswalk files.

This module provides functions to download crosswalk files from the Census Bureau
and cache them locally for efficient repeated access.

Census crosswalk files describe how geographic boundaries changed between
decennial census years. They are essential for:
- Comparing data across different Census years
- Tracking demographic changes in consistent geographies
- Normalizing historical data to current boundaries

Example usage:
    from siege_utilities.geo.crosswalk import get_crosswalk

    # Get 2010-2020 tract crosswalk for California
    crosswalk_df = get_crosswalk(
        source_year=2010,
        target_year=2020,
        geography_level='tract',
        state_fips='06'
    )

    # View relationships
    print(crosswalk_df.head())
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from io import StringIO

import pandas as pd
import requests

from .relationship_types import (
    RelationshipType,
    CrosswalkMetadata,
    CrosswalkRelationship,
    CROSSWALK_BASE_URL,
    CROSSWALK_FILE_PATTERNS,
    SUPPORTED_CROSSWALK_YEARS,
)

log = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Cache timeout (7 days - crosswalks rarely change)
CROSSWALK_CACHE_TIMEOUT_DAYS = 7
CROSSWALK_CACHE_TIMEOUT = timedelta(days=CROSSWALK_CACHE_TIMEOUT_DAYS)

# Request timeout
CROSSWALK_REQUEST_TIMEOUT = 120  # seconds - files can be large

# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / '.siege_utilities' / 'cache' / 'crosswalk'


# =============================================================================
# COLUMN MAPPINGS
# =============================================================================

# Census crosswalk file column mappings (pipe-delimited)
# These vary by geography level but follow general patterns

TRACT_COLUMNS_2010_2020 = {
    'GEOID_TRACT_20': 'target_geoid',
    'GEOID_TRACT_10': 'source_geoid',
    'NAMELSAD_TRACT_20': 'target_name',
    'NAMELSAD_TRACT_10': 'source_name',
    'AREALAND_TRACT_20': 'target_area',
    'AREALAND_TRACT_10': 'source_area',
    'AREALAND_PART': 'overlap_area',
    'AREAWATER_PART': 'overlap_water',
    'OID_TRACT_20': 'target_oid',
    'OID_TRACT_10': 'source_oid',
}

BLOCK_GROUP_COLUMNS_2010_2020 = {
    'GEOID_BLKGRP_20': 'target_geoid',
    'GEOID_BLKGRP_10': 'source_geoid',
    'AREALAND_BLKGRP_20': 'target_area',
    'AREALAND_BLKGRP_10': 'source_area',
    'AREALAND_PART': 'overlap_area',
}

COUNTY_COLUMNS_2010_2020 = {
    'GEOID_COUNTY_20': 'target_geoid',
    'GEOID_COUNTY_10': 'source_geoid',
    'NAMELSAD_COUNTY_20': 'target_name',
    'NAMELSAD_COUNTY_10': 'source_name',
    'AREALAND_COUNTY_20': 'target_area',
    'AREALAND_COUNTY_10': 'source_area',
    'AREALAND_PART': 'overlap_area',
}

COLUMN_MAPPINGS = {
    ('tract', 2010, 2020): TRACT_COLUMNS_2010_2020,
    ('block_group', 2010, 2020): BLOCK_GROUP_COLUMNS_2010_2020,
    ('county', 2010, 2020): COUNTY_COLUMNS_2010_2020,
}


# =============================================================================
# CROSSWALK CLIENT
# =============================================================================

class CrosswalkClient:
    """
    Client for downloading and managing Census crosswalk files.

    This client handles:
    - Downloading crosswalk files from Census Bureau
    - Caching files locally as parquet for fast access
    - Parsing pipe-delimited Census files
    - Filtering by state if needed

    Attributes:
        cache_dir: Directory for cached crosswalk files
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        timeout: int = CROSSWALK_REQUEST_TIMEOUT
    ):
        """
        Initialize the crosswalk client.

        Args:
            cache_dir: Directory for caching files (defaults to ~/.siege_utilities/cache/crosswalk)
            timeout: Request timeout in seconds
        """
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

        log.info(f"Initialized CrosswalkClient (cache: {self.cache_dir})")

    def get_crosswalk(
        self,
        source_year: int = 2010,
        target_year: int = 2020,
        geography_level: str = 'tract',
        state_fips: Optional[str] = None,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Get a crosswalk DataFrame for the specified years and geography.

        Args:
            source_year: Source Census year (e.g., 2010)
            target_year: Target Census year (e.g., 2020)
            geography_level: Geographic level ('tract', 'block_group', 'county')
            state_fips: Optional state FIPS code to filter results
            force_refresh: If True, re-download even if cached

        Returns:
            DataFrame with crosswalk relationships including:
            - source_geoid: GEOID in source year
            - target_geoid: GEOID in target year
            - area_weight: Proportion based on land area overlap
            - Additional metadata columns

        Raises:
            ValueError: If year combination is not supported
            requests.RequestException: If download fails
        """
        # Normalize geography level
        geo_level = geography_level.lower().replace(' ', '_').replace('-', '_')
        if geo_level == 'blockgroup':
            geo_level = 'block_group'

        # Validate year combination
        year_pair = (source_year, target_year)
        if year_pair not in SUPPORTED_CROSSWALK_YEARS:
            raise ValueError(
                f"Crosswalk not supported for {source_year}->{target_year}. "
                f"Supported: {list(SUPPORTED_CROSSWALK_YEARS.keys())}"
            )

        if geo_level not in SUPPORTED_CROSSWALK_YEARS[year_pair]:
            raise ValueError(
                f"Geography level '{geo_level}' not supported for {source_year}->{target_year}"
            )

        # Generate cache key
        cache_key = self._generate_cache_key(source_year, target_year, geo_level, state_fips)
        cache_file = self.cache_dir / f"{cache_key}.parquet"

        # Check cache
        if not force_refresh and self._is_cache_valid(cache_file):
            log.info(f"Loading crosswalk from cache: {cache_file.name}")
            return pd.read_parquet(cache_file)

        # Download and process
        log.info(f"Downloading {geo_level} crosswalk for {source_year}->{target_year}")
        df = self._download_crosswalk(source_year, target_year, geo_level)

        # Filter by state if specified
        if state_fips:
            state_fips = str(state_fips).zfill(2)
            df = self._filter_by_state(df, state_fips)

        # Calculate area weights
        df = self._calculate_weights(df)

        # Save to cache
        self._save_to_cache(df, cache_file)

        return df

    def get_crosswalk_metadata(
        self,
        source_year: int = 2010,
        target_year: int = 2020,
        geography_level: str = 'tract',
        state_fips: Optional[str] = None
    ) -> CrosswalkMetadata:
        """
        Get metadata about a crosswalk.

        Args:
            source_year: Source Census year
            target_year: Target Census year
            geography_level: Geographic level
            state_fips: Optional state FIPS filter

        Returns:
            CrosswalkMetadata with statistics about the crosswalk
        """
        df = self.get_crosswalk(source_year, target_year, geography_level, state_fips)

        # Count relationship types
        source_counts = df.groupby('source_geoid')['target_geoid'].count()
        target_counts = df.groupby('target_geoid')['source_geoid'].count()

        # One-to-one: source maps to exactly one target with ~100% area
        one_to_one = (source_counts == 1).sum()

        # Splits: one source maps to multiple targets
        splits = (source_counts > 1).sum()

        # Merges: multiple sources map to one target
        merges = (target_counts > 1).sum()

        return CrosswalkMetadata(
            source_year=source_year,
            target_year=target_year,
            geography_level=geography_level,
            state_fips=state_fips,
            total_source_units=len(source_counts),
            total_target_units=len(target_counts),
            one_to_one_count=int(one_to_one),
            split_count=int(splits),
            merged_count=int(merges),
        )

    def list_available_crosswalks(self) -> List[Dict]:
        """
        List all available crosswalk combinations.

        Returns:
            List of dictionaries describing available crosswalks
        """
        available = []
        for (source_year, target_year), geographies in SUPPORTED_CROSSWALK_YEARS.items():
            for geo_level, is_available in geographies.items():
                if is_available:
                    available.append({
                        'source_year': source_year,
                        'target_year': target_year,
                        'geography_level': geo_level,
                    })
        return available

    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear cached crosswalk files.

        Args:
            older_than_days: Only clear files older than this many days.
                            If None, clear all files.

        Returns:
            Number of files deleted
        """
        deleted = 0
        cutoff = None
        if older_than_days is not None:
            cutoff = datetime.now() - timedelta(days=older_than_days)

        for cache_file in self.cache_dir.glob('*.parquet'):
            if cutoff is not None:
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_mtime > cutoff:
                    continue

            try:
                cache_file.unlink()
                deleted += 1
            except Exception as e:
                log.warning(f"Failed to delete {cache_file}: {e}")

        log.info(f"Cleared {deleted} cached crosswalk files")
        return deleted

    # -------------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------------

    def _generate_cache_key(
        self,
        source_year: int,
        target_year: int,
        geography_level: str,
        state_fips: Optional[str]
    ) -> str:
        """Generate a cache key for the crosswalk."""
        parts = [str(source_year), str(target_year), geography_level]
        if state_fips:
            parts.append(state_fips)
        key_str = '_'.join(parts)
        return f"crosswalk_{key_str}"

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_file.exists():
            return False

        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - file_mtime

        if age > CROSSWALK_CACHE_TIMEOUT:
            log.debug(f"Cache expired: {cache_file.name} ({age.days} days old)")
            return False

        return True

    def _download_crosswalk(
        self,
        source_year: int,
        target_year: int,
        geography_level: str
    ) -> pd.DataFrame:
        """Download and parse a crosswalk file from Census Bureau."""
        # Get file pattern
        file_patterns = CROSSWALK_FILE_PATTERNS.get(geography_level, {})
        file_path = file_patterns.get((source_year, target_year))

        if file_path is None:
            raise ValueError(
                f"No crosswalk file available for {geography_level} "
                f"{source_year}->{target_year}"
            )

        # Construct URL
        url = f"{CROSSWALK_BASE_URL}/{file_path}"
        log.debug(f"Downloading crosswalk from: {url}")

        # Download
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        # Parse pipe-delimited file
        content = response.text

        # Read as DataFrame
        df = pd.read_csv(
            StringIO(content),
            sep='|',
            dtype=str,
            low_memory=False
        )

        # Rename columns to standard names
        column_mapping = COLUMN_MAPPINGS.get(
            (geography_level, source_year, target_year),
            {}
        )
        if column_mapping:
            # Only rename columns that exist
            rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=rename_map)

        log.info(f"Downloaded crosswalk with {len(df)} relationships")
        return df

    def _filter_by_state(
        self,
        df: pd.DataFrame,
        state_fips: str
    ) -> pd.DataFrame:
        """Filter crosswalk to a specific state."""
        # GEOIDs start with state FIPS
        mask = (
            df['source_geoid'].str.startswith(state_fips) |
            df['target_geoid'].str.startswith(state_fips)
        )
        filtered = df[mask].copy()
        log.info(f"Filtered to state {state_fips}: {len(filtered)} relationships")
        return filtered

    def _calculate_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate area-based weights for crosswalk relationships."""
        df = df.copy()

        # Convert area columns to numeric
        area_cols = ['source_area', 'target_area', 'overlap_area']
        for col in area_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calculate area weight: overlap_area / source_area
        if 'overlap_area' in df.columns and 'source_area' in df.columns:
            df['area_weight'] = df['overlap_area'] / df['source_area'].replace(0, float('nan'))
            df['area_weight'] = df['area_weight'].fillna(0).clip(0, 1)
        else:
            # Default weight of 1.0 if areas not available
            df['area_weight'] = 1.0

        return df

    def _save_to_cache(self, df: pd.DataFrame, cache_file: Path) -> None:
        """Save DataFrame to cache as parquet."""
        try:
            df.to_parquet(cache_file, index=False)
            log.debug(f"Cached crosswalk to: {cache_file}")
        except Exception as e:
            log.warning(f"Failed to cache crosswalk: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Module-level client instance
_default_client: Optional[CrosswalkClient] = None


def get_crosswalk_client() -> CrosswalkClient:
    """Get or create the default crosswalk client."""
    global _default_client
    if _default_client is None:
        _default_client = CrosswalkClient()
    return _default_client


def get_crosswalk(
    source_year: int = 2010,
    target_year: int = 2020,
    geography_level: str = 'tract',
    state_fips: Optional[str] = None,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Convenience function to get a crosswalk DataFrame.

    Args:
        source_year: Source Census year (e.g., 2010)
        target_year: Target Census year (e.g., 2020)
        geography_level: Geographic level ('tract', 'block_group', 'county')
        state_fips: Optional state FIPS code to filter results
        force_refresh: If True, re-download even if cached

    Returns:
        DataFrame with crosswalk relationships

    Example:
        # Get California tract crosswalk
        df = get_crosswalk(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            state_fips='06'
        )
    """
    client = get_crosswalk_client()
    return client.get_crosswalk(
        source_year=source_year,
        target_year=target_year,
        geography_level=geography_level,
        state_fips=state_fips,
        force_refresh=force_refresh
    )


def get_crosswalk_metadata(
    source_year: int = 2010,
    target_year: int = 2020,
    geography_level: str = 'tract',
    state_fips: Optional[str] = None
) -> CrosswalkMetadata:
    """
    Convenience function to get crosswalk metadata.

    Args:
        source_year: Source Census year
        target_year: Target Census year
        geography_level: Geographic level
        state_fips: Optional state FIPS filter

    Returns:
        CrosswalkMetadata with statistics
    """
    client = get_crosswalk_client()
    return client.get_crosswalk_metadata(
        source_year=source_year,
        target_year=target_year,
        geography_level=geography_level,
        state_fips=state_fips
    )


def list_available_crosswalks() -> List[Dict]:
    """
    List all available crosswalk combinations.

    Returns:
        List of dictionaries describing available crosswalks
    """
    client = get_crosswalk_client()
    return client.list_available_crosswalks()
