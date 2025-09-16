"""
Simple database configuration management for siege_utilities.
Handles database connection settings for Spark and other uses.
"""

import json
import pathlib
import logging
from typing import Dict, Any, Optional
import importlib
import sys
import inspect

logger = logging.getLogger(__name__)

# Helper function for graceful dependency failures
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

# Import core logging functions for package-level access
from .core.logging import (
    log_info, log_warning, log_error, log_debug, log_critical,
    init_logger, get_logger, configure_shared_logging
)

# Import core utility functions
from .core.string_utils import remove_wrapping_quotes_and_trim
from .files.operations import check_if_file_exists_at_path

# Import configuration functions
from .config.databases import (
    create_database_config, save_database_config, load_database_config,
    get_spark_database_options, test_database_connection, list_database_configs,
    create_spark_session_with_databases
)

from .config.projects import (
    create_project_config, save_project_config, load_project_config,
    setup_project_directories, get_project_path, list_projects, update_project_config
)

from .config.directories import (
    create_directory_structure, create_standard_project_structure,
    save_directory_config, load_directory_config, ensure_directories_exist,
    get_directory_info, clean_empty_directories, list_directory_configs
)

from .config.clients import (
    create_client_profile, save_client_profile, load_client_profile,
    update_client_profile, list_client_profiles, search_client_profiles,
    associate_client_with_project, get_client_project_associations, validate_client_profile
)

from .config.connections import (
    create_connection_profile, save_connection_profile, load_connection_profile,
    find_connection_by_name, list_connection_profiles, update_connection_profile,
    verify_connection_profile, get_connection_status, cleanup_old_connections
)

# Import distributed utilities
from .distributed.spark_utils import *
from .distributed.hdfs_config import *
from .distributed.hdfs_operations import *
from .distributed.hdfs_legacy import *

# Import file utilities
from .files.hashing import (
    calculate_file_hash, generate_sha256_hash_for_file, 
    get_file_hash, get_quick_file_signature, verify_file_integrity
)
from .files.paths import (
    ensure_path_exists, unzip_file_to_directory, get_file_extension,
    get_file_name_without_extension, is_hidden_file, normalize_path,
    get_relative_path, create_backup_path, find_files_by_pattern
)
from .files.operations import (
    file_exists, touch_file, count_lines, copy_file, move_file, 
    get_file_size, list_directory, run_command, remove_tree,
    delete_existing_file_and_replace_it_with_an_empty_file
)

# Import remote and shell utilities
from .files.remote import (
    generate_local_path_from_url, download_file, download_file_with_retry,
    get_file_info, is_downloadable
)
from .files.shell import (
    run_subprocess
)

# Import comprehensive Census functionality (the missing sophisticated functions!)
try:
    from .geo import get_census_intelligence, quick_census_selection
    from .geo.geocoding import concatenate_addresses, use_nominatim_geocoder
    
    # Census Data Selection Intelligence
    from .geo.census_data_selector import (
        get_census_data_selector, select_census_datasets, get_analysis_approach,
        select_datasets_for_analysis, get_dataset_compatibility_matrix, suggest_analysis_approach
    )
    
    # Census Dataset Mapping & Recommendations
    from .geo.census_dataset_mapper import (
        get_census_dataset_mapper, get_best_dataset_for_analysis, compare_census_datasets,
        get_dataset_info, list_datasets_by_type, list_datasets_by_geography,
        get_best_dataset_for_use_case, get_dataset_relationships, compare_datasets,
        get_data_selection_guide, export_dataset_catalog
    )
    
    # Spatial Data & Boundary Downloads
    from .geo.spatial_data import (
        get_census_data, get_census_boundaries, download_osm_data,
        get_available_years, get_year_directory_contents, discover_boundary_types,
        construct_download_url, validate_download_url, get_optimal_year,
        download_data, get_geographic_boundaries, get_available_boundary_types,
        refresh_discovery_cache, get_available_state_fips, get_state_abbreviations,
        get_comprehensive_state_info, get_state_by_abbreviation, get_state_by_name,
        validate_state_fips, get_state_name, get_state_abbreviation, download_dataset,
        get_unified_fips_data, normalize_state_identifier_standalone as normalize_state_identifier,
        normalize_state_input, normalize_state_name, normalize_state_abbreviation, normalize_fips_code
    )
    
