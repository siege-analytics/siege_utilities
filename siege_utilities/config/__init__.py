"""
Configuration module for siege_utilities.
Centralized constants and configuration management.

All submodules load on first attribute access via PEP 562 __getattr__.
Pure-Python modules (constants, census_constants, nces_constants, paths) are
importable without optional dependencies. Pydantic-dependent modules
(user_config, enhanced_config, models) gracefully degrade with a helpful
ImportError when pydantic is not installed.
"""

import importlib
import logging as _logging
import sys

# Re-export settings singleton eagerly — it is lightweight and pervasive.
from siege_utilities.conf import settings  # noqa: F401

_config_logger = _logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-import registry
# ---------------------------------------------------------------------------

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- constants.py ---
_register([
    # Library metadata
    'LIBRARY_NAME', 'LIBRARY_VERSION', 'LIBRARY_AUTHOR', 'LIBRARY_URL',
    # Network and timeout constants
    'DEFAULT_TIMEOUT', 'LONG_TIMEOUT', 'EXTENDED_TIMEOUT', 'CACHE_TIMEOUT',
    'DEFAULT_CHUNK_SIZE', 'MAX_RETRY_ATTEMPTS', 'RETRY_DELAY',
    # File system constants
    'SIEGE_UTILITIES_HOME', 'SIEGE_CACHE_DIR', 'SIEGE_OUTPUT_DIR',
    'SMALL_FILE_THRESHOLD', 'LARGE_FILE_THRESHOLD',
    'SUPPORTED_FILE_FORMATS', 'SUPPORTED_IMAGE_FORMATS',
    # Visualization constants
    'DEFAULT_CHART_WIDTH', 'DEFAULT_CHART_HEIGHT',
    'WIDE_CHART_WIDTH', 'WIDE_CHART_HEIGHT',
    'PRESENTATION_CHART_WIDTH', 'PRESENTATION_CHART_HEIGHT',
    'DEFAULT_DPI', 'DEFAULT_FONT_SIZE', 'HEADER_FONT_SIZE', 'TITLE_FONT_SIZE',
    'DEFAULT_COLOR_SCHEME', 'DEFAULT_COLOR_PALETTE',
    'DEFAULT_MAP_ZOOM', 'DEFAULT_MARKER_SIZE', 'DEFAULT_POPUP_WIDTH',
    'DEFAULT_CLUSTER_RADIUS',
    # Database constants
    'DB_CONNECTION_TIMEOUT', 'DB_QUERY_TIMEOUT', 'DB_CLEANUP_DAYS',
    'MAX_CONNECTIONS', 'CONNECTION_RETRY_ATTEMPTS',
    # Data processing constants
    'DEFAULT_ROW_LIMIT', 'DEFAULT_PAGE_SIZE', 'MAX_RESULTS_LIMIT',
    'DEFAULT_SPARK_PARTITIONS', 'SPARK_DRIVER_MEMORY', 'SPARK_EXECUTOR_MEMORY',
    # Testing constants
    'TEST_TIMEOUT', 'MAX_TEST_FAILURES', 'MIN_COVERAGE_THRESHOLD',
    'LOG_MAX_BYTES', 'LOG_BACKUP_COUNT',
    # API and service constants
    'API_RATE_LIMIT', 'API_BURST_LIMIT', 'DEFAULT_BATCH_SIZE', 'MAX_BATCH_SIZE',
    'SERVICE_TIMEOUTS', 'SERVICE_ROW_LIMITS',
    # Helper functions
    'get_timeout', 'get_chart_dimensions', 'get_file_path',
    'get_service_timeout', 'get_service_row_limit',
], '.constants')

