"""
Modern file operations for siege_utilities.
Provides clean, type-safe file manipulation utilities.
"""

import json
import subprocess
import shutil
import logging
from typing import Union, Optional, List, Any
from pathlib import Path

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]

def remove_tree(path: FilePath) -> bool:
    """
    Remove a file or directory tree safely.

    SECURITY: Validates paths to prevent removing sensitive system files.

    Args:
        path: Path to file or directory to remove

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> remove_tree("temp_directory")
        >>> remove_tree(Path("old_files"))
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
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
            log.warning(f"Path does not exist: {path_obj}")
            return False

        return True

    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to remove {path}: {e}")
        return False

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
        >>> if file_exists("config.yaml"):
        ...     print("Config file found")
        >>>
        >>> # This will raise PathSecurityError
        >>> file_exists("../../../etc/passwd")  # Path traversal blocked

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
    except Exception as e:
        log.error(f"Error checking file existence for {path}: {e}")
        return False

def touch_file(path: FilePath, create_parents: bool = True) -> bool:
    """
    Create an empty file, creating parent directories if needed.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        path: Path to the file to create
        create_parents: Whether to create parent directories

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> touch_file("logs/app.log")
        >>> touch_file(Path("data/output.txt"))
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_safe_path, PathSecurityError
            path_obj = validate_safe_path(path, allow_absolute=True)
        except ImportError:
            path_obj = Path(path)

        if create_parents:
            path_obj.parent.mkdir(parents=True, exist_ok=True)

        path_obj.touch(exist_ok=True)
        log.info(f"Created/updated file: {path_obj}")
        return True

    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to create file {path}: {e}")
        return False

def count_lines(file_path: FilePath, encoding: str = 'utf-8') -> Optional[int]:
    """
    Count the total number of lines in a text file.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the text file
        encoding: File encoding to use

    Returns:
        Number of lines, or None if failed

    Raises:
        PathSecurityError: If path fails security validation (from validation module)

    Example:
        >>> line_count = count_lines("data.csv")
        >>> print(f"File has {line_count} lines")
        >>>
        >>> # This will raise PathSecurityError
        >>> count_lines("../../../etc/passwd")  # Path traversal blocked

    Security Changes:
        - Now validates paths to block path traversal
        - Blocks access to sensitive system files
        - Resolves symlinks and validates final destination
    """
    try:
        # Import validation function
        try:
            from siege_utilities.files.validation import validate_file_path, PathSecurityError
        except ImportError:
            # Fallback: use basic Path validation without security checks
            log.warning("Path validation module not available - using basic validation")
            path_obj = Path(file_path)
        else:
            # Validate path with security checks
            try:
                path_obj = validate_file_path(file_path, must_exist=True)
            except PathSecurityError as e:
                log.error(f"Path security validation failed: {e}")
                raise  # Re-raise to caller

        if not path_obj.exists():
            log.warning(f"File does not exist: {path_obj}")
            return None

        if not path_obj.is_file():
            log.warning(f"Path is not a file: {path_obj}")
            return None

        with open(path_obj, 'r', encoding=encoding) as f:
            line_count = sum(1 for _ in f)

        log.info(f"Counted {line_count} lines in {path_obj}")
        return line_count

    except PathSecurityError:
        # Re-raise security errors
        raise
    except Exception as e:
        log.error(f"Failed to count lines in {file_path}: {e}")
        return None

def copy_file(source: FilePath, destination: FilePath, overwrite: bool = False) -> bool:
    """
    Copy a file from source to destination.

    SECURITY: Validates both source and destination paths.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If paths fail security validation

    Example:
        >>> copy_file("source.txt", "backup/source.txt")
        >>> copy_file(Path("config.yaml"), Path("config.yaml.bak"))
    """
    try:
        # Validate paths
        try:
            from siege_utilities.files.validation import validate_file_path, validate_safe_path, PathSecurityError
            source_obj = validate_file_path(source, must_exist=True)
            dest_obj = validate_safe_path(destination, allow_absolute=True)
        except ImportError:
            source_obj = Path(source)
            dest_obj = Path(destination)

        if not source_obj.exists():
            log.error(f"Source file does not exist: {source_obj}")
            return False

        if not source_obj.is_file():
            log.error(f"Source is not a file: {source_obj}")
            return False

        # Create destination directory if needed
        dest_obj.parent.mkdir(parents=True, exist_ok=True)

        # Check if destination exists
        if dest_obj.exists() and not overwrite:
            log.warning(f"Destination file exists and overwrite=False: {dest_obj}")
            return False

        shutil.copy2(source_obj, dest_obj)
        log.info(f"Copied {source_obj} to {dest_obj}")
        return True

    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to copy {source} to {destination}: {e}")
        return False

