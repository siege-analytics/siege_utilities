"""
Simple project configuration management for siege_utilities.
Handles basic project settings, directories, and metadata.
"""

import json
import pathlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import logging functions from main package
try:
    from siege_utilities import log_info, log_warning, log_error
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")


def create_project_config(project_name: str, project_code: str,
                          base_directory: str = "projects", **kwargs) -> Dict[str, Any]:
    """
    Create a simple project configuration.

    Args:
        project_name: Human-readable project name
        project_code: Short project code (e.g., "PROJ001")
        base_directory: Base directory for projects
        **kwargs: Additional project settings

    Returns:
        Dictionary with project configuration

    Example:
        >>> import siege_utilities
        >>> config = siege_utilities.create_project_config(
        ...     "Customer Analytics",
        ...     "CA001",
        ...     description="Analytics for customer behavior"
        ... )
        >>> print(config['directories']['output'])
    """

    project_dir = pathlib.Path(base_directory) / project_code

    config = {
        'project_name': project_name,
        'project_code': project_code,
        'description': kwargs.get('description', ''),
        'created_date': kwargs.get('created_date', str(pathlib.Path().cwd())),
        'directories': {
            'base': str(project_dir),
            'input': str(project_dir / "input"),
            'output': str(project_dir / "output"),
            'data': str(project_dir / "data"),
            'reports': str(project_dir / "reports"),
            'logs': str(project_dir / "logs"),
            'config': str(project_dir / "config")
        },
        'settings': {
            'data_format': kwargs.get('data_format', 'parquet'),
            'log_level': kwargs.get('log_level', 'INFO'),
            'backup_enabled': kwargs.get('backup_enabled', True)
        }
    }

    # Add any custom settings
    for key, value in kwargs.items():
        if key not in ['description', 'created_date', 'data_format', 'log_level', 'backup_enabled']:
            config['settings'][key] = value

    log_info(f"Created project config: {project_name} ({project_code})")
    return config


def save_project_config(config: Dict[str, Any], config_directory: str = "config") -> str:
    """
    Save project configuration to JSON file.

    Args:
        config: Project configuration dictionary
        config_directory: Directory to save config files

    Returns:
        Path to saved config file

    Example:
        >>> config = create_project_config("My Project", "MP001")
        >>> file_path = siege_utilities.save_project_config(config)
        >>> print(f"Config saved to: {file_path}")
    """

    config_dir = pathlib.Path(config_directory)
    config_dir.mkdir(parents=True, exist_ok=True)

    project_code = config['project_code']
    config_file = config_dir / f"project_{project_code}.json"

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    log_info(f"Saved project config to: {config_file}")
    return str(config_file)


def load_project_config(project_code: str, config_directory: str = "config") -> Optional[Dict[str, Any]]:
    """
    Load project configuration from JSON file.

    Args:
        project_code: Project code to load
        config_directory: Directory containing config files

    Returns:
        Project configuration dictionary or None if not found

    Example:
        >>> config = siege_utilities.load_project_config("MP001")
        >>> if config:
        ...     print(f"Loaded: {config['project_name']}")
    """

    config_file = pathlib.Path(config_directory) / f"project_{project_code}.json"

    if not config_file.exists():
        log_warning(f"Project config not found: {config_file}")
        return None

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        log_info(f"Loaded project config: {project_code}")
        return config

    except Exception as e:
        log_error(f"Error loading project config {config_file}: {e}")
        return None


def setup_project_directories(config: Dict[str, Any]) -> bool:
    """
    Create the directory structure for a project.

    Args:
        config: Project configuration dictionary

    Returns:
        True if successful, False otherwise

    Example:
        >>> config = create_project_config("My Project", "MP001")
        >>> success = siege_utilities.setup_project_directories(config)
        >>> if success:
        ...     print("Project directories created")
    """

    try:
        directories = config.get('directories', {})

        for dir_name, dir_path in directories.items():
            path = pathlib.Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)

            # Create .gitkeep file to ensure directory is tracked
            gitkeep = path / ".gitkeep"
            gitkeep.touch(exist_ok=True)

            log_debug(f"Created directory: {dir_path}")

        log_info(f"Project directories setup complete for {config['project_code']}")
        return True

    except Exception as e:
        log_error(f"Error setting up project directories: {e}")
        return False


def get_project_path(config: Dict[str, Any], path_type: str) -> Optional[str]:
    """
    Get a specific path from project configuration.

    Args:
        config: Project configuration dictionary
        path_type: Type of path (input, output, data, reports, logs, config)

    Returns:
        Path string or None if not found

    Example:
        >>> config = load_project_config("MP001")
        >>> output_dir = siege_utilities.get_project_path(config, "output")
        >>> print(f"Output directory: {output_dir}")
    """

    directories = config.get('directories', {})
    path = directories.get(path_type)

    if path:
        log_debug(f"Retrieved {path_type} path: {path}")
        return path
    else:
        log_warning(f"Path type '{path_type}' not found in project config")
        return None


def list_projects(config_directory: str = "config") -> list:
    """
    List all available project configurations.

    Args:
        config_directory: Directory containing config files

    Returns:
        List of dictionaries with project info

    Example:
        >>> projects = siege_utilities.list_projects()
        >>> for project in projects:
        ...     print(f"{project['code']}: {project['name']}")
    """

    config_dir = pathlib.Path(config_directory)

    if not config_dir.exists():
        log_info("Config directory does not exist")
        return []

    projects = []

    for config_file in config_dir.glob("project_*.json"):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            projects.append({
                'code': config['project_code'],
                'name': config['project_name'],
                'description': config.get('description', ''),
                'config_file': str(config_file)
            })

        except Exception as e:
            log_error(f"Error reading project config {config_file}: {e}")

    log_info(f"Found {len(projects)} project configurations")
    return projects


def update_project_config(project_code: str, updates: Dict[str, Any],
                          config_directory: str = "config") -> bool:
    """
    Update an existing project configuration.

    Args:
        project_code: Project code to update
        updates: Dictionary of updates to apply
        config_directory: Directory containing config files

    Returns:
        True if successful, False otherwise

    Example:
        >>> success = siege_utilities.update_project_config(
        ...     "MP001",
        ...     {"description": "Updated description", "settings": {"log_level": "DEBUG"}}
        ... )
    """

    config = load_project_config(project_code, config_directory)

    if config is None:
        log_error(f"Cannot update - project config not found: {project_code}")
        return False

    try:
        # Apply updates
        for key, value in updates.items():
            if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                # Merge dictionaries
                config[key].update(value)
            else:
                # Direct assignment
                config[key] = value

        # Save updated config
        save_project_config(config, config_directory)
        log_info(f"Updated project config: {project_code}")
        return True

    except Exception as e:
        log_error(f"Error updating project config {project_code}: {e}")
        return False