# --- census_constants.py ---
_register([
    # URLs
    'CENSUS_BASE_URL', 'CENSUS_API_BASE_URL', 'CENSUS_FTP_BASE_URL',
    # Geographic levels
    'CANONICAL_GEOGRAPHIC_LEVELS', 'resolve_geographic_level',
    'GEOGRAPHIC_LEVELS', 'GEOGRAPHIC_HIERARCHY',
    # Dataset types
    'DATASET_TYPES', 'RELIABILITY_LEVELS',
    # FIPS codes and mappings
    'STATE_FIPS_CODES', 'STATEFIPS_LOOKUP_DICT', 'FIPS_TO_STATE', 'STATE_NAMES',
    # Years and availability
    'AVAILABLE_CENSUS_YEARS', 'DEFAULT_CENSUS_YEAR', 'DECENNIAL_YEARS',
    'ACS_AVAILABLE_YEARS', 'ACS5_AVAILABLE_YEARS', 'BOUNDARY_CHANGE_YEARS',
    # File patterns
    'TIGER_FILE_PATTERNS',
    # Operation settings
    'CENSUS_CACHE_TIMEOUT', 'CENSUS_MAX_CACHE_SIZE',
    'CENSUS_TIMEOUT', 'CENSUS_RETRY_ATTEMPTS',
    # API-specific settings
    'CENSUS_API_CACHE_TIMEOUT', 'CENSUS_API_DEFAULT_TIMEOUT',
    'CENSUS_API_RATE_LIMIT_RETRY_DELAY',
    # Helper functions
    'normalize_state_identifier', 'get_tiger_url',
    'validate_geographic_level', 'get_fips_info',
    # Canonical enum types
    'SurveyType', 'DataReliability', 'GeographyLevel',
    # Variable groups and descriptions
    'VARIABLE_GROUPS', 'VARIABLE_DESCRIPTIONS',
], '.census_constants')

# --- nces_constants.py ---
_register([
    # URLs
    'NCES_BASE_URL', 'NCES_GEOGRAPHIC_URL', 'NCES_LOCALE_BOUNDARIES_URL',
    'NCES_DOWNLOAD_ENDPOINTS',
    # Locale classification
    'LOCALE_CATEGORIES', 'LOCALE_SUBCATEGORIES',
    'LOCALE_NUMERIC_CODES', 'LOCALE_CODE_TO_NUMERIC',
    # Urbanicity definitions
    'POPULATION_THRESHOLDS', 'DISTANCE_THRESHOLDS',
    # File patterns and formats
    'NCES_FILE_PATTERNS', 'NCES_SUPPORTED_FORMATS',
    # Years and availability
    'AVAILABLE_NCES_YEARS', 'DEFAULT_NCES_YEAR',
    # Calculation settings
    'URBANICITY_SETTINGS', 'CENSUS_NCES_JOIN_FIELDS',
    # Helper functions
    'get_locale_category', 'get_locale_subcategory', 'classify_urbanicity',
    'get_nces_download_url', 'validate_locale_code', 'get_urbanicity_info',
], '.nces_constants')

# --- paths.py ---
# Most path names are registered directly; three are aliased below to avoid
# conflicts with constants.py names (SIEGE_UTILITIES_HOME, SIEGE_CACHE_DIR,
# SIEGE_OUTPUT_DIR).
_register([
    'SIEGE_UTILITIES_TEST', 'SIEGE_ANALYTICS_ROOT',
    'GEOCODING_PROJECT', 'MASAI_PROJECT',
    # Cache and temp directories
    'SPARK_CACHE_DIR', 'TEMP_DIR', 'DOWNLOAD_TEMP_DIR', 'PROCESSING_TEMP_DIR',
    # Output directories
    'REPORTS_OUTPUT_DIR', 'CHARTS_OUTPUT_DIR', 'MAPS_OUTPUT_DIR',
    # Data directories
    'DATA_DIR', 'CENSUS_DATA_DIR', 'NCES_DATA_DIR', 'SAMPLE_DATA_DIR',
    # Configuration directories
    'CONFIG_DIR', 'USER_CONFIG_FILE', 'DATABASE_CONFIG_DIR',
    # Log directories
    'LOG_DIR', 'ERROR_LOG_DIR', 'DEBUG_LOG_DIR',
    # Backup directories
    'BACKUP_DIR', 'CONFIG_BACKUP_DIR', 'DATA_BACKUP_DIR',
    # Standard structure
    'STANDARD_SUBDIRS', 'FILE_EXTENSIONS',
    # Helper functions
    'ensure_directory_exists', 'get_project_path', 'get_cache_path',
    'get_output_path', 'get_data_path', 'setup_standard_directories',
    'get_file_type', 'get_relative_to_home', 'initialize_siege_directories',
], '.paths')