def move_file(source: FilePath, destination: FilePath, overwrite: bool = False) -> bool:
    """
    Move a file from source to destination.

    SECURITY: Validates both source and destination paths.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If paths fail security validation

    Example:
        >>> move_file("temp.txt", "archive/temp.txt")
        >>> move_file(Path("old.log"), Path("logs/old.log"))
    """
    try:
        # Validate paths
        try:
            from siege_utilities.files.validation import validate_file_path, validate_safe_path, PathSecurityError
            source_obj = validate_file_path(source, must_exist=True)
            dest_obj = validate_safe_path(destination, allow_absolute=True)
        except ImportError:
            source_obj = Path(source)
            dest_obj = Path(destination)

        if not source_obj.exists():
            log.error(f"Source file does not exist: {source_obj}")
            return False

        if not source_obj.is_file():
            log.error(f"Source is not a file: {source_obj}")
            return False

        # Create destination directory if needed
        dest_obj.parent.mkdir(parents=True, exist_ok=True)

        # Check if destination exists
        if dest_obj.exists() and not overwrite:
            log.warning(f"Destination file exists and overwrite=False: {dest_obj}")
            return False

        shutil.move(str(source_obj), str(dest_obj))
        log.info(f"Moved {source_obj} to {dest_obj}")
        return True

    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to move {source} to {destination}: {e}")
        return False

def get_file_size(file_path: FilePath) -> Optional[int]:
    """
    Get the size of a file in bytes.

    SECURITY: This function validates paths to prevent path traversal attacks
    and access to sensitive system files.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes, or None if failed

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> size = get_file_size("large_file.zip")
        >>> print(f"File size: {size} bytes")
        >>>
        >>> # This will raise PathSecurityError
        >>> get_file_size("/etc/shadow")  # Sensitive file blocked

    Security Changes:
        - Now validates paths to block path traversal
        - Blocks access to sensitive system files
    """
    try:
        # Import validation function
        try:
            from siege_utilities.files.validation import validate_file_path, PathSecurityError
        except ImportError:
            # Fallback: use basic Path validation without security checks
            log.warning("Path validation module not available - using basic validation")
            path_obj = Path(file_path)
        else:
            # Validate path with security checks
            try:
                path_obj = validate_file_path(file_path, must_exist=True)
            except PathSecurityError as e:
                log.error(f"Path security validation failed: {e}")
                raise  # Re-raise to caller

        if not path_obj.exists():
            log.warning(f"File does not exist: {path_obj}")
            return None

        if not path_obj.is_file():
            log.warning(f"Path is not a file: {path_obj}")
            return None

        size = path_obj.stat().st_size
        log.debug(f"File size for {path_obj}: {size} bytes")
        return size

    except PathSecurityError:
        # Re-raise security errors
        raise
    except Exception as e:
        log.error(f"Failed to get file size for {file_path}: {e}")
        return None

def list_directory(path: FilePath,
                  pattern: str = "*",
                  include_dirs: bool = True,
                  include_files: bool = True) -> Optional[List[Path]]:
    """
    List contents of a directory with optional filtering.

    SECURITY: Validates directory path to prevent traversal attacks.

    Args:
        path: Directory path to list
        pattern: Glob pattern for filtering files
        include_dirs: Whether to include directories
        include_files: Whether to include files

    Returns:
        List of Path objects, or None if failed

    Raises:
        PathSecurityError: If path fails security validation

    Example:
        >>> files = list_directory("data", "*.csv")
        >>> dirs = list_directory("logs", include_files=False)
    """
    try:
        # Validate path
        try:
            from siege_utilities.files.validation import validate_directory_path, PathSecurityError
            path_obj = validate_directory_path(path, must_exist=True)
        except ImportError:
            path_obj = Path(path)

        if not path_obj.exists():
            log.warning(f"Directory does not exist: {path_obj}")
            return None

        if not path_obj.is_dir():
            log.warning(f"Path is not a directory: {path_obj}")
            return None

        items = []

        for item in path_obj.glob(pattern):
            if item.is_dir() and include_dirs:
                items.append(item)
            elif item.is_file() and include_files:
                items.append(item)

        log.debug(f"Listed {len(items)} items in {path_obj}")
        return sorted(items)

    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to list directory {path}: {e}")
        return None

