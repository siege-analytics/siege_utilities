"""
Simple directory management for siege_utilities.
Handles directory creation, organization, and path management.
"""

import json
import pathlib
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def create_directory_structure(base_path: str, structure: Dict[str, Any]) -> Dict[str, str]:
    """
    Create a directory structure from a configuration dictionary.

    Args:
        base_path: Base directory path
        structure: Dictionary defining directory structure

    Returns:
        Dictionary mapping directory names to created paths

    Example:
        >>> import siege_utilities
        >>> structure = {
        ...     "data": {"raw": {}, "processed": {}, "output": {}},
        ...     "reports": {},
        ...     "logs": {}
        ... }
        >>> paths = siege_utilities.create_directory_structure("my_project", structure)
        >>> print(paths["data/raw"])
    """

    base_path = pathlib.Path(base_path)
    created_paths = {}

    def create_recursive(current_path: pathlib.Path, struct: Dict[str, Any], prefix: str = ""):
        for name, subdirs in struct.items():
            dir_path = current_path / name
            dir_path.mkdir(parents=True, exist_ok=True)

            # Create .gitkeep file
            gitkeep = dir_path / ".gitkeep"
            gitkeep.touch(exist_ok=True)

            # Store the path with a readable key
            key = f"{prefix}/{name}" if prefix else name
            created_paths[key] = str(dir_path)

            log_debug(f"Created directory: {dir_path}")

            # Recursively create subdirectories
            if isinstance(subdirs, dict) and subdirs:
                create_recursive(dir_path, subdirs, key)

    create_recursive(base_path, structure)

    log_info(f"Created directory structure at {base_path} with {len(created_paths)} directories")
    return created_paths


def create_standard_project_structure(project_path: str) -> Dict[str, str]:
    """
    Create a standard project directory structure.

    Args:
        project_path: Path for the project

    Returns:
        Dictionary mapping directory names to paths

    Example:
        >>> import siege_utilities
        >>> paths = siege_utilities.create_standard_project_structure("my_analytics_project")
        >>> print(f"Data directory: {paths['data']}")
    """

    standard_structure = {
        "data": {
            "raw": {},
            "processed": {},
            "external": {}
        },
        "notebooks": {},
        "src": {},
        "reports": {
            "figures": {},
            "tables": {}
        },
        "config": {},
        "logs": {},
        "output": {},
        "docs": {}
    }

    paths = create_directory_structure(project_path, standard_structure)

    # Create some additional files
    project_path_obj = pathlib.Path(project_path)

    # Create README.md
    readme = project_path_obj / "README.md"
    if not readme.exists():
        readme.write_text(f"# {project_path_obj.name}\n\nProject directory created by siege_utilities.\n")

    # Create .gitignore
    gitignore = project_path_obj / ".gitignore"
    if not gitignore.exists():
        gitignore_content = """
# Python
__pycache__/
*.py[cod]
*.so
.env

# Data files
data/raw/*
!data/raw/.gitkeep
logs/*
!logs/.gitkeep

# Jupyter Notebook
.ipynb_checkpoints

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
"""
        gitignore.write_text(gitignore_content.strip())

    log_info(f"Created standard project structure: {project_path}")
    return paths


def save_directory_config(paths: Dict[str, str], config_name: str,
                          config_directory: str = "config") -> str:
    """
    Save directory configuration to JSON file.

    Args:
        paths: Dictionary of directory paths
        config_name: Name for the configuration
        config_directory: Directory to save config files

    Returns:
        Path to saved config file

    Example:
        >>> paths = create_standard_project_structure("my_project")
        >>> config_file = siege_utilities.save_directory_config(paths, "my_project_dirs")
    """

    config_dir = pathlib.Path(config_directory)
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / f"directories_{config_name}.json"

    config = {
        'name': config_name,
        'paths': paths,
        'created_date': str(pathlib.Path().stat().st_mtime)
    }

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    log_info(f"Saved directory config to: {config_file}")
    return str(config_file)


def load_directory_config(config_name: str, config_directory: str = "config") -> Optional[Dict[str, Any]]:
    """
    Load directory configuration from JSON file.

    Args:
        config_name: Name of the configuration to load
        config_directory: Directory containing config files

    Returns:
        Directory configuration dictionary or None if not found

    Example:
        >>> dir_config = siege_utilities.load_directory_config("my_project_dirs")
        >>> if dir_config:
        ...     print(dir_config['paths']['data'])
    """

    config_file = pathlib.Path(config_directory) / f"directories_{config_name}.json"

    if not config_file.exists():
        log_warning(f"Directory config not found: {config_file}")
        return None

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        log_info(f"Loaded directory config: {config_name}")
        return config

    except Exception as e:
        log_error(f"Error loading directory config {config_file}: {e}")
        return None


