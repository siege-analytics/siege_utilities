"""
Backward-compatibility tests for siege_utilities public API.

Written BEFORE lazy import conversion (su#183) as the regression gate.
Ensures that all critical names remain importable from the top-level
package and that dir() is complete.

These tests verify import semantics, not runtime behavior — they confirm
that `from siege_utilities import X` still works after the __init__.py
rewrites.
"""

import pytest


# ---------- Critical names that MUST remain importable ----------
# Grouped by subsystem for readability

CORE_NAMES = [
    # Logging
    'log_info', 'log_warning', 'log_error', 'log_debug', 'log_critical',
    'init_logger', 'get_logger', 'configure_shared_logging',
    # String utils
    'remove_wrapping_quotes_and_trim',
    # Settings
    'settings',
]

FILE_NAMES = [
    'check_if_file_exists_at_path', 'file_exists', 'touch_file', 'count_lines',
    'copy_file', 'move_file', 'get_file_size', 'list_directory', 'run_command',
    'remove_tree', 'delete_existing_file_and_replace_it_with_an_empty_file',
    'calculate_file_hash', 'generate_sha256_hash_for_file', 'get_file_hash',
    'get_quick_file_signature', 'verify_file_integrity',
    'ensure_path_exists', 'unzip_file_to_directory', 'get_file_extension',
    'get_file_name_without_extension', 'is_hidden_file', 'normalize_path',
    'get_relative_path', 'create_backup_path', 'find_files_by_pattern',
    'generate_local_path_from_url', 'download_file', 'download_file_with_retry',
    'get_file_info', 'is_downloadable', 'run_subprocess',
]

CONFIG_NAMES = [
    'create_database_config', 'save_database_config', 'load_database_config',
    'get_spark_database_options', 'test_database_connection', 'list_database_configs',
    'create_spark_session_with_databases',
    'create_project_config', 'save_project_config', 'load_project_config',
    'setup_project_directories', 'get_project_path', 'list_projects', 'update_project_config',
    'create_directory_structure', 'create_standard_project_structure',
    'save_directory_config', 'load_directory_config', 'ensure_directories_exist',
    'get_directory_info', 'clean_empty_directories', 'list_directory_configs',
    'create_client_profile', 'save_client_profile', 'load_client_profile',
    'update_client_profile', 'search_client_profiles',
    'associate_client_with_project', 'get_client_project_associations', 'validate_client_profile',
    'create_connection_profile', 'save_connection_profile', 'load_connection_profile',
    'find_connection_by_name', 'list_connection_profiles', 'update_connection_profile',
    'verify_connection_profile', 'get_connection_status', 'cleanup_old_connections',
]

GEO_NAMES = [
    'get_census_intelligence', 'quick_census_selection',
    'concatenate_addresses', 'use_nominatim_geocoder',
    'get_country_name', 'get_country_code', 'list_countries', 'get_coordinates',
    'get_census_data_selector', 'select_census_datasets', 'get_analysis_approach',
    'select_datasets_for_analysis', 'get_dataset_compatibility_matrix', 'suggest_analysis_approach',
    'get_census_dataset_mapper', 'get_best_dataset_for_analysis', 'compare_census_datasets',
    'get_census_data', 'get_census_boundaries', 'download_osm_data',
    'get_available_years', 'get_year_directory_contents', 'discover_boundary_types',
    'construct_download_url', 'validate_download_url', 'get_optimal_year',
    'download_data', 'get_geographic_boundaries', 'get_available_boundary_types',
    'refresh_discovery_cache', 'get_available_state_fips', 'get_state_abbreviations',
    'get_comprehensive_state_info', 'get_state_by_abbreviation', 'get_state_by_name',
    'validate_state_fips', 'get_state_name', 'get_state_abbreviation', 'download_dataset',
    'get_unified_fips_data', 'normalize_state_identifier',
    'normalize_state_input', 'normalize_state_name', 'normalize_state_abbreviation',
    'normalize_fips_code',
]

