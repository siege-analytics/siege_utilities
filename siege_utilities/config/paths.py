"""
Path configuration constants for siege_utilities.
Centralized path management following the Zsh configuration pattern.
"""

import logging
import os
from pathlib import Path
from typing import Callable, Dict, Optional, List

from ._home import _fallback_home_directory, _home_directory

__all__ = [
    'SIEGE_UTILITIES_HOME',
    'SIEGE_UTILITIES_TEST',
    'SIEGE_ANALYTICS_ROOT',
    'GEOCODING_PROJECT',
    'MASAI_PROJECT',
    'SIEGE_CACHE_DIR',
    'SPARK_CACHE_DIR',
    'TEMP_DIR',
    'DOWNLOAD_TEMP_DIR',
    'PROCESSING_TEMP_DIR',
    'SIEGE_OUTPUT_DIR',
    'REPORTS_OUTPUT_DIR',
    'CHARTS_OUTPUT_DIR',
    'MAPS_OUTPUT_DIR',
    'DATA_DIR',
    'CENSUS_DATA_DIR',
    'NCES_DATA_DIR',
    'SAMPLE_DATA_DIR',
    'CONFIG_DIR',
    'USER_CONFIG_FILE',
    'DATABASE_CONFIG_DIR',
    'LOG_DIR',
    'ERROR_LOG_DIR',
    'DEBUG_LOG_DIR',
    'BACKUP_DIR',
    'CONFIG_BACKUP_DIR',
    'DATA_BACKUP_DIR',
    'STANDARD_SUBDIRS',
    'FILE_EXTENSIONS',
    'ensure_directory_exists',
    'get_project_path',
    'get_cache_path',
    'get_output_path',
    'get_data_path',
    'setup_standard_directories',
    'get_file_type',
    'get_relative_to_home',
    'initialize_siege_directories',
]

log = logging.getLogger(__name__)


def _env_path(name: str, default: Path | Callable[[], Path]) -> Path:
    """Read a path-shaped env var with a safety guard.

    Without this guard, ``SIEGE_OUTPUT=/etc`` (or any other system path)
    would happily flow into the package's I/O routines. We resolve the
    candidate and refuse paths that escape the home directory (or its
    temporary substitute when home lookup fails). Setting
    ``SIEGE_ALLOW_UNSAFE_PATHS=1`` opts out of the check for power
    users who genuinely want a non-home target.

    Resolution uses ``Path.expanduser().resolve()`` so ``~`` and
    relative components are handled consistently. A callable default is
    evaluated only if the override is absent or rejected.
    """
    raw = os.getenv(name)
    if not raw:
        return default() if callable(default) else default
    try:
        resolved = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError, KeyError):
        fallback = default() if callable(default) else default
        log.warning("Env var %s=%r could not be resolved; using default %s.",
                    name, raw, fallback)
        return fallback
    if os.environ.get("SIEGE_ALLOW_UNSAFE_PATHS", "").lower() in ("1", "true", "yes"):
        return resolved
    # Validate the override without evaluating any home-based default or
    # calling Path.home(). expanduser also supports passwd lookup without HOME.
    try:
        home = Path('~').expanduser().resolve()
    except (RuntimeError, KeyError):
        home = _fallback_home_directory().resolve()
    try:
        resolved.relative_to(home)
    except ValueError:
        fallback = default() if callable(default) else default
        log.warning(
            "Env var %s=%r resolves outside $HOME (%s). Refusing as a "
            "path-traversal safety guard; using default %s. Set "
            "SIEGE_ALLOW_UNSAFE_PATHS=1 to opt out.",
            name, str(resolved), home, fallback,
        )
        return fallback
    return resolved


# =============================================================================
# ENVIRONMENT-BASED PATH CONFIGURATION
# =============================================================================
# Following the ${VARIABLE:-default} pattern from Zsh configuration.
# Env-var values are constrained to ${HOME}-relative paths by default —
# see _env_path for the rationale.

