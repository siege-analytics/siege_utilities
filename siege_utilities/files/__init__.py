"""
File utilities for siege_utilities.

This module provides comprehensive file operations including:
- Path manipulation and directory management
- File operations (copy, move, delete, etc.)
- Remote file downloads with retry logic
- File hashing and integrity verification

All functions are available at the top level for mutual availability across modules.
"""

import warnings
from pathlib import Path

# Import all functions from submodules for mutual availability
from .paths import (
    ensure_path_exists,
    unzip_file_to_directory,
    get_file_extension,
    get_file_name_without_extension,
    is_hidden_file,
    get_relative_path,
    find_files_by_pattern,
    create_backup_path,
    normalize_path,
)

from .operations import (
    remove_tree,
    file_exists,
    touch_file,
    count_lines,
    copy_file,
    move_file,
    get_file_size,
    list_directory,
    run_command,
    delete_existing_file_and_replace_it_with_an_empty_file,
    ensure_directory_exists,
    safe_file_write,
    safe_file_read,
    safe_json_write,
    safe_json_read,
    get_file_size_mb,
    list_files_recursive,
)

from .remote import (
    download_file,
    generate_local_path_from_url,
    download_file_with_retry,
    get_file_info,
    is_downloadable,
)

from .formats import (
    SpatialFormat,
    TabularFormat,
    save_spatial,
    save_tabular,
)

from .hashing import (
    generate_sha256_hash_for_file,
    get_file_hash,
    calculate_file_hash,
    get_quick_file_signature,
    verify_file_integrity,
)

# Convenience function for getting download directory
def get_download_directory() -> Path:
    """Get the default download directory for siege_utilities.

    .. deprecated:: 3.19.0
        Use :func:`siege_utilities.config.user_config.get_download_directory`
        instead, or ``from siege_utilities import get_download_directory``.
        Will be removed in v4.0.0.

    Returns:
        Path to the download directory
    """
    import os

    warnings.warn(
        "siege_utilities.files.get_download_directory is deprecated and will be "
        "removed in v4.0.0. Use siege_utilities.config.user_config.get_download_directory "
        "or import get_download_directory from siege_utilities directly.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Preserve SIEGE_DOWNLOAD_DIR env-var override during the deprecation window
    download_dir = os.environ.get('SIEGE_DOWNLOAD_DIR')
    if download_dir:
        return Path(download_dir)

    from ..config.user_config import get_download_directory as _canonical
    return _canonical()

# Export all functions for mutual availability
__all__ = [
    # Path functions
    'ensure_path_exists',
    'unzip_file_to_directory', 
    'get_file_extension',
    'get_file_name_without_extension',
    'is_hidden_file',
    'get_relative_path',
    'find_files_by_pattern',
    'create_backup_path',
    'normalize_path',
    
    # Operations functions
    'remove_tree',
    'file_exists',
    'touch_file',
    'count_lines',
    'copy_file',
    'move_file',
    'get_file_size',
    'list_directory',
    'run_command',
    'delete_existing_file_and_replace_it_with_an_empty_file',
    'ensure_directory_exists',
    'safe_file_write',
    'safe_file_read',
    'safe_json_write',
    'safe_json_read',
    'get_file_size_mb',
    'list_files_recursive',
    
    # Remote functions
    'download_file',
    'generate_local_path_from_url',
    'download_file_with_retry',
    'get_file_info',
    'is_downloadable',
    'get_download_directory',  # Convenience alias
    
    # Format functions
    'SpatialFormat',
    'TabularFormat',
    'save_spatial',
    'save_tabular',

    # Hashing functions
    'generate_sha256_hash_for_file',
    'get_file_hash',
    'calculate_file_hash',
    'get_quick_file_signature',
    'verify_file_integrity',
]
