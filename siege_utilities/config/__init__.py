"""
Configuration module for siege_utilities.
Centralized constants and configuration management.
"""

# Import all constants for easy access
from .constants import (
    # Library metadata
    LIBRARY_NAME,
    LIBRARY_VERSION,
    LIBRARY_AUTHOR,
    LIBRARY_URL,
    
    # Network and timeout constants
    DEFAULT_TIMEOUT,
    LONG_TIMEOUT,
    EXTENDED_TIMEOUT,
    CACHE_TIMEOUT,
    DEFAULT_CHUNK_SIZE,
    MAX_RETRY_ATTEMPTS,
    RETRY_DELAY,
    
    # File system constants
    SIEGE_UTILITIES_HOME,
    SIEGE_CACHE_DIR,
    SIEGE_OUTPUT_DIR,
    SMALL_FILE_THRESHOLD,
    LARGE_FILE_THRESHOLD,
    SUPPORTED_FILE_FORMATS,
    SUPPORTED_IMAGE_FORMATS,
    
    # Visualization constants
    DEFAULT_CHART_WIDTH,
    DEFAULT_CHART_HEIGHT,
    WIDE_CHART_WIDTH,
    WIDE_CHART_HEIGHT,
    PRESENTATION_CHART_WIDTH,
    PRESENTATION_CHART_HEIGHT,
    DEFAULT_DPI,
    DEFAULT_FONT_SIZE,
    HEADER_FONT_SIZE,
    TITLE_FONT_SIZE,
    DEFAULT_COLOR_SCHEME,
    DEFAULT_COLOR_PALETTE,
    DEFAULT_MAP_ZOOM,
    DEFAULT_MARKER_SIZE,
    DEFAULT_POPUP_WIDTH,
    DEFAULT_CLUSTER_RADIUS,
    
    # Database constants
    DB_CONNECTION_TIMEOUT,
    DB_QUERY_TIMEOUT,
    DB_CLEANUP_DAYS,
    MAX_CONNECTIONS,
    CONNECTION_RETRY_ATTEMPTS,
    
    # Data processing constants
    DEFAULT_ROW_LIMIT,
    DEFAULT_PAGE_SIZE,
    MAX_RESULTS_LIMIT,
    DEFAULT_SPARK_PARTITIONS,
    SPARK_DRIVER_MEMORY,
    SPARK_EXECUTOR_MEMORY,
    
    # Testing constants
    TEST_TIMEOUT,
    MAX_TEST_FAILURES,
    MIN_COVERAGE_THRESHOLD,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    
    # API and service constants
    API_RATE_LIMIT,
    API_BURST_LIMIT,
    DEFAULT_BATCH_SIZE,
    MAX_BATCH_SIZE,
    SERVICE_TIMEOUTS,
    SERVICE_ROW_LIMITS,
    
    # Helper functions
    get_timeout,
    get_chart_dimensions,
    get_file_path,
    get_service_timeout,
    get_service_row_limit,
)

# Import Census-specific constants
from .census_constants import (
    # URLs
    CENSUS_BASE_URL,
    CENSUS_API_BASE_URL,
    CENSUS_FTP_BASE_URL,
    
    # Geographic levels
    GEOGRAPHIC_LEVELS,
    GEOGRAPHIC_HIERARCHY,
    
    # Dataset types
    DATASET_TYPES,
    RELIABILITY_LEVELS,
    
    # FIPS codes and mappings
    STATE_FIPS_CODES,
    FIPS_TO_STATE,
    STATE_NAMES,
    
    # Years and availability
    AVAILABLE_CENSUS_YEARS,
    DEFAULT_CENSUS_YEAR,
    DECENNIAL_YEARS,
    ACS_AVAILABLE_YEARS,
    
    # File patterns
    TIGER_FILE_PATTERNS,
    
    # Operation settings
    CENSUS_CACHE_TIMEOUT,
    CENSUS_MAX_CACHE_SIZE,
    CENSUS_TIMEOUT,
    CENSUS_RETRY_ATTEMPTS,
    
    # Helper functions
    normalize_state_identifier,
    get_tiger_url,
    validate_geographic_level,
    get_fips_info,
)

# Import NCES-specific constants
from .nces_constants import (
    # URLs
    NCES_BASE_URL,
    NCES_GEOGRAPHIC_URL,
    NCES_LOCALE_BOUNDARIES_URL,
    NCES_DOWNLOAD_ENDPOINTS,
    
    # Locale classification
    LOCALE_CATEGORIES,
    LOCALE_SUBCATEGORIES,
    LOCALE_NUMERIC_CODES,
    LOCALE_CODE_TO_NUMERIC,
    
    # Urbanicity definitions
    POPULATION_THRESHOLDS,
    DISTANCE_THRESHOLDS,
    
    # File patterns and formats
    NCES_FILE_PATTERNS,
    NCES_SUPPORTED_FORMATS,
    
    # Years and availability
    AVAILABLE_NCES_YEARS,
    DEFAULT_NCES_YEAR,
    
    # Calculation settings
    URBANICITY_SETTINGS,
    CENSUS_NCES_JOIN_FIELDS,
    
    # Helper functions
    get_locale_category,
    get_locale_subcategory,
    classify_urbanicity,
    get_nces_download_url,
    validate_locale_code,
    get_urbanicity_info,
)

