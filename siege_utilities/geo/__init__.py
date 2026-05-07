"""
Geographic utilities for spatial data analysis, Census data access, and mapping.

All submodules load on first attribute access via PEP 562 __getattr__.
Pure-Python modules (census_constants, geoid_utils) are importable without geopandas.
"""

import importlib
import sys

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- capabilities (runtime tier detection) ---
_register(['geo_capabilities'], '.capabilities')

# --- crs (configurable default CRS) ---
_register([
    'get_default_crs', 'set_default_crs', 'reproject_if_needed',
], '.crs')

# --- boundary_result (structured diagnostics) ---
_register([
    'BoundaryFetchResult',
    'BoundaryRetrievalError', 'BoundaryInputError', 'BoundaryDiscoveryError',
    'BoundaryConfigurationError',
    'BoundaryUrlValidationError', 'BoundaryDownloadError', 'BoundaryParseError',
], '.boundary_result')

# --- boundary_providers (pluggable boundary data sources) ---
# Moved to geo/providers/ under ELE-2438; the submodule path here points
# at the new location directly (the old geo/boundary_providers.py remains
# as a deprecation shim).
_register([
    'BoundaryProvider', 'CensusTIGERProvider', 'GADMProvider',
    'RDHProvider', 'BoundaryFetchError',
    'resolve_boundary_provider',
], '.providers.boundary_providers')

# --- spatial_data ---
_register([
    'CensusDirectoryDiscovery', 'CensusDataSource', 'SpatialDataSource',
    'GovernmentDataSource', 'OpenStreetMapDataSource',
    'BOUNDARY_TYPE_CATALOG',
    'get_census_boundaries', 'download_data', 'normalize_state_identifier',
    'get_state_by_abbreviation', 'get_state_by_name', 'discover_boundary_types',
    'get_census_data', 'download_osm_data',
    'get_available_years', 'get_year_directory_contents',
    'construct_download_url', 'validate_download_url', 'get_optimal_year',
    'get_geographic_boundaries', 'fetch_geographic_boundaries',
    'get_available_boundary_types',
    'refresh_discovery_cache', 'get_available_state_fips', 'get_state_abbreviations',
    'get_comprehensive_state_info', 'validate_state_fips',
    'get_state_name', 'get_state_abbreviation', 'download_dataset',
    'get_unified_fips_data', 'normalize_state_identifier_standalone',
    'normalize_state_input', 'normalize_state_name', 'normalize_state_abbreviation',
    'normalize_fips_code',
], '.spatial_data')

# --- census_dataset_mapper ---
_register([
    'CensusDatasetMapper', 'SurveyType', 'GeographyLevel', 'DataReliability',
    'CensusDataset', 'DatasetRelationship',
    'get_census_dataset_mapper', 'get_best_dataset_for_analysis', 'compare_census_datasets',
    'get_dataset_info', 'list_datasets_by_type', 'list_datasets_by_geography',
    'get_best_dataset_for_use_case', 'get_dataset_relationships', 'compare_datasets',
    'get_data_selection_guide', 'export_dataset_catalog',
], '.census_dataset_mapper')

# --- census_data_selector ---
_register([
    'CensusDataSelector', 'get_census_data_selector', 'select_census_datasets',
    'select_datasets_for_analysis', 'get_dataset_compatibility_matrix',
    'get_analysis_approach', 'suggest_analysis_approach',
], '.census_data_selector')

# --- spatial_transformations ---
_register(['SpatialDataTransformer', 'DUCKDB_AVAILABLE'], '.spatial_transformations')

# --- geocoding ---
_register([
    'concatenate_addresses', 'use_nominatim_geocoder', 'NominatimGeoClassifier',
    'get_country_name', 'get_country_code', 'list_countries', 'get_coordinates',
    'NOMINATIM_INTERNAL_URL',
    'validate_geocode_data_pandas', 'mark_valid_geocode_data_pandas',
], '.geocoding')

