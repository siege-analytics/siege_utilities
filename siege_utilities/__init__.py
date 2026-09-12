"""
siege_utilities — lazy-loaded package for data engineering, analytics, and distributed computing.

Only core logging, settings, and string utilities are loaded eagerly.
All other modules are loaded on first access via PEP 562 __getattr__.
"""

import importlib
import logging
import sys
import threading
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
except (ImportError, ValueError, ModuleNotFoundError):
    __version__ = "3.23.0"  # fallback for editable installs without metadata
__author__ = "Siege Analytics"
__description__ = "Comprehensive utilities for data engineering, analytics, and distributed computing"

# ── Dependency wrapper for graceful failures ─────────────────────────


import re as _re

_DEP_NAME_RE = _re.compile(r'^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)')
_DEP_FLOOR_RE = _re.compile(r'>=\s*(\d+)')


def _installed_major(mod) -> int:
    """Best-effort major version of an imported module (VERSION or __version__)."""
    raw = getattr(mod, 'VERSION', None) or getattr(mod, '__version__', '') or ''
    try:
        return int(str(raw).split('.', 1)[0])
    except (ValueError, IndexError):
        return -1  # unknown — treat as satisfying (don't false-positive)


_DEPENDENCY_IMPORT_MODULES = {
    'google-analytics-data': 'google.analytics.data_v1beta',
    'snowflake-connector-python': 'snowflake.connector',
}


def _dependency_name(spec: str) -> str | None:
    match = _DEP_NAME_RE.match(spec)
    return match.group(1) if match else None


def _dependency_is_installed(dep_name: str) -> bool:
    import_name = _DEPENDENCY_IMPORT_MODULES.get(dep_name, dep_name.replace('-', '_'))
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def _missing_dependencies(deps: list) -> list[str]:
    """Return dependency specs that are unavailable or below a major-version floor.

    A package counts as missing when it is uninstalled OR installed below a
    declared major-version floor (e.g. ``pydantic>=2.0`` under pydantic v1).
    Dependency specs are distribution names, not always import-module names,
    so known mismatches are resolved through ``_DEPENDENCY_IMPORT_MODULES`` and
    then checked against installed distributions before being marked missing.
    """
    missing = []
    for spec in deps:
        dep_name = _dependency_name(spec)
        if not dep_name:
            continue
        if not _dependency_is_installed(dep_name):
            missing.append(spec)
            continue
        floor = _DEP_FLOOR_RE.search(spec)
        if floor:
            import_name = _DEPENDENCY_IMPORT_MODULES.get(dep_name, dep_name.replace('-', '_'))
            try:
                mod = importlib.import_module(import_name)
            except ImportError:
                continue
            major = _installed_major(mod)
            if major != -1 and major < int(floor.group(1)):
                missing.append(spec)
    return missing


def _is_dep_missing(deps: list) -> bool:
    return bool(_missing_dependencies(deps))


def _create_dependency_wrapper(func_name: str, required_deps: list):
    """Create a wrapper that gives helpful error messages for missing dependencies."""
    def wrapper(*args, **kwargs):
        deps_str = ', '.join(required_deps)
        raise ImportError(
            f"Function '{func_name}' requires additional dependencies: {deps_str}\n"
            f"Install with: pip install {' '.join(required_deps)}"
        )
    wrapper.__name__ = func_name
    wrapper.__qualname__ = func_name
    wrapper.__doc__ = f"Function requires dependencies: {', '.join(required_deps)}"
    wrapper.__siege_optional_dependency_wrapper__ = True
    wrapper.__siege_required_dependencies__ = tuple(required_deps)
    wrapper.__siege_missing_dependencies__ = tuple(required_deps)
    wrapper.__siege_available__ = False
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
        # #1176 hostile-review F1: raise on duplicate registration so a
        # future promotion batch cannot silently pick a collision winner.
        if name in _LAZY_IMPORTS and _LAZY_IMPORTS[name][0] != module:
            existing_module = _LAZY_IMPORTS[name][0]
            raise RuntimeError(
                f"_register_lazy: duplicate registration for {name!r}: "
                f"already bound to {existing_module!r}, would rebind to {module!r}. "
                "Rename the losing definition or delete the stale copy before promotion."
            )
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
    'UserConfigManager', 'UserProfile',
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
    'GeocodingError', 'concatenate_addresses',
    'get_country_name', 'get_country_code', 'list_countries',
], '.geo.geocoding_core')

