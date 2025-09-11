"""
File utilities for siege_utilities.

This module provides comprehensive file operations including:
- Path manipulation and directory management
- File operations (copy, move, delete, etc.)
- Remote file downloads with retry logic
- File hashing and integrity verification

All functions are available at the top level for mutual availability across modules.
"""

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
)

from .remote import (
    download_file,
    generate_local_path_from_url,
    download_file_with_retry,
    get_file_info,
    is_downloadable,
)

from .hashing import (
    generate_sha256_hash_for_file,
    get_file_hash,
    calculate_file_hash,
    get_quick_file_signature,
    verify_file_integrity,
    test_hash_functions,
)

# Convenience function for getting download directory
def get_download_directory() -> Path:
    """
    Get the default download directory for siege_utilities.
    
    Returns:
        Path to the download directory
    """
    from pathlib import Path
    import os
    
    # Try to get from environment variable first
    download_dir = os.environ.get('SIEGE_DOWNLOAD_DIR', None)
    if download_dir:
        return Path(download_dir)
    
    # Default to Downloads/siege_utilities
    downloads_dir = Path.home() / "Downloads" / "siege_utilities"
    ensure_path_exists(downloads_dir)
    return downloads_dir

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
    
    # Remote functions
    'download_file',
    'generate_local_path_from_url',
    'download_file_with_retry',
    'get_file_info',
    'is_downloadable',
    'get_download_directory',  # Convenience alias
    
    # Hashing functions
    'generate_sha256_hash_for_file',
    'get_file_hash',
    'calculate_file_hash',
    'get_quick_file_signature',
    'verify_file_integrity',
    'test_hash_functions',
]
