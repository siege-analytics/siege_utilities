"""
Modern file operations for siege_utilities.
Provides clean, type-safe file manipulation utilities.
"""

import contextlib
import json
import os
import re
import subprocess
import shutil
import logging
import tempfile
from typing import Generator, Union, Optional, List, Any
from pathlib import Path

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]

# Characters that are unsafe in a filename across the common filesystems.
# Anything that is not a word char, dot, or hyphen is replaced.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\-]+")


def sanitize_filename(name: str) -> str:
    """Convert an arbitrary string into a safe filename component.

    Unsafe characters (path separators, control characters, punctuation other
    than ``.`` and ``-``) are replaced with underscores, runs of underscores
    are collapsed, and leading/trailing dots and underscores are trimmed. The
    result is always a non-empty string and the operation is idempotent
    (``sanitize_filename(sanitize_filename(x)) == sanitize_filename(x)``).

    Parameters
    ----------
    name : str
        Arbitrary input string.

    Returns
    -------
    str
        A filesystem-safe filename component.

    Raises
    ------
    TypeError
        If ``name`` is not a string.
    """
    if not isinstance(name, str):
        raise TypeError(f"name must be str, got {type(name).__name__}")

    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", name)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("._")
    return cleaned or "_"


@contextlib.contextmanager
def atomic_write_path(target: FilePath) -> Generator[Path, None, None]:
    """Context manager that yields a temporary path for writing, then
    atomically replaces the target on successful exit.

    Usage::

        with atomic_write_path("/data/output.csv") as tmp:
            df.to_csv(tmp, index=False)
        # target is now atomically updated

    If the block raises, the temp file is cleaned up and the target
    is left unchanged.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent,
        prefix="atomic_",
        suffix=target.suffix or ".tmp",
    )
    os.close(fd)
    tmp = Path(tmp_path)
    try:
        yield tmp
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_shapefile(gdf, target: FilePath, **kwargs) -> None:
    """Write a GeoDataFrame as a Shapefile atomically.

    Shapefiles produce sidecar files (.shx, .dbf, .prj, .cpg). This writes
    to a temp stem then renames all produced files to the final stem.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=target.parent, prefix="atomic_shp_"))
    tmp_shp = tmp_dir / target.name
    try:
        gdf.to_file(str(tmp_shp), driver="ESRI Shapefile", **kwargs)
        for f in tmp_dir.iterdir():
            dest = target.parent / (target.stem + f.suffix)
            os.replace(f, dest)
        tmp_dir.rmdir()
    except BaseException:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def remove_tree(path: FilePath) -> None:
    """
    Remove a file or directory tree safely.

    SECURITY: Validates paths to prevent removing sensitive system files.

    Args:
        path: Path to file or directory to remove

    Raises:
        FileNotFoundError: If path does not exist
        PathSecurityError: If path fails security validation
        OSError: If removal fails

    Example:
        >>> remove_tree("temp_directory")  # doctest: +SKIP
        >>> remove_tree(Path("old_files"))  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_safe_path
        path_obj = validate_safe_path(path, allow_absolute=True)
    except ImportError:
        path_obj = Path(path)

    if path_obj.is_file():
        path_obj.unlink()
        log.info(f"Removed file: {path_obj}")
    elif path_obj.is_dir():
        shutil.rmtree(path_obj)
        log.info(f"Removed directory tree: {path_obj}")
    else:
        raise FileNotFoundError(f"Path does not exist: {path_obj}")

def file_exists(path: FilePath) -> bool:
    """
    Check if a file exists at the specified path.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        path: Path to check

    Returns:
        True if file exists, False otherwise

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> if file_exists("config.yaml"):  # doctest: +SKIP
        ...     print("Config file found")
        >>> file_exists("../../../etc/passwd")  # doctest: +SKIP

    Security Changes:
        - Now validates paths to block path traversal
        - Blocks access to sensitive system files
    """
    try:
        # Import validation function
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
        except ImportError:
            # Fallback: use basic Path validation without security checks
            log.warning("Path validation module not available - using basic validation")
            path_obj = Path(path)
        else:
            # Validate path with security checks
            try:
                path_obj = validate_safe_path(path, allow_absolute=True)
            except PathSecurityError as e:
                log.error(f"Path security validation failed: {e}")
                raise  # Re-raise to caller

        exists = path_obj.exists()
        log.debug(f"File exists check for {path}: {exists}")
        return exists

    except PathSecurityError:
        # Re-raise security errors
        raise
    except OSError as e:
        log.error(f"Error checking file existence for {path}: {e}")
        return False

def touch_file(path: FilePath, create_parents: bool = True) -> None:
    """
    Create an empty file, creating parent directories if needed.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        path: Path to the file to create
        create_parents: Whether to create parent directories

    Raises:
        PathSecurityError: If path fails security validation
        OSError: If file creation fails

    Example:
        >>> touch_file("logs/app.log")  # doctest: +SKIP
        >>> touch_file(Path("data/output.txt"))  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_safe_path
        path_obj = validate_safe_path(path, allow_absolute=True)
    except ImportError:
        path_obj = Path(path)

    if create_parents:
        path_obj.parent.mkdir(parents=True, exist_ok=True)

    path_obj.touch(exist_ok=True)
    log.info(f"Created/updated file: {path_obj}")

