"""
siege_utilities — lazy-loaded package for data engineering, analytics, and distributed computing.

Only core logging, settings, and string utilities are loaded eagerly.
All other modules are loaded on first access via PEP 562 __getattr__.
"""

import importlib
import logging
import sys
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Eager imports: core-only, no heavy dependencies ──────────────────

from .conf import settings  # noqa: F401

from .core.logging import (  # noqa: F401
    log_info, log_warning, log_error, log_debug, log_critical,
    init_logger, get_logger, configure_shared_logging,
)

from .core.string_utils import remove_wrapping_quotes_and_trim  # noqa: F401

# ── Package metadata ─────────────────────────────────────────────────

try:
    from importlib.metadata import version as _meta_version
    __version__ = _meta_version("siege-utilities")
except Exception:
    __version__ = "3.14.0"  # fallback for editable installs without metadata
__author__ = "Siege Analytics"
__description__ = "Comprehensive utilities for data engineering, analytics, and distributed computing"

# ── Dependency wrapper for graceful failures ─────────────────────────


def _create_dependency_wrapper(func_name: str, required_deps: list):
    """Create a wrapper that gives helpful error messages for missing dependencies."""
    def wrapper(*args, **kwargs):
        deps_str = ', '.join(required_deps)
        raise ImportError(
            f"Function '{func_name}' requires additional dependencies: {deps_str}\n"
            f"Install with: pip install {' '.join(required_deps)}"
        )
    wrapper.__name__ = func_name
    wrapper.__doc__ = f"Function requires dependencies: {', '.join(required_deps)}"
    return wrapper


# ── Lazy import registry ─────────────────────────────────────────────
# Maps name -> (module_path, attr_name, [required_deps])
#
# When accessed via __getattr__, the module is imported and the attribute
# is fetched and cached in the module namespace for subsequent accesses.

_LAZY_IMPORTS = {}


def _register_lazy(names, module, deps=None, renames=None):
    """Register names for lazy import from a submodule.

    Args:
        names: List of attribute names to expose at package level.
        module: Dotted module path relative to this package (e.g. '.geo.spatial_data').
        deps: Optional list of pip packages required (for error messages).
        renames: Optional dict mapping exposed_name -> source_name for aliases.
    """
    renames = renames or {}
    for name in names:
        source_name = renames.get(name, name)
        _LAZY_IMPORTS[name] = (module, source_name, deps or [])


# ── File utilities (stdlib-only) ─────────────────────────────────────

_register_lazy([
    'check_if_file_exists_at_path', 'file_exists', 'touch_file', 'count_lines',
    'copy_file', 'move_file', 'get_file_size', 'list_directory', 'run_command',
    'remove_tree', 'delete_existing_file_and_replace_it_with_an_empty_file',
], '.files.operations')

_register_lazy([
    'calculate_file_hash', 'generate_sha256_hash_for_file',
    'get_file_hash', 'get_quick_file_signature', 'verify_file_integrity',
], '.files.hashing')

_register_lazy([
    'ensure_path_exists', 'unzip_file_to_directory', 'get_file_extension',
    'get_file_name_without_extension', 'is_hidden_file', 'normalize_path',
    'get_relative_path', 'create_backup_path', 'find_files_by_pattern',
], '.files.paths')

_register_lazy([
    'generate_local_path_from_url', 'download_file', 'download_file_with_retry',
    'get_file_info', 'is_downloadable',
], '.files.remote')

_register_lazy(['run_subprocess'], '.files.shell')

# ── Config: databases, projects, directories, clients, connections ───

_register_lazy([
    'create_database_config', 'save_database_config', 'load_database_config',
    'get_spark_database_options', 'test_database_connection', 'list_database_configs',
    'create_spark_session_with_databases',
], '.config.databases')

_register_lazy([
    'create_project_config', 'save_project_config', 'load_project_config',
    'setup_project_directories', 'get_project_path', 'list_projects', 'update_project_config',
], '.config.projects')

_register_lazy([
    'create_directory_structure', 'create_standard_project_structure',
    'save_directory_config', 'load_directory_config', 'ensure_directories_exist',
    'get_directory_info', 'clean_empty_directories', 'list_directory_configs',
], '.config.directories')

