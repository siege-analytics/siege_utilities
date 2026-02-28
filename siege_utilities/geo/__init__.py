"""
Geographic utilities for spatial data analysis, Census data access, and mapping.

This package provides comprehensive tools for working with geographic data,
including enhanced Census utilities, intelligent data selection, spatial analysis,
boundary crosswalks, and time-series analysis.
"""

from .spatial_data import (
    CensusDirectoryDiscovery,
    CensusDataSource,
    SpatialDataSource,
    GovernmentDataSource,
    OpenStreetMapDataSource,
    # Reference data
    BOUNDARY_TYPE_CATALOG,
    # Convenience functions
    get_census_boundaries,
    download_data,
    normalize_state_identifier,
    get_state_by_abbreviation,
    get_state_by_name,
    discover_boundary_types,
)

from .census_dataset_mapper import (
    CensusDatasetMapper,
    SurveyType,
    GeographyLevel,
    DataReliability,
    CensusDataset,
    DatasetRelationship,
    get_census_dataset_mapper,
    get_best_dataset_for_analysis,
    compare_census_datasets
)

from .census_data_selector import (
    CensusDataSelector,
    get_census_data_selector,
    select_census_datasets,
    select_datasets_for_analysis,
    get_dataset_compatibility_matrix,
    get_analysis_approach,
    suggest_analysis_approach
)

from .spatial_transformations import (
    SpatialDataTransformer,
    DUCKDB_AVAILABLE
)

from .geocoding import (
    concatenate_addresses,
    use_nominatim_geocoder,
    NominatimGeoClassifier
)

from .census_api_client import (
    CensusAPIClient,
    CensusAPIError,
    CensusAPIKeyError,
    CensusRateLimitError,
    CensusVariableError,
    CensusGeographyError,
    VARIABLE_GROUPS,
    VARIABLE_DESCRIPTIONS,
    get_demographics,
    get_population,
    get_income_data,
    get_education_data,
    get_housing_data,
    get_census_api_client,
    get_census_data_with_geometry,
    join_demographics_to_shapes,
)

from .geoid_utils import (
    GEOID_LENGTHS,
    GEOID_COMPONENT_LENGTHS,
    normalize_geoid,
    normalize_geoid_column,
    construct_geoid,
    construct_geoid_from_row,
    parse_geoid,
    extract_parent_geoid,
    validate_geoid,
    can_normalize_geoid,
    validate_geoid_column,
    prepare_geoid_for_join,
    find_geoid_column,
)

# Canonical geographic level resolution
from siege_utilities.config.census_constants import (
    CANONICAL_GEOGRAPHIC_LEVELS,
    resolve_geographic_level,
)

# Crosswalk support for boundary changes between Census years
from .crosswalk import (
    # Enums
    RelationshipType,
    WeightMethod,
    # Data classes
    CrosswalkRelationship,
    CrosswalkMetadata,
    GeographyChange,
    # Client
    CrosswalkClient,
    get_crosswalk,
    get_crosswalk_client,
    get_crosswalk_metadata,
    list_available_crosswalks,
    # Processor
    CrosswalkProcessor,
    apply_crosswalk,
    normalize_to_year,
    # Analysis
    identify_boundary_changes,
    get_split_tracts,
    get_merged_tracts,
    # Constants
    SUPPORTED_CROSSWALK_YEARS,
)