# Each entry is (environment variable, parent constant, relative suffix).
# A missing parent means the user's home, resolved only when needed.
# Type declarations do not resolve the lazy module attributes.
SIEGE_UTILITIES_HOME: Path
SIEGE_UTILITIES_TEST: Path
SIEGE_ANALYTICS_ROOT: Path
GEOCODING_PROJECT: Path
MASAI_PROJECT: Path
SIEGE_CACHE_DIR: Path
SPARK_CACHE_DIR: Path
TEMP_DIR: Path
DOWNLOAD_TEMP_DIR: Path
PROCESSING_TEMP_DIR: Path
SIEGE_OUTPUT_DIR: Path
REPORTS_OUTPUT_DIR: Path
CHARTS_OUTPUT_DIR: Path
MAPS_OUTPUT_DIR: Path
DATA_DIR: Path
CENSUS_DATA_DIR: Path
NCES_DATA_DIR: Path
SAMPLE_DATA_DIR: Path
CONFIG_DIR: Path
USER_CONFIG_FILE: Path
DATABASE_CONFIG_DIR: Path
LOG_DIR: Path
ERROR_LOG_DIR: Path
DEBUG_LOG_DIR: Path
BACKUP_DIR: Path
CONFIG_BACKUP_DIR: Path
DATA_BACKUP_DIR: Path

_PATH_DEFAULTS = {
    'SIEGE_UTILITIES_HOME': ('SIEGE_UTILITIES', None, 'siege_utilities'),
    'SIEGE_UTILITIES_TEST': ('SIEGE_UTILITIES_TEST', None, 'siege_utilities_test'),
    'SIEGE_ANALYTICS_ROOT': ('SIEGE', None, 'siege_analytics'),
    'GEOCODING_PROJECT': ('GEOCODE', 'SIEGE_ANALYTICS_ROOT', 'geocoding'),
    'MASAI_PROJECT': ('MASAI', 'SIEGE_ANALYTICS_ROOT', 'masai'),
    'SIEGE_CACHE_DIR': ('SIEGE_CACHE', None, '.siege_cache'),
    'SPARK_CACHE_DIR': ('SPARK_CACHE', None, '.spark_hdfs_cache'),
    'TEMP_DIR': ('SIEGE_TEMP', None, '.siege_temp'),
    'DOWNLOAD_TEMP_DIR': (None, 'TEMP_DIR', 'downloads'),
    'PROCESSING_TEMP_DIR': (None, 'TEMP_DIR', 'processing'),
    'SIEGE_OUTPUT_DIR': ('SIEGE_OUTPUT', None, 'Downloads'),
    'REPORTS_OUTPUT_DIR': ('SIEGE_REPORTS', 'SIEGE_OUTPUT_DIR', 'siege_reports'),
    'CHARTS_OUTPUT_DIR': ('SIEGE_CHARTS', 'SIEGE_OUTPUT_DIR', 'siege_charts'),
    'MAPS_OUTPUT_DIR': ('SIEGE_MAPS', 'SIEGE_OUTPUT_DIR', 'siege_maps'),
    'DATA_DIR': ('SIEGE_DATA', 'SIEGE_UTILITIES_HOME', 'data'),
    'CENSUS_DATA_DIR': ('CENSUS_DATA', 'DATA_DIR', 'census'),
    'NCES_DATA_DIR': ('NCES_DATA', 'DATA_DIR', 'nces'),
    'SAMPLE_DATA_DIR': ('SAMPLE_DATA', 'DATA_DIR', 'samples'),
    'CONFIG_DIR': ('SIEGE_CONFIG', 'SIEGE_UTILITIES_HOME', 'config'),
    'USER_CONFIG_FILE': ('SIEGE_USER_CONFIG', None, '.siege_config.yaml'),
    'DATABASE_CONFIG_DIR': (None, 'CONFIG_DIR', 'databases'),
    'LOG_DIR': ('SIEGE_LOG_DIR', None, '.siege_logs'),
    'ERROR_LOG_DIR': (None, 'LOG_DIR', 'errors'),
    'DEBUG_LOG_DIR': (None, 'LOG_DIR', 'debug'),
    'BACKUP_DIR': ('SIEGE_BACKUP', None, '.siege_backups'),
    'CONFIG_BACKUP_DIR': (None, 'BACKUP_DIR', 'config'),
    'DATA_BACKUP_DIR': (None, 'BACKUP_DIR', 'data'),
}
# importlib.reload() must also discard paths resolved by an earlier import.
for _name in _PATH_DEFAULTS:
    globals().pop(_name, None)