except ImportError as e:
    logger.warning(f"Could not import geo utilities: {e}")
    
    # Basic geo functions
    get_census_intelligence = _create_dependency_wrapper('get_census_intelligence', ['pandas', 'geopandas'])
    quick_census_selection = _create_dependency_wrapper('quick_census_selection', ['pandas', 'geopandas'])
    concatenate_addresses = _create_dependency_wrapper('concatenate_addresses', ['geopy'])
    use_nominatim_geocoder = _create_dependency_wrapper('use_nominatim_geocoder', ['geopy'])
    
    # Census Data Selection Intelligence
    get_census_data_selector = _create_dependency_wrapper('get_census_data_selector', ['pandas', 'geopandas'])
    select_census_datasets = _create_dependency_wrapper('select_census_datasets', ['pandas', 'geopandas'])
    get_analysis_approach = _create_dependency_wrapper('get_analysis_approach', ['pandas', 'geopandas'])
    select_datasets_for_analysis = _create_dependency_wrapper('select_datasets_for_analysis', ['pandas', 'geopandas'])
    get_dataset_compatibility_matrix = _create_dependency_wrapper('get_dataset_compatibility_matrix', ['pandas', 'geopandas'])
    suggest_analysis_approach = _create_dependency_wrapper('suggest_analysis_approach', ['pandas', 'geopandas'])
    
    # Census Dataset Mapping & Recommendations
    get_census_dataset_mapper = _create_dependency_wrapper('get_census_dataset_mapper', ['pandas', 'geopandas'])
    get_best_dataset_for_analysis = _create_dependency_wrapper('get_best_dataset_for_analysis', ['pandas', 'geopandas'])
    compare_census_datasets = _create_dependency_wrapper('compare_census_datasets', ['pandas', 'geopandas'])
    get_dataset_info = _create_dependency_wrapper('get_dataset_info', ['pandas', 'geopandas'])
    list_datasets_by_type = _create_dependency_wrapper('list_datasets_by_type', ['pandas', 'geopandas'])
    list_datasets_by_geography = _create_dependency_wrapper('list_datasets_by_geography', ['pandas', 'geopandas'])
    get_best_dataset_for_use_case = _create_dependency_wrapper('get_best_dataset_for_use_case', ['pandas', 'geopandas'])
    get_dataset_relationships = _create_dependency_wrapper('get_dataset_relationships', ['pandas', 'geopandas'])
    compare_datasets = _create_dependency_wrapper('compare_datasets', ['pandas', 'geopandas'])
    get_data_selection_guide = _create_dependency_wrapper('get_data_selection_guide', ['pandas', 'geopandas'])
    export_dataset_catalog = _create_dependency_wrapper('export_dataset_catalog', ['pandas', 'geopandas'])
    
    # Spatial Data & Boundary Downloads
    get_census_data = _create_dependency_wrapper('get_census_data', ['pandas', 'geopandas'])
    get_census_boundaries = _create_dependency_wrapper('get_census_boundaries', ['pandas', 'geopandas'])
    download_osm_data = _create_dependency_wrapper('download_osm_data', ['pandas', 'geopandas', 'osmnx'])
    get_available_years = _create_dependency_wrapper('get_available_years', ['pandas', 'requests'])
    get_year_directory_contents = _create_dependency_wrapper('get_year_directory_contents', ['pandas', 'requests'])
    discover_boundary_types = _create_dependency_wrapper('discover_boundary_types', ['pandas', 'requests'])
    construct_download_url = _create_dependency_wrapper('construct_download_url', ['pandas'])
    validate_download_url = _create_dependency_wrapper('validate_download_url', ['requests'])
    get_optimal_year = _create_dependency_wrapper('get_optimal_year', ['pandas'])
    download_data = _create_dependency_wrapper('download_data', ['pandas', 'geopandas', 'requests'])
    get_geographic_boundaries = _create_dependency_wrapper('get_geographic_boundaries', ['pandas', 'geopandas'])
    get_available_boundary_types = _create_dependency_wrapper('get_available_boundary_types', ['pandas', 'requests'])
    refresh_discovery_cache = _create_dependency_wrapper('refresh_discovery_cache', ['pandas', 'requests'])
    get_available_state_fips = _create_dependency_wrapper('get_available_state_fips', ['pandas'])
    get_state_abbreviations = _create_dependency_wrapper('get_state_abbreviations', ['pandas'])
    get_comprehensive_state_info = _create_dependency_wrapper('get_comprehensive_state_info', ['pandas'])
    get_state_by_abbreviation = _create_dependency_wrapper('get_state_by_abbreviation', ['pandas'])
    get_state_by_name = _create_dependency_wrapper('get_state_by_name', ['pandas'])
    validate_state_fips = _create_dependency_wrapper('validate_state_fips', ['pandas'])
    get_state_name = _create_dependency_wrapper('get_state_name', ['pandas'])
    get_state_abbreviation = _create_dependency_wrapper('get_state_abbreviation', ['pandas'])
    download_dataset = _create_dependency_wrapper('download_dataset', ['pandas', 'geopandas', 'requests'])
    get_unified_fips_data = _create_dependency_wrapper('get_unified_fips_data', ['pandas'])
    normalize_state_identifier = _create_dependency_wrapper('normalize_state_identifier', ['pandas'])
    normalize_state_input = _create_dependency_wrapper('normalize_state_input', ['pandas'])
    normalize_state_name = _create_dependency_wrapper('normalize_state_name', ['pandas'])
    normalize_state_abbreviation = _create_dependency_wrapper('normalize_state_abbreviation', ['pandas'])
    normalize_fips_code = _create_dependency_wrapper('normalize_fips_code', ['pandas'])