_register_lazy([
    'create_client_profile', 'save_client_profile', 'load_client_profile',
    'update_client_profile', 'list_client_profiles', 'search_client_profiles',
    'associate_client_with_project', 'get_client_project_associations', 'validate_client_profile',
], '.config.clients')

_register_lazy([
    'create_connection_profile', 'save_connection_profile', 'load_connection_profile',
    'find_connection_by_name', 'list_connection_profiles', 'update_connection_profile',
    'verify_connection_profile', 'get_connection_status', 'cleanup_old_connections',
], '.config.connections')

# ── Pydantic config system (requires pydantic>=2.0) ──────────────────

_register_lazy([
    'UserConfigManager', 'UserProfile', 'user_config',
    'get_user_config', 'get_download_directory',
], '.config.user_config', deps=['pydantic>=2.0'])

_register_lazy([
    'EnhancedUserProfile', 'ClientProfile', 'SiegeConfig',
    'load_user_profile', 'save_user_profile',
    'enhanced_load_client_profile', 'enhanced_save_client_profile',
    'enhanced_list_client_profiles',
    'export_config_yaml', 'import_config_yaml',
], '.config.enhanced_config', deps=['pydantic>=2.0'],
    renames={
        'EnhancedUserProfile': 'UserProfile',
        'enhanced_load_client_profile': 'load_client_profile',
        'enhanced_save_client_profile': 'save_client_profile',
        'enhanced_list_client_profiles': 'list_client_profiles',
    })

_register_lazy([
    'get_default_profile_location', 'set_profile_location',
    'get_profile_location', 'list_profile_locations',
    'migrate_profiles', 'create_default_profiles',
    'validate_profile_location', 'get_profile_summary',
], '.admin.profile_manager', deps=['pydantic>=2.0'])

# ── Distributed / Spark (custom functions only) ──────────────────────

_register_lazy([
    'sanitise_dataframe_column_names', 'tabulate_null_vs_not_null',
    'get_row_count', 'repartition_and_cache', 'register_temp_table',
    'move_column_to_front_of_dataframe', 'write_df_to_parquet', 'read_parquet_to_df',
    'flatten_json_column_and_join_back_to_df',
    'validate_geocode_data', 'mark_valid_geocode_data', 'clean_and_reorder_bbox',
    'ensure_literal', 'reproject_geom_columns',
    'prepare_dataframe_for_export', 'prepare_summary_dataframe',
    'export_pyspark_df_to_excel', 'pivot_summary_table_for_bools',
    'pivot_summary_with_metrics', 'export_prepared_df_as_csv_to_path_using_delimiter',
    'print_debug_table', 'compute_walkability', 'validate_geometry',
    'backup_full_dataframe', 'atomic_write_with_staging', 'create_unique_staging_directory',
    'walkability_config',
], '.distributed.spark_utils', deps=['pyspark'])

_register_lazy([
    'HDFSConfig', 'create_hdfs_config', 'create_local_config',
    'create_cluster_config', 'create_geocoding_config',
    'create_yarn_config', 'create_census_analysis_config',
], '.distributed.hdfs_config', deps=['pyspark'])

_register_lazy([
    'AbstractHDFSOperations', 'setup_distributed_environment', 'create_hdfs_operations',
], '.distributed.hdfs_operations', deps=['pyspark'])

# ── Geo / Census / Spatial ───────────────────────────────────────────

_register_lazy([
    'get_census_intelligence', 'quick_census_selection',
], '.geo', deps=['geopandas'])

_register_lazy([
    'concatenate_addresses', 'use_nominatim_geocoder',
    'get_country_name', 'get_country_code', 'list_countries', 'get_coordinates',
], '.geo.geocoding', deps=['geopandas'])

_register_lazy([
    'DEFAULT_ORS_BASE_URL', 'DEFAULT_VALHALLA_BASE_URL',
    'build_isochrone_request', 'get_isochrone', 'isochrone_to_geodataframe',
], '.geo.isochrones', deps=['requests'])

