"""
Path validation and sanitization utilities for siege_utilities.

This module provides security-focused path validation to prevent:
- Path traversal attacks (../, ~/../, etc.)
- Access to sensitive system files and directories
- Symlink-based attacks
- Null byte injection

Use base_directory to confine paths to a trusted directory. Without a base,
the sensitive-path blocklist is not a sandbox.
"""

import os
import logging
from pathlib import Path, PureWindowsPath
from typing import Union, Optional

from siege_utilities.core._sensitive_paths import ROOT_CREDENTIAL_STORES

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]


class PathSecurityError(Exception):
    """Raised when a path fails security validation."""
    pass


# File-only additions, subject to the /dev and /root exceptions below.
# Unlike the shell policy, logs and shadow backups use exact path components.
_FILE_SENSITIVE_PATH_ADDITIONS = {
    # Unix/Linux sensitive files
    '/etc/passwd',
    '/etc/passwd-',
    '/etc/shadow',
    '/etc/shadow-',
    '/etc/gshadow',
    '/etc/gshadow-',
    '/etc/sudoers',
    '/etc/ssh',
    '/root',
    '/root/.bash_history',
    '/root/.zsh_history',
    '/var/log/auth.log',
    '/var/log/secure',

    # SSH keys
    '/.ssh',
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

SENSITIVE_PATHS = _FILE_SENSITIVE_PATH_ADDITIONS | ROOT_CREDENTIAL_STORES

# C0 controls, DEL and C1 controls. Names containing them break line-oriented
# tools and can replay terminal escapes when listed (#1692).
_CONTROL_CHARACTERS = frozenset(
    [chr(c) for c in range(0x20)] + ['\x7f'] + [chr(c) for c in range(0x80, 0xA0)]
)


def _is_unsafe_name_character(ch: str) -> bool:
    # Lone surrogates are how undecodable (non-UTF-8) bytes reach Python via
    # surrogateescape; a directory created from one has a non-UTF-8 name (#1716).
    return ch in _CONTROL_CHARACTERS or '\ud800' <= ch <= '\udfff'


def is_path_traversal_attempt(path: FilePath) -> bool:
    """
    Check for parent components, home expansion, or null bytes in a local path.

    Both slash styles are treated as separators for this check. Percent
    sequences such as %2f and %2e%2e are literal filename characters; they
    are neither decoded nor rejected. Dots within a name are also literal.

    Parameters
    ----------
    path : str or Path
        Local filesystem path to check.

    Returns
    -------
    bool
        Whether the path contains a prohibited component or null byte.

    Examples
    --------
        >>> is_path_traversal_attempt("../../../etc/passwd")
        True
        >>> is_path_traversal_attempt("data/file.txt")
        False
    """
    path_str = str(path)

    normalized = path_str.replace('\\', '/')
    return (
        '..' in normalized.split('/')
        or '..' in PureWindowsPath(normalized).parts
        or normalized.startswith('~/')
        or '\x00' in path_str
    )


def is_sensitive_path(path: FilePath, base_directory: Optional[FilePath] = None) -> bool:
    """
    Check if a path points to or contains a sensitive system location.

    Under /dev, only /dev/shm and its descendants and the exact pseudo-devices
    /dev/null, /dev/zero, /dev/random, and /dev/urandom escape the directory ban.
    The /root tree is blocked except for paths contained in a resolved cwd or
    base_directory that is /root or one of its descendants. Other sensitive-path
    checks, including root's credential files, still apply in both cases.

    Parameters
    ----------
    path : str or Path
        Path to check, resolved before applying the blocklist.
    base_directory : str or Path, optional
        Operating base for the /root exception; this function does not enforce
        containment. Relative paths still resolve against the cwd.

    Returns
    -------
    bool
        True if the path is sensitive or cannot be resolved.

    Example:
        >>> is_sensitive_path("/etc/passwd")
        True
        >>> is_sensitive_path("/tmp/data.txt")
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
                if sensitive == '/dev' and (
                    path_str in {'/dev/null', '/dev/zero', '/dev/random', '/dev/urandom'}
                    or path_obj == Path('/dev/shm')
                    or Path('/dev/shm') in path_obj.parents
                ):
                    continue
                if sensitive == '/root':
                    anchors = [Path.cwd().resolve()]
                    if base_directory is not None:
                        anchors.append(Path(base_directory).resolve())
                    if any(
                        anchor.is_relative_to('/root') and path_obj.is_relative_to(anchor)
                        for anchor in anchors
                    ):
                        continue
                return True

        # Check for .ssh anywhere in path
        if '.ssh' in path_obj.parts:
            return True

        # Check for private keys: exact default names, or a '_'/'-' separated
        # prefix (deploy_id_rsa, github-id_ed25519), but not paid_rsa (#1702)
        name = path_obj.name
        if any(name == k or name.endswith(("_" + k, "-" + k))
               for k in ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")):
            return True

        return False

    except (OSError, RuntimeError, TypeError):
        # If we can't resolve, assume it's potentially dangerous
        return True


def validate_safe_path(path: FilePath,
                       allow_absolute: bool = True,
                       base_directory: Optional[FilePath] = None) -> Path:
    """
    Validate that a path is safe to access.

    Performs the following checks:
    1. Blocks path traversal attempts
    2. Blocks access to sensitive system paths
    3. Optionally restricts to a base directory
    4. Blocks null byte injection
    5. Resolves symlinks and checks final destination

    Without base_directory, the blocklist is not a sandbox: absolute paths
    outside the listed sensitive locations are allowed by default. Supply
    a trusted base for untrusted paths. Percent sequences are kept literal.
    The /dev and /root exceptions follow is_sensitive_path, including the
    requirement that a path be contained in a resolved cwd or base at or below
    /root for its tree exception. Root's credential files remain blocked.
    Checks describe the filesystem at validation time; they do not prevent
    concurrent symlink changes between validation and a subsequent operation.

    Parameters
    ----------
    path : str or Path
        Path to validate. Relative paths are resolved against the current
        working directory, not joined onto base_directory.
    allow_absolute : bool, default True
        Whether to allow absolute paths.
    base_directory : str or Path, optional
        Resolved containment boundary, including for symlink destinations.

    Returns
    -------
    Path
        Validated absolute path.

    Raises
    ------
    PathSecurityError
        If the path fails security validation.
    ValueError
        If the path is invalid.

    Examples
    --------
        >>> # Safe path
        >>> validated = validate_safe_path("data/file.txt")
        >>>
        >>> try:
        ...     validate_safe_path("../../../etc/passwd")
        ... except PathSecurityError as e:
        ...     pass  # raises PathSecurityError
        >>>
        >>> validated = validate_safe_path("/safe/dir/subdir/file.txt", base_directory="/safe/dir")  # doctest: +SKIP
    """
    if not path:
        raise ValueError("Path cannot be empty")

    path_str = str(path)

    # Check for null bytes
    if '\x00' in path_str:
        raise PathSecurityError(f"Null byte detected in path: {path_str!r}")

    # Check for path traversal
    if is_path_traversal_attempt(path):
        raise PathSecurityError(
            f"Path traversal attempt blocked: {path_str!r}"
        )

    try:
        # Convert to Path object
        path_obj = Path(path)

        # Check if absolute when not allowed
        if not allow_absolute and path_obj.is_absolute():
            raise PathSecurityError(
                f"Absolute paths not allowed: {path_str!r}"
            )

        # Resolve to absolute path (follows symlinks)
        resolved_path = path_obj.resolve()

        # Check if resolved path is sensitive
        if is_sensitive_path(resolved_path, base_directory=base_directory):
            raise PathSecurityError(
                f"Access to sensitive path blocked: {str(resolved_path)!r}"
            )

        # If base directory specified, ensure path is within it
        if base_directory is not None:
            base_path = Path(base_directory).resolve()

            try:
                # This raises ValueError if resolved_path is not relative to base_path
                resolved_path.relative_to(base_path)
            except ValueError as e:
                raise PathSecurityError(
                    f"Path {str(resolved_path)!r} is outside base directory {str(base_path)!r}"
                ) from e

        log.debug(f"Path validation passed: {path_str!r} -> {str(resolved_path)!r}")
        return resolved_path

    except PathSecurityError:
        # Re-raise our security errors
        raise
    except (OSError, RuntimeError, TypeError) as e:
        # Other errors during validation
        raise ValueError(f"Invalid path: {path_str!r} - {e}") from e


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
        >>> path = validate_file_path("data.csv", must_exist=True)  # doctest: +SKIP
        >>>
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


def _reject_control_characters_in_new_components(path: Path) -> None:
    """Raise if a not-yet-existing component of a resolved path has a control
    character or a lone surrogate."""
    current = path
    # os.path.exists, unlike Path.exists on 3.11, returns False on any OSError
    # (e.g. ENAMETOOLONG), leaving that failure to the caller's mkdir.
    while not os.path.exists(current) and current != current.parent:
        if any(_is_unsafe_name_character(ch) for ch in current.name):
            raise PathSecurityError(
                f"Control character or undecodable byte in new directory name "
                f"{current.name!r}: {str(path)!r}"
            )
        current = current.parent


def reject_unsafe_new_directory_names(directory: FilePath) -> Path:
    """Refuse a directory path whose not-yet-existing components would be unsafe names.

    Call this immediately before ``Path(directory).mkdir(parents=True)``, for
    example on a file's parent. The path is checked as written, not resolved,
    because that is what ``mkdir`` creates: in ``a/<new>/../b`` it creates
    ``<new>`` on the way, so ``<new>`` is checked even though ``..`` cancels
    it. Components that already exist (including symlinks) are accepted
    whatever their name; a new one containing a C0, DEL or C1 control, or a
    lone surrogate (undecodable bytes), raises. Nothing is created.

    Returns:
        ``directory`` as a Path, unchanged.

    Raises:
        PathSecurityError: If a component to be created has an unsafe name.
    """
    path = Path(directory)
    prefix = Path(path.anchor)
    for part in path.parts[1 if path.anchor else 0:]:
        prefix = prefix / part
        if part in ('.', '..'):
            continue
        # lexists returns False on errors such as an unencodable name, so
        # such a component is treated as new and checked.
        if not os.path.lexists(prefix) and any(_is_unsafe_name_character(ch) for ch in part):
            raise PathSecurityError(
                f"Control character or undecodable byte in new name "
                f"{part!r}: {str(path)!r}"
            )
    return path


def reject_unsafe_new_file_path(file_path: FilePath) -> Path:
    """Refuse a file path whose new components, the file name included, would be unsafe names.

    Call this immediately before creating ``file_path``. It applies the same
    as-written check as :func:`reject_unsafe_new_directory_names` to every
    component, so a new file name containing a C0, DEL or C1 control, or a
    lone surrogate, raises, as does any new parent directory. An existing
    file may be overwritten whatever its name (#1737). Nothing is created.

    Returns:
        ``file_path`` as a Path, unchanged.

    Raises:
        PathSecurityError: If a component to be created has an unsafe name.
    """
    return reject_unsafe_new_directory_names(file_path)


def validate_directory_path(dir_path: FilePath,
                           must_exist: bool = False,
                           base_directory: Optional[FilePath] = None) -> Path:
    """
    Validate a directory path.

    When must_exist is False the directory may be about to be created, so any
    component that does not exist yet must be free of control characters (C0,
    DEL, C1). Existing directories with such names still validate, provided
    they can be stat'ed; one under an unreadable parent counts as new.

    Args:
        dir_path: Path to validate
        must_exist: If True, directory must exist
        base_directory: If provided, path must be within this directory

    Returns:
        Validated Path object

    Raises:
        PathSecurityError: If path fails security validation, or a component
            that would be created contains a control character
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

    if not must_exist:
        _reject_control_characters_in_new_components(validated_path)

    if must_exist:
        if not validated_path.exists():
            raise FileNotFoundError(f"Directory does not exist: {validated_path}")
        if not validated_path.is_dir():
            raise ValueError(f"Path is not a directory: {validated_path}")

    return validated_path


def safe_join_paths(*paths: FilePath, base_directory: Optional[FilePath] = None) -> Path:
    """
    Join paths within a resolved base and apply security validation.

    Absolute, rooted, and drive-qualified components after the first are
    rejected, including Windows forms on other platforms. The first component
    is the default containment base. A supplied base overrides that boundary;
    it does not get prepended to the joined path. Symlink destinations must
    remain within the resolved base, using path-component boundaries.

    Parameters
    ----------
    *paths : str or Path
        Path components to join. Relative paths use the working directory.
    base_directory : str or Path, optional
        Containment boundary, defaulting to the first component.

    Returns
    -------
    Path
        Validated absolute joined path.

    Raises
    ------
    PathSecurityError
        If a component or the result fails security validation.
    ValueError
        If no components are provided or a path is invalid.

    Examples
    --------
        >>> # Safe join
        >>> path = safe_join_paths("data", "2024", "file.txt")
        >>>
        >>> path = safe_join_paths("/safe/dir/subdir", "file.txt", base_directory="/safe/dir")  # doctest: +SKIP
    """
    if not paths:
        raise ValueError("At least one path component required")

    # Validate each component
    for index, component in enumerate(paths):
        if is_path_traversal_attempt(component):
            raise PathSecurityError(
                f"Path traversal in component: {component}"
            )
        if index and (Path(component).is_absolute() or PureWindowsPath(component).anchor):
            raise PathSecurityError(
                f"Absolute or drive-qualified path component not allowed: {component}"
            )

    # Join paths
    joined = Path(paths[0])
    for component in paths[1:]:
        joined = joined / component

    # Validate final result
    return validate_safe_path(
        joined,
        allow_absolute=True,
        base_directory=paths[0] if base_directory is None else base_directory
    )


__all__ = [
    'PathSecurityError',
    'is_path_traversal_attempt',
    'is_sensitive_path',
    'validate_safe_path',
    'validate_file_path',
    'validate_directory_path',
    'reject_unsafe_new_directory_names',
    'reject_unsafe_new_file_path',
    'safe_join_paths',
]