# --- databases.py ---
_register([
    'create_database_config', 'save_database_config',
    'load_database_config', 'list_database_configs',
    'test_database_connection',
], '.databases')

# --- connections.py ---
_register([
    'cleanup_old_connections', 'get_connection_status',
], '.connections')

# --- credential_manager.py ---
_register([
    'get_google_service_account_from_1password',
    'get_google_oauth_from_1password',
    'create_temporary_service_account_file',
    'CredentialManager', 'CredentialNotFoundError',
    'get_credential', 'store_credential',
    'store_ga_credentials_from_file', 'get_ga_credentials',
    'credential_status',
    'store_ga_service_account_from_file',
    'get_ga_service_account_credentials',
], '.credential_manager')

# --- Pydantic-dependent modules (optional) ---
# These are registered in _LAZY_IMPORTS like any other name. The __getattr__
# function catches ImportError and falls back to dependency wrappers.
_register([
    'UserProfile', 'UserConfigManager',
    'get_user_config', 'get_download_directory',
], '.user_config')

_register([
    'SiegeConfig',
    'load_user_profile', 'save_user_profile',
    'load_client_profile', 'save_client_profile',
    'list_client_profiles',
    'export_config_yaml', 'import_config_yaml',
], '.enhanced_config')

_register([
    'ContactInfo', 'BrandingConfig', 'ReportPreferences', 'SocialMediaAccount',
], '.models')

_register(['Person'], '.models.person')

_register([
    'User', 'Client', 'Collaborator', 'Organization', 'Collaboration',
], '.models.actor_types')

_register([
    'Credential', 'OnePasswordCredential',
], '.models.credential')

_register([
    'OAuthIntegration', 'OAuthScope',
], '.models.oauth_integration')

_register(['DatabaseConnection'], '.models.database_connection')

_register([
    'JurisdictionLevel', 'Jurisdiction',
    'DataSourceType', 'DataSourceStatus',
    'DataSource', 'SourceCredential',
], '.models.data_sources')

_register(['DataSourceRegistry'], '.data_source_registry')
_register(['GoogleAccountRegistry'], '.google_account_registry')

_register([
    'ConfigurationMigrator', 'migrate_configurations', 'backup_and_migrate',
], '.migration')

_register(['HydraConfigManager'], '.hydra_manager')

# ---------------------------------------------------------------------------
# Aliases — names whose public attribute differs from the source attribute
# ---------------------------------------------------------------------------

_ALIASES = {
    # paths.py names that conflict with constants.py names
    'PATH_SIEGE_UTILITIES_HOME': ('.paths', 'SIEGE_UTILITIES_HOME'),
    'PATH_SIEGE_CACHE_DIR': ('.paths', 'SIEGE_CACHE_DIR'),
    'PATH_SIEGE_OUTPUT_DIR': ('.paths', 'SIEGE_OUTPUT_DIR'),
    # enhanced_config re-exports UserProfile under a different name
    'EnhancedUserProfile': ('.enhanced_config', 'UserProfile'),
    'ClientProfile': ('.enhanced_config', 'ClientProfile'),
    # models re-exports under prefixed names to avoid collision
    'PydanticUserProfile': ('.models', 'UserProfile'),
    'PydanticClientProfile': ('.models', 'ClientProfile'),
}

# ---------------------------------------------------------------------------
# Modules whose ImportError should produce a helpful wrapper, not a raw error
# ---------------------------------------------------------------------------