_register_lazy([
    'get_census_data_selector', 'select_census_datasets', 'get_analysis_approach',
    'select_datasets_for_analysis', 'get_dataset_compatibility_matrix', 'suggest_analysis_approach',
], '.geo.census_data_selector', deps=['geopandas'])

_register_lazy([
    'get_census_dataset_mapper', 'get_best_dataset_for_analysis', 'compare_census_datasets',
    'get_dataset_info', 'list_datasets_by_type', 'list_datasets_by_geography',
    'get_best_dataset_for_use_case', 'get_dataset_relationships', 'compare_datasets',
    'get_data_selection_guide', 'export_dataset_catalog',
], '.geo.census_dataset_mapper', deps=['geopandas'])

_register_lazy([
    'get_census_data', 'get_census_boundaries', 'download_osm_data',
    'get_available_years', 'get_year_directory_contents', 'discover_boundary_types',
    'construct_download_url', 'validate_download_url', 'get_optimal_year',
    'download_data', 'get_geographic_boundaries', 'get_available_boundary_types',
    'refresh_discovery_cache', 'get_available_state_fips', 'get_state_abbreviations',
    'get_comprehensive_state_info', 'get_state_by_abbreviation', 'get_state_by_name',
    'validate_state_fips', 'get_state_name', 'get_state_abbreviation', 'download_dataset',
    'get_unified_fips_data',
    'normalize_state_input', 'normalize_state_name', 'normalize_state_abbreviation',
    'normalize_fips_code',
], '.geo.spatial_data', deps=['geopandas'])

# normalize_state_identifier is an alias for normalize_state_identifier_standalone
_register_lazy(
    ['normalize_state_identifier'],
    '.geo.spatial_data', deps=['geopandas'],
    renames={'normalize_state_identifier': 'normalize_state_identifier_standalone'},
)

# ── Databricks helpers (requires databricks-sdk, pyspark) ────────────

_register_lazy([
    'build_databricks_run_url', 'build_foreign_table_sql', 'build_jdbc_url',
    'build_lakebase_psql_command', 'build_pgpass_entry',
    'build_schema_and_table_sync_sql', 'ensure_secret_scope',
    'geopandas_to_spark', 'get_active_spark_session', 'get_dbutils',
    'get_runtime_secret', 'get_workspace_client', 'pandas_to_spark',
    'parse_conninfo', 'put_secret', 'runtime_secret_exists',
    'spark_to_geopandas', 'spark_to_pandas',
], '.databricks', deps=['pyspark'])

# ── Sample data (requires pandas, faker) ─────────────────────────────

_register_lazy([
    'load_sample_data', 'list_available_datasets',
    'join_boundaries_and_data', 'create_sample_dataset',
    'generate_synthetic_population', 'generate_synthetic_businesses',
    'generate_synthetic_housing',
    'SAMPLE_DATASETS', 'CENSUS_SAMPLES', 'SYNTHETIC_SAMPLES',
], '.data.sample_data', deps=['pandas'],
)

# ── Analytics ────────────────────────────────────────────────────────

_register_lazy([
    'GoogleAnalyticsConnector', 'create_ga_account_profile', 'save_ga_account_profile',
    'load_ga_account_profile', 'list_ga_accounts_for_client', 'batch_retrieve_ga_data',
], '.analytics.google_analytics', deps=['google-analytics-data'])

_register_lazy([
    'get_datadotworld_connector', 'search_datadotworld_datasets',
    'load_datadotworld_dataset', 'query_datadotworld_dataset',
    'search_datasets', 'list_datasets',
], '.analytics.datadotworld_connector', deps=['datadotworld'])

_register_lazy([
    'get_snowflake_connector', 'upload_to_snowflake',
    'download_from_snowflake', 'execute_snowflake_query',
], '.analytics.snowflake_connector', deps=['snowflake-connector-python'])

_register_lazy([
    'FacebookBusinessConnector', 'create_facebook_account_profile',
    'save_facebook_account_profile', 'load_facebook_account_profile',
    'list_facebook_accounts_for_client', 'batch_retrieve_facebook_data',
], '.analytics.facebook_business', deps=['facebook-business'])

