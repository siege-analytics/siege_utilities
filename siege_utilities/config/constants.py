"""
Centralized constants for siege_utilities.
Following the centralized configuration pattern from Zsh configuration.

This module provides a single source of truth for all constants used
throughout the siege_utilities library, organized by domain and functionality.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

# =============================================================================
# GLOBAL SYSTEM CONSTANTS
# =============================================================================

# Library metadata
LIBRARY_NAME = "siege_utilities"
LIBRARY_VERSION = "2.0.0"
LIBRARY_AUTHOR = "Siege Analytics"
LIBRARY_URL = "https://github.com/siege-analytics/siege_utilities"

# =============================================================================
# NETWORK AND TIMEOUT CONSTANTS
# =============================================================================
# Different services require different timeout values based on their characteristics:
# - Fast APIs (10-30s): Quick response expected
# - File downloads (30-60s): Network transfer time varies by file size
# - Database queries (30-300s): Complex queries may take longer
# - Census/Government APIs (45-60s): Often slower, high reliability needed
# - Cache operations (1-24 hours): Based on data freshness requirements

# Default timeout values (in seconds) - use for general HTTP requests
DEFAULT_TIMEOUT = 30  # Standard web APIs, health checks
LONG_TIMEOUT = 60     # File downloads, slower APIs
EXTENDED_TIMEOUT = 300  # Complex database operations, large data processing
CACHE_TIMEOUT = 3600  # 1 hour - balance between freshness and performance

# HTTP request settings
DEFAULT_CHUNK_SIZE = 8192  # 8KB - optimal for most network conditions
MAX_RETRY_ATTEMPTS = 3     # Standard retry pattern for transient failures
RETRY_DELAY = 1           # seconds between retries - prevents overwhelming services

# =============================================================================
# FILE SYSTEM CONSTANTS
# =============================================================================

# Default paths (using environment variables with fallbacks)
SIEGE_UTILITIES_HOME = Path(os.getenv('SIEGE_UTILITIES', Path.home() / 'siege_utilities'))
SIEGE_CACHE_DIR = Path(os.getenv('SIEGE_CACHE', Path.home() / '.siege_cache'))
SIEGE_OUTPUT_DIR = Path(os.getenv('SIEGE_OUTPUT', Path.home() / 'Downloads'))

# File size limits
SMALL_FILE_THRESHOLD = 1024 * 1024  # 1 MB
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB

# Supported file formats
SUPPORTED_FILE_FORMATS = ['csv', 'json', 'parquet', 'xlsx', 'shp', 'geojson']
SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'pdf', 'svg']

# =============================================================================
# VISUALIZATION AND REPORTING CONSTANTS
# =============================================================================

# Chart dimensions (in inches)
DEFAULT_CHART_WIDTH = 10.0
DEFAULT_CHART_HEIGHT = 8.0
WIDE_CHART_WIDTH = 12.0
WIDE_CHART_HEIGHT = 10.0
PRESENTATION_CHART_WIDTH = 14.0
PRESENTATION_CHART_HEIGHT = 10.0

# Chart settings
DEFAULT_DPI = 300
DEFAULT_FONT_SIZE = 10
HEADER_FONT_SIZE = 12
TITLE_FONT_SIZE = 14

# Color settings
DEFAULT_COLOR_SCHEME = "YlOrRd"
DEFAULT_COLOR_PALETTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

# Map settings
DEFAULT_MAP_ZOOM = 10
DEFAULT_MARKER_SIZE = 15
DEFAULT_POPUP_WIDTH = 300
DEFAULT_CLUSTER_RADIUS = 80

# =============================================================================
# DATABASE AND CONNECTION CONSTANTS
# =============================================================================
# Database timeout values vary by operation complexity:
# - Connection establishment: Quick (30s) - should be fast or fail
# - Simple queries: Medium (30-60s) - most queries are fast
# - Complex queries/reports: Long (300s+) - analytical queries take time
# - Connection cleanup: Days/weeks - balance between cleanup and stability

# Connection timeouts (in seconds)
DB_CONNECTION_TIMEOUT = 30   # Fast connection or fail - network issues are binary
DB_QUERY_TIMEOUT = 300       # Complex analytical queries need time
DB_CLEANUP_DAYS = 90         # Quarterly cleanup - not too aggressive

# Connection pool settings
MAX_CONNECTIONS = 10         # Conservative limit to prevent overwhelming DB
CONNECTION_RETRY_ATTEMPTS = 3  # Standard retry for transient connection issues

# =============================================================================
# DATA PROCESSING CONSTANTS
# =============================================================================
# Different data sources have different optimal limits based on their APIs and performance:
# - Google Analytics API: 100,000 rows max per request (API limitation)
# - Census API: 50,000 rows recommended for stability
# - Database queries: 1,000-10,000 rows for responsive pagination
# - Spark processing: 100+ partitions for parallel processing efficiency

# Default data limits - adjust per service as needed
DEFAULT_ROW_LIMIT = 100000    # Large datasets, batch processing
DEFAULT_PAGE_SIZE = 1000      # Interactive queries, web APIs
MAX_RESULTS_LIMIT = 1000000   # Absolute maximum to prevent memory issues

# Spark settings - optimized for typical cluster configurations
DEFAULT_SPARK_PARTITIONS = 100  # Good parallelism for most datasets
SPARK_DRIVER_MEMORY = "2g"      # Sufficient for coordination tasks
SPARK_EXECUTOR_MEMORY = "1g"    # Conservative per-executor memory

# =============================================================================
# TESTING AND DEVELOPMENT CONSTANTS
# =============================================================================

# Test settings
TEST_TIMEOUT = 300  # 5 minutes
MAX_TEST_FAILURES = 10
MIN_COVERAGE_THRESHOLD = 60

# Development settings
LOG_MAX_BYTES = 5000000  # 5 MB
LOG_BACKUP_COUNT = 5

# =============================================================================
# API AND SERVICE CONSTANTS
# =============================================================================
# Service-specific settings based on API characteristics and limitations:

# Rate limiting - varies by service provider
API_RATE_LIMIT = 1000  # requests per hour - conservative default
API_BURST_LIMIT = 100  # requests per minute - prevent overwhelming services

# Batch processing - optimal sizes vary by service and data complexity
DEFAULT_BATCH_SIZE = 500   # Good balance for most APIs
MAX_BATCH_SIZE = 5000      # Upper limit to prevent timeouts/memory issues

# Service-specific timeouts (in seconds) - documented reasons for differences
SERVICE_TIMEOUTS = {
    'google_analytics': 30,     # Fast commercial API, predictable response times
    'facebook_business': 30,    # Fast commercial API, predictable response times  
    'census_api': 45,          # Government API, slower servers, large datasets
    'census_download': 60,     # Large file downloads (shapefiles 10-100MB+)
    'snowflake': 30,           # Database connections should be fast
    'snowflake_query': 300,    # Complex analytical queries need time
    'file_download': 60,       # Network transfer time varies by file size
    'health_check': 10,        # Health checks should be very fast
    'cache_refresh': 30,       # Cache operations should be responsive
}

# Service-specific row limits - based on API capabilities and performance
SERVICE_ROW_LIMITS = {
    'google_analytics': 100000,  # API maximum per request
    'facebook_business': 50000,  # Reasonable limit for API stability
    'census_api': 50000,         # Recommended for government API reliability
    'database_query': 10000,     # Interactive query performance
    'batch_processing': 100000,  # Large batch operations
    'reporting': 1000000,        # Report generation can handle more data
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_timeout(operation_type: str = "default") -> int:
    """
    Get timeout value for specific operation types.
    
    Different services need different timeouts based on their characteristics:
    - 'default' (30s): Standard web APIs, health checks
    - 'download' (60s): File downloads, network transfer time varies
    - 'database' (30s): Connection establishment should be fast
    - 'census' (45s): Government servers, large files, reliability critical
    - 'api' (30s): Most commercial APIs are fast
    - 'extended' (300s): Complex operations, large data processing
    - 'cache' (3600s): Data freshness vs performance balance
    """
    timeout_map = {
        "default": DEFAULT_TIMEOUT,        # 30s - standard web requests
        "download": LONG_TIMEOUT,          # 60s - file transfer time varies
        "database": DB_CONNECTION_TIMEOUT, # 30s - connections should be fast
        "census": 45,                      # 45s - government servers are slower
        "api": DEFAULT_TIMEOUT,            # 30s - most APIs are responsive  
        "extended": EXTENDED_TIMEOUT,      # 300s - complex operations
        "cache": CACHE_TIMEOUT             # 3600s - data freshness balance
    }
    return timeout_map.get(operation_type, DEFAULT_TIMEOUT)

def get_chart_dimensions(chart_type: str = "default") -> tuple[float, float]:
    """Get chart dimensions for specific chart types."""
    dimension_map = {
        "default": (DEFAULT_CHART_WIDTH, DEFAULT_CHART_HEIGHT),
        "wide": (WIDE_CHART_WIDTH, WIDE_CHART_HEIGHT),
        "presentation": (PRESENTATION_CHART_WIDTH, PRESENTATION_CHART_HEIGHT)
    }
    return dimension_map.get(chart_type, (DEFAULT_CHART_WIDTH, DEFAULT_CHART_HEIGHT))

def get_file_path(path_type: str) -> Path:
    """Get standard file paths."""
    path_map = {
        "home": SIEGE_UTILITIES_HOME,
        "cache": SIEGE_CACHE_DIR,
        "output": SIEGE_OUTPUT_DIR
    }
    return path_map.get(path_type, SIEGE_UTILITIES_HOME)

def get_service_timeout(service_name: str) -> int:
    """
    Get timeout for specific service.
    
    Args:
        service_name: Name of the service (e.g., 'census_api', 'google_analytics')
        
    Returns:
        Timeout value in seconds, with fallback to default
    """
    return SERVICE_TIMEOUTS.get(service_name, DEFAULT_TIMEOUT)

def get_service_row_limit(service_name: str) -> int:
    """
    Get row limit for specific service.
    
    Args:
        service_name: Name of the service (e.g., 'census_api', 'google_analytics')
        
    Returns:
        Row limit for the service, with fallback to default
    """
    return SERVICE_ROW_LIMITS.get(service_name, DEFAULT_ROW_LIMIT)
