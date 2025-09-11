"""
Path configuration constants for siege_utilities.
Centralized path management following the Zsh configuration pattern.
"""

import os
from pathlib import Path
from typing import Dict, Optional, List

# =============================================================================
# ENVIRONMENT-BASED PATH CONFIGURATION
# =============================================================================
# Following the ${VARIABLE:-default} pattern from Zsh configuration

# Primary project paths (from environment variables with fallbacks)
SIEGE_UTILITIES_HOME = Path(os.getenv('SIEGE_UTILITIES', Path.home() / 'Documents/Professional/Siege_Analytics/Code/siege_utilities'))
SIEGE_UTILITIES_TEST = Path(os.getenv('SIEGE_UTILITIES_TEST', Path.home() / 'projects/test-remote-branch/siege_utilities'))

# Siege Analytics organization paths
SIEGE_ANALYTICS_ROOT = Path(os.getenv('SIEGE', Path.home() / 'Documents/Professional/Siege_Analytics'))
GEOCODING_PROJECT = Path(os.getenv('GEOCODE', SIEGE_ANALYTICS_ROOT / 'Clients/TAN/Projects/tan_geocoding_test'))
MASAI_PROJECT = Path(os.getenv('MASAI', SIEGE_ANALYTICS_ROOT / 'Clients/MI'))

# =============================================================================
# CACHE AND TEMPORARY DIRECTORIES
# =============================================================================

# Cache directories (configurable via environment)
SIEGE_CACHE_DIR = Path(os.getenv('SIEGE_CACHE', Path.home() / '.siege_cache'))
SPARK_CACHE_DIR = Path(os.getenv('SPARK_CACHE', Path.home() / '.spark_hdfs_cache'))

# Temporary directories
TEMP_DIR = Path(os.getenv('SIEGE_TEMP', Path.home() / '.siege_temp'))
DOWNLOAD_TEMP_DIR = TEMP_DIR / 'downloads'
PROCESSING_TEMP_DIR = TEMP_DIR / 'processing'

# =============================================================================
# OUTPUT AND RESULTS DIRECTORIES
# =============================================================================

# Output directories (configurable via environment)
SIEGE_OUTPUT_DIR = Path(os.getenv('SIEGE_OUTPUT', Path.home() / 'Downloads'))
REPORTS_OUTPUT_DIR = Path(os.getenv('SIEGE_REPORTS', SIEGE_OUTPUT_DIR / 'siege_reports'))
CHARTS_OUTPUT_DIR = Path(os.getenv('SIEGE_CHARTS', SIEGE_OUTPUT_DIR / 'siege_charts'))
MAPS_OUTPUT_DIR = Path(os.getenv('SIEGE_MAPS', SIEGE_OUTPUT_DIR / 'siege_maps'))

# =============================================================================
# DATA DIRECTORIES
# =============================================================================

# Data storage directories
DATA_DIR = Path(os.getenv('SIEGE_DATA', SIEGE_UTILITIES_HOME / 'data'))
CENSUS_DATA_DIR = Path(os.getenv('CENSUS_DATA', DATA_DIR / 'census'))
NCES_DATA_DIR = Path(os.getenv('NCES_DATA', DATA_DIR / 'nces'))
SAMPLE_DATA_DIR = Path(os.getenv('SAMPLE_DATA', DATA_DIR / 'samples'))

# =============================================================================
# CONFIGURATION DIRECTORIES
# =============================================================================

# Configuration file locations
CONFIG_DIR = Path(os.getenv('SIEGE_CONFIG', SIEGE_UTILITIES_HOME / 'config'))
USER_CONFIG_FILE = Path(os.getenv('SIEGE_USER_CONFIG', Path.home() / '.siege_config.yaml'))
DATABASE_CONFIG_DIR = CONFIG_DIR / 'databases'

# =============================================================================
# LOG DIRECTORIES
# =============================================================================

# Logging directories (configurable via environment)
LOG_DIR = Path(os.getenv('SIEGE_LOG_DIR', Path.home() / '.siege_logs'))
ERROR_LOG_DIR = LOG_DIR / 'errors'
DEBUG_LOG_DIR = LOG_DIR / 'debug'

# =============================================================================
# BACKUP AND ARCHIVE DIRECTORIES
# =============================================================================

# Backup locations
BACKUP_DIR = Path(os.getenv('SIEGE_BACKUP', Path.home() / '.siege_backups'))
CONFIG_BACKUP_DIR = BACKUP_DIR / 'config'
DATA_BACKUP_DIR = BACKUP_DIR / 'data'

# =============================================================================
# STANDARD DIRECTORY STRUCTURE
# =============================================================================

# Standard subdirectories that should exist in projects
STANDARD_SUBDIRS = {
    'config': 'Configuration files',
    'data': 'Data files and datasets',
    'logs': 'Log files',
    'output': 'Generated output files',
    'cache': 'Cached data and temporary files',
    'reports': 'Generated reports',
    'charts': 'Generated charts and visualizations',
    'maps': 'Generated maps and spatial visualizations'
}

# =============================================================================
# FILE EXTENSION MAPPINGS
# =============================================================================

