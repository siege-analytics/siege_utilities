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

logger = logging.getLogger(__name__)

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
from .files.paths import ensure_path_exists, unzip_file_to_its_own_directory
from .files.operations import (
    check_if_file_exists_at_path, delete_existing_file_and_replace_it_with_an_empty_file,
    count_total_rows_in_file_pythonically, count_empty_rows_in_file_pythonically,
    count_duplicate_rows_in_file_using_awk, count_total_rows_in_file_using_sed,
    count_empty_rows_in_file_using_awk, remove_empty_rows_in_file_using_sed,
    write_data_to_a_new_empty_file, write_data_to_an_existing_file,
    check_for_file_type_in_directory
)

# Import remote and shell utilities
from .files.remote import (
    generate_local_path_from_url, download_file
)
from .files.shell import (
    run_subprocess
)

# Import geo utilities
from .geo.geocoding import concatenate_addresses, use_nominatim_geocoder

# Import hygiene utilities
from .hygiene.generate_docstrings import generate_docstring_template, analyze_function_signature

# Import development utilities
from .development.architecture import generate_architecture_diagram, analyze_package_structure

# Import git utilities
from .git.branch_analyzer import analyze_branch_status, generate_branch_report
from .git.git_operations import create_feature_branch, switch_branch, merge_branch
from .git.git_status import get_repository_status, get_branch_info
from .git.git_workflow import start_feature_workflow, validate_branch_naming

# Import analytics utilities
from .analytics.google_analytics import (
    GoogleAnalyticsConnector, create_ga_account_profile, save_ga_account_profile,
    load_ga_account_profile, list_ga_accounts_for_client, batch_retrieve_ga_data
)
from .analytics.facebook_business import (
    FacebookBusinessConnector, create_facebook_account_profile, save_facebook_account_profile,
    load_facebook_account_profile, list_facebook_accounts_for_client, batch_retrieve_facebook_data
)

# Import reporting utilities
from .reporting import (
    BaseReportTemplate, ReportGenerator, ChartGenerator, 
    ClientBrandingManager, AnalyticsReportGenerator, PowerPointGenerator
)

# Import testing utilities
from .testing.environment import setup_spark_environment, get_system_info

# Package version and metadata
__version__ = "1.0.0"
__author__ = "Siege Analytics"
__description__ = "Comprehensive utilities for data engineering, analytics, and distributed computing"