def run_command(command: Union[str, List[str]],
                cwd: Optional[FilePath] = None,
                timeout: Optional[int] = 30,
                capture_output: bool = True,
                allow_list: Optional[set] = None,
                unsafe: bool = False) -> Optional[subprocess.CompletedProcess]:
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
        unsafe: If True, bypass security validation (DANGEROUS - use with caution)

    Returns:
        CompletedProcess object, or None if failed

    Raises:
        SecurityError: If command fails security validation (when unsafe=False)

    Example:
        >>> # Safe command (works by default)
        >>> result = run_command("ls -la")
        >>> if result and result.returncode == 0:
        ...     print("Command succeeded")
        >>>
        >>> # Dangerous command (blocked by default)
        >>> result = run_command("rm -rf /")  # Raises SecurityError
        >>>
        >>> # Custom whitelist
        >>> result = run_command("git status", allow_list={'git', 'ls'})
        >>>
        >>> # Bypass security (DANGEROUS - use only with trusted input)
        >>> result = run_command("custom_cmd", unsafe=True)

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
        except ImportError:
            # Fallback: define minimal SecurityError
            class SecurityError(Exception):
                pass
            # If we can't import validation, we must be in unsafe mode or fail
            if not unsafe:
                log.error("Cannot validate command: security module not available")
                raise SecurityError("Security validation unavailable")

        # Parse command
        if isinstance(command, str):
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
                use_shell = False
            except (SecurityError, ValueError) as e:
                log.error(f"Security validation failed: {e}")
                raise
        else:
            # Unsafe mode: log warning and proceed
            log.warning(
                f"⚠️ SECURITY WARNING: Running command without validation: {command}"
            )
            if isinstance(command, str):
                command_to_run = command
                use_shell = True  # DANGER: Required for string commands in unsafe mode
            else:
                command_to_run = command_list
                use_shell = False

        # Execute command
        result = subprocess.run(
            command_to_run,
            shell=use_shell,
            cwd=cwd,
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
        return None
    except Exception as e:
        log.error(f"Failed to run command {command}: {e}")
        if not unsafe:
            raise  # Re-raise security exceptions
        return None

# Backward compatibility aliases
rmtree = remove_tree
check_if_file_exists_at_path = file_exists

def delete_existing_file_and_replace_it_with_an_empty_file(file_path: FilePath, create_parents: bool = True) -> bool:
    """
    Backward compatibility function that deletes existing file and replaces it with empty file.

    SECURITY: Validates paths to prevent path traversal attacks.

    Args:
        file_path: Path to the file
        create_parents: Whether to create parent directories

    Returns:
        True if successful, False otherwise

    Raises:
        PathSecurityError: If path fails security validation
    """
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

        # Create empty file
        path_obj.touch()
        log.info(f"Created/updated empty file: {path_obj}")
        return True
    except PathSecurityError:
        raise
    except Exception as e:
        log.error(f"Failed to create empty file {file_path}: {e}")
        return False

count_total_rows_in_file_pythonically = count_lines


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to directory

    Returns:
        Path object for the directory
    """
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
    """
    try:
        file_path = Path(file_path)
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        log.error(f"Error writing to {file_path}: {e}")
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
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return default
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        log.error(f"Error reading {file_path}: {e}")
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
    """
    try:
        file_path = Path(file_path)
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        log.error(f"Error writing JSON to {file_path}: {e}")
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
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return default
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Error reading JSON from {file_path}: {e}")
        return default


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        File size in MB (0.0 if file doesn't exist)
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return 0.0
        size_bytes = file_path.stat().st_size
        return round(size_bytes / (1024 * 1024), 2)
    except Exception as e:
        log.error(f"Error getting file size for {file_path}: {e}")
        return 0.0


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
    """
    try:
        directory = Path(directory)
        if not directory.exists():
            return []
        if exclude_dirs:
            return [p for p in directory.rglob(pattern) if p.is_file()]
        else:
            return list(directory.rglob(pattern))
    except Exception as e:
        log.error(f"Error listing files in {directory}: {e}")
        return []


__all__ = [
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