# Common file extensions and their purposes
FILE_EXTENSIONS = {
    'data': ['.csv', '.json', '.parquet', '.xlsx', '.shp', '.geojson'],
    'images': ['.png', '.jpg', '.jpeg', '.pdf', '.svg'],
    'documents': ['.pdf', '.docx', '.pptx', '.html', '.md'],
    'config': ['.yaml', '.yml', '.json', '.toml', '.ini'],
    'code': ['.py', '.sql', '.r', '.js', '.sh'],
    'compressed': ['.zip', '.tar.gz', '.7z', '.rar']
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_directory_exists(path: Path) -> Path:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Path to directory
        
    Returns:
        Path object (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_project_path(project_name: str) -> Optional[Path]:
    """
    Get path for a specific project.
    
    Args:
        project_name: Name of the project
        
    Returns:
        Path object or None if project not found
    """
    project_map = {
        'siege_utilities': SIEGE_UTILITIES_HOME,
        'siege_utilities_test': SIEGE_UTILITIES_TEST,
        'geocoding': GEOCODING_PROJECT,
        'masai': MASAI_PROJECT,
        'siege_analytics': SIEGE_ANALYTICS_ROOT
    }
    
    return project_map.get(project_name.lower())

def get_cache_path(cache_type: str = 'default') -> Path:
    """
    Get cache directory path for specific cache type.
    
    Args:
        cache_type: Type of cache (default, spark, census, nces)
        
    Returns:
        Path to cache directory
    """
    cache_map = {
        'default': SIEGE_CACHE_DIR,
        'spark': SPARK_CACHE_DIR,
        'census': SIEGE_CACHE_DIR / 'census',
        'nces': SIEGE_CACHE_DIR / 'nces',
        'downloads': SIEGE_CACHE_DIR / 'downloads'
    }
    
    cache_path = cache_map.get(cache_type, SIEGE_CACHE_DIR)
    return ensure_directory_exists(cache_path)

def get_output_path(output_type: str = 'default') -> Path:
    """
    Get output directory path for specific output type.
    
    Args:
        output_type: Type of output (default, reports, charts, maps)
        
    Returns:
        Path to output directory
    """
    output_map = {
        'default': SIEGE_OUTPUT_DIR,
        'reports': REPORTS_OUTPUT_DIR,
        'charts': CHARTS_OUTPUT_DIR,
        'maps': MAPS_OUTPUT_DIR,
        'temp': TEMP_DIR
    }
    
    output_path = output_map.get(output_type, SIEGE_OUTPUT_DIR)
    return ensure_directory_exists(output_path)

def get_data_path(data_type: str = 'default') -> Path:
    """
    Get data directory path for specific data type.
    
    Args:
        data_type: Type of data (default, census, nces, samples)
        
    Returns:
        Path to data directory
    """
    data_map = {
        'default': DATA_DIR,
        'census': CENSUS_DATA_DIR,
        'nces': NCES_DATA_DIR,
        'samples': SAMPLE_DATA_DIR
    }
    
    data_path = data_map.get(data_type, DATA_DIR)
    return ensure_directory_exists(data_path)

def setup_standard_directories(base_path: Path) -> Dict[str, Path]:
    """
    Set up standard directory structure in a project.
    
    Args:
        base_path: Base project path
        
    Returns:
        Dictionary mapping directory names to paths
    """
    created_dirs = {}
    
    for dirname, description in STANDARD_SUBDIRS.items():
        dir_path = base_path / dirname
        ensure_directory_exists(dir_path)
        created_dirs[dirname] = dir_path
    
    return created_dirs

def get_file_type(file_path: Path) -> str:
    """
    Determine file type based on extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        File type category (data, images, documents, etc.)
    """
    suffix = file_path.suffix.lower()
    
    for file_type, extensions in FILE_EXTENSIONS.items():
        if suffix in extensions:
            return file_type
    
    return 'unknown'

def get_relative_to_home(path: Path) -> str:
    """
    Get path relative to user home directory.
    
    Args:
        path: Absolute path
        
    Returns:
        Path relative to home with ~ prefix
    """
    try:
        relative = path.relative_to(Path.home())
        return f"~/{relative}"
    except ValueError:
        return str(path)

# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_siege_directories() -> List[Path]:
    """Initialize all standard Siege utilities directories."""
    directories_to_create = [
        SIEGE_CACHE_DIR,
        TEMP_DIR,
        DOWNLOAD_TEMP_DIR,
        PROCESSING_TEMP_DIR,
        SIEGE_OUTPUT_DIR,
        REPORTS_OUTPUT_DIR,
        CHARTS_OUTPUT_DIR,
        MAPS_OUTPUT_DIR,
        DATA_DIR,
        CENSUS_DATA_DIR,
        NCES_DATA_DIR,
        SAMPLE_DATA_DIR,
        LOG_DIR,
        ERROR_LOG_DIR,
        DEBUG_LOG_DIR,
        BACKUP_DIR,
        CONFIG_BACKUP_DIR,
        DATA_BACKUP_DIR
    ]
    
    for directory in directories_to_create:
        ensure_directory_exists(directory)
    
    return directories_to_create

# Auto-initialize on import (can be disabled by setting environment variable)
if os.getenv('SIEGE_AUTO_INIT_DIRS', 'true').lower() == 'true':
    initialize_siege_directories()