# Import path constants
from .paths import (
    # Environment-based paths
    SIEGE_UTILITIES_HOME as PATH_SIEGE_UTILITIES_HOME,  # Avoid naming conflict
    SIEGE_UTILITIES_TEST,
    SIEGE_ANALYTICS_ROOT,
    GEOCODING_PROJECT,
    MASAI_PROJECT,
    
    # Cache and temp directories
    SIEGE_CACHE_DIR as PATH_SIEGE_CACHE_DIR,  # Avoid naming conflict
    SPARK_CACHE_DIR,
    TEMP_DIR,
    DOWNLOAD_TEMP_DIR,
    PROCESSING_TEMP_DIR,
    
    # Output directories
    SIEGE_OUTPUT_DIR as PATH_SIEGE_OUTPUT_DIR,  # Avoid naming conflict
    REPORTS_OUTPUT_DIR,
    CHARTS_OUTPUT_DIR,
    MAPS_OUTPUT_DIR,
    
    # Data directories
    DATA_DIR,
    CENSUS_DATA_DIR,
    NCES_DATA_DIR,
    SAMPLE_DATA_DIR,
    
    # Configuration directories
    CONFIG_DIR,
    USER_CONFIG_FILE,
    DATABASE_CONFIG_DIR,
    
    # Log directories
    LOG_DIR,
    ERROR_LOG_DIR,
    DEBUG_LOG_DIR,
    
    # Backup directories
    BACKUP_DIR,
    CONFIG_BACKUP_DIR,
    DATA_BACKUP_DIR,
    
    # Standard structure
    STANDARD_SUBDIRS,
    FILE_EXTENSIONS,
    
    # Helper functions
    ensure_directory_exists,
    get_project_path,
    get_cache_path,
    get_output_path,
    get_data_path,
    setup_standard_directories,
    get_file_type,
    get_relative_to_home,
    initialize_siege_directories,
)

# Import existing config modules for backward compatibility
from .user_config import (
    UserProfile,
    UserConfigManager,
    get_user_config,
    get_download_directory,
)

# Enhanced config system with Pydantic validation
from .enhanced_config import (
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

# Hydra + Pydantic configuration system
from .hydra_manager import HydraConfigManager
from .models import (
    UserProfile as PydanticUserProfile,
    ClientProfile as PydanticClientProfile,
    ContactInfo,
    BrandingConfig,
    ReportPreferences,
    SocialMediaAccount,
)

# Import Person/Actor architecture models
from .models.person import Person
from .models.actor_types import User, Client, Collaborator, Organization, Collaboration
from .models.credential import Credential, OnePasswordCredential
from .models.oauth_integration import OAuthIntegration, OAuthScope
from .models.database_connection import DatabaseConnection

# Migration utilities
from .migration import (
    ConfigurationMigrator,
    migrate_configurations,
    backup_and_migrate,
)

from .databases import (
    create_database_config,
    save_database_config,
    load_database_config,
    list_database_configs,
    test_database_connection,
)

from .connections import (
    cleanup_old_connections,
    get_connection_status,
)

from .credential_manager import (
    get_google_service_account_from_1password,
    create_temporary_service_account_file,
)

# Import credential management functions
from .credential_manager import (
    CredentialManager,
    get_credential,
    store_credential,
    store_ga_credentials_from_file,
    get_ga_credentials,
    credential_status,
    store_ga_service_account_from_file,
    get_ga_service_account_credentials,
)

# Export all for easy importing
__all__ = [
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
    'GEOGRAPHIC_LEVELS', 'GEOGRAPHIC_HIERARCHY',
    'DATASET_TYPES', 'RELIABILITY_LEVELS',
    'STATE_FIPS_CODES', 'FIPS_TO_STATE', 'STATE_NAMES',
    'AVAILABLE_CENSUS_YEARS', 'DEFAULT_CENSUS_YEAR', 'DECENNIAL_YEARS', 'ACS_AVAILABLE_YEARS',
    'TIGER_FILE_PATTERNS',
    'CENSUS_CACHE_TIMEOUT', 'CENSUS_MAX_CACHE_SIZE', 'CENSUS_TIMEOUT', 'CENSUS_RETRY_ATTEMPTS',
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
    
    # Existing config classes and functions
    'UserProfile', 'UserConfigManager', 'get_user_config', 'get_download_directory',
    'create_database_config', 'save_database_config',
    'load_database_config', 'list_database_configs', 'test_database_connection',
    'cleanup_old_connections', 'get_connection_status',
    
    # Credential management functions
    'get_google_service_account_from_1password',
    'create_temporary_service_account_file',
    
    # Credential management functions
    'CredentialManager', 'get_credential', 'store_credential', 
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
]
