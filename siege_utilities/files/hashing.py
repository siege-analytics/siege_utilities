"""
Hash Management Functions - Fixed Version
Provides standardized hash functions that actually exist and work properly
"""
import hashlib
import pathlib
from typing import Optional

from siege_utilities.core.logging import log_info, log_error

# Module-level validation import. Falling open to raw pathlib.Path
# inside each function when the validation module is missing would
# silently disable the security guardrail; if validation is unavailable
# we want to know about it at import time instead of letting individual
# call sites silently downgrade.
try:
    from siege_utilities.files.validation import (
        validate_file_path,
        PathSecurityError,
    )
    _VALIDATION_AVAILABLE = True
except ImportError:  # pragma: no cover - validation should always be present
    validate_file_path = None  # type: ignore[assignment]

    class PathSecurityError(Exception):  # type: ignore[no-redef]
        """Placeholder when siege_utilities.files.validation is unavailable."""

    _VALIDATION_AVAILABLE = False
    log_error(
        "siege_utilities.files.validation not importable; "
        "hashing.py will operate WITHOUT path security guards. "
        "This is almost certainly a packaging bug — investigate."
    )

# 64 KiB — matches stdlib hashlib's recommended buffered-read size and
# what the reference filehash recipe uses. Centralised so we don't
# drift across the four hash helpers below.
_HASH_CHUNK_SIZE = 64 * 1024


def _validated_path(file_path, *, must_exist: bool):
    """Apply path validation if available; otherwise fall through.

    Centralising the per-function try/except blocks here.
    """
    if _VALIDATION_AVAILABLE:
        return validate_file_path(file_path, must_exist=must_exist)
    return pathlib.Path(file_path)


def _update_from_file(hash_obj, fp) -> None:
    """Feed *fp* into *hash_obj* in fixed-size chunks until EOF."""
    while True:
        chunk = fp.read(_HASH_CHUNK_SIZE)
        if not chunk:
            return
        hash_obj.update(chunk)


