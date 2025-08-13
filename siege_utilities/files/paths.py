"""
Modern path utilities for siege_utilities.
Provides clean, type-safe path manipulation utilities.
"""

import pathlib
import zipfile
import logging
from pathlib import Path
from typing import Union, Optional

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]

def ensure_path_exists(desired_path: FilePath) -> Path:
    """
    Ensure a directory path exists, creating it if necessary.
    
    Args:
        desired_path: Path to ensure exists
        
    Returns:
        Path object for the created directory
        
    Example:
        >>> path = ensure_path_exists("logs/2024/01")
        >>> print(f"Directory created: {path}")
    """
    try:
        path_obj = Path(desired_path)
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep file to ensure directory is tracked by git
        gitkeep_file = path_obj / '.gitkeep'
        if not gitkeep_file.exists():
            gitkeep_file.touch()
            log.debug(f"Created .gitkeep file in {path_obj}")
        
        log.info(f"Ensured path exists: {path_obj}")
        return path_obj
        
    except Exception as e:
        log.error(f"Failed to create path {desired_path}: {e}")
        raise

def unzip_file_to_directory(zip_file_path: FilePath,
                           extract_to: Optional[FilePath] = None,
                           create_subdirectory: bool = True) -> Optional[Path]:
    """
    Extract a zip file to a directory.
    
    Args:
        zip_file_path: Path to the zip file
        extract_to: Directory to extract to (defaults to zip file's parent)
        create_subdirectory: Whether to create a subdirectory for extracted files
        
    Returns:
        Path to the extraction directory, or None if failed
        
    Example:
        >>> extract_dir = unzip_file_to_directory("data.zip")
        >>> print(f"Files extracted to: {extract_dir}")
    """
    try:
        zip_path = Path(zip_file_path)
        
        if not zip_path.exists():
            log.error(f"Zip file does not exist: {zip_path}")
            return None
            
        if not zip_path.is_file():
            log.error(f"Path is not a file: {zip_path}")
            return None
        
        # Determine extraction directory
        if extract_to is None:
            extract_to = zip_path.parent
        
        extract_dir = Path(extract_to)
        
        if create_subdirectory:
            # Create subdirectory based on zip file name
            subdir_name = zip_path.stem
            target_dir = extract_dir / subdir_name
        else:
            target_dir = extract_dir
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract files
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        log.info(f"Extracted {zip_path} to {target_dir}")
        return target_dir
        
    except zipfile.BadZipFile:
        log.error(f"Invalid zip file: {zip_file_path}")
        return None
    except Exception as e:
        log.error(f"Failed to extract {zip_file_path}: {e}")
        return None

def get_file_extension(file_path: FilePath) -> str:
    """
    Get the file extension from a file path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (including the dot)
        
    Example:
        >>> ext = get_file_extension("document.pdf")
        >>> print(f"File extension: {ext}")  # .pdf
    """
    path_obj = Path(file_path)
    return path_obj.suffix

def get_file_name_without_extension(file_path: FilePath) -> str:
    """
    Get the file name without its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File name without extension
        
    Example:
        >>> name = get_file_name_without_extension("document.pdf")
        >>> print(f"File name: {name}")  # document
    """
    path_obj = Path(file_path)
    return path_obj.stem

def is_hidden_file(file_path: FilePath) -> bool:
    """
    Check if a file or directory is hidden.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if the file/directory is hidden
        
    Example:
        >>> if is_hidden_file(".config"):
        ...     print("Hidden file detected")
    """
    path_obj = Path(file_path)
    return path_obj.name.startswith('.')

def get_relative_path(base_path: FilePath, target_path: FilePath) -> Optional[Path]:
    """
    Get the relative path from base_path to target_path.
    
    Args:
        base_path: Base directory path
        target_path: Target file/directory path
        
    Returns:
        Relative path from base to target, or None if failed
        
    Example:
        >>> rel_path = get_relative_path("/home/user", "/home/user/documents/file.txt")
        >>> print(f"Relative path: {rel_path}")  # documents/file.txt
    """
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        
        try:
            relative = target.relative_to(base)
            return relative
        except ValueError:
            log.warning(f"Target {target} is not relative to base {base}")
            return None
            
    except Exception as e:
        log.error(f"Failed to get relative path: {e}")
        return None

def find_files_by_pattern(directory: FilePath, 
                         pattern: str = "*",
                         recursive: bool = False) -> list[Path]:
    """
    Find files matching a pattern in a directory.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
        
    Example:
        >>> files = find_files_by_pattern("data", "*.csv", recursive=True)
        >>> print(f"Found {len(files)} CSV files")
    """
    try:
        dir_path = Path(directory)
        
        if not dir_path.exists() or not dir_path.is_dir():
            log.warning(f"Directory does not exist or is not a directory: {dir_path}")
            return []
        
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        # Filter to only files (not directories)
        files = [f for f in files if f.is_file()]
        
        log.debug(f"Found {len(files)} files matching '{pattern}' in {dir_path}")
        return sorted(files)
        
    except Exception as e:
        log.error(f"Failed to find files in {directory}: {e}")
        return []

def create_backup_path(original_path: FilePath, 
                      backup_suffix: str = ".backup",
                      backup_dir: Optional[FilePath] = None) -> Path:
    """
    Create a backup path for a file.
    
    Args:
        original_path: Path to the original file
        backup_suffix: Suffix to add to the backup filename
        backup_dir: Directory to place backup in (defaults to original file's directory)
        
    Returns:
        Path for the backup file
        
    Example:
        >>> backup_path = create_backup_path("config.yaml", ".bak")
        >>> print(f"Backup will be saved to: {backup_path}")
    """
    original = Path(original_path)
    
    if backup_dir is None:
        backup_dir = original.parent
    
    backup_dir_path = Path(backup_dir)
    backup_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create backup filename
    backup_name = original.stem + backup_suffix + original.suffix
    backup_path = backup_dir_path / backup_name
    
    log.debug(f"Created backup path: {backup_path}")
    return backup_path

def normalize_path(path: FilePath) -> Path:
    """
    Normalize a file path, resolving any relative components.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized absolute path
        
    Example:
        >>> norm_path = normalize_path("./../data/file.txt")
        >>> print(f"Normalized path: {norm_path}")
    """
    path_obj = Path(path)
    normalized = path_obj.resolve()
    log.debug(f"Normalized {path} to {normalized}")
    return normalized

# Backward compatibility aliases
unzip_file_to_its_own_directory = unzip_file_to_directory

__all__ = [
    'ensure_path_exists',
    'unzip_file_to_directory',
    'get_file_extension',
    'get_file_name_without_extension',
    'is_hidden_file',
    'get_relative_path',
    'find_files_by_pattern',
    'create_backup_path',
    'normalize_path',
    # Backward compatibility
    'unzip_file_to_its_own_directory'
]