# ── Reporting (requires matplotlib, reportlab, etc.) ─────────────────

_register_lazy([
    'BaseReportTemplate', 'ReportGenerator', 'ChartGenerator',
    'ClientBrandingManager', 'AnalyticsReportGenerator', 'PowerPointGenerator',
    'get_report_output_directory', 'create_report_generator', 'create_powerpoint_generator',
    'export_branding_config', 'import_branding_config', 'export_chart_type_config',
], '.reporting', deps=['matplotlib', 'reportlab'])

_register_lazy(['ChartTypeRegistry'], '.reporting.chart_types', deps=['matplotlib'])
_register_lazy(['PollingAnalyzer'], '.reporting.analytics.polling_analyzer', deps=['matplotlib'])

_register_lazy([
    'create_bar_chart', 'create_line_chart', 'create_pie_chart', 'create_scatter_plot',
    'create_heatmap', 'create_choropleth_map', 'create_bivariate_choropleth',
    'create_marker_map', 'create_flow_map', 'create_dashboard',
    'create_dataframe_summary_charts', 'generate_chart_from_dataframe',
], '.reporting.chart_generator', deps=['matplotlib', 'seaborn'])

# ── Runtime guard (stdlib-only, always importable) ────────────────

_register_lazy([
    'ensure_compatible', 'diagnose_environment', 'purge_stale_modules',
    'is_databricks_runtime', 'RuntimeGuardError',
], '.runtime')

# ── Hygiene ──────────────────────────────────────────────────────────

_register_lazy([
    'generate_docstring_template', 'analyze_function_signature',
    'categorize_function', 'process_python_file', 'find_python_files',
], '.hygiene.generate_docstrings')

# ── Development ──────────────────────────────────────────────────────

_register_lazy([
    'generate_architecture_diagram', 'analyze_package_structure',
    'analyze_module', 'analyze_function', 'analyze_class',
], '.development.architecture')

# ── Git ──────────────────────────────────────────────────────────────

_register_lazy([
    'analyze_branch_status', 'generate_branch_report', 'get_commit_history',
    'categorize_commits', 'get_file_changes', 'get_file_stats',
], '.git.branch_analyzer')

_register_lazy([
    'create_feature_branch', 'switch_branch', 'merge_branch', 'rebase_branch',
    'stash_changes', 'apply_stash', 'clean_working_directory', 'reset_to_commit',
    'cherry_pick_commit', 'create_tag', 'push_branch', 'pull_branch',
], '.git.git_operations')

_register_lazy(['get_repository_status', 'get_branch_info'], '.git.git_status')
_register_lazy(['start_feature_workflow', 'validate_branch_naming'], '.git.git_workflow')

# ── Testing ──────────────────────────────────────────────────────────

_register_lazy([
    'setup_spark_environment', 'get_system_info', 'ensure_env_vars',
    'check_java_version', 'diagnose_test_environment', 'quick_environment_setup',
], '.testing.environment',
    renames={'diagnose_test_environment': 'diagnose_environment'})

_register_lazy([
    'run_test_suite', 'get_test_report', 'run_comprehensive_test',
    'quick_smoke_test', 'build_pytest_command',
], '.testing.runner')


# ── PEP 562 __getattr__ (lazy loading) ───────────────────────────────

# Track which distributed module names we've already cached (avoid repeated lookups)
_distributed_module = None  # cached module or False (import failed)