def count_lines(file_path: FilePath, encoding: str = 'utf-8') -> int:
    """
    Count the total number of lines in a text file.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the text file
        encoding: File encoding to use

    Returns:
        Number of lines

    Raises:
        FileNotFoundError: If file does not exist or is not a file
        PathSecurityError: If path fails security validation
        OSError: If file cannot be read
        UnicodeDecodeError: If file cannot be decoded with given encoding

    Example:
        >>> line_count = count_lines("data.csv")  # doctest: +SKIP
        >>> print(f"File has {line_count} lines")  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        path_obj = validate_file_path(file_path, must_exist=True)
    except ImportError:
        path_obj = Path(file_path)

    if not path_obj.exists():
        raise FileNotFoundError(f"File does not exist: {path_obj}")

    if not path_obj.is_file():
        raise FileNotFoundError(f"Path is not a file: {path_obj}")

    with open(path_obj, 'r', encoding=encoding) as f:
        line_count = sum(1 for _ in f)

    log.info(f"Counted {line_count} lines in {path_obj}")
    return line_count

def copy_file(source: FilePath, destination: FilePath, overwrite: bool = False) -> None:
    """
    Copy a file from source to destination.

    SECURITY: Validates both source and destination paths.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Raises:
        FileNotFoundError: If source does not exist or is not a file
        FileExistsError: If destination exists and overwrite=False
        PathSecurityError: If paths fail security validation
        OSError: If copy fails

    Example:
        >>> copy_file("source.txt", "backup/source.txt")  # doctest: +SKIP
        >>> copy_file(Path("config.yaml"), Path("config.yaml.bak"))  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_file_path, validate_safe_path
        source_obj = validate_file_path(source, must_exist=True)
        dest_obj = validate_safe_path(destination, allow_absolute=True)
    except ImportError:
        source_obj = Path(source)
        dest_obj = Path(destination)

    if not source_obj.exists():
        raise FileNotFoundError(f"Source file does not exist: {source_obj}")

    if not source_obj.is_file():
        raise FileNotFoundError(f"Source is not a file: {source_obj}")

    dest_obj.parent.mkdir(parents=True, exist_ok=True)

    if dest_obj.exists() and not overwrite:
        raise FileExistsError(f"Destination file exists and overwrite=False: {dest_obj}")

    shutil.copy2(source_obj, dest_obj)
    log.info(f"Copied {source_obj} to {dest_obj}")

def move_file(source: FilePath, destination: FilePath, overwrite: bool = False) -> None:
    """
    Move a file from source to destination.

    SECURITY: Validates both source and destination paths.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Raises:
        FileNotFoundError: If source does not exist or is not a file
        FileExistsError: If destination exists and overwrite=False
        PathSecurityError: If paths fail security validation
        OSError: If move fails

    Example:
        >>> move_file("temp.txt", "archive/temp.txt")  # doctest: +SKIP
        >>> move_file(Path("old.log"), Path("logs/old.log"))  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_file_path, validate_safe_path
        source_obj = validate_file_path(source, must_exist=True)
        dest_obj = validate_safe_path(destination, allow_absolute=True)
    except ImportError:
        source_obj = Path(source)
        dest_obj = Path(destination)

    if not source_obj.exists():
        raise FileNotFoundError(f"Source file does not exist: {source_obj}")

    if not source_obj.is_file():
        raise FileNotFoundError(f"Source is not a file: {source_obj}")

    dest_obj.parent.mkdir(parents=True, exist_ok=True)

    if dest_obj.exists() and not overwrite:
        raise FileExistsError(f"Destination file exists and overwrite=False: {dest_obj}")

    shutil.move(str(source_obj), str(dest_obj))
    log.info(f"Moved {source_obj} to {dest_obj}")

def get_file_size(file_path: FilePath) -> int:
    """
    Get the size of a file in bytes.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes

    Raises:
        FileNotFoundError: If file does not exist or is not a file
        PathSecurityError: If path fails security validation
        OSError: If file size cannot be determined

    Example:
        >>> size = get_file_size("large_file.zip")  # doctest: +SKIP
        >>> print(f"File size: {size} bytes")  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        path_obj = validate_file_path(file_path, must_exist=True)
    except ImportError:
        path_obj = Path(file_path)

    if not path_obj.exists():
        raise FileNotFoundError(f"File does not exist: {path_obj}")

    if not path_obj.is_file():
        raise FileNotFoundError(f"Path is not a file: {path_obj}")

    size = path_obj.stat().st_size
    log.debug(f"File size for {path_obj}: {size} bytes")
    return size