# --- isochrones ---
_register([
    'DEFAULT_ORS_BASE_URL', 'DEFAULT_VALHALLA_BASE_URL',
    'ISOCHRONE_DEFAULT_RETRIES',
    'IsochroneError', 'IsochroneNetworkError', 'IsochroneProviderError',
    'IsochroneRequest',
    'IsochroneProvider', 'OpenRouteServiceProvider', 'ValhallaProvider',
    'build_isochrone_request', 'get_isochrone', 'isochrone_to_geodataframe',
    'get_provider',
], '.isochrones')

# --- census_geocoder (moved to geo/providers/ under ELE-2438) ---
_register([
    'CensusGeocodeError',
    'CensusVintage', 'CensusGeocodeResult',
    'select_vintage_for_cycle', 'geocode_single', 'geocode_batch',
    'geocode_batch_chunked',
], '.providers.census_geocoder')

# --- census_api_client ---
_register([
    'CensusAPIClient', 'CensusAPIError', 'CensusAPIKeyError',
    'CensusRateLimitError', 'CensusVariableError', 'CensusGeographyError',
    'VARIABLE_GROUPS', 'VARIABLE_DESCRIPTIONS',
    'get_demographics', 'get_population', 'get_income_data',
    'get_education_data', 'get_housing_data', 'get_census_api_client',
    'get_census_data_with_geometry', 'join_demographics_to_shapes',
], '.census_api_client')

# --- geoid_utils (pure Python, no geopandas needed) ---
_register([
    'GEOID_LENGTHS', 'GEOID_COMPONENT_LENGTHS',
    'normalize_geoid', 'normalize_geoid_column', 'construct_geoid',
    'construct_geoid_from_row', 'parse_geoid', 'extract_parent_geoid',
    'validate_geoid', 'can_normalize_geoid', 'validate_geoid_column',
    'prepare_geoid_for_join', 'find_geoid_column',
    'geoid_to_slug', 'slug_to_geoid',
], '.geoid_utils')

# --- validators (GEOID validation for Django and standalone) ---
_register([
    'is_valid_state_fips', 'is_valid_county_fips',
    'is_valid_tract_geoid', 'is_valid_block_group_geoid',
], '.validators')

# --- census_constants (pure Python, via config module) ---
_register([
    'CANONICAL_GEOGRAPHIC_LEVELS', 'resolve_geographic_level',
], 'siege_utilities.config.census_constants')

# --- crosswalk ---
_register([
    'RelationshipType', 'WeightMethod',
    'CrosswalkRelationship', 'CrosswalkMetadata', 'GeographyChange',
    'CrosswalkClient', 'get_crosswalk', 'get_crosswalk_client',
    'get_crosswalk_metadata', 'list_available_crosswalks',
    'CrosswalkProcessor', 'apply_crosswalk', 'normalize_to_year',
    'identify_boundary_changes', 'get_split_tracts', 'get_merged_tracts',
    'SUPPORTED_CROSSWALK_YEARS',
], '.crosswalk')

# --- timeseries ---
_register([
    'BoundaryStabilityMetrics', 'AllocationEfficiencyMetrics',
    'ChainLink', 'ReallocationChain',
    'compute_boundary_stability', 'compute_allocation_efficiency',
    'build_reallocation_chain', 'compare_vintage_stability',
    'identify_volatile_boundaries',
    'get_longitudinal_data', 'get_available_survey_years', 'validate_longitudinal_years',
    'calculate_change_metrics', 'calculate_multi_period_changes',
    'calculate_index', 'get_change_summary',
    'TrendCategory', 'TrendThresholds',
    'classify_trends', 'classify_by_zscore', 'classify_by_quantiles',
    'get_trend_summary', 'identify_outliers', 'compare_trends',
    'THRESHOLD_PRESETS',
], '.timeseries')