def __getattr__(name):
    global _distributed_module

    # 1. Check the explicit lazy registry
    if name in _LAZY_IMPORTS:
        module_path, attr_name, deps = _LAZY_IMPORTS[name]
        try:
            mod = importlib.import_module(module_path, __package__)
            val = getattr(mod, attr_name)
            setattr(sys.modules[__name__], name, val)
            return val
        except ImportError:
            if deps:
                wrapper = _create_dependency_wrapper(attr_name, deps)
                setattr(sys.modules[__name__], name, wrapper)
                return wrapper
            raise

    # 2. Fallback: try the distributed module for PySpark re-exports
    #    (col, lit, when, sum, etc. — ~524 functions from pyspark.sql.functions)
    if _distributed_module is None:
        try:
            _distributed_module = importlib.import_module('.distributed', __package__)
        except ImportError:
            _distributed_module = False  # Don't retry import on failure

    if _distributed_module and hasattr(_distributed_module, name):
        val = getattr(_distributed_module, name)
        setattr(sys.modules[__name__], name, val)
        return val

    # 3. Not found
    raise AttributeError(f"module 'siege_utilities' has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))


# ── Introspection functions (defined here, always available) ─────────

def get_package_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the siege_utilities package.
    Uses DYNAMIC discovery to report only actually available functions.

    Returns:
        Dictionary containing package information, available functions, and module status
    """
    import inspect as _inspect

    current_module = sys.modules[__name__]

    package_info = {
        'package_name': 'siege_utilities',
        'version': __version__,
        'description': __description__,
        'total_functions': 0,
        'total_modules': 0,
        'available_functions': [],
        'available_modules': [],
        'unavailable_functions': [],
        'failed_imports': [],
        'subpackages': [],
        'categories': {
            'core': [], 'files': [], 'distributed': [], 'geo': [],
            'config': [], 'admin': [], 'hygiene': [], 'testing': [],
            'data': [], 'analytics': [], 'reporting': [], 'git': [],
            'development': [],
        }
    }

    # Function name to category mapping
    function_categories = {
        'log_info': 'core', 'log_warning': 'core', 'log_error': 'core',
        'log_debug': 'core', 'log_critical': 'core',
        'init_logger': 'core', 'get_logger': 'core', 'configure_shared_logging': 'core',
        'remove_wrapping_quotes_and_trim': 'core',
        'check_if_file_exists_at_path': 'files', 'calculate_file_hash': 'files',
        'ensure_path_exists': 'files', 'generate_sha256_hash_for_file': 'files',
        'get_file_hash': 'files', 'get_quick_file_signature': 'files',
        'verify_file_integrity': 'files', 'unzip_file_to_directory': 'files',
        'file_exists': 'files', 'touch_file': 'files', 'count_lines': 'files',
        'copy_file': 'files', 'move_file': 'files', 'get_file_size': 'files',
        'list_directory': 'files', 'run_command': 'files', 'remove_tree': 'files',
        'generate_local_path_from_url': 'files', 'download_file': 'files',
        'download_file_with_retry': 'files', 'get_file_info': 'files',
        'is_downloadable': 'files', 'run_subprocess': 'files',
        'get_row_count': 'distributed', 'repartition_and_cache': 'distributed',
        'register_temp_table': 'distributed',
        'move_column_to_front_of_dataframe': 'distributed',
        'write_df_to_parquet': 'distributed', 'read_parquet_to_df': 'distributed',
        'create_database_config': 'config', 'save_database_config': 'config',
        'load_database_config': 'config', 'get_spark_database_options': 'config',
        'test_database_connection': 'config', 'list_database_configs': 'config',
        'create_spark_session_with_databases': 'config',
        'create_project_config': 'config', 'save_project_config': 'config',
        'load_project_config': 'config', 'setup_project_directories': 'config',
        'get_project_path': 'config', 'list_projects': 'config',
        'update_project_config': 'config',
        'create_directory_structure': 'config',
        'create_standard_project_structure': 'config',
        'save_directory_config': 'config', 'load_directory_config': 'config',
        'ensure_directories_exist': 'config', 'get_directory_info': 'config',
        'clean_empty_directories': 'config', 'list_directory_configs': 'config',
        'create_client_profile': 'config', 'save_client_profile': 'config',
        'load_client_profile': 'config', 'update_client_profile': 'config',
        'list_client_profiles': 'config', 'search_client_profiles': 'config',
        'associate_client_with_project': 'config',
        'get_client_project_associations': 'config',
        'validate_client_profile': 'config',
        'create_connection_profile': 'config', 'save_connection_profile': 'config',
        'load_connection_profile': 'config', 'find_connection_by_name': 'config',
        'list_connection_profiles': 'config', 'update_connection_profile': 'config',
        'verify_connection_profile': 'config', 'get_connection_status': 'config',
        'cleanup_old_connections': 'config',
        'get_user_config': 'config', 'get_download_directory': 'config',
        'load_user_profile': 'config', 'save_user_profile': 'config',
        'export_config_yaml': 'config', 'import_config_yaml': 'config',
        'get_default_profile_location': 'admin', 'set_profile_location': 'admin',
        'get_profile_location': 'admin', 'list_profile_locations': 'admin',
        'migrate_profiles': 'admin', 'create_default_profiles': 'admin',
        'validate_profile_location': 'admin', 'get_profile_summary': 'admin',
        'concatenate_addresses': 'geo', 'use_nominatim_geocoder': 'geo',
        'get_census_intelligence': 'geo', 'quick_census_selection': 'geo',
        'get_census_data_selector': 'geo', 'select_census_datasets': 'geo',
        'get_analysis_approach': 'geo', 'select_datasets_for_analysis': 'geo',
        'get_dataset_compatibility_matrix': 'geo', 'suggest_analysis_approach': 'geo',
        'get_census_dataset_mapper': 'geo', 'get_best_dataset_for_analysis': 'geo',
        'compare_census_datasets': 'geo', 'get_dataset_info': 'geo',
        'list_datasets_by_type': 'geo', 'list_datasets_by_geography': 'geo',
        'get_best_dataset_for_use_case': 'geo', 'get_dataset_relationships': 'geo',
        'compare_datasets': 'geo', 'get_data_selection_guide': 'geo',
        'export_dataset_catalog': 'geo',
        'get_census_data': 'geo', 'get_census_boundaries': 'geo',
        'download_osm_data': 'geo', 'get_available_years': 'geo',
        'get_year_directory_contents': 'geo', 'discover_boundary_types': 'geo',
        'construct_download_url': 'geo', 'validate_download_url': 'geo',
        'get_optimal_year': 'geo', 'download_data': 'geo',
        'get_geographic_boundaries': 'geo', 'get_available_boundary_types': 'geo',
        'refresh_discovery_cache': 'geo', 'get_available_state_fips': 'geo',
        'get_state_abbreviations': 'geo', 'get_comprehensive_state_info': 'geo',
        'get_state_by_abbreviation': 'geo', 'get_state_by_name': 'geo',
        'validate_state_fips': 'geo', 'get_state_name': 'geo',
        'get_state_abbreviation': 'geo', 'download_dataset': 'geo',
        'get_unified_fips_data': 'geo', 'normalize_state_identifier': 'geo',
        'generate_docstring_template': 'hygiene',
        'analyze_function_signature': 'hygiene',
        'generate_architecture_diagram': 'development',
        'analyze_package_structure': 'development',
        'analyze_branch_status': 'git', 'generate_branch_report': 'git',
        'create_feature_branch': 'git', 'switch_branch': 'git',
        'merge_branch': 'git', 'get_repository_status': 'git',
        'get_branch_info': 'git', 'start_feature_workflow': 'git',
        'validate_branch_naming': 'git',
        'setup_spark_environment': 'testing', 'get_system_info': 'testing',
        'load_sample_data': 'data', 'list_available_datasets': 'data',
        'join_boundaries_and_data': 'data',
        'create_sample_dataset': 'data', 'generate_synthetic_population': 'data',
        'generate_synthetic_businesses': 'data', 'generate_synthetic_housing': 'data',
        'create_ga_account_profile': 'analytics', 'save_ga_account_profile': 'analytics',
        'load_ga_account_profile': 'analytics', 'list_ga_accounts_for_client': 'analytics',
        'batch_retrieve_ga_data': 'analytics',
        'create_facebook_account_profile': 'analytics',
        'save_facebook_account_profile': 'analytics',
        'load_facebook_account_profile': 'analytics',
        'list_facebook_accounts_for_client': 'analytics',
        'batch_retrieve_facebook_data': 'analytics',
        'get_datadotworld_connector': 'analytics',
        'search_datadotworld_datasets': 'analytics',
        'load_datadotworld_dataset': 'analytics',
        'query_datadotworld_dataset': 'analytics',
        'search_datasets': 'analytics', 'list_datasets': 'analytics',
        'get_snowflake_connector': 'analytics', 'upload_to_snowflake': 'analytics',
        'download_from_snowflake': 'analytics', 'execute_snowflake_query': 'analytics',
        'BaseReportTemplate': 'reporting', 'ReportGenerator': 'reporting',
        'ChartGenerator': 'reporting', 'ClientBrandingManager': 'reporting',
        'AnalyticsReportGenerator': 'reporting', 'PowerPointGenerator': 'reporting',
        'get_report_output_directory': 'reporting',
        'create_report_generator': 'reporting',
        'create_powerpoint_generator': 'reporting',
        'export_branding_config': 'reporting', 'import_branding_config': 'reporting',
        'export_chart_type_config': 'reporting', 'PollingAnalyzer': 'reporting',
        'create_bar_chart': 'reporting', 'create_line_chart': 'reporting',
        'create_pie_chart': 'reporting', 'create_scatter_plot': 'reporting',
        'create_heatmap': 'reporting', 'create_choropleth_map': 'reporting',
        'create_bivariate_choropleth': 'reporting', 'create_marker_map': 'reporting',
        'create_flow_map': 'reporting', 'create_dashboard': 'reporting',
        'create_dataframe_summary_charts': 'reporting',
        'generate_chart_from_dataframe': 'reporting',
    }

    for name in dir(current_module):
        if name.startswith('_') or name in ('sys', 'json', 'pathlib', 'logging', 'importlib', 'inspect'):
            continue
        obj = getattr(current_module, name)
        if name in function_categories:
            if obj is None:
                package_info['unavailable_functions'].append(name)
            elif callable(obj) or _inspect.isclass(obj):
                package_info['available_functions'].append(name)
                package_info['categories'][function_categories[name]].append(name)
                package_info['total_functions'] += 1
        elif callable(obj) or _inspect.isclass(obj):
            package_info['available_functions'].append(name)
            package_info['total_functions'] += 1

    package_info['total_modules'] = len([
        n for n in dir(current_module)
        if _inspect.ismodule(getattr(current_module, n, None))
    ])

    package_info['available_functions'].sort()
    package_info['unavailable_functions'].sort()
    for cat in package_info['categories']:
        package_info['categories'][cat].sort()

    log_info(
        f"Package info generated: {package_info['total_functions']} available functions, "
        f"{package_info['total_modules']} modules, "
        f"{len(package_info['unavailable_functions'])} unavailable"
    )
    return package_info


def check_dependencies() -> Dict[str, bool]:
    """
    Check the availability of optional dependencies.

    Returns:
        Dictionary mapping dependency names to availability status
    """
    dependencies = {
        'pandas': False, 'numpy': False, 'pyspark': False,
        'sqlalchemy': False, 'psycopg2': False, 'pymysql': False,
        'cx_oracle': False, 'pyodbc': False, 'requests': False,
        'geopy': False, 'shapely': False, 'folium': False,
        'geopandas': False, 'duckdb': False, 'fiona': False,
        'pyproj': False, 'faker': False, 'tqdm': False,
    }

    for dep_name in dependencies:
        try:
            importlib.import_module(dep_name)
            dependencies[dep_name] = True
        except ImportError:
            pass

    import builtins
    available_count = builtins.sum(dependencies.values())
    total_count = len(dependencies)
    log_info(f"Dependency check complete: {available_count}/{total_count} available")

    return dependencies


def get_available_functions() -> Dict[str, list]:
    """
    Get a categorized list of available functions.

    Returns:
        Dictionary mapping categories to lists of function names
    """
    return get_package_info()['categories']


def get_function_help(function_name: str) -> Optional[str]:
    """
    Get help information for a specific function.

    Args:
        function_name: Name of the function to get help for

    Returns:
        Function help string or None if function not found
    """
    if hasattr(sys.modules[__name__], function_name):
        func = getattr(sys.modules[__name__], function_name)
        if hasattr(func, '__doc__') and func.__doc__:
            return func.__doc__
    return None