_PYDANTIC_MODULES = frozenset({
    '.user_config', '.enhanced_config', '.models', '.models.person',
    '.models.actor_types', '.models.credential', '.models.oauth_integration',
    '.models.database_connection', '.models.data_sources',
    '.data_source_registry', '.google_account_registry', '.migration',
})

_HYDRA_MODULES = frozenset({'.hydra_manager'})


def _config_dependency_wrapper(func_name, required_deps):
    """Create a callable that raises ImportError with a helpful message."""
    def wrapper(*args, **kwargs):
        raise ImportError(
            f"Function '{func_name}' requires: {', '.join(required_deps)}. "
            f"Install with: pip install {' '.join(required_deps)}"
        )
    wrapper.__name__ = func_name
    wrapper.__qualname__ = func_name
    return wrapper


def _is_pkg_missing(pkg_name: str) -> bool:
    """Return True when *pkg_name* is unavailable.

    For ``pydantic`` the config system requires v2+, so a pydantic v1 install
    (which lacks ``field_validator`` and other v2 APIs the config models use)
    counts as missing — otherwise the raw v2-only ImportError leaks instead of
    the helpful dependency wrapper (see #1118).
    """
    try:
        mod = importlib.import_module(pkg_name.replace('-', '_'))
    except ImportError:
        return True
    if pkg_name == 'pydantic':
        raw = getattr(mod, 'VERSION', None) or getattr(mod, '__version__', '') or ''
        try:
            return int(str(raw).split('.', 1)[0]) < 2
        except (ValueError, IndexError):
            return False
    return False


def _resolve_with_fallback(mod_path, attr_name, public_name):
    """Import *attr_name* from *mod_path*, returning a dependency wrapper on failure."""
    try:
        mod = importlib.import_module(mod_path, __package__)
        return getattr(mod, attr_name)
    except ImportError as exc:
        if mod_path in _PYDANTIC_MODULES and _is_pkg_missing('pydantic'):
            _config_logger.warning("Could not import Pydantic config system: %s", exc)
            return _config_dependency_wrapper(public_name, ['pydantic>=2.0'])
        if mod_path in _HYDRA_MODULES and _is_pkg_missing('hydra'):
            _config_logger.debug(
                "Hydra config manager not available (install with the "
                "'config-extras' extra: pip install "
                "siege-utilities[config-extras]): %s",
                exc,
            )
            return _config_dependency_wrapper(
                public_name,
                ['hydra-core>=1.3.0', 'omegaconf>=2.3.0'],
            )
        raise


# ---------------------------------------------------------------------------
# PEP 562 lazy loading
# ---------------------------------------------------------------------------

def __getattr__(name):
    # Check aliases first (renamed re-exports)
    if name in _ALIASES:
        mod_path, orig_name = _ALIASES[name]
        val = _resolve_with_fallback(mod_path, orig_name, name)
        setattr(sys.modules[__name__], name, val)
        return val

    # Check the main lazy-import map
    if name in _LAZY_IMPORTS:
        mod_path = _LAZY_IMPORTS[name]
        val = _resolve_with_fallback(mod_path, name, name)
        setattr(sys.modules[__name__], name, val)
        return val

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# __all__ — kept accurate for star-imports and IDE completion
# ---------------------------------------------------------------------------