def list_directory(path: FilePath,
                  pattern: str = "*",
                  include_dirs: bool = True,
                  include_files: bool = True) -> List[Path]:
    """
    List contents of a directory with optional filtering.

    SECURITY: Validates directory path to prevent traversal attacks.

    Args:
        path: Directory path to list
        pattern: Glob pattern for filtering files
        include_dirs: Whether to include directories
        include_files: Whether to include files

    Returns:
        List of Path objects

    Raises:
        FileNotFoundError: If directory does not exist or is not a directory
        PathSecurityError: If path fails security validation
        OSError: If directory cannot be read

    Example:
        >>> files = list_directory("data", "*.csv")  # doctest: +SKIP
        >>> dirs = list_directory("logs", include_files=False)  # doctest: +SKIP
    """
    try:
        from siege_utilities.files.validation import validate_directory_path
        path_obj = validate_directory_path(path, must_exist=True)
    except ImportError:
        path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Directory does not exist: {path_obj}")

    if not path_obj.is_dir():
        raise FileNotFoundError(f"Path is not a directory: {path_obj}")

    items = []

    for item in path_obj.glob(pattern):
        if item.is_dir() and include_dirs:
            items.append(item)
        elif item.is_file() and include_files:
            items.append(item)

    log.debug(f"Listed {len(items)} items in {path_obj}")
    return sorted(items)

def run_command(command: Union[str, List[str]],
                cwd: Optional[FilePath] = None,
                timeout: Optional[int] = 30,
                capture_output: bool = True,
                allow_list: Optional[set] = None,
                unsafe: bool = False) -> subprocess.CompletedProcess:
    """
    Run a shell command with security validation and proper error handling.

    SECURITY: This function now validates commands by default. Only whitelisted
    commands are allowed unless unsafe=True is explicitly set.

    Args:
        command: Command to run (string or list)
        cwd: Working directory for the command
        timeout: Timeout in seconds (default: 30)
        capture_output: Whether to capture command output
        allow_list: Optional custom whitelist of allowed commands
        unsafe: If True, bypass the allow-list check. The command is
            still executed via argv (shell=False) — string commands are
            shlex-split and run without shell expansion. Use this when
            you legitimately need a binary that isn't in the allow-list,
            not when you need shell features.

    Returns:
        CompletedProcess object on success or non-zero exit.

    Raises:
        SecurityError: If command fails security validation (when unsafe=False).
        subprocess.TimeoutExpired: If the command exceeds *timeout*.
        OSError: If the command binary cannot be found or executed.

    Example:
        >>> result = run_command("ls -la")  # doctest: +SKIP
        >>> if result and result.returncode == 0:  # doctest: +SKIP
        ...     print("Command succeeded")
        >>> result = run_command("rm -rf /")  # doctest: +SKIP
        >>> result = run_command("git status", allow_list={'git', 'ls'})  # doctest: +SKIP
        >>> result = run_command("custom_cmd", unsafe=True)  # doctest: +SKIP

    Security Changes:
        - Previously used shell=True with no validation (CRITICAL VULNERABILITY)
        - Now validates all commands against whitelist by default
        - Blocks command injection, path traversal, sensitive file access
        - Use unsafe=True ONLY with trusted input in trusted environments
    """
    try:
        # Import validation function
        try:
            from siege_utilities.files.shell import validate_command_safety, SecurityError
        except ImportError as imp_err:
            # Fallback: define minimal SecurityError
            class SecurityError(Exception):
                pass
            # If we can't import validation, we must be in unsafe mode or fail
            if not unsafe:
                log.error("Cannot validate command: security module not available")
                raise SecurityError("Security validation unavailable") from imp_err

        # Parse command. In unsafe mode we additionally reject string
        # commands that contain shell metacharacters — callers that
        # previously relied on pipes / redirects / globs / $VAR under
        # shell=True now get a clear error instead of silently-different
        # argv-level behaviour. The remediation is documented: pass a
        # list directly.
        _SHELL_META = "|&;<>(){}$`*?#~"
        if isinstance(command, str):
            if unsafe and any(ch in command for ch in _SHELL_META):
                raise ValueError(
                    f"run_command(unsafe=True) refuses string commands "
                    f"containing shell metacharacters ({_SHELL_META!r}); "
                    f"pass a list[str] argv to run those, or invoke "
                    f"subprocess directly with shell=True."
                )
            import shlex
            try:
                command_list = shlex.split(command)
            except ValueError:
                command_list = [command]
        else:
            command_list = list(command)

        # Security validation (unless explicitly bypassed)
        if not unsafe:
            try:
                validated_command = validate_command_safety(command_list, allow_list)
                command_to_run = validated_command
            except (SecurityError, ValueError) as e:
                log.error(f"Security validation failed: {e}")
                raise
        else:
            # Unsafe mode: skip the allow-list but still run the command
            # via argv (shell=False). Bypassing the whitelist is the
            # caller's risk to take; bypassing argv-level argument
            # parsing would let the string be interpreted by /bin/sh,
            # which is a separate (and worse) class of vulnerability we
            # don't expose here.
            log.warning(
                "run_command(unsafe=True): allow-list bypassed; "
                "argv-level execution preserved (no shell expansion)"
            )
            command_to_run = command_list

        # Validate cwd if provided
        validated_cwd = None
        if cwd is not None:
            try:
                from siege_utilities.files.validation import validate_safe_path
                validated_cwd = str(validate_safe_path(cwd, allow_absolute=True))
            except ImportError:
                validated_cwd = str(cwd)

        # Execute command. shell=False unconditionally — argv list, no
        # /bin/sh interpretation of the command string.
        result = subprocess.run(
            command_to_run,
            shell=False,
            cwd=validated_cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True
        )

        if result.returncode == 0:
            log.info(f"Command succeeded: {command}")
        else:
            log.warning(f"Command failed with code {result.returncode}: {command}")
            if result.stderr:
                log.warning(f"Error output: {result.stderr}")

        return result

    except subprocess.TimeoutExpired:
        log.error(f"Command timed out: {command}")
        raise
    except (OSError, ValueError) as e:
        log.error(f"Failed to run command {command}: {e}")
        raise

