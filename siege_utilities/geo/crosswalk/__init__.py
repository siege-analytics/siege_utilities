"""
Census boundary crosswalk support for tracking geographic changes over time.

This module provides tools for working with Census boundary crosswalks,
which describe how geographic units (tracts, block groups, etc.) changed
between decennial census years (e.g., 2010 to 2020).

Key features:
- Download and cache crosswalk files from Census Bureau
- Apply crosswalks to transform data between boundary vintages
- Identify which geographies were split, merged, or unchanged

Example usage:
    from siege_utilities.geo.crosswalk import (
        get_crosswalk,
        apply_crosswalk,
        identify_boundary_changes,
        WeightMethod
    )

    # Get the crosswalk for California tracts
    crosswalk = get_crosswalk(
        source_year=2010,
        target_year=2020,
        geography_level='tract',
        state_fips='06'
    )

    # Transform 2010 data to 2020 boundaries
    df_2020 = apply_crosswalk(
        df=df_2010,
        source_year=2010,
        target_year=2020,
        geography_level='tract',
        weight_method=WeightMethod.AREA
    )

    # See which tracts changed
    changes = identify_boundary_changes(
        source_year=2010,
        target_year=2020,
        geography_level='tract',
        state_fips='06'
    )
"""

from .relationship_types import (
    # Enums
    RelationshipType,
    WeightMethod,
    # Data classes
    CrosswalkRelationship,
    CrosswalkMetadata,
    GeographyChange,
    # Constants
    SUPPORTED_CROSSWALK_YEARS,
    CROSSWALK_BASE_URL,
    CROSSWALK_FILE_PATTERNS,
)

from .crosswalk_client import (
    # Client class
    CrosswalkClient,
    # Convenience functions
    get_crosswalk,
    get_crosswalk_client,
    get_crosswalk_metadata,
    list_available_crosswalks,
    # Constants
    CROSSWALK_CACHE_TIMEOUT_DAYS,
)

from .crosswalk_processor import (
    # Processor class
    CrosswalkProcessor,
    # Main functions
    apply_crosswalk,
    normalize_to_year,
    # Analysis functions
    identify_boundary_changes,
    get_split_tracts,
    get_merged_tracts,
)

__all__ = [
    # Enums
    'RelationshipType',
    'WeightMethod',
    # Data classes
    'CrosswalkRelationship',
    'CrosswalkMetadata',
    'GeographyChange',
    # Client
    'CrosswalkClient',
    'get_crosswalk',
    'get_crosswalk_client',
    'get_crosswalk_metadata',
    'list_available_crosswalks',
    # Processor
    'CrosswalkProcessor',
    'apply_crosswalk',
    'normalize_to_year',
    # Analysis
    'identify_boundary_changes',
    'get_split_tracts',
    'get_merged_tracts',
    # Constants
    'SUPPORTED_CROSSWALK_YEARS',
    'CROSSWALK_BASE_URL',
    'CROSSWALK_FILE_PATTERNS',
    'CROSSWALK_CACHE_TIMEOUT_DAYS',
]
