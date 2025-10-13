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

    SECURITY: Validates paths to prevent path traversal and sensitive file access.

    Args:
        desired_path: Path to ensure exists

    Returns:
        Path object for the created directory

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> path = ensure_path_exists("logs/2024/01")
        >>> print(f"Directory created: {path}")
        >>>
        >>> # This will raise PathSecurityError
        >>> ensure_path_exists("../../../etc")  # Path traversal blocked
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_directory_path, PathSecurityError
            path_obj = validate_directory_path(desired_path, must_exist=False)
        except ImportError:
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

    SECURITY: Validates paths to prevent zip slip attacks and path traversal.

    Args:
        zip_file_path: Path to the zip file
        extract_to: Directory to extract to (defaults to zip file's parent)
        create_subdirectory: Whether to create a subdirectory for extracted files

    Returns:
        Path to the extraction directory, or None if failed

    Raises:
        PathSecurityError: If paths fail security validation

    Example:
        >>> extract_dir = unzip_file_to_directory("data.zip")
        >>> print(f"Files extracted to: {extract_dir}")
    """
    try:
        # Validate paths
        try:
            from siege_utilities.files.validation import validate_file_path, validate_directory_path, PathSecurityError
            zip_path = validate_file_path(zip_file_path, must_exist=True)
        except ImportError:
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

        try:
            from siege_utilities.files.validation import validate_directory_path, PathSecurityError
            extract_dir = validate_directory_path(extract_to, must_exist=False)
        except ImportError:
            extract_dir = Path(extract_to)

        if create_subdirectory:
            # Create subdirectory based on zip file name
            subdir_name = zip_path.stem
            target_dir = extract_dir / subdir_name
        else:
            target_dir = extract_dir

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Extract files (with zip slip protection)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Validate each member to prevent zip slip attacks
            for member in zip_ref.namelist():
                member_path = target_dir / member
                # Resolve to absolute path and check it's within target_dir
                try:
                    member_path.resolve().relative_to(target_dir.resolve())
                except ValueError:
                    log.error(f"Zip slip attempt detected: {member}")
                    continue
            # If all members are safe, extract
            zip_ref.extractall(target_dir)

        log.info(f"Extracted {zip_path} to {target_dir}")
        return target_dir

    except zipfile.BadZipFile:
        log.error(f"Invalid zip file: {zip_file_path}")
        return None
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to extract {zip_file_path}: {e}")
        return None

def get_file_extension(file_path: FilePath) -> str:
    """
    Get the file extension from a file path.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        file_path: Path to the file

    Returns:
        File extension (including the dot)

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> ext = get_file_extension("document.pdf")
        >>> print(f"File extension: {ext}")  # .pdf
        >>>
        >>> # This will raise PathSecurityError
        >>> get_file_extension("../../../etc/passwd")  # Path traversal blocked
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
            path_obj = validate_safe_path(file_path, allow_absolute=True)
        except ImportError:
            path_obj = Path(file_path)

        return path_obj.suffix
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to get extension for {file_path}: {e}")
        raise

def get_file_name_without_extension(file_path: FilePath) -> str:
    """
    Get the file name without its extension.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        file_path: Path to the file

    Returns:
        File name without extension

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> name = get_file_name_without_extension("document.pdf")
        >>> print(f"File name: {name}")  # document
        >>>
        >>> # This will raise PathSecurityError
        >>> get_file_name_without_extension("../../../etc/shadow")  # Path traversal blocked
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
            path_obj = validate_safe_path(file_path, allow_absolute=True)
        except ImportError:
            path_obj = Path(file_path)

        return path_obj.stem
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to get filename for {file_path}: {e}")
        raise

def is_hidden_file(file_path: FilePath) -> bool:
    """
    Check if a file or directory is hidden.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        file_path: Path to check

    Returns:
        True if the file/directory is hidden

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> if is_hidden_file(".config"):
        ...     print("Hidden file detected")
        >>>
        >>> # This will raise PathSecurityError
        >>> is_hidden_file("../../.ssh/id_rsa")  # Path traversal blocked
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
            path_obj = validate_safe_path(file_path, allow_absolute=True)
        except ImportError:
            path_obj = Path(file_path)

        return path_obj.name.startswith('.')
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to check if hidden: {file_path}: {e}")
        raise

def get_relative_path(base_path: FilePath, target_path: FilePath) -> Optional[Path]:
    """
    Get the relative path from base_path to target_path.

    SECURITY: Validates both base and target paths to prevent path traversal attacks.

    Args:
        base_path: Base directory path
        target_path: Target file/directory path

    Returns:
        Relative path from base to target, or None if failed

    Raises:
        PathSecurityError: If paths fail security validation

    Example:
        >>> rel_path = get_relative_path("/home/user", "/home/user/documents/file.txt")
        >>> print(f"Relative path: {rel_path}")  # documents/file.txt
        >>>
        >>> # This will raise PathSecurityError
        >>> get_relative_path("/etc", "/etc/passwd")  # Sensitive path blocked
    """
    try:
        # Validate paths
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
            base = validate_safe_path(base_path, allow_absolute=True)
            target = validate_safe_path(target_path, allow_absolute=True)
        except ImportError:
            base = Path(base_path).resolve()
            target = Path(target_path).resolve()

        try:
            relative = target.relative_to(base)
            return relative
        except ValueError:
            log.warning(f"Target {target} is not relative to base {base}")
            return None
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to get relative path: {e}")
        return None

def find_files_by_pattern(directory: FilePath,
                         pattern: str = "*",
                         recursive: bool = False) -> list[Path]:
    """
    Find files matching a pattern in a directory.

    SECURITY: Validates directory path to prevent path traversal attacks.

    Args:
        directory: Directory to search in
        pattern: Glob pattern to match
        recursive: Whether to search recursively

    Returns:
        List of matching file paths

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> files = find_files_by_pattern("data", "*.csv", recursive=True)
        >>> print(f"Found {len(files)} CSV files")
        >>>
        >>> # This will raise PathSecurityError
        >>> find_files_by_pattern("../../../etc", "*")  # Path traversal blocked
    """
    try:
        # Validate directory path
        try:
            from siege_utilities.files.validation import validate_directory_path, PathSecurityError
            dir_path = validate_directory_path(directory, must_exist=True)
        except ImportError:
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
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to find files in {directory}: {e}")
        return []

def create_backup_path(original_path: FilePath,
                      backup_suffix: str = ".backup",
                      backup_dir: Optional[FilePath] = None) -> Path:
    """
    Create a backup path for a file.

    SECURITY: Validates both original and backup paths to prevent path traversal attacks.

    Args:
        original_path: Path to the original file
        backup_suffix: Suffix to add to the backup filename
        backup_dir: Directory to place backup in (defaults to original file's directory)

    Returns:
        Path for the backup file

    Raises:
        PathSecurityError: If paths fail security validation

    Example:
        >>> backup_path = create_backup_path("config.yaml", ".bak")
        >>> print(f"Backup will be saved to: {backup_path}")
        >>>
        >>> # This will raise PathSecurityError
        >>> create_backup_path("/etc/passwd", ".bak")  # Sensitive file blocked
    """
    try:
        # Validate original path
        try:
            from siege_utilities.files.validation import validate_safe_path, validate_directory_path, PathSecurityError
            original = validate_safe_path(original_path, allow_absolute=True)
        except ImportError:
            original = Path(original_path)

        if backup_dir is None:
            backup_dir = original.parent

        # Validate backup directory
        try:
            from siege_utilities.files.validation import validate_directory_path, PathSecurityError
            backup_dir_path = validate_directory_path(backup_dir, must_exist=False)
        except ImportError:
            backup_dir_path = Path(backup_dir)

        backup_dir_path.mkdir(parents=True, exist_ok=True)

        # Create backup filename
        backup_name = original.stem + backup_suffix + original.suffix
        backup_path = backup_dir_path / backup_name

        log.debug(f"Created backup path: {backup_path}")
        return backup_path
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to create backup path for {original_path}: {e}")
        raise

def normalize_path(path: FilePath) -> Path:
    """
    Normalize a file path, resolving any relative components.

    This function expands ~ (home directory), resolves .. (parent directory),
    and converts to an absolute path. It does NOT validate for security -
    use validate_safe_path() if you need security validation.

    Args:
        path: Path to normalize

    Returns:
        Normalized absolute path

    Example:
        >>> norm_path = normalize_path("~/../data/file.txt")
        >>> print(f"Normalized path: {norm_path}")

        >>> # Resolves relative paths
        >>> norm_path = normalize_path("./../data/file.txt")
    """
    try:
        path_obj = Path(path).expanduser().resolve()
        log.debug(f"Normalized {path} to {path_obj}")
        return path_obj
    except Exception as e:
        log.error(f"Failed to normalize path {path}: {e}")
        raise

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