def ensure_directories_exist(paths: Dict[str, str]) -> bool:
    """
    Ensure all directories in a path configuration exist.

    Args:
        paths: Dictionary of directory paths

    Returns:
        True if all directories exist or were created successfully

    Example:
        >>> dir_config = load_directory_config("my_project_dirs")
        >>> if dir_config:
        ...     success = siege_utilities.ensure_directories_exist(dir_config['paths'])
    """

    try:
        for name, path in paths.items():
            dir_path = pathlib.Path(path)
            dir_path.mkdir(parents=True, exist_ok=True)

            # Ensure .gitkeep exists
            gitkeep = dir_path / ".gitkeep"
            gitkeep.touch(exist_ok=True)

            log_debug(f"Ensured directory exists: {path}")

        log_info(f"Verified/created {len(paths)} directories")
        return True

    except Exception as e:
        log_error(f"Error ensuring directories exist: {e}")
        return False


def get_directory_info(directory_path: str) -> Dict[str, Any]:
    """
    Get information about a directory (size, file count, etc.).

    Args:
        directory_path: Path to directory

    Returns:
        Dictionary with directory information

    Example:
        >>> info = siege_utilities.get_directory_info("my_project/data")
        >>> print(f"Total files: {info['file_count']}")
    """

    dir_path = pathlib.Path(directory_path)

    if not dir_path.exists() or not dir_path.is_dir():
        log_warning(f"Directory does not exist: {directory_path}")
        return {}

    try:
        files = list(dir_path.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        dir_count = len([f for f in files if f.is_dir()])

        total_size = sum(f.stat().st_size for f in files if f.is_file())

        info = {
            'path': str(dir_path),
            'exists': True,
            'file_count': file_count,
            'directory_count': dir_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'subdirectories': [str(d.relative_to(dir_path)) for d in dir_path.iterdir() if d.is_dir()]
        }

        log_info(f"Directory info for {directory_path}: {file_count} files, {total_size_mb} MB")
        return info

    except Exception as e:
        log_error(f"Error getting directory info for {directory_path}: {e}")
        return {'path': str(dir_path), 'exists': False, 'error': str(e)}


def clean_empty_directories(base_path: str, keep_gitkeep: bool = True) -> int:
    """
    Remove empty directories (optionally keeping ones with .gitkeep).

    Args:
        base_path: Base path to start cleaning from
        keep_gitkeep: If True, don't remove directories that only contain .gitkeep

    Returns:
        Number of directories removed

    Example:
        >>> removed = siege_utilities.clean_empty_directories("my_project/data")
        >>> print(f"Removed {removed} empty directories")
    """

    base_path = pathlib.Path(base_path)

    if not base_path.exists():
        log_warning(f"Base path does not exist: {base_path}")
        return 0

    removed_count = 0

    try:
        # Get all directories, sorted by depth (deepest first)
        directories = [d for d in base_path.rglob("*") if d.is_dir()]
        directories.sort(key=lambda x: len(x.parts), reverse=True)

        for directory in directories:
            try:
                contents = list(directory.iterdir())

                if not contents:
                    # Completely empty
                    directory.rmdir()
                    removed_count += 1
                    log_debug(f"Removed empty directory: {directory}")

                elif keep_gitkeep and len(contents) == 1 and contents[0].name == ".gitkeep":
                    # Only contains .gitkeep, keep it
                    log_debug(f"Keeping directory with .gitkeep: {directory}")

                elif not keep_gitkeep and all(f.name == ".gitkeep" for f in contents):
                    # Remove .gitkeep files and directory
                    for f in contents:
                        f.unlink()
                    directory.rmdir()
                    removed_count += 1
                    log_debug(f"Removed directory with only .gitkeep: {directory}")

            except OSError:
                # Directory not empty or permission error
                continue

        log_info(f"Cleaned {removed_count} empty directories from {base_path}")
        return removed_count

    except Exception as e:
        log_error(f"Error cleaning directories: {e}")
        return 0


def list_directory_configs(config_directory: str = "config") -> List[Dict[str, Any]]:
    """
    List all available directory configurations.

    Args:
        config_directory: Directory containing config files

    Returns:
        List of dictionaries with directory config info

    Example:
        >>> configs = siege_utilities.list_directory_configs()
        >>> for config in configs:
        ...     print(f"{config['name']}: {len(config['paths'])} directories")
    """

    config_dir = pathlib.Path(config_directory)

    if not config_dir.exists():
        log_info("Config directory does not exist")
        return []

    configs = []

    for config_file in config_dir.glob("directories_*.json"):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            configs.append({
                'name': config['name'],
                'path_count': len(config.get('paths', {})),
                'config_file': str(config_file),
                'paths': list(config.get('paths', {}).keys())
            })

        except Exception as e:
            log_error(f"Error reading directory config {config_file}: {e}")

    log_info(f"Found {len(configs)} directory configurations")
    return configs