# Backward compatibility aliases
rmtree = remove_tree


def check_if_file_exists_at_path(path: FilePath) -> bool:
    """Check if a file exists at the specified path.

    .. deprecated:: 3.19.0
        Use :func:`file_exists` instead. Will be removed in v4.0.0.
    """
    import warnings
    warnings.warn(
        "check_if_file_exists_at_path is deprecated and will be removed in v4.0.0. "
        "Use file_exists instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return file_exists(path)


def delete_existing_file_and_replace_it_with_an_empty_file(file_path: FilePath, create_parents: bool = True) -> None:
    """Backward compatibility function that deletes existing file and replaces it with empty file.

    .. deprecated:: 3.19.0
        Use :func:`touch_file` for creating empty files. Note that ``touch_file``
        does not delete the existing file first; if you need delete-then-create
        semantics, call ``Path.unlink()`` before ``touch_file()``.
        Will be removed in v4.0.0.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        file_path: Path to the file
        create_parents: Whether to create parent directories

    Raises:
        PathSecurityError: If path fails security validation
        OSError: If file creation fails
    """
    import warnings
    warnings.warn(
        "delete_existing_file_and_replace_it_with_an_empty_file is deprecated and "
        "will be removed in v4.0.0. Use touch_file instead (note: touch_file does "
        "not delete the existing file first).",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
            path_obj = validate_safe_path(file_path, allow_absolute=True)
        except ImportError:
            path_obj = Path(file_path)

        # Create parent directories if needed
        if create_parents:
            path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing file if it exists
        if path_obj.exists():
            path_obj.unlink()

        path_obj.touch()
        log.info(f"Created/updated empty file: {path_obj}")
    except PathSecurityError:
        raise
    except OSError as e:
        raise OSError(f"Failed to create empty file {file_path}") from e

count_total_rows_in_file_pythonically = count_lines


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to directory

    Returns:
        Path object for the directory

    Raises:
        PathSecurityError: If path fails security validation.
    """
    try:
        from siege_utilities.files.validation import validate_safe_path
        dir_path = validate_safe_path(directory, allow_absolute=True)
    except ImportError:
        dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_file_write(
    file_path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    create_dirs: bool = True,
) -> bool:
    """
    Safely write content to a file, optionally creating parent directories.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding (default: utf-8)
        create_dirs: Create parent directories if they don't exist

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If path fails security validation.
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        validated = validate_file_path(file_path, must_exist=False)
    except ImportError:
        validated = Path(file_path)
    try:
        if create_dirs:
            validated.parent.mkdir(parents=True, exist_ok=True)
        with open(validated, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except (OSError, TypeError) as e:
        log.error(f"Error writing to {validated}: {e}")
        return False


def safe_file_read(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Safely read content from a file.

    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)
        default: Default value to return if file doesn't exist or error occurs

    Returns:
        File content or default value

    Raises:
        PathSecurityError: If path fails security validation.
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        validated = validate_file_path(file_path, must_exist=False)
    except ImportError:
        validated = Path(file_path)
    try:
        if not validated.exists():
            return default
        with open(validated, "r", encoding=encoding) as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        log.error(f"Error reading {validated}: {e}")
        return default


def safe_json_write(
    file_path: Union[str, Path],
    data: Any,
    indent: int = 2,
    create_dirs: bool = True,
) -> bool:
    """
    Safely write data to a JSON file.

    Args:
        file_path: Path to JSON file
        data: Data to write (must be JSON serializable)
        indent: JSON indentation (default: 2)
        create_dirs: Create parent directories if they don't exist

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If path fails security validation.
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        validated = validate_file_path(file_path, must_exist=False)
    except ImportError:
        validated = Path(file_path)
    try:
        if create_dirs:
            validated.parent.mkdir(parents=True, exist_ok=True)
        with open(validated, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except (OSError, TypeError, ValueError) as e:
        log.error(f"Error writing JSON to {validated}: {e}")
        return False


def safe_json_read(
    file_path: Union[str, Path],
    default: Optional[Any] = None,
) -> Optional[Any]:
    """
    Safely read data from a JSON file.

    Args:
        file_path: Path to JSON file
        default: Default value to return if file doesn't exist or error occurs

    Returns:
        Parsed JSON data or default value

    Raises:
        PathSecurityError: If path fails security validation.
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        validated = validate_file_path(file_path, must_exist=False)
    except ImportError:
        validated = Path(file_path)
    try:
        if not validated.exists():
            return default
        with open(validated, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        log.error(f"Error reading JSON from {validated}: {e}")
        return default


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        File size in MB.

    Raises:
        FileNotFoundError: If the file does not exist.
        PathSecurityError: If path fails security validation.
        OSError: If the file size cannot be determined.
    """
    try:
        from siege_utilities.files.validation import validate_file_path
        validated = validate_file_path(file_path, must_exist=True)
    except ImportError:
        validated = Path(file_path)
        if not validated.exists():
            raise FileNotFoundError(f"File does not exist: {validated}")
    size_bytes = validated.stat().st_size
    return round(size_bytes / (1024 * 1024), 2)


def list_files_recursive(
    directory: Union[str, Path],
    pattern: str = "*",
    exclude_dirs: bool = True,
) -> list[Path]:
    """
    List all files in a directory recursively.

    Args:
        directory: Directory to search
        pattern: Glob pattern (default: "*" for all files)
        exclude_dirs: Exclude directories from results

    Returns:
        List of Path objects

    Raises:
        FileNotFoundError: If the directory does not exist.
        PathSecurityError: If path fails security validation.
        OSError: If the directory cannot be read.
    """
    try:
        from siege_utilities.files.validation import validate_safe_path
        validated = validate_safe_path(directory, allow_absolute=True)
    except ImportError:
        validated = Path(directory)
    if not validated.exists():
        raise FileNotFoundError(f"Directory does not exist: {validated}")
    if exclude_dirs:
        return [p for p in validated.rglob(pattern) if p.is_file()]
    else:
        return list(validated.rglob(pattern))


__all__ = [
    'FilePath',
    'sanitize_filename',
    'atomic_write_path',
    'atomic_write_shapefile',
    'remove_tree',
    'file_exists',
    'touch_file',
    'count_lines',
    'copy_file',
    'move_file',
    'get_file_size',
    'list_directory',
    'run_command',
    # Safe file operations
    'ensure_directory_exists',
    'safe_file_write',
    'safe_file_read',
    'safe_json_write',
    'safe_json_read',
    'get_file_size_mb',
    'list_files_recursive',
    # Backward compatibility
    'rmtree',
    'check_if_file_exists_at_path',
    'delete_existing_file_and_replace_it_with_an_empty_file',
    'count_total_rows_in_file_pythonically',
]