_auto_init_pending = os.getenv('SIEGE_AUTO_INIT_DIRS', 'false').lower() == 'true'


def _get_path(name: str) -> Path:
    global _auto_init_pending
    if name not in globals():
        env_name, parent, suffix = _PATH_DEFAULTS[name]

        def default() -> Path:
            base = _get_path(parent) if parent else _home_directory()
            return base / suffix

        globals()[name] = _env_path(env_name, default) if env_name else default()
    if _auto_init_pending:
        _auto_init_pending = False
        initialize_siege_directories()
    return globals()[name]


def __getattr__(name: str) -> Path:
    if name in _PATH_DEFAULTS:
        return _get_path(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


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
        'siege_utilities': 'SIEGE_UTILITIES_HOME',
        'siege_utilities_test': 'SIEGE_UTILITIES_TEST',
        'geocoding': 'GEOCODING_PROJECT',
        'masai': 'MASAI_PROJECT',
        'siege_analytics': 'SIEGE_ANALYTICS_ROOT'
    }
    
    name = project_map.get(project_name.lower())
    return _get_path(name) if name else None

def get_cache_path(cache_type: str = 'default') -> Path:
    """
    Get cache directory path for specific cache type.
    
    Args:
        cache_type: Type of cache (default, spark, census, nces)
        
    Returns:
        Path to cache directory
    """
    cache_map = {
        'default': ('SIEGE_CACHE_DIR', ''),
        'spark': ('SPARK_CACHE_DIR', ''),
        'census': ('SIEGE_CACHE_DIR', 'census'),
        'nces': ('SIEGE_CACHE_DIR', 'nces'),
        'downloads': ('SIEGE_CACHE_DIR', 'downloads')
    }
    name, suffix = cache_map.get(cache_type, ('SIEGE_CACHE_DIR', ''))
    cache_path = _get_path(name) / suffix
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
        'default': 'SIEGE_OUTPUT_DIR',
        'reports': 'REPORTS_OUTPUT_DIR',
        'charts': 'CHARTS_OUTPUT_DIR',
        'maps': 'MAPS_OUTPUT_DIR',
        'temp': 'TEMP_DIR'
    }
    
    output_path = _get_path(output_map.get(output_type, 'SIEGE_OUTPUT_DIR'))
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
        'default': 'DATA_DIR',
        'census': 'CENSUS_DATA_DIR',
        'nces': 'NCES_DATA_DIR',
        'samples': 'SAMPLE_DATA_DIR'
    }
    
    data_path = _get_path(data_map.get(data_type, 'DATA_DIR'))
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
        relative = path.relative_to(_home_directory())
        return f"~/{relative}"
    except ValueError:
        return str(path)

# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_siege_directories() -> List[Path]:
    """Initialize all standard Siege utilities directories.

    Catches filesystem errors for containers, CI, and cross-platform use.
    With ``SIEGE_AUTO_INIT_DIRS=true``, this runs on first path access.
    """
    global _auto_init_pending
    _auto_init_pending = False
    directories_to_create = [
        'SIEGE_CACHE_DIR',
        'TEMP_DIR',
        'DOWNLOAD_TEMP_DIR',
        'PROCESSING_TEMP_DIR',
        'SIEGE_OUTPUT_DIR',
        'REPORTS_OUTPUT_DIR',
        'CHARTS_OUTPUT_DIR',
        'MAPS_OUTPUT_DIR',
        'DATA_DIR',
        'CENSUS_DATA_DIR',
        'NCES_DATA_DIR',
        'SAMPLE_DATA_DIR',
        'LOG_DIR',
        'ERROR_LOG_DIR',
        'DEBUG_LOG_DIR',
        'BACKUP_DIR',
        'CONFIG_BACKUP_DIR',
        'DATA_BACKUP_DIR'
    ]

    created = []
    for name in directories_to_create:
        directory = _get_path(name)
        try:
            ensure_directory_exists(directory)
            created.append(directory)
        except (PermissionError, FileNotFoundError, OSError) as exc:
            logging.getLogger(__name__).warning(
                "Could not create directory %s: %s", directory, exc
            )

    return created
