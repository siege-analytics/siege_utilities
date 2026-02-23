"""
Path validation and sanitization utilities for siege_utilities.

This module provides security-focused path validation to prevent:
- Path traversal attacks (../, ~/../, etc.)
- Access to sensitive system files and directories
- Symlink-based attacks
- Null byte injection

Use these validators in all file operations to ensure secure path handling.
"""

import os
import logging
from pathlib import Path
from typing import Union, Optional, List

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]


class PathSecurityError(Exception):
    """Raised when a path fails security validation."""
    pass


# Sensitive system paths that should never be accessed
SENSITIVE_PATHS = {
    # Unix/Linux sensitive files
    '/etc/passwd',
    '/etc/shadow',
    '/etc/sudoers',
    '/etc/ssh',
    '/root',
    '/var/log/auth.log',
    '/var/log/secure',

    # SSH keys
    '/.ssh',
    '/root/.ssh',
    '~/.ssh',

    # System binaries
    '/bin',
    '/sbin',
    '/usr/bin',
    '/usr/sbin',

    # Kernel and system
    '/proc',
    '/sys',
    '/dev',

    # macOS specific
    '/System',
    '/private/etc',

    # Windows sensitive (for cross-platform)
    'C:\\Windows\\System32',
    'C:\\Windows\\SysWOW64',
}


# Path traversal patterns to block
TRAVERSAL_PATTERNS = [
    '..',      # Parent directory
    '~/',      # Home directory expansion
    '~\\',     # Windows home directory
]


def is_path_traversal_attempt(path: FilePath) -> bool:
    """
    Check if a path contains traversal patterns.

    Args:
        path: Path to check

    Returns:
        True if path contains traversal patterns

    Example:
        >>> is_path_traversal_attempt("../../../etc/passwd")
        True
        >>> is_path_traversal_attempt("data/file.txt")
        False
    """
    path_str = str(path)

    # Check for common traversal patterns
    for pattern in TRAVERSAL_PATTERNS:
        if pattern in path_str:
            return True

    # Check for URL-encoded traversal
    if '%2e%2e' in path_str.lower() or '%2f' in path_str.lower():
        return True

    # Check for null bytes
    if '\x00' in path_str:
        return True

    return False


def is_sensitive_path(path: FilePath) -> bool:
    """
    Check if a path points to or contains a sensitive system location.

    Args:
        path: Path to check

    Returns:
        True if path is sensitive

    Example:
        >>> is_sensitive_path("/etc/passwd")
        True
        >>> is_sensitive_path("/home/user/data.txt")
        False
    """
    try:
        # Resolve to absolute path
        path_obj = Path(path).resolve()
        path_str = str(path_obj)

        # Check against sensitive paths
        for sensitive in SENSITIVE_PATHS:
            sensitive_resolved = str(Path(sensitive).expanduser())

            # Exact match or parent directory
            if path_str == sensitive_resolved or path_str.startswith(sensitive_resolved + os.sep):
                return True

        # Check for .ssh anywhere in path
        if '/.ssh/' in path_str or '\\.ssh\\' in path_str:
            return True

        # Check for private keys
        if path_str.endswith('id_rsa') or path_str.endswith('id_dsa') or path_str.endswith('id_ecdsa'):
            return True

        return False

    except Exception:
        # If we can't resolve, assume it's potentially dangerous
        return True