# Package discovery and dependency checking
def get_package_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the siege_utilities package.
    
    Returns:
        Dictionary containing package information, available functions, and module status
    """
    package_info = {
        'package_name': 'siege_utilities',
        'version': '1.0.0',
        'description': 'Comprehensive utilities for data engineering, analytics, and distributed computing',
        'total_functions': 0,
        'total_modules': 0,
        'available_functions': [],
        'available_modules': [],
        'failed_imports': {},
        'subpackages': ['core', 'files', 'distributed', 'geo', 'config', 'hygiene', 'testing'],
        'categories': {
            'core': [],
            'files': [],
            'distributed': [],
            'geo': [],
            'config': [],
            'hygiene': [],
            'testing': []
        }
    }
    
    # Core functions
    core_functions = [
        'log_info', 'log_warning', 'log_error', 'log_debug', 'log_critical',
        'init_logger', 'get_logger', 'configure_shared_logging',
        'remove_wrapping_quotes_and_trim'
    ]
    
    # File functions
    file_functions = [
        'check_if_file_exists_at_path', 'calculate_file_hash',
        'ensure_path_exists', 'unzip_file_to_its_own_directory',
        'generate_sha256_hash_for_file', 'get_file_hash', 'get_quick_file_signature',
        'verify_file_integrity', 'delete_existing_file_and_replace_it_with_an_empty_file',
        'count_total_rows_in_file_pythonically', 'count_empty_rows_in_file_pythonically',
        'count_duplicate_rows_in_file_using_awk', 'count_total_rows_in_file_using_sed',
        'count_empty_rows_in_file_using_awk', 'remove_empty_rows_in_file_using_sed',
        'write_data_to_a_new_empty_file', 'write_data_to_an_existing_file',
        'check_for_file_type_in_directory', 'generate_local_path_from_url',
        'download_file', 'run_subprocess'
    ]
    
    # Distributed functions
    distributed_functions = [
        'get_row_count', 'repartition_and_cache',
        'register_temp_table', 'move_column_to_front_of_dataframe',
        'write_df_to_parquet', 'read_parquet_to_df',
        'flatten_json_column_and_join_back_to_df', 'validate_geocode_data',
        'backup_full_dataframe', 'atomic_write_with_staging'
    ]
    
    # Config functions
    config_functions = [
        'create_database_config', 'save_database_config', 'load_database_config',
        'get_spark_database_options', 'test_database_connection', 'list_database_configs',
        'create_spark_session_with_databases',
        'create_project_config', 'save_project_config', 'load_project_config',
        'setup_project_directories', 'get_project_path', 'list_projects', 'update_project_config',
        'create_directory_structure', 'create_standard_project_structure',
        'save_directory_config', 'load_directory_config', 'ensure_directories_exist',
        'get_directory_info', 'clean_empty_directories', 'list_directory_configs',
        'create_client_profile', 'save_client_profile', 'load_client_profile',
        'update_client_profile', 'list_client_profiles', 'search_client_profiles',
        'associate_client_with_project', 'get_client_project_associations', 'validate_client_profile',
        'create_connection_profile', 'save_connection_profile', 'load_connection_profile',
        'find_connection_by_name', 'list_connection_profiles', 'update_connection_profile',
        'verify_connection_profile', 'get_connection_status', 'cleanup_old_connections'
    ]
    
    # Geo functions
    geo_functions = [
        'concatenate_addresses', 'use_nominatim_geocoder'
    ]
    
    # Hygiene functions
    hygiene_functions = [
        'generate_docstring_template', 'analyze_function_signature'
    ]
    
    # Testing functions
    testing_functions = [
        'setup_spark_environment', 'get_system_info'
    ]
    
    # Check availability of all functions
    all_functions = {
        'core': core_functions,
        'files': file_functions,
        'distributed': distributed_functions,
        'config': config_functions,
        'geo': geo_functions,
        'hygiene': hygiene_functions,
        'testing': testing_functions
    }
    
    for category, functions in all_functions.items():
        for func_name in functions:
            if hasattr(sys.modules[__name__], func_name):
                package_info['categories'][category].append(func_name)
                package_info['available_functions'].append(func_name)
                package_info['total_functions'] += 1
    
    # Count modules
    package_info['available_modules'] = [
        'core.logging', 'core.string_utils',
        'files.operations', 'files.hashing', 'files.paths', 'files.remote', 'files.shell',
        'distributed.spark_utils', 'distributed.hdfs_config', 'distributed.hdfs_operations',
        'geo.geocoding', 'config.databases', 'config.projects', 'config.directories',
        'hygiene.generate_docstrings'
    ]
    package_info['total_modules'] = len(package_info['available_modules'])
    
    log_info(f"Package info generated: {package_info['total_functions']} functions, {package_info['total_modules']} modules")
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
        'folium': False
    }
    
    # Check each dependency
    try:
        import pandas
        dependencies['pandas'] = True
    except ImportError:
        pass
    
    try:
        import numpy
        dependencies['numpy'] = True
    except ImportError:
        pass
    
    try:
        import pyspark
        dependencies['pyspark'] = True
    except ImportError:
        pass
    
    try:
        import sqlalchemy
        dependencies['sqlalchemy'] = True
    except ImportError:
        pass
    
    try:
        import psycopg2
        dependencies['psycopg2'] = True
    except ImportError:
        pass
    
    try:
        import pymysql
        dependencies['pymysql'] = True
    except ImportError:
        pass
    
    try:
        import cx_oracle
        dependencies['cx_oracle'] = True
    except ImportError:
        pass
    
    try:
        import pyodbc
        dependencies['pyodbc'] = True
    except ImportError:
        pass
    
    try:
        import requests
        dependencies['requests'] = True
    except ImportError:
        pass
    
    try:
        import geopy
        dependencies['geopy'] = True
    except ImportError:
        pass
    
    try:
        import shapely
        dependencies['shapely'] = True
    except ImportError:
        pass
    
    try:
        import folium
        dependencies['folium'] = True
    except ImportError:
        pass
    
    available_count = sum(dependencies.values())
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