# Spatial utilities are now consolidated in the geo module  
# All spatial functions are available through the geo module

# Import user configuration
from .config.user_config import (
    UserConfigManager, UserProfile, user_config,
    get_user_config, get_download_directory
)

# Enhanced config system with Pydantic validation
from .config.enhanced_config import (
    UserProfile as EnhancedUserProfile,
    ClientProfile,
    SiegeConfig,
    load_user_profile,
    save_user_profile,
    load_client_profile,
    save_client_profile,
    list_client_profiles,
    export_config_yaml,
    import_config_yaml,
)

# Admin utilities for profile management
from .admin.profile_manager import (
    get_default_profile_location,
    set_profile_location,
    get_profile_location,
    list_profile_locations,
    migrate_profiles,
    create_default_profiles,
    validate_profile_location,
    get_profile_summary
)

# Import hygiene utilities (expanded)
from .hygiene.generate_docstrings import (
    generate_docstring_template, analyze_function_signature, categorize_function,
    process_python_file, find_python_files
)

# Import development utilities (actual functions only)
from .development.architecture import (
    generate_architecture_diagram, analyze_package_structure, analyze_module,
    analyze_function, analyze_class
)

# Import git utilities (actual functions only)
from .git.branch_analyzer import analyze_branch_status, generate_branch_report
from .git.git_operations import (
    create_feature_branch, switch_branch, merge_branch, rebase_branch,
    stash_changes, apply_stash, clean_working_directory, reset_to_commit,
    cherry_pick_commit, create_tag, push_branch, pull_branch
)
from .git.git_status import get_repository_status, get_branch_info
from .git.git_workflow import start_feature_workflow, validate_branch_naming

# Import sample data utilities - made optional due to pandas dependency
try:
    from .data.sample_data import (
        load_sample_data, list_available_datasets, get_dataset_info,
        join_boundaries_and_data, create_sample_dataset,
        generate_synthetic_population, generate_synthetic_businesses, generate_synthetic_housing,
        SAMPLE_DATASETS, CENSUS_SAMPLES, SYNTHETIC_SAMPLES
    )
except ImportError as e:
    logger.warning(f"Could not import sample data utilities: {e}")
    # Create helpful wrapper functions instead of None
    load_sample_data = _create_dependency_wrapper('load_sample_data', ['pandas'])
    list_available_datasets = _create_dependency_wrapper('list_available_datasets', ['pandas'])
    get_dataset_info = _create_dependency_wrapper('get_dataset_info', ['pandas'])
    get_census_data = _create_dependency_wrapper('get_census_data', ['pandas'])
    join_boundaries_and_data = _create_dependency_wrapper('join_boundaries_and_data', ['pandas', 'geopandas'])
    create_sample_dataset = _create_dependency_wrapper('create_sample_dataset', ['pandas'])
    generate_synthetic_population = _create_dependency_wrapper('generate_synthetic_population', ['pandas', 'faker'])
    generate_synthetic_businesses = _create_dependency_wrapper('generate_synthetic_businesses', ['pandas', 'faker'])
    generate_synthetic_housing = _create_dependency_wrapper('generate_synthetic_housing', ['pandas', 'faker'])
    SAMPLE_DATASETS = {}
    CENSUS_SAMPLES = {}
    SYNTHETIC_SAMPLES = {}