_register_lazy([
    'use_nominatim_geocoder', 'get_coordinates',
], '.geo.geocoding', deps=['pandas', 'geopy'])

_register_lazy([
    'DEFAULT_ORS_BASE_URL', 'DEFAULT_VALHALLA_BASE_URL',
    'build_isochrone_request', 'get_isochrone', 'isochrone_to_geodataframe',
], '.geo.isochrones', deps=['httpx'])

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

# normalize_state_identifier delegates to the canonical config version;
# no geopandas dependency needed for pure FIPS lookup.
_register_lazy(
    ['normalize_state_identifier'],
    '.config.census_registry',
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
], '.reference.sample_data', deps=['pandas'],
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

# ── CRM Connectors (protocol + error types, core-only deps) ───────────

_register_lazy([
    'ConnectorProtocol', 'UpsertResult', 'UpsertError',
    'ConnectorError', 'ConnectorAuthError',
    'ConnectorRateLimitError', 'ConnectorNotFoundError',
], '.connectors._protocol', deps=['pandas'])

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

_distributed_module = None
_distributed_module_lock = threading.Lock()


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
            if deps and _is_dep_missing(deps):
                # Don't cache the dependency-wrapper stub. Caching would
                # break the recovery path where a user installs the missing
                # dep and expects the next attribute access to load the
                # real symbol. Recreating the wrapper on each access is
                # cheap relative to the ImportError it fronts.
                # (SU-1 / CLAUDE.md rule 6: caching a failure stub silently
                # degrades the documented "install X" contract.)
                return _create_dependency_wrapper(attr_name, deps)
            raise

    # 2. Fallback: try the distributed module for PySpark re-exports
    if _distributed_module is None:
        with _distributed_module_lock:
            if _distributed_module is None:
                try:
                    _distributed_module = importlib.import_module('.distributed', __package__)
                except ImportError:
                    _distributed_module = False

    if _distributed_module and hasattr(_distributed_module, name):
        val = getattr(_distributed_module, name)
        setattr(sys.modules[__name__], name, val)
        return val

    # 3. Not found
    raise AttributeError(f"module 'siege_utilities' has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))


# ── Explicit public API surface (#1176) ──────────────────────────────
# Canonical public API — symbols documented in README / notebooks / release
# notes that consumers may import directly from `siege_utilities`. Additions
# happen per-subpackage via promotion PRs; each candidate is classified by
# `scripts/audit_public_api_surface.py` before landing here.
#
# Anything in `_LAZY_IMPORTS` but NOT in `__all__` remains addressable via
# `__getattr__` for backward compatibility but is not part of the declared
# public contract.
#
# Backward-compat note: prior to #1176, `siege_utilities.__all__` resolved
# implicitly to `.distributed.__all__` via the __getattr__ fallback. The
# `.distributed` block below preserves that surface so `from siege_utilities
# import *` behaviour is unchanged for existing consumers.

__all__ = [
    # Eagerly-imported core (available without hitting __getattr__)
    'settings',
    'log_info', 'log_warning', 'log_error', 'log_debug', 'log_critical',
    'init_logger', 'get_logger', 'configure_shared_logging',
    'remove_wrapping_quotes_and_trim',
    # Package metadata
    '__version__', '__author__', '__description__',
    # ── Preserved: prior implicit surface via .distributed fallback ──
    'AbstractHDFSOperations', 'HDFSConfig', 'PYSPARK_AVAILABLE',
    'atomic_write_with_staging', 'backup_full_dataframe',
    'clean_and_reorder_bbox', 'compute_walkability',
    'create_census_analysis_config', 'create_cluster_config',
    'create_geocoding_config', 'create_hdfs_config',
    'create_hdfs_operations', 'create_local_config',
    'create_unique_staging_directory', 'create_yarn_config',
    'ensure_literal', 'export_prepared_df_as_csv_to_path_using_delimiter',
    'export_pyspark_df_to_excel', 'flatten_json_column_and_join_back_to_df',
    'get_row_count', 'mark_valid_geocode_data',
    'move_column_to_front_of_dataframe', 'pivot_summary_table_for_bools',
    'pivot_summary_with_metrics', 'prepare_dataframe_for_export',
    'prepare_summary_dataframe', 'print_debug_table', 'py_round',
    'read_parquet_to_df', 'register_temp_table', 'repartition_and_cache',
    'reproject_geom_columns', 'sanitise_dataframe_column_names',
    'setup_distributed_environment', 'tabulate_null_vs_not_null',
    'validate_geocode_data', 'validate_geometry', 'walkability_config',
    'write_df_to_parquet',
    # ── Promoted canonicals (per #1176 audit) ────────────────────────
    # geo.spatial_data (27 symbols, batch 1)
    'discover_boundary_types',
    'download_data',
    'download_dataset',
    'download_osm_data',
    'get_available_state_fips',
    'get_available_years',
    'get_census_boundaries',
    'get_census_data',
    'get_geographic_boundaries',
    'get_optimal_year',
    'get_state_abbreviations',
    'get_state_by_abbreviation',
    'normalize_fips_code',
    'normalize_state_abbreviation',
    'normalize_state_input',
    'normalize_state_name',
    'construct_download_url',
    'get_available_boundary_types',
    'get_comprehensive_state_info',
    'get_state_abbreviation',
    'get_state_by_name',
    'get_state_name',
    'get_unified_fips_data',
    'get_year_directory_contents',
    'refresh_discovery_cache',
    'validate_download_url',
    'validate_state_fips',
    # reporting (26 symbols, batch 2)
    # NOTE: `create_bivariate_choropleth` also exists in
    # `siege_utilities.geo.choropleth` with a different (GeoDataFrame-based)
    # signature. Top-level resolves to the reporting variant per
    # `_LAZY_IMPORTS`. Reconciliation tracked at #1208.
    'AnalyticsReportGenerator',
    'BaseReportTemplate',
    'ChartGenerator',
    'ChartTypeRegistry',
    'ClientBrandingManager',
    'PollingAnalyzer',
    'PowerPointGenerator',
    'ReportGenerator',
    'create_bar_chart',
    'create_bivariate_choropleth',
    'create_choropleth_map',
    'create_dashboard',
    'create_dataframe_summary_charts',
    'create_flow_map',
    'create_heatmap',
    'create_line_chart',
    'create_marker_map',
    'create_pie_chart',
    'create_powerpoint_generator',
    'create_report_generator',
    'create_scatter_plot',
    'export_branding_config',
    'export_chart_type_config',
    'generate_chart_from_dataframe',
    'get_report_output_directory',
    'import_branding_config',
    # databricks (18 symbols, batch 3)
    # NOTE: `quote_ident` is intentionally not a top-level symbol.
    # Both `.databricks.lakehouse_federation` and `.trino.federation`
    # export helpers with this name, but they implement different SQL
    # dialect quoting rules (Databricks backticks vs Trino double quotes).
    # Promoting either helper to `siege_utilities.quote_ident` would make
    # the other dialect look accidentally canonical. Use the dialect module
    # directly instead. See #1210.
    'build_databricks_run_url',
    'build_foreign_table_sql',
    'build_jdbc_url',
    'build_lakebase_psql_command',
    'build_pgpass_entry',
    'build_schema_and_table_sync_sql',
    'ensure_secret_scope',
    'geopandas_to_spark',
    'get_active_spark_session',
    'get_dbutils',
    'get_runtime_secret',
    'get_workspace_client',
    'pandas_to_spark',
    'parse_conninfo',
    'put_secret',
    'runtime_secret_exists',
    'spark_to_geopandas',
    'spark_to_pandas',
    # config profiles (17 symbols, batch 4)
    'associate_client_with_project',
    'cleanup_old_connections',
    'create_client_profile',
    'create_connection_profile',
    'find_connection_by_name',
    'get_client_project_associations',
    'get_connection_status',
    'list_client_profiles',
    'list_connection_profiles',
    'load_client_profile',
    'load_connection_profile',
    'save_client_profile',
    'save_connection_profile',
    'search_client_profiles',
    'update_client_profile',
    'update_connection_profile',
    'validate_client_profile',
    # file utilities (14 symbols, batch 5)
    'calculate_file_hash',
    'copy_file',
    'download_file',
    'download_file_with_retry',
    'ensure_path_exists',
    'file_exists',
    'generate_sha256_hash_for_file',
    'get_file_hash',
    'get_file_info',
    'get_quick_file_signature',
    'is_downloadable',
    'move_file',
    'verify_file_integrity',
    # sample data (8 symbols, batch 6 / #1213)
    'CENSUS_SAMPLES',
    'SAMPLE_DATASETS',
    'SYNTHETIC_SAMPLES',
    'generate_synthetic_businesses',
    'generate_synthetic_housing',
    'generate_synthetic_population',
    'list_available_datasets',
    'load_sample_data',
    # geocoding (6 canonical + 1 extension symbol, batch 7)
    'GeocodingError',
    'concatenate_addresses',
    'get_coordinates',
    'get_country_code',
    'get_country_name',
    'list_countries',
    'use_nominatim_geocoder',
]


# ── Introspection functions (defined here, always available) ─────────

_CATEGORY_NAMES = (
    'core', 'files', 'config', 'admin', 'distributed', 'geo', 'hygiene',
    'development', 'git', 'testing', 'data', 'analytics', 'reporting',
)

_EAGER_CATEGORIES = {
    'configure_shared_logging': 'core',
    'get_logger': 'core',
    'init_logger': 'core',
    'log_critical': 'core',
    'log_debug': 'core',
    'log_error': 'core',
    'log_info': 'core',
    'log_warning': 'core',
    'remove_wrapping_quotes_and_trim': 'core',
}


def _category_from_module_path(module_path: str) -> str | None:
    if module_path.startswith('siege_utilities.'):
        parts = module_path.split('.')[1:]
    else:
        parts = module_path.lstrip('.').split('.')
    if not parts or not parts[0]:
        return None
    first = parts[0]
    if first == 'reference':
        return 'data'
    if first in _CATEGORY_NAMES:
        return first
    return None


def _lazy_category(name: str) -> str | None:
    entry = _LAZY_IMPORTS.get(name)
    if not entry:
        return _EAGER_CATEGORIES.get(name)
    return _category_from_module_path(entry[0])


def _lazy_entry_metadata(name: str) -> dict[str, Any]:
    module_path, attr_name, deps = _LAZY_IMPORTS[name]
    missing = _missing_dependencies(deps)
    return {
        'name': name,
        'module': module_path,
        'attribute': attr_name,
        'category': _lazy_category(name),
        'required_dependencies': list(deps),
        'missing_dependencies': missing,
        'available': not missing,
    }


def get_package_info() -> Dict[str, Any]:
    """Get comprehensive package information.

    Lazy public symbols are classified from the lazy-import registry without
    first resolving optional-dependency wrappers. Symbols whose declared
    dependencies are missing appear in ``unavailable_functions`` and
    ``optional_dependency_symbols`` with machine-readable dependency metadata.
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
        'optional_dependency_symbols': {},
        'categories': {category: [] for category in _CATEGORY_NAMES},
    }

    public_names = sorted(set(__all__) | set(_LAZY_IMPORTS))

    for name in public_names:
        if name.startswith('_'):
            continue
        if name in _LAZY_IMPORTS:
            metadata = _lazy_entry_metadata(name)
            if metadata['required_dependencies']:
                package_info['optional_dependency_symbols'][name] = metadata
            category = metadata['category']
            if metadata['missing_dependencies']:
                package_info['unavailable_functions'].append(name)
                continue
            try:
                obj = getattr(current_module, name)
            except ImportError as exc:
                metadata = dict(metadata)
                metadata['available'] = False
                metadata['missing_dependencies'] = metadata['missing_dependencies'] or list(metadata['required_dependencies'])
                metadata['error'] = str(exc)
                package_info['optional_dependency_symbols'][name] = metadata
                package_info['unavailable_functions'].append(name)
                package_info['failed_imports'].append({'name': name, 'error': str(exc)})
                continue
        else:
            try:
                obj = getattr(current_module, name)
            except AttributeError:
                continue
            category = _EAGER_CATEGORIES.get(name)

        if callable(obj) or _inspect.isclass(obj):
            package_info['available_functions'].append(name)
            package_info['total_functions'] += 1
            if category:
                package_info['categories'][category].append(name)
        elif _inspect.ismodule(obj):
            package_info['available_modules'].append(name)

    package_info['total_modules'] = len(package_info['available_modules'])
    package_info['available_functions'].sort()
    package_info['unavailable_functions'].sort()
    package_info['available_modules'].sort()
    package_info['failed_imports'].sort(key=lambda item: item['name'])
    package_info['optional_dependency_symbols'] = {
        name: package_info['optional_dependency_symbols'][name]
        for name in sorted(package_info['optional_dependency_symbols'])
    }
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