# --- locale (NCES classification) ---
_register([
    'LocaleCode', 'LocaleType', 'NCESLocaleClassifier',
    'ALL_LOCALE_CODES', 'locale_from_code',
    'CITY_LARGE', 'CITY_MIDSIZE', 'CITY_SMALL',
    'SUBURB_LARGE', 'SUBURB_MIDSIZE', 'SUBURB_SMALL',
    'TOWN_FRINGE', 'TOWN_DISTANT', 'TOWN_REMOTE',
    'RURAL_FRINGE', 'RURAL_DISTANT', 'RURAL_REMOTE',
], '.locale')

# --- nces_download ---
_register(['NCESDownloader', 'NCESDownloadError'], '.providers.nces_download')

# --- databricks_fallback ---
_register([
    'SpatialLoaderPlan', 'select_spatial_loader',
    'build_census_table_name', 'build_census_ingest_targets',
], '.databricks_fallback')

# --- spatial_runtime ---
_register([
    'SpatialRuntimePlan',
    'resolve_spatial_runtime_plan',
    'GeometryPayload',
    'encode_geometry',
    'decode_geometry',
    'payload_to_spark_row',
    'spark_row_to_payload',
], '.spatial_runtime')

# --- census_files (PL 94-171) ---
_register([
    'PLFileDownloader', 'get_pl_data', 'get_pl_blocks', 'get_pl_tracts',
    'download_pl_file', 'list_available_pl_files',
    'PL_FILE_TYPES', 'PL_TABLES',
], '.census_files')

# --- interpolation (areal interpolation) ---
_register([
    'ArealInterpolationResult', 'interpolate_areal',
    'interpolate_extensive', 'interpolate_intensive', 'compute_area_weights',
], '.interpolation')

# --- choropleth ---
_register([
    'create_choropleth', 'create_choropleth_comparison',
    'create_classified_comparison', 'create_bivariate_choropleth',
    'create_bivariate_crosstab', 'create_bivariate_companion_maps',
    'verify_bivariate_classification', 'create_bivariate_analysis',
    'BivariateAnalysisResult', 'save_map', 'BIVARIATE_COLOR_SCHEMES',
], '.choropleth')

# --- schemas (demographics) ---
_register([
    'DemographicVariableSchema', 'DemographicSnapshotSchema',
    'DemographicTimeSeriesSchema', 'schemas_to_gdf',
], '.schemas')

# --- h3_utils (H3 hexagonal spatial index) ---
_register([
    'H3_AVAILABLE',
    'h3_index_points', 'h3_index_polygon', 'h3_spatial_join',
    'h3_hex_to_boundary', 'h3_resolution_for_area',
    'h3_resolution_for_admin_level', 'ADMIN_LEVEL_AVG_AREA_KM2',
], '.h3_utils')

# --- temporal (pure-Python temporal data management) ---
_register([
    'TemporalDataStore', 'get_temporal_store',
    'save_boundaries', 'load_boundaries', 'query_boundaries_at_date',
    'save_demographics', 'load_demographics',
    'TemporalTimeseriesBuilder', 'TemporalDemographicService',
    'TimeseriesBuildResult',
    'spatial_query', 'temporal_filter', 'point_in_boundary',
], '.temporal')


__all__ = list(_LAZY_IMPORTS.keys())

# Version is derived from the top-level package; no separate version here.
__author__ = "Siege Analytics"
__description__ = "Enhanced geographic utilities with intelligent Census data selection"


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        # Handle absolute module paths (census_constants)
        if module_path.startswith('siege_utilities.'):
            mod = importlib.import_module(module_path)
        else:
            mod = importlib.import_module(module_path, __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))


# Convenience functions (defined here, no external imports needed)

def get_census_intelligence():
    """
    Get a comprehensive Census intelligence system.

    Returns:
        tuple: (CensusDatasetMapper, CensusDataSelector) for full Census data intelligence
    """
    from .census_dataset_mapper import get_census_dataset_mapper
    from .census_data_selector import get_census_data_selector
    return get_census_dataset_mapper(), get_census_data_selector()


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
    return {
        "recommendations": select_census_datasets(analysis_type, geography_level),
        "analysis_approach": get_analysis_approach(analysis_type, geography_level),
    }