PYDANTIC_CONFIG_NAMES = [
    'UserConfigManager', 'UserProfile', 'get_user_config', 'get_download_directory',
    'SiegeConfig', 'load_user_profile', 'save_user_profile',
    'export_config_yaml', 'import_config_yaml',
    'get_default_profile_location', 'set_profile_location',
    'get_profile_location', 'list_profile_locations',
    'migrate_profiles', 'create_default_profiles',
    'validate_profile_location', 'get_profile_summary',
]

REPORTING_NAMES = [
    'BaseReportTemplate', 'ReportGenerator', 'ChartGenerator',
    'ClientBrandingManager', 'AnalyticsReportGenerator', 'PowerPointGenerator',
    'get_report_output_directory', 'create_report_generator', 'create_powerpoint_generator',
    'export_branding_config', 'import_branding_config', 'export_chart_type_config',
    'create_bar_chart', 'create_line_chart', 'create_pie_chart', 'create_scatter_plot',
    'create_heatmap', 'create_choropleth_map', 'create_bivariate_choropleth',
    'create_marker_map', 'create_flow_map', 'create_dashboard',
    'create_dataframe_summary_charts', 'generate_chart_from_dataframe',
]

ANALYTICS_NAMES = [
    'GoogleAnalyticsConnector', 'create_ga_account_profile', 'save_ga_account_profile',
    'load_ga_account_profile', 'list_ga_accounts_for_client', 'batch_retrieve_ga_data',
    'FacebookBusinessConnector', 'create_facebook_account_profile', 'save_facebook_account_profile',
    'load_facebook_account_profile', 'list_facebook_accounts_for_client', 'batch_retrieve_facebook_data',
    'get_datadotworld_connector', 'search_datadotworld_datasets',
    'load_datadotworld_dataset', 'query_datadotworld_dataset',
    'search_datasets', 'list_datasets',
    'get_snowflake_connector', 'upload_to_snowflake',
    'download_from_snowflake', 'execute_snowflake_query',
]

DATABRICKS_NAMES = [
    'build_databricks_run_url', 'build_foreign_table_sql', 'build_jdbc_url',
    'build_lakebase_psql_command', 'build_pgpass_entry',
    'build_schema_and_table_sync_sql', 'ensure_secret_scope',
    'geopandas_to_spark', 'get_active_spark_session', 'get_dbutils',
    'get_runtime_secret', 'get_workspace_client', 'pandas_to_spark',
    'parse_conninfo', 'put_secret', 'runtime_secret_exists',
    'spark_to_geopandas', 'spark_to_pandas',
]

DATA_NAMES = [
    'load_sample_data', 'list_available_datasets', 'create_sample_dataset',
    'generate_synthetic_population', 'generate_synthetic_businesses',
    'generate_synthetic_housing', 'join_boundaries_and_data',
]

DISTRIBUTED_NAMES = [
    'get_row_count', 'repartition_and_cache', 'register_temp_table',
    'move_column_to_front_of_dataframe', 'write_df_to_parquet', 'read_parquet_to_df',
]

HYGIENE_NAMES = [
    'generate_docstring_template', 'analyze_function_signature',
    'categorize_function', 'process_python_file', 'find_python_files',
]

DEV_NAMES = [
    'generate_architecture_diagram', 'analyze_package_structure',
    'analyze_module', 'analyze_function', 'analyze_class',
]

GIT_NAMES = [
    'analyze_branch_status', 'generate_branch_report', 'get_commit_history',
    'categorize_commits', 'get_file_changes', 'get_file_stats',
    'create_feature_branch', 'switch_branch', 'merge_branch', 'rebase_branch',
    'stash_changes', 'apply_stash', 'clean_working_directory', 'reset_to_commit',
    'cherry_pick_commit', 'create_tag', 'push_branch', 'pull_branch',
    'get_repository_status', 'get_branch_info',
    'start_feature_workflow', 'validate_branch_naming',
]