def generate_sha256_hash_for_file(file_path) -> str:
    """Generate SHA256 hash for a file - chunked reading for large files.

    .. deprecated:: 3.19.0
        Use :func:`calculate_file_hash` or :func:`get_file_hash` instead.
        Will be removed in v4.0.0.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the file (str or Path object)

    Returns:
        SHA256 hash as hexadecimal string.

    Raises:
        PathSecurityError: If path fails security validation.
        FileNotFoundError: If the file does not exist.
        ValueError: If the path is not a regular file.
        OSError: On I/O failure.
    """
    import warnings
    warnings.warn(
        "generate_sha256_hash_for_file is deprecated and will be removed in v4.0.0. "
        "Use calculate_file_hash or get_file_hash instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_file_hash(file_path, 'sha256')


def get_file_hash(file_path, algorithm='sha256') -> str:
    """
    Generate hash for a file using specified algorithm.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the file (str or Path object)
        algorithm: Hash algorithm to use ('sha256', 'md5', 'sha1', etc.)

    Returns:
        Hash as hexadecimal string.

    Raises:
        PathSecurityError: If path fails security validation.
        FileNotFoundError: If the file does not exist.
        ValueError: If the path is not a regular file or algorithm is unknown.
        OSError: On I/O failure.
    """
    path_obj = _validated_path(file_path, must_exist=True)
    if not path_obj.exists():
        raise FileNotFoundError(f"File does not exist: {path_obj}")
    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {path_obj}")
    if algorithm.lower() == 'sha256':
        hash_func = hashlib.sha256()
    elif algorithm.lower() == 'md5':
        hash_func = hashlib.md5()
    elif algorithm.lower() == 'sha1':
        hash_func = hashlib.sha1()
    else:
        hash_func = hashlib.new(algorithm)
    with open(path_obj, 'rb') as f:
        _update_from_file(hash_func, f)
    return hash_func.hexdigest()


def calculate_file_hash(file_path) -> str:
    """
    Alias for get_file_hash with SHA256 - for backward compatibility.
    """
    return get_file_hash(file_path, 'sha256')


def get_quick_file_signature(file_path) ->str:
    """
    Generate a quick file signature using file stats + partial hash
    Faster for change detection, not cryptographically secure

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the file

    Returns:
        Quick signature string ('missing', fallback stat string, or hash)

    Raises:
        PathSecurityError: If path fails security validation
        Exception: If both primary and fallback signature generation fail
            (logged before re-raise)

    Example:
        >>> sig = get_quick_file_signature("data.txt")
        >>>
        >>> # This will raise PathSecurityError
        >>> get_quick_file_signature("/etc/passwd")  # Sensitive file blocked

    Security Changes:
        - Now validates paths to block path traversal
        - Blocks access to sensitive system files
    """
    try:
        path_obj = _validated_path(file_path, must_exist=False)

        if not path_obj.exists():
            return 'missing'
        stat = path_obj.stat()
        if stat.st_size <= 1024 * 1024:
            return get_file_hash(file_path) or f'stat_{stat.st_size}_{stat.st_mtime}'
        # Past 1 MiB we always read both ends — the previous inner guard
        # `stat.st_size > 2 * _HASH_CHUNK_SIZE` was always true here
        # (2 * 64 KiB = 128 KiB < 1 MiB), so it was dead code.
        hash_obj = hashlib.sha256()
        with open(path_obj, 'rb') as f:
            first_chunk = f.read(_HASH_CHUNK_SIZE)
            hash_obj.update(first_chunk)
            f.seek(-_HASH_CHUNK_SIZE, 2)
            last_chunk = f.read(_HASH_CHUNK_SIZE)
            hash_obj.update(last_chunk)
        stat_string = f'{stat.st_size}_{stat.st_mtime}_{len(first_chunk)}'
        hash_obj.update(stat_string.encode())
        return hash_obj.hexdigest()
    except PathSecurityError:
        raise
    except (OSError, ValueError) as e:
        log_error(f'Error generating quick signature for {file_path}: {e}')
        try:
            stat = pathlib.Path(file_path).stat()
            return f'fallback_{stat.st_size}_{stat.st_mtime}'
        except OSError as fallback_exc:
            log_error(f'Fallback signature also failed for {file_path}: {fallback_exc}')
            raise


def verify_file_integrity(file_path, expected_hash, algorithm='sha256') ->bool:
    """
    Verify file integrity by comparing with expected hash

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files (through get_file_hash).

    Args:
        file_path: Path to the file
        expected_hash: Expected hash value
        algorithm: Hash algorithm used

    Returns:
        True if file matches expected hash, False if hash does not match

    Raises:
        PathSecurityError: If path fails security validation
        Exception: If hash computation fails (logged before re-raise)

    Example:
        >>> expected = "abc123..."
        >>> if verify_file_integrity("data.txt", expected):
        ...     print("File integrity verified")
        >>>
        >>> # This will raise PathSecurityError
        >>> verify_file_integrity("/etc/shadow", expected)  # Sensitive file blocked

    Security Changes:
        - Now validates paths via get_file_hash() to block path traversal
        - Blocks access to sensitive system files
    """
    try:
        current_hash = get_file_hash(file_path, algorithm)
        return current_hash is not None and current_hash.lower(
            ) == expected_hash.lower()
    except (OSError, ValueError) as exc:
        log_error(f"Failed to verify hash for {file_path}: {exc}")
        raise


def test_hash_functions():
    """Test the hash functions with a temporary file"""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt'
        ) as f:
        f.write('Hello, World! This is a test file for hashing.')
        test_file = f.name
    try:
        log_info('Testing hash functions...')
        sha256_hash = generate_sha256_hash_for_file(test_file)
        log_info(f'SHA256: {sha256_hash}')
        md5_hash = get_file_hash(test_file, 'md5')
        log_info(f'MD5: {md5_hash}')
        quick_sig = get_quick_file_signature(test_file)
        log_info(f'Quick signature: {quick_sig}')
        if sha256_hash:
            verification = verify_file_integrity(test_file, sha256_hash)
            log_info(f'Verification: {verification}')
        log_info('All hash functions working!')
    finally:
        os.unlink(test_file)


if __name__ == '__main__':
    test_hash_functions()
