"""
Configuration module for siege_utilities.
Centralized constants and configuration management.
"""

# Re-export settings singleton for discoverability
from siege_utilities.conf import settings

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
    CANONICAL_GEOGRAPHIC_LEVELS,
    resolve_geographic_level,
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

    # API-specific settings
    CENSUS_API_CACHE_TIMEOUT,
    CENSUS_API_DEFAULT_TIMEOUT,
    CENSUS_API_RATE_LIMIT_RETRY_DELAY,

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

# Pydantic-validated config system — requires pydantic>=2.0
import logging as _logging
_config_logger = _logging.getLogger(__name__)


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


try:
    from .user_config import (
        UserProfile,
        UserConfigManager,
        get_user_config,
        get_download_directory,
    )
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
    from .hydra_manager import HydraConfigManager
    from .models import (
        UserProfile as PydanticUserProfile,
        ClientProfile as PydanticClientProfile,
        ContactInfo,
        BrandingConfig,
        ReportPreferences,
        SocialMediaAccount,
    )
    from .models.person import Person
    from .models.actor_types import User, Client, Collaborator, Organization, Collaboration
    from .models.credential import Credential, OnePasswordCredential
    from .models.oauth_integration import OAuthIntegration, OAuthScope
    from .models.database_connection import DatabaseConnection
    from .migration import (
        ConfigurationMigrator,
        migrate_configurations,
        backup_and_migrate,
    )
except ImportError as e:
    _config_logger.warning(f"Could not import Pydantic config system: {e}")
    _pd = ['pydantic>=2.0']
    UserProfile = _config_dependency_wrapper('UserProfile', _pd)
    UserConfigManager = _config_dependency_wrapper('UserConfigManager', _pd)
    get_user_config = _config_dependency_wrapper('get_user_config', _pd)
    get_download_directory = _config_dependency_wrapper('get_download_directory', _pd)
    EnhancedUserProfile = _config_dependency_wrapper('EnhancedUserProfile', _pd)
    ClientProfile = _config_dependency_wrapper('ClientProfile', _pd)
    SiegeConfig = _config_dependency_wrapper('SiegeConfig', _pd)
    load_user_profile = _config_dependency_wrapper('load_user_profile', _pd)
    save_user_profile = _config_dependency_wrapper('save_user_profile', _pd)
    load_client_profile = _config_dependency_wrapper('load_client_profile', _pd)
    save_client_profile = _config_dependency_wrapper('save_client_profile', _pd)
    list_client_profiles = _config_dependency_wrapper('list_client_profiles', _pd)
    export_config_yaml = _config_dependency_wrapper('export_config_yaml', _pd)
    import_config_yaml = _config_dependency_wrapper('import_config_yaml', _pd)
    HydraConfigManager = _config_dependency_wrapper('HydraConfigManager', _pd)
    PydanticUserProfile = _config_dependency_wrapper('PydanticUserProfile', _pd)
    PydanticClientProfile = _config_dependency_wrapper('PydanticClientProfile', _pd)
    ContactInfo = _config_dependency_wrapper('ContactInfo', _pd)
    BrandingConfig = _config_dependency_wrapper('BrandingConfig', _pd)
    ReportPreferences = _config_dependency_wrapper('ReportPreferences', _pd)
    SocialMediaAccount = _config_dependency_wrapper('SocialMediaAccount', _pd)
    Person = _config_dependency_wrapper('Person', _pd)
    User = _config_dependency_wrapper('User', _pd)
    Client = _config_dependency_wrapper('Client', _pd)
    Collaborator = _config_dependency_wrapper('Collaborator', _pd)
    Organization = _config_dependency_wrapper('Organization', _pd)
    Collaboration = _config_dependency_wrapper('Collaboration', _pd)
    Credential = _config_dependency_wrapper('Credential', _pd)
    OnePasswordCredential = _config_dependency_wrapper('OnePasswordCredential', _pd)
    OAuthIntegration = _config_dependency_wrapper('OAuthIntegration', _pd)
    OAuthScope = _config_dependency_wrapper('OAuthScope', _pd)
    DatabaseConnection = _config_dependency_wrapper('DatabaseConnection', _pd)
    ConfigurationMigrator = _config_dependency_wrapper('ConfigurationMigrator', _pd)
    migrate_configurations = _config_dependency_wrapper('migrate_configurations', _pd)
    backup_and_migrate = _config_dependency_wrapper('backup_and_migrate', _pd)

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
    get_google_oauth_from_1password,
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
    'DATASET_TYPES', 'RELIABILITY_LEVELS',
    'STATE_FIPS_CODES', 'FIPS_TO_STATE', 'STATE_NAMES',
    'AVAILABLE_CENSUS_YEARS', 'DEFAULT_CENSUS_YEAR', 'DECENNIAL_YEARS', 'ACS_AVAILABLE_YEARS',
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