TESTING_NAMES = [
    'setup_spark_environment', 'get_system_info', 'ensure_env_vars',
    'check_java_version', 'diagnose_environment', 'quick_environment_setup',
    'run_test_suite', 'get_test_report', 'run_comprehensive_test',
    'quick_smoke_test', 'build_pytest_command',
]

INTROSPECTION_NAMES = [
    '__version__', 'get_package_info', 'check_dependencies',
    'get_available_functions', 'get_function_help',
]

ALL_CRITICAL_NAMES = (
    CORE_NAMES + FILE_NAMES + CONFIG_NAMES + GEO_NAMES +
    PYDANTIC_CONFIG_NAMES + REPORTING_NAMES + ANALYTICS_NAMES +
    DATABRICKS_NAMES + DATA_NAMES + DISTRIBUTED_NAMES +
    HYGIENE_NAMES + DEV_NAMES + GIT_NAMES + TESTING_NAMES +
    INTROSPECTION_NAMES
)


class TestTopLevelImport:
    """Package must import and expose version."""

    def test_import_siege_utilities(self):
        import siege_utilities
        assert hasattr(siege_utilities, '__version__')

    def test_version_is_string(self):
        import siege_utilities
        assert isinstance(siege_utilities.__version__, str)

    def test_version_is_semver(self):
        import siege_utilities
        parts = siege_utilities.__version__.split('.')
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestDirCompleteness:
    """dir(siege_utilities) must contain all critical names."""

    def test_dir_contains_all_critical_names(self):
        import siege_utilities
        names = dir(siege_utilities)
        missing = [n for n in ALL_CRITICAL_NAMES if n not in names]
        assert not missing, f"Missing from dir(): {missing}"


class TestCoreImports:
    """Core functions must be importable and callable."""

    @pytest.mark.parametrize("name", CORE_NAMES)
    def test_core_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        if name != 'settings':
            assert callable(obj), f"{name} should be callable"

    @pytest.mark.parametrize("name", FILE_NAMES)
    def test_file_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable"

    @pytest.mark.parametrize("name", CONFIG_NAMES)
    def test_config_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable"


class TestGeoImports:
    """Geo functions must be importable (callable or dependency wrapper)."""

    @pytest.mark.parametrize("name", GEO_NAMES)
    def test_geo_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable (real or wrapper)"


class TestReportingImports:
    """Reporting functions must be importable (callable or dependency wrapper)."""

    @pytest.mark.parametrize("name", REPORTING_NAMES)
    def test_reporting_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable (real or wrapper)"


class TestAnalyticsImports:
    """Analytics functions must be importable (callable or dependency wrapper)."""

    @pytest.mark.parametrize("name", ANALYTICS_NAMES)
    def test_analytics_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable (real or wrapper)"


class TestDatabricksImports:
    """Databricks functions must be importable (callable or dependency wrapper)."""

    @pytest.mark.parametrize("name", DATABRICKS_NAMES)
    def test_databricks_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable (real or wrapper)"


class TestDistributedImports:
    """Distributed functions must be importable (callable or dependency wrapper)."""

    @pytest.mark.parametrize("name", DISTRIBUTED_NAMES)
    def test_distributed_name_accessible(self, name):
        import siege_utilities
        obj = getattr(siege_utilities, name)
        assert callable(obj), f"{name} should be callable (real or wrapper)"


class TestIntrospection:
    """Introspection functions must work."""

    def test_get_package_info(self):
        import siege_utilities
        info = siege_utilities.get_package_info()
        assert isinstance(info, dict)
        assert 'total_functions' in info
        assert info['total_functions'] > 0

    def test_check_dependencies(self):
        import siege_utilities
        deps = siege_utilities.check_dependencies()
        assert isinstance(deps, dict)

    def test_get_available_functions(self):
        import siege_utilities
        funcs = siege_utilities.get_available_functions()
        assert isinstance(funcs, dict)