# Time-series analysis for longitudinal data
from .timeseries import (
    # Crosswalk analytics
    BoundaryStabilityMetrics,
    AllocationEfficiencyMetrics,
    ChainLink,
    ReallocationChain,
    compute_boundary_stability,
    compute_allocation_efficiency,
    build_reallocation_chain,
    compare_vintage_stability,
    identify_volatile_boundaries,
    # Longitudinal data
    get_longitudinal_data,
    get_available_years,
    validate_longitudinal_years,
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

# NCES locale classification
from .locale import (
    LocaleCode,
    LocaleType,
    NCESLocaleClassifier,
    ALL_LOCALE_CODES,
    locale_from_code,
    CITY_LARGE, CITY_MIDSIZE, CITY_SMALL,
    SUBURB_LARGE, SUBURB_MIDSIZE, SUBURB_SMALL,
    TOWN_FRINGE, TOWN_DISTANT, TOWN_REMOTE,
    RURAL_FRINGE, RURAL_DISTANT, RURAL_REMOTE,
)

# NCES data download
from .nces_download import (
    NCESDownloader,
    NCESDownloadError,
)

# Databricks spatial fallback planning
from .databricks_fallback import (
    SpatialLoaderPlan,
    select_spatial_loader,
    build_census_table_name,
    build_census_ingest_targets,
)

# PL 94-171 redistricting file downloads
from .census_files import (
    PLFileDownloader,
    get_pl_data,
    get_pl_blocks,
    get_pl_tracts,
    download_pl_file,
    list_available_pl_files,
    PL_FILE_TYPES,
    PL_TABLES,
)

# Areal interpolation for boundary data transfer
from .interpolation import (
    ArealInterpolationResult,
    interpolate_areal,
    interpolate_extensive,
    interpolate_intensive,
    compute_area_weights,
)

# Choropleth map creation
from .choropleth import (
    create_choropleth,
    create_choropleth_comparison,
    create_classified_comparison,
    create_bivariate_choropleth,
    create_bivariate_crosstab,
    create_bivariate_companion_maps,
    verify_bivariate_classification,
    create_bivariate_analysis,
    BivariateAnalysisResult,
    save_map,
    BIVARIATE_COLOR_SCHEMES,
)

__all__ = [
    # Core spatial data classes
    'CensusDirectoryDiscovery',
    'CensusDataSource',
    'SpatialDataSource',
    'GovernmentDataSource',
    'OpenStreetMapDataSource',
    # Convenience functions for Census boundaries
    'get_census_boundaries',
    'download_data',
    'normalize_state_identifier',
    'get_state_by_abbreviation',
    'get_state_by_name',
    'discover_boundary_types',
    
    # Census dataset mapping and intelligence
    'CensusDatasetMapper',
    'SurveyType',
    'GeographyLevel', 
    'DataReliability',
    'CensusDataset',
    'DatasetRelationship',
    'get_census_dataset_mapper',
    'get_best_dataset_for_analysis',
    'compare_census_datasets',
    
    # Intelligent data selection
    'CensusDataSelector',
    'get_census_data_selector',
    'select_census_datasets',
    'select_datasets_for_analysis',
    'get_dataset_compatibility_matrix',
    'get_analysis_approach',
    'suggest_analysis_approach',
    
    # Spatial transformations
    'SpatialDataTransformer',
    'DUCKDB_AVAILABLE',
    
    # Geocoding
    'concatenate_addresses',
    'use_nominatim_geocoder',
    'NominatimGeoClassifier',

    # Census API client for demographic data
    'CensusAPIClient',
    'CensusAPIError',
    'CensusAPIKeyError',
    'CensusRateLimitError',
    'CensusVariableError',
    'CensusGeographyError',
    'VARIABLE_GROUPS',
    'VARIABLE_DESCRIPTIONS',
    'get_demographics',
    'get_population',
    'get_income_data',
    'get_education_data',
    'get_housing_data',
    'get_census_api_client',
    'get_census_data_with_geometry',
    'join_demographics_to_shapes',

    # Geographic level resolution
    'CANONICAL_GEOGRAPHIC_LEVELS',
    'resolve_geographic_level',

    # GEOID utilities
    'GEOID_LENGTHS',
    'GEOID_COMPONENT_LENGTHS',
    'normalize_geoid',
    'normalize_geoid_column',
    'construct_geoid',
    'construct_geoid_from_row',
    'parse_geoid',
    'extract_parent_geoid',
    'validate_geoid',
    'can_normalize_geoid',
    'validate_geoid_column',
    'prepare_geoid_for_join',
    'find_geoid_column',

    # Crosswalk support
    'RelationshipType',
    'WeightMethod',
    'CrosswalkRelationship',
    'CrosswalkMetadata',
    'GeographyChange',
    'CrosswalkClient',
    'get_crosswalk',
    'get_crosswalk_client',
    'get_crosswalk_metadata',
    'list_available_crosswalks',
    'CrosswalkProcessor',
    'apply_crosswalk',
    'normalize_to_year',
    'identify_boundary_changes',
    'get_split_tracts',
    'get_merged_tracts',
    'SUPPORTED_CROSSWALK_YEARS',

    # Crosswalk analytics
    'BoundaryStabilityMetrics',
    'AllocationEfficiencyMetrics',
    'ChainLink',
    'ReallocationChain',
    'compute_boundary_stability',
    'compute_allocation_efficiency',
    'build_reallocation_chain',
    'compare_vintage_stability',
    'identify_volatile_boundaries',
    # Time-series analysis
    'get_longitudinal_data',
    'get_available_years',
    'validate_longitudinal_years',
    'calculate_change_metrics',
    'calculate_multi_period_changes',
    'calculate_index',
    'get_change_summary',
    'TrendCategory',
    'TrendThresholds',
    'classify_trends',
    'classify_by_zscore',
    'classify_by_quantiles',
    'get_trend_summary',
    'identify_outliers',
    'compare_trends',
    'THRESHOLD_PRESETS',

    # Choropleth mapping
    'create_choropleth',
    'create_choropleth_comparison',
    'create_classified_comparison',
    'create_bivariate_choropleth',
    'create_bivariate_crosstab',
    'create_bivariate_companion_maps',
    'verify_bivariate_classification',
    'create_bivariate_analysis',
    'BivariateAnalysisResult',
    'save_map',
    'BIVARIATE_COLOR_SCHEMES',

    # Areal interpolation
    'ArealInterpolationResult',
    'interpolate_areal',
    'interpolate_extensive',
    'interpolate_intensive',
    'compute_area_weights',

    # NCES locale classification
    'LocaleCode',
    'LocaleType',
    'NCESLocaleClassifier',
    'ALL_LOCALE_CODES',
    'locale_from_code',
    'CITY_LARGE', 'CITY_MIDSIZE', 'CITY_SMALL',
    'SUBURB_LARGE', 'SUBURB_MIDSIZE', 'SUBURB_SMALL',
    'TOWN_FRINGE', 'TOWN_DISTANT', 'TOWN_REMOTE',
    'RURAL_FRINGE', 'RURAL_DISTANT', 'RURAL_REMOTE',

    # NCES data download
    'NCESDownloader',
    'NCESDownloadError',

    # Databricks spatial fallback
    'SpatialLoaderPlan',
    'select_spatial_loader',
    'build_census_table_name',
    'build_census_ingest_targets',

    # PL 94-171 redistricting files
    'PLFileDownloader',
    'get_pl_data',
    'get_pl_blocks',
    'get_pl_tracts',
    'download_pl_file',
    'list_available_pl_files',
    'PL_FILE_TYPES',
    'PL_TABLES',
]

# Package metadata
__version__ = "3.0.0"
__author__ = "Siege Analytics"
__description__ = "Enhanced geographic utilities with intelligent Census data selection"

# Convenience function for quick access to Census intelligence
def get_census_intelligence():
    """
    Get a comprehensive Census intelligence system.
    
    Returns:
        tuple: (CensusDatasetMapper, CensusDataSelector) for full Census data intelligence
    """
    from .census_dataset_mapper import get_census_dataset_mapper
    from .census_data_selector import get_census_data_selector
    
    return get_census_dataset_mapper(), get_census_data_selector()

# Quick access to common Census data selection
def quick_census_selection(analysis_type: str, geography_level: str):
    """
    Quick access to Census data selection recommendations.
    
    Args:
        analysis_type: Type of analysis (e.g., "demographics", "housing", "business")
        geography_level: Required geography level (e.g., "tract", "county", "state")
    
    Returns:
        dict: Dataset recommendations and analysis approach
    """
    from .census_data_selector import select_census_datasets, get_analysis_approach
    
    recommendations = select_census_datasets(analysis_type, geography_level)
    approach = get_analysis_approach(analysis_type, geography_level)
    
    return {
        "recommendations": recommendations,
        "analysis_approach": approach
    }