# Import analytics utilities - made optional due to pandas dependency
try:
    from .analytics.google_analytics import (
        GoogleAnalyticsConnector, create_ga_account_profile, save_ga_account_profile,
        load_ga_account_profile, list_ga_accounts_for_client, batch_retrieve_ga_data
    )
except ImportError as e:
    logger.warning(f"Could not import Google Analytics utilities: {e}")
    GoogleAnalyticsConnector = _create_dependency_wrapper('GoogleAnalyticsConnector', ['pandas', 'google-analytics-data'])
    create_ga_account_profile = _create_dependency_wrapper('create_ga_account_profile', ['pandas', 'google-analytics-data'])
    save_ga_account_profile = _create_dependency_wrapper('save_ga_account_profile', ['pandas', 'google-analytics-data'])
    load_ga_account_profile = _create_dependency_wrapper('load_ga_account_profile', ['pandas', 'google-analytics-data'])
    list_ga_accounts_for_client = _create_dependency_wrapper('list_ga_accounts_for_client', ['pandas', 'google-analytics-data'])
    batch_retrieve_ga_data = _create_dependency_wrapper('batch_retrieve_ga_data', ['pandas', 'google-analytics-data'])

# Import additional analytics utilities
try:
    from .analytics.datadotworld_connector import (
        get_datadotworld_connector, search_datadotworld_datasets, load_datadotworld_dataset,
        query_datadotworld_dataset, search_datasets, list_datasets, get_dataset_metadata,
        download_dataset, upload_dataset, create_dataset
    )
    from .analytics.snowflake_connector import (
        get_snowflake_connector, upload_to_snowflake, download_from_snowflake,
        execute_snowflake_query, connect, disconnect, list_tables, get_table_schema
    )
except ImportError as e:
    logger.warning(f"Could not import additional analytics utilities: {e}")
    # Data.world functions
    get_datadotworld_connector = _create_dependency_wrapper('get_datadotworld_connector', ['pandas', 'datadotworld'])
    search_datadotworld_datasets = _create_dependency_wrapper('search_datadotworld_datasets', ['pandas', 'datadotworld'])
    load_datadotworld_dataset = _create_dependency_wrapper('load_datadotworld_dataset', ['pandas', 'datadotworld'])
    query_datadotworld_dataset = _create_dependency_wrapper('query_datadotworld_dataset', ['pandas', 'datadotworld'])
    search_datasets = _create_dependency_wrapper('search_datasets', ['pandas', 'datadotworld'])
    list_datasets = _create_dependency_wrapper('list_datasets', ['pandas', 'datadotworld'])
    get_dataset_metadata = _create_dependency_wrapper('get_dataset_metadata', ['pandas', 'datadotworld'])
    download_dataset = _create_dependency_wrapper('download_dataset', ['pandas', 'datadotworld'])
    upload_dataset = _create_dependency_wrapper('upload_dataset', ['pandas', 'datadotworld'])
    create_dataset = _create_dependency_wrapper('create_dataset', ['pandas', 'datadotworld'])
    # Snowflake functions
    get_snowflake_connector = _create_dependency_wrapper('get_snowflake_connector', ['pandas', 'snowflake-connector-python'])
    upload_to_snowflake = _create_dependency_wrapper('upload_to_snowflake', ['pandas', 'snowflake-connector-python'])
    download_from_snowflake = _create_dependency_wrapper('download_from_snowflake', ['pandas', 'snowflake-connector-python'])
    execute_snowflake_query = _create_dependency_wrapper('execute_snowflake_query', ['pandas', 'snowflake-connector-python'])
    connect = _create_dependency_wrapper('connect', ['snowflake-connector-python'])
    disconnect = _create_dependency_wrapper('disconnect', ['snowflake-connector-python'])
    list_tables = _create_dependency_wrapper('list_tables', ['pandas', 'snowflake-connector-python'])
    get_table_schema = _create_dependency_wrapper('get_table_schema', ['pandas', 'snowflake-connector-python'])

try:
    from .analytics.facebook_business import (
        FacebookBusinessConnector, create_facebook_account_profile, save_facebook_account_profile,
        load_facebook_account_profile, list_facebook_accounts_for_client, batch_retrieve_facebook_data
    )