__all__ = [
    # Settings singleton
    'settings',

    # Library metadata
    'LIBRARY_NAME', 'LIBRARY_VERSION', 'LIBRARY_AUTHOR', 'LIBRARY_URL',

    # Network and timeout constants
    'DEFAULT_TIMEOUT', 'LONG_TIMEOUT', 'EXTENDED_TIMEOUT', 'CACHE_TIMEOUT',
    'DEFAULT_CHUNK_SIZE', 'MAX_RETRY_ATTEMPTS', 'RETRY_DELAY',

    # File system constants
    'SIEGE_UTILITIES_HOME', 'SIEGE_CACHE_DIR', 'SIEGE_OUTPUT_DIR',
    'SMALL_FILE_THRESHOLD', 'LARGE_FILE_THRESHOLD',
    'SUPPORTED_FILE_FORMATS', 'SUPPORTED_IMAGE_FORMATS',

    # Visualization constants
    'DEFAULT_CHART_WIDTH', 'DEFAULT_CHART_HEIGHT', 'WIDE_CHART_WIDTH', 'WIDE_CHART_HEIGHT',
    'PRESENTATION_CHART_WIDTH', 'PRESENTATION_CHART_HEIGHT',
    'DEFAULT_DPI', 'DEFAULT_FONT_SIZE', 'HEADER_FONT_SIZE', 'TITLE_FONT_SIZE',
    'DEFAULT_COLOR_SCHEME', 'DEFAULT_COLOR_PALETTE',
    'DEFAULT_MAP_ZOOM', 'DEFAULT_MARKER_SIZE', 'DEFAULT_POPUP_WIDTH', 'DEFAULT_CLUSTER_RADIUS',

    # Database constants
    'DB_CONNECTION_TIMEOUT', 'DB_QUERY_TIMEOUT', 'DB_CLEANUP_DAYS',
    'MAX_CONNECTIONS', 'CONNECTION_RETRY_ATTEMPTS',

    # Data processing constants
    'DEFAULT_ROW_LIMIT', 'DEFAULT_PAGE_SIZE', 'MAX_RESULTS_LIMIT',
    'DEFAULT_SPARK_PARTITIONS', 'SPARK_DRIVER_MEMORY', 'SPARK_EXECUTOR_MEMORY',

    # Testing constants
    'TEST_TIMEOUT', 'MAX_TEST_FAILURES', 'MIN_COVERAGE_THRESHOLD',
    'LOG_MAX_BYTES', 'LOG_BACKUP_COUNT',

    # API and service constants
    'API_RATE_LIMIT', 'API_BURST_LIMIT', 'DEFAULT_BATCH_SIZE', 'MAX_BATCH_SIZE',
    'SERVICE_TIMEOUTS', 'SERVICE_ROW_LIMITS',

    # Helper functions
    'get_timeout', 'get_chart_dimensions', 'get_file_path',
    'get_service_timeout', 'get_service_row_limit',

    # Census constants
    'CENSUS_BASE_URL', 'CENSUS_API_BASE_URL', 'CENSUS_FTP_BASE_URL',
    'CANONICAL_GEOGRAPHIC_LEVELS', 'resolve_geographic_level',
    'GEOGRAPHIC_LEVELS', 'GEOGRAPHIC_HIERARCHY',
    'DATASET_TYPES', 'RELIABILITY_LEVELS', 'SurveyType', 'DataReliability', 'GeographyLevel',
    'VARIABLE_GROUPS', 'VARIABLE_DESCRIPTIONS',
    'STATE_FIPS_CODES', 'STATEFIPS_LOOKUP_DICT', 'FIPS_TO_STATE', 'STATE_NAMES',
    'AVAILABLE_CENSUS_YEARS', 'DEFAULT_CENSUS_YEAR', 'DECENNIAL_YEARS', 'ACS_AVAILABLE_YEARS',
    'ACS5_AVAILABLE_YEARS', 'BOUNDARY_CHANGE_YEARS',
    'TIGER_FILE_PATTERNS',
    'CENSUS_CACHE_TIMEOUT', 'CENSUS_MAX_CACHE_SIZE', 'CENSUS_TIMEOUT', 'CENSUS_RETRY_ATTEMPTS',
    'CENSUS_API_CACHE_TIMEOUT', 'CENSUS_API_DEFAULT_TIMEOUT', 'CENSUS_API_RATE_LIMIT_RETRY_DELAY',
    'normalize_state_identifier', 'get_tiger_url', 'validate_geographic_level', 'get_fips_info',

    # NCES constants
    'NCES_BASE_URL', 'NCES_GEOGRAPHIC_URL', 'NCES_LOCALE_BOUNDARIES_URL', 'NCES_DOWNLOAD_ENDPOINTS',
    'LOCALE_CATEGORIES', 'LOCALE_SUBCATEGORIES', 'LOCALE_NUMERIC_CODES', 'LOCALE_CODE_TO_NUMERIC',
    'POPULATION_THRESHOLDS', 'DISTANCE_THRESHOLDS',
    'NCES_FILE_PATTERNS', 'NCES_SUPPORTED_FORMATS',
    'AVAILABLE_NCES_YEARS', 'DEFAULT_NCES_YEAR',
    'URBANICITY_SETTINGS', 'CENSUS_NCES_JOIN_FIELDS',
    'get_locale_category', 'get_locale_subcategory', 'classify_urbanicity',
    'get_nces_download_url', 'validate_locale_code', 'get_urbanicity_info',

    # Path constants (with prefixes to avoid conflicts)
    'PATH_SIEGE_UTILITIES_HOME', 'SIEGE_UTILITIES_TEST', 'SIEGE_ANALYTICS_ROOT',
    'GEOCODING_PROJECT', 'MASAI_PROJECT',
    'PATH_SIEGE_CACHE_DIR', 'SPARK_CACHE_DIR', 'TEMP_DIR', 'DOWNLOAD_TEMP_DIR', 'PROCESSING_TEMP_DIR',
    'PATH_SIEGE_OUTPUT_DIR', 'REPORTS_OUTPUT_DIR', 'CHARTS_OUTPUT_DIR', 'MAPS_OUTPUT_DIR',
    'DATA_DIR', 'CENSUS_DATA_DIR', 'NCES_DATA_DIR', 'SAMPLE_DATA_DIR',
    'CONFIG_DIR', 'USER_CONFIG_FILE', 'DATABASE_CONFIG_DIR',
    'LOG_DIR', 'ERROR_LOG_DIR', 'DEBUG_LOG_DIR',
    'BACKUP_DIR', 'CONFIG_BACKUP_DIR', 'DATA_BACKUP_DIR',
    'STANDARD_SUBDIRS', 'FILE_EXTENSIONS',
    'ensure_directory_exists', 'get_project_path', 'get_cache_path', 'get_output_path',
    'get_data_path', 'setup_standard_directories', 'get_file_type', 'get_relative_to_home',
    'initialize_siege_directories',

    # Enhanced config
    'SiegeConfig',
    'load_user_profile', 'save_user_profile',
    'load_client_profile', 'save_client_profile',
    'list_client_profiles',
    'export_config_yaml', 'import_config_yaml',

    # Existing config classes and functions
    'UserProfile', 'UserConfigManager', 'get_user_config', 'get_download_directory',
    'create_database_config', 'save_database_config',
    'load_database_config', 'list_database_configs', 'test_database_connection',
    'cleanup_old_connections', 'get_connection_status',

    # Credential management functions
    'get_google_service_account_from_1password',
    'get_google_oauth_from_1password',
    'create_temporary_service_account_file',

    # Credential management functions
    'CredentialManager', 'CredentialNotFoundError',
    'get_credential', 'store_credential',
    'store_ga_credentials_from_file', 'get_ga_credentials', 'credential_status',
    'store_ga_service_account_from_file', 'get_ga_service_account_credentials',

    # Hydra + Pydantic configuration system
    'HydraConfigManager',
    'PydanticUserProfile', 'PydanticClientProfile', 'ContactInfo',
    'BrandingConfig', 'ReportPreferences', 'DatabaseConnection', 'SocialMediaAccount',

    # Person/Actor architecture models
    'Person', 'User', 'Client', 'Collaborator', 'Organization', 'Collaboration',
    'Credential', 'OnePasswordCredential', 'OAuthIntegration', 'OAuthScope',

    # Migration utilities
    'ConfigurationMigrator', 'migrate_configurations', 'backup_and_migrate',

    # Data source registry
    'JurisdictionLevel', 'Jurisdiction',
    'DataSourceType', 'DataSourceStatus',
    'DataSource', 'SourceCredential',
    'DataSourceRegistry',
    'GoogleAccountRegistry',
]
