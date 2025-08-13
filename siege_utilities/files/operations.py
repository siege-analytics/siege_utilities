"""
Modern file operations for siege_utilities.
Provides clean, type-safe file manipulation utilities.
"""

import pathlib
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
    
    Args:
        path: Path to file or directory to remove
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> remove_tree("temp_directory")
        >>> remove_tree(Path("old_files"))
    """
    try:
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
        
    except Exception as e:
        log.error(f"Failed to remove {path}: {e}")
        return False

def file_exists(path: FilePath) -> bool:
    """
    Check if a file exists at the specified path.
    
    Args:
        path: Path to check
        
    Returns:
        True if file exists, False otherwise
        
    Example:
        >>> if file_exists("config.yaml"):
        ...     print("Config file found")
    """
    try:
        path_obj = Path(path)
        exists = path_obj.exists()
        log.debug(f"File exists check for {path}: {exists}")
        return exists
    except Exception as e:
        log.error(f"Error checking file existence for {path}: {e}")
        return False

def touch_file(path: FilePath, create_parents: bool = True) -> bool:
    """
    Create an empty file, creating parent directories if needed.
    
    Args:
        path: Path to the file to create
        create_parents: Whether to create parent directories
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> touch_file("logs/app.log")
        >>> touch_file(Path("data/output.txt"))
    """
    try:
        path_obj = Path(path)
        
        if create_parents:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        path_obj.touch(exist_ok=True)
        log.info(f"Created/updated file: {path_obj}")
        return True
        
    except Exception as e:
        log.error(f"Failed to create file {path}: {e}")
        return False

def count_lines(file_path: FilePath, encoding: str = 'utf-8') -> Optional[int]:
    """
    Count the total number of lines in a text file.
    
    Args:
        file_path: Path to the text file
        encoding: File encoding to use
        
    Returns:
        Number of lines, or None if failed
        
    Example:
        >>> line_count = count_lines("data.csv")
        >>> print(f"File has {line_count} lines")
    """
    try:
        path_obj = Path(file_path)
        
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
        
    except Exception as e:
        log.error(f"Failed to count lines in {file_path}: {e}")
        return None

def copy_file(source: FilePath, destination: FilePath, overwrite: bool = False) -> bool:
    """
    Copy a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> copy_file("source.txt", "backup/source.txt")
        >>> copy_file(Path("config.yaml"), Path("config.yaml.bak"))
    """
    try:
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
        
    except Exception as e:
        log.error(f"Failed to copy {source} to {destination}: {e}")
        return False

def move_file(source: FilePath, destination: FilePath, overwrite: bool = False) -> bool:
    """
    Move a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> move_file("temp.txt", "archive/temp.txt")
        >>> move_file(Path("old.log"), Path("logs/old.log"))
    """
    try:
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
        
    except Exception as e:
        log.error(f"Failed to move {source} to {destination}: {e}")
        return False

def get_file_size(file_path: FilePath) -> Optional[int]:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes, or None if failed
        
    Example:
        >>> size = get_file_size("large_file.zip")
        >>> print(f"File size: {size} bytes")
    """
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            log.warning(f"File does not exist: {path_obj}")
            return None
            
        if not path_obj.is_file():
            log.warning(f"Path is not a file: {path_obj}")
            return None
        
        size = path_obj.stat().st_size
        log.debug(f"File size for {path_obj}: {size} bytes")
        return size
        
    except Exception as e:
        log.error(f"Failed to get file size for {file_path}: {e}")
        return None

def list_directory(path: FilePath, 
                  pattern: str = "*",
                  include_dirs: bool = True,
                  include_files: bool = True) -> Optional[List[Path]]:
    """
    List contents of a directory with optional filtering.
    
    Args:
        path: Directory path to list
        pattern: Glob pattern for filtering files
        include_dirs: Whether to include directories
        include_files: Whether to include files
        
    Returns:
        List of Path objects, or None if failed
        
    Example:
        >>> files = list_directory("data", "*.csv")
        >>> dirs = list_directory("logs", include_files=False)
    """
    try:
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
        
    except Exception as e:
        log.error(f"Failed to list directory {path}: {e}")
        return None

def run_command(command: Union[str, List[str]], 
                cwd: Optional[FilePath] = None,
                timeout: Optional[int] = None,
                capture_output: bool = True) -> Optional[subprocess.CompletedProcess]:
    """
    Run a shell command with proper error handling.
    
    Args:
        command: Command to run (string or list)
        cwd: Working directory for the command
        timeout: Timeout in seconds
        capture_output: Whether to capture command output
        
    Returns:
        CompletedProcess object, or None if failed
        
    Example:
        >>> result = run_command("ls -la")
        >>> if result and result.returncode == 0:
        ...     print("Command succeeded")
    """
    try:
        if isinstance(command, str):
            # Use shell=True for string commands
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True
            )
        else:
            # Use shell=False for list commands (safer)
            result = subprocess.run(
                command,
                shell=False,
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
        return None

# Backward compatibility aliases
rmtree = remove_tree
check_if_file_exists_at_path = file_exists

def delete_existing_file_and_replace_it_with_an_empty_file(file_path: FilePath, create_parents: bool = True) -> bool:
    """
    Backward compatibility function that deletes existing file and replaces it with empty file.
    
    Args:
        file_path: Path to the file
        create_parents: Whether to create parent directories
        
    Returns:
        True if successful, False otherwise
    """
    try:
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
        
    except Exception as e:
        log.error(f"Failed to create empty file {file_path}: {e}")
        return False

count_total_rows_in_file_pythonically = count_lines

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
    # Backward compatibility
    'rmtree',
    'check_if_file_exists_at_path',
    'delete_existing_file_and_replace_it_with_an_empty_file',
    'count_total_rows_in_file_pythonically'
]