except ImportError as e:
    logger.warning(f"Could not import Facebook Business utilities: {e}")
    FacebookBusinessConnector = _create_dependency_wrapper('FacebookBusinessConnector', ['pandas', 'facebook-business'])
    create_facebook_account_profile = _create_dependency_wrapper('create_facebook_account_profile', ['pandas', 'facebook-business'])
    save_facebook_account_profile = _create_dependency_wrapper('save_facebook_account_profile', ['pandas', 'facebook-business'])
    load_facebook_account_profile = _create_dependency_wrapper('load_facebook_account_profile', ['pandas', 'facebook-business'])
    list_facebook_accounts_for_client = _create_dependency_wrapper('list_facebook_accounts_for_client', ['pandas', 'facebook-business'])
    batch_retrieve_facebook_data = _create_dependency_wrapper('batch_retrieve_facebook_data', ['pandas', 'facebook-business'])

# Import reporting utilities - made optional due to dependencies
try:
    from .reporting import (
        BaseReportTemplate, ReportGenerator, ChartGenerator, 
        ClientBrandingManager, AnalyticsReportGenerator, PowerPointGenerator,
        get_report_output_directory, create_report_generator, create_powerpoint_generator,
        export_branding_config, import_branding_config, export_chart_type_config
    )
    # Import branding export functions
    from .reporting.client_branding import ClientBrandingManager
    from .reporting.chart_types import ChartTypeRegistry
except ImportError as e:
    logger.warning(f"Could not import reporting utilities: {e}")
    BaseReportTemplate = _create_dependency_wrapper('BaseReportTemplate', ['requests', 'jinja2'])
    ReportGenerator = _create_dependency_wrapper('ReportGenerator', ['requests', 'jinja2'])
    ChartGenerator = _create_dependency_wrapper('ChartGenerator', ['pandas', 'matplotlib', 'seaborn'])
    ClientBrandingManager = _create_dependency_wrapper('ClientBrandingManager', ['requests', 'pillow'])
    AnalyticsReportGenerator = _create_dependency_wrapper('AnalyticsReportGenerator', ['pandas', 'matplotlib'])
    PowerPointGenerator = _create_dependency_wrapper('PowerPointGenerator', ['python-pptx', 'pandas'])
    get_report_output_directory = _create_dependency_wrapper('get_report_output_directory', ['requests', 'jinja2'])
    create_report_generator = _create_dependency_wrapper('create_report_generator', ['requests', 'jinja2'])
    create_powerpoint_generator = _create_dependency_wrapper('create_powerpoint_generator', ['python-pptx'])
    export_branding_config = _create_dependency_wrapper('export_branding_config', ['requests', 'jinja2'])
    import_branding_config = _create_dependency_wrapper('import_branding_config', ['requests', 'jinja2'])
    export_chart_type_config = _create_dependency_wrapper('export_chart_type_config', ['requests', 'jinja2'])

# Import chart generation functions specifically (high value!)
try:
    from .reporting.chart_generator import (
        create_bar_chart, create_line_chart, create_pie_chart, create_scatter_plot,
        create_heatmap, create_choropleth_map, create_bivariate_choropleth,
        create_marker_map, create_flow_map, create_dashboard,
        create_dataframe_summary_charts, generate_chart_from_dataframe
    )
except ImportError as e:
    logger.warning(f"Could not import chart generation functions: {e}")
    create_bar_chart = _create_dependency_wrapper('create_bar_chart', ['matplotlib', 'seaborn', 'pandas'])
    create_line_chart = _create_dependency_wrapper('create_line_chart', ['matplotlib', 'seaborn', 'pandas'])
    create_pie_chart = _create_dependency_wrapper('create_pie_chart', ['matplotlib', 'seaborn', 'pandas'])
    create_scatter_plot = _create_dependency_wrapper('create_scatter_plot', ['matplotlib', 'seaborn', 'pandas'])
    create_heatmap = _create_dependency_wrapper('create_heatmap', ['matplotlib', 'seaborn', 'pandas'])
    create_choropleth_map = _create_dependency_wrapper('create_choropleth_map', ['folium', 'geopandas', 'pandas'])
    create_bivariate_choropleth = _create_dependency_wrapper('create_bivariate_choropleth', ['matplotlib', 'geopandas', 'pandas'])
    create_marker_map = _create_dependency_wrapper('create_marker_map', ['folium', 'pandas'])
    create_flow_map = _create_dependency_wrapper('create_flow_map', ['folium', 'pandas'])
    create_dashboard = _create_dependency_wrapper('create_dashboard', ['matplotlib', 'seaborn', 'pandas'])
    create_dataframe_summary_charts = _create_dependency_wrapper('create_dataframe_summary_charts', ['matplotlib', 'seaborn', 'pandas'])
    generate_chart_from_dataframe = _create_dependency_wrapper('generate_chart_from_dataframe', ['matplotlib', 'seaborn', 'pandas'])