def validate_safe_path(path: FilePath,
                       allow_absolute: bool = True,
                       base_directory: Optional[FilePath] = None) -> Path:
    """
    Validate that a path is safe to access.

    Performs comprehensive security checks:
    1. Blocks path traversal attempts
    2. Blocks access to sensitive system paths
    3. Optionally restricts to a base directory
    4. Blocks null byte injection
    5. Resolves symlinks and checks final destination

    Args:
        path: Path to validate
        allow_absolute: Whether to allow absolute paths
        base_directory: If provided, path must be within this directory

    Returns:
        Validated Path object

    Raises:
        PathSecurityError: If path fails security validation
        ValueError: If path is invalid

    Example:
        >>> # Safe path
        >>> validated = validate_safe_path("data/file.txt")
        >>>
        >>> # Dangerous path (raises exception)
        >>> try:
        ...     validate_safe_path("../../../etc/passwd")
        ... except PathSecurityError as e:
        ...     print(f"Blocked: {e}")
        >>>
        >>> # Restrict to base directory
        >>> validated = validate_safe_path("subdir/file.txt", base_directory="/safe/dir")
    """
    if not path:
        raise ValueError("Path cannot be empty")

    path_str = str(path)

    # Check for null bytes
    if '\x00' in path_str:
        raise PathSecurityError(f"Null byte detected in path: {path_str}")

    # Check for path traversal
    if is_path_traversal_attempt(path):
        raise PathSecurityError(
            f"Path traversal attempt blocked: {path_str}"
        )

    try:
        # Convert to Path object
        path_obj = Path(path)

        # Check if absolute when not allowed
        if not allow_absolute and path_obj.is_absolute():
            raise PathSecurityError(
                f"Absolute paths not allowed: {path_str}"
            )

        # Resolve to absolute path (follows symlinks)
        resolved_path = path_obj.resolve()

        # Check if resolved path is sensitive
        if is_sensitive_path(resolved_path):
            raise PathSecurityError(
                f"Access to sensitive path blocked: {resolved_path}"
            )

        # If base directory specified, ensure path is within it
        if base_directory:
            base_path = Path(base_directory).resolve()

            try:
                # This raises ValueError if resolved_path is not relative to base_path
                resolved_path.relative_to(base_path)
            except ValueError:
                raise PathSecurityError(
                    f"Path {resolved_path} is outside base directory {base_path}"
                )

        log.debug(f"Path validation passed: {path_str} -> {resolved_path}")
        return resolved_path

    except PathSecurityError:
        # Re-raise our security errors
        raise
    except Exception as e:
        # Other errors during validation
        raise ValueError(f"Invalid path: {path_str} - {e}")


def validate_file_path(file_path: FilePath,
                       must_exist: bool = False,
                       base_directory: Optional[FilePath] = None) -> Path:
    """
    Validate a file path for read/write operations.

    Args:
        file_path: Path to validate
        must_exist: If True, path must exist
        base_directory: If provided, path must be within this directory

    Returns:
        Validated Path object

    Raises:
        PathSecurityError: If path fails security validation
        FileNotFoundError: If must_exist=True and file doesn't exist
        ValueError: If path is invalid

    Example:
        >>> # Validate existing file
        >>> path = validate_file_path("data.csv", must_exist=True)
        >>>
        >>> # Validate path for writing (doesn't need to exist)
        >>> path = validate_file_path("output.txt", must_exist=False)
    """
    validated_path = validate_safe_path(
        file_path,
        allow_absolute=True,
        base_directory=base_directory
    )

    if must_exist and not validated_path.exists():
        raise FileNotFoundError(f"File does not exist: {validated_path}")

    return validated_path


def validate_directory_path(dir_path: FilePath,
                           must_exist: bool = False,
                           base_directory: Optional[FilePath] = None) -> Path:
    """
    Validate a directory path.

    Args:
        dir_path: Path to validate
        must_exist: If True, directory must exist
        base_directory: If provided, path must be within this directory

    Returns:
        Validated Path object

    Raises:
        PathSecurityError: If path fails security validation
        FileNotFoundError: If must_exist=True and directory doesn't exist
        ValueError: If path is invalid or not a directory

    Example:
        >>> # Validate directory
        >>> path = validate_directory_path("logs", must_exist=True)
    """
    validated_path = validate_safe_path(
        dir_path,
        allow_absolute=True,
        base_directory=base_directory
    )

    if must_exist:
        if not validated_path.exists():
            raise FileNotFoundError(f"Directory does not exist: {validated_path}")
        if not validated_path.is_dir():
            raise ValueError(f"Path is not a directory: {validated_path}")

    return validated_path


def safe_join_paths(*paths: FilePath, base_directory: Optional[FilePath] = None) -> Path:
    """
    Safely join multiple path components with security validation.

    Args:
        *paths: Path components to join
        base_directory: If provided, result must be within this directory

    Returns:
        Validated joined Path object

    Raises:
        PathSecurityError: If any component or result fails security validation
        ValueError: If components are invalid

    Example:
        >>> # Safe join
        >>> path = safe_join_paths("data", "2024", "file.txt")
        >>>
        >>> # With base directory restriction
        >>> path = safe_join_paths("subdir", "file.txt", base_directory="/safe/dir")
    """
    if not paths:
        raise ValueError("At least one path component required")

    # Validate each component
    for component in paths:
        if is_path_traversal_attempt(component):
            raise PathSecurityError(
                f"Path traversal in component: {component}"
            )

    # Join paths
    joined = Path(paths[0])
    for component in paths[1:]:
        joined = joined / component

    # Validate final result
    return validate_safe_path(
        joined,
        allow_absolute=True,
        base_directory=base_directory
    )


__all__ = [
    'PathSecurityError',
    'is_path_traversal_attempt',
    'is_sensitive_path',
    'validate_safe_path',
    'validate_file_path',
    'validate_directory_path',
    'safe_join_paths',
]