# Import testing utilities
from .testing.environment import setup_spark_environment, get_system_info

# Package version and metadata
__version__ = "1.0.0"
__author__ = "Siege Analytics"
__description__ = "Comprehensive utilities for data engineering, analytics, and distributed computing"

# Package discovery and dependency checking - NOW WITH DYNAMIC DISCOVERY!
def get_package_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the siege_utilities package.
    Uses DYNAMIC discovery to report only actually available functions (no more lies!).
    
    Returns:
        Dictionary containing package information, available functions, and module status
    """
    current_module = sys.modules[__name__]
    
    package_info = {
        'package_name': 'siege_utilities',
        'version': '1.0.0',
        'description': 'Comprehensive utilities for data engineering, analytics, and distributed computing',
        'total_functions': 0,
        'total_modules': 0,
        'available_functions': [],
        'available_modules': [],
        'unavailable_functions': [],
        'failed_imports': [],
        'subpackages': [],
        'categories': {
            'core': [],
            'files': [],
            'distributed': [],
            'geo': [],
            'config': [],
            'admin': [],
            'hygiene': [],
            'testing': [],
            'data': [],
            'analytics': [],
            'reporting': [],
            'git': [],
            'development': []
        }
    }
    
    # Function name to category mapping (for organization)
    function_categories = {
        # Core functions
        'log_info': 'core', 'log_warning': 'core', 'log_error': 'core', 'log_debug': 'core', 'log_critical': 'core',
        'init_logger': 'core', 'get_logger': 'core', 'configure_shared_logging': 'core',
        'remove_wrapping_quotes_and_trim': 'core',
        
        # File functions
        'check_if_file_exists_at_path': 'files', 'calculate_file_hash': 'files', 'ensure_path_exists': 'files',
        'generate_sha256_hash_for_file': 'files', 'get_file_hash': 'files', 'get_quick_file_signature': 'files',
        'verify_file_integrity': 'files', 'unzip_file_to_directory': 'files',
        'file_exists': 'files', 'touch_file': 'files', 'count_lines': 'files',
        'copy_file': 'files', 'move_file': 'files', 'get_file_size': 'files', 'list_directory': 'files',
        'run_command': 'files', 'remove_tree': 'files',
        'generate_local_path_from_url': 'files', 'download_file': 'files', 'download_file_with_retry': 'files',
        'get_file_info': 'files', 'is_downloadable': 'files', 'run_subprocess': 'files',
        
        # Distributed functions  
        'get_row_count': 'distributed', 'repartition_and_cache': 'distributed',
        'register_temp_table': 'distributed', 'move_column_to_front_of_dataframe': 'distributed',
        'write_df_to_parquet': 'distributed', 'read_parquet_to_df': 'distributed',
        
        # Config functions
        'create_database_config': 'config', 'save_database_config': 'config', 'load_database_config': 'config',
        'get_spark_database_options': 'config', 'test_database_connection': 'config', 'list_database_configs': 'config',
        'create_spark_session_with_databases': 'config',
        'create_project_config': 'config', 'save_project_config': 'config', 'load_project_config': 'config',
        'setup_project_directories': 'config', 'get_project_path': 'config', 'list_projects': 'config', 'update_project_config': 'config',
        'create_directory_structure': 'config', 'create_standard_project_structure': 'config',
        'save_directory_config': 'config', 'load_directory_config': 'config', 'ensure_directories_exist': 'config',
        'get_directory_info': 'config', 'clean_empty_directories': 'config', 'list_directory_configs': 'config',
        'create_client_profile': 'config', 'save_client_profile': 'config', 'load_client_profile': 'config',
        'update_client_profile': 'config', 'list_client_profiles': 'config', 'search_client_profiles': 'config',
        'associate_client_with_project': 'config', 'get_client_project_associations': 'config', 'validate_client_profile': 'config',
        'create_connection_profile': 'config', 'save_connection_profile': 'config', 'load_connection_profile': 'config',
        'find_connection_by_name': 'config', 'list_connection_profiles': 'config', 'update_connection_profile': 'config',
        'verify_connection_profile': 'config', 'get_connection_status': 'config', 'cleanup_old_connections': 'config',
        'get_user_config': 'config', 'get_download_directory': 'config',
        'load_user_profile': 'config', 'save_user_profile': 'config',
        'load_client_profile': 'config', 'save_client_profile': 'config',
        'list_client_profiles': 'config', 'export_config_yaml': 'config',
        'import_config_yaml': 'config',
        
        # Admin functions
        'get_default_profile_location': 'admin', 'set_profile_location': 'admin',
        'get_profile_location': 'admin', 'list_profile_locations': 'admin',
        'migrate_profiles': 'admin', 'create_default_profiles': 'admin',
        'validate_profile_location': 'admin', 'get_profile_summary': 'admin',
        
        # Geo/Census functions (comprehensive!)
        'concatenate_addresses': 'geo', 'use_nominatim_geocoder': 'geo',
        'get_census_intelligence': 'geo', 'quick_census_selection': 'geo',
        
        # Census Data Selection Intelligence
        'get_census_data_selector': 'geo', 'select_census_datasets': 'geo', 'get_analysis_approach': 'geo',
        'select_datasets_for_analysis': 'geo', 'get_dataset_compatibility_matrix': 'geo', 'suggest_analysis_approach': 'geo',
        
        # Census Dataset Mapping & Recommendations
        'get_census_dataset_mapper': 'geo', 'get_best_dataset_for_analysis': 'geo', 'compare_census_datasets': 'geo',
        'get_dataset_info': 'geo', 'list_datasets_by_type': 'geo', 'list_datasets_by_geography': 'geo',
        'get_best_dataset_for_use_case': 'geo', 'get_dataset_relationships': 'geo', 'compare_datasets': 'geo',
        'get_data_selection_guide': 'geo', 'export_dataset_catalog': 'geo',
        
        # Spatial Data & Boundary Downloads
        'get_census_data': 'geo', 'get_census_boundaries': 'geo', 'download_osm_data': 'geo',
        'get_available_years': 'geo', 'get_year_directory_contents': 'geo', 'discover_boundary_types': 'geo',
        'construct_download_url': 'geo', 'validate_download_url': 'geo', 'get_optimal_year': 'geo',
        'download_data': 'geo', 'get_geographic_boundaries': 'geo', 'get_available_boundary_types': 'geo',
        'refresh_discovery_cache': 'geo', 'get_available_state_fips': 'geo', 'get_state_abbreviations': 'geo',
        'get_comprehensive_state_info': 'geo', 'get_state_by_abbreviation': 'geo', 'get_state_by_name': 'geo',
        'validate_state_fips': 'geo', 'get_state_name': 'geo', 'get_state_abbreviation': 'geo', 'download_dataset': 'geo',
        'get_unified_fips_data': 'geo', 'normalize_state_identifier': 'geo',
        
        # Hygiene functions
        'generate_docstring_template': 'hygiene', 'analyze_function_signature': 'hygiene',
        
        # Development functions
        'generate_architecture_diagram': 'development', 'analyze_package_structure': 'development',
        
        # Git functions
        'analyze_branch_status': 'git', 'generate_branch_report': 'git',
        'create_feature_branch': 'git', 'switch_branch': 'git', 'merge_branch': 'git',
        'get_repository_status': 'git', 'get_branch_info': 'git',
        'start_feature_workflow': 'git', 'validate_branch_naming': 'git',
        
        # Testing functions
        'setup_spark_environment': 'testing', 'get_system_info': 'testing',
        
        # Data functions
        'load_sample_data': 'data', 'list_available_datasets': 'data', 'get_dataset_info': 'data',
        'join_boundaries_and_data': 'data', 'create_sample_dataset': 'data',
        'generate_synthetic_population': 'data', 'generate_synthetic_businesses': 'data', 'generate_synthetic_housing': 'data',
        
        # Analytics functions
        'create_ga_account_profile': 'analytics', 'save_ga_account_profile': 'analytics',
        'load_ga_account_profile': 'analytics', 'list_ga_accounts_for_client': 'analytics', 'batch_retrieve_ga_data': 'analytics',
        'create_facebook_account_profile': 'analytics', 'save_facebook_account_profile': 'analytics',
        'load_facebook_account_profile': 'analytics', 'list_facebook_accounts_for_client': 'analytics', 'batch_retrieve_facebook_data': 'analytics',
        # Data.world functions
        'get_datadotworld_connector': 'analytics', 'search_datadotworld_datasets': 'analytics',
        'load_datadotworld_dataset': 'analytics', 'query_datadotworld_dataset': 'analytics',
        'search_datasets': 'analytics', 'list_datasets': 'analytics', 'get_dataset_metadata': 'analytics',
        'download_dataset': 'analytics', 'upload_dataset': 'analytics', 'create_dataset': 'analytics',
        # Snowflake functions
        'get_snowflake_connector': 'analytics', 'upload_to_snowflake': 'analytics',
        'download_from_snowflake': 'analytics', 'execute_snowflake_query': 'analytics',
        'connect': 'analytics', 'disconnect': 'analytics', 'list_tables': 'analytics', 'get_table_schema': 'analytics',
        
        # Reporting functions  
        'BaseReportTemplate': 'reporting', 'ReportGenerator': 'reporting', 'ChartGenerator': 'reporting',
        'ClientBrandingManager': 'reporting', 'AnalyticsReportGenerator': 'reporting', 'PowerPointGenerator': 'reporting',
        'get_report_output_directory': 'reporting', 'create_report_generator': 'reporting', 'create_powerpoint_generator': 'reporting',
        'export_branding_config': 'reporting', 'import_branding_config': 'reporting', 'export_chart_type_config': 'reporting',
        # Chart generation functions (high value!)
        'create_bar_chart': 'reporting', 'create_line_chart': 'reporting', 'create_pie_chart': 'reporting',
        'create_scatter_plot': 'reporting', 'create_heatmap': 'reporting', 'create_choropleth_map': 'reporting',
        'create_bivariate_choropleth': 'reporting', 'create_marker_map': 'reporting', 'create_flow_map': 'reporting',
        'create_dashboard': 'reporting', 'create_dataframe_summary_charts': 'reporting', 'generate_chart_from_dataframe': 'reporting'
    }
    
    # Dynamically discover what's actually available
    for name in dir(current_module):
        if not name.startswith('_') and name not in ['sys', 'json', 'pathlib', 'logging', 'importlib', 'inspect']:
            obj = getattr(current_module, name)
            
            # Check if this is a known function (in our category mapping)
            if name in function_categories:
                if obj is None:
                    package_info['unavailable_functions'].append(name)
                elif callable(obj) or inspect.isclass(obj):
                    package_info['available_functions'].append(name)
                    category = function_categories[name]
                    package_info['categories'][category].append(name)
                    package_info['total_functions'] += 1
            # Also include other callable objects not in our mapping
            elif callable(obj) or inspect.isclass(obj):
                package_info['available_functions'].append(name)
                package_info['total_functions'] += 1
    
    # Count modules
    package_info['total_modules'] = len([name for name in dir(current_module) if inspect.ismodule(getattr(current_module, name, None))])
    
    # Sort for consistent output
    package_info['available_functions'].sort()
    package_info['unavailable_functions'].sort()
    for category in package_info['categories']:
        package_info['categories'][category].sort()
    
    log_info(f"Package info generated: {package_info['total_functions']} available functions, {package_info['total_modules']} modules, {len(package_info['unavailable_functions'])} unavailable")
    return package_info


def check_dependencies() -> Dict[str, bool]:
    """
    Check the availability of optional dependencies.
    
    Returns:
        Dictionary mapping dependency names to availability status
    """
    dependencies = {
        'pandas': False,
        'numpy': False,
        'pyspark': False,
        'sqlalchemy': False,
        'psycopg2': False,
        'pymysql': False,
        'cx_oracle': False,
        'pyodbc': False,
        'requests': False,
        'geopy': False,
        'shapely': False,
        'folium': False,
        'geopandas': False,
        'duckdb': False,
        'fiona': False,
        'pyproj': False,
        'faker': False,
        'tqdm': False
    }
    
    for dep_name in dependencies.keys():
        try:
            importlib.import_module(dep_name)
            dependencies[dep_name] = True
        except ImportError:
            pass
    
    # Use builtins.sum to avoid conflict with PySpark's sum function
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
    package_info = get_package_info()
    return package_info['categories']


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
