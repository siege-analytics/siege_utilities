"""
User configuration management for siege_utilities.
Handles user preferences, default settings, and personal information.
Enhanced with Pydantic validation while maintaining backward compatibility.
"""

import logging
import warnings
import yaml
from pathlib import Path
from typing import Optional
import os
from dataclasses import dataclass, asdict

# Import enhanced config for validation

log = logging.getLogger(__name__)


def _is_databricks_runtime() -> bool:
    """Detect whether we are running inside a Databricks environment.

    Checks for ``DATABRICKS_RUNTIME_VERSION`` (set on every DBR cluster)
    and falls back to probing for ``/dbfs`` which exists on Databricks
    worker nodes.
    """
    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        return True
    # /dbfs is mounted on every Databricks cluster node
    if Path("/dbfs").is_dir():
        return True
    return False


def _default_download_directory() -> Path:
    """Return the platform-appropriate default download directory.

    On Databricks, ``~/Downloads`` is typically under ``/root`` and blocked
    by the cluster filesystem policy.  We default to ``/tmp/siege_utilities/downloads``
    instead, which is always writable on Databricks nodes.

    On all other platforms, we use ``~/Downloads/siege_utilities``.
    """
    if _is_databricks_runtime():
        return Path("/tmp/siege_utilities/downloads")
    return Path.home() / "Downloads" / "siege_utilities"

@dataclass
class UserProfile:
    """User profile information and preferences.

    .. deprecated::
        Use ``User`` from ``siege_utilities.config.models.actor_types`` instead.
    """

    def __post_init__(self):
        warnings.warn(
            "UserProfile (dataclass) is deprecated. Use User from siege_utilities.config.models.actor_types instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Personal Information
    username: str = ""
    email: str = ""
    full_name: str = ""
    github_login: str = ""
    organization: str = ""
    
    # Preferences
    preferred_download_directory: str = ""
    default_output_format: str = "pdf"  # pdf, pptx, html
    preferred_map_style: str = "open-street-map"
    default_color_scheme: str = "YlOrRd"
    
    # Technical Preferences
    default_dpi: int = 300
    default_figure_size: tuple = (10, 8)
    enable_logging: bool = True
    log_level: str = "INFO"
    
    # API Keys (encrypted)
    google_analytics_key: str = ""
    facebook_business_key: str = ""
    census_api_key: str = ""
    
    # Database Preferences
    default_database: str = "postgresql"
    postgresql_connection: str = ""
    duckdb_path: str = ""

class UserConfigManager:
    """
    Manages user configuration and preferences.
    Handles user profiles, default settings, and configuration persistence.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the user configuration manager.
        
        Args:
            config_dir: Directory containing user configuration files
        """
        self.config_dir = config_dir or Path.home() / ".siege_utilities" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.user_config_file = self.config_dir / "user_config.yaml"
        self.user_profile = self._load_user_profile()
        
        # Set default download directory if not specified
        if not self.user_profile.preferred_download_directory:
            self.user_profile.preferred_download_directory = str(_default_download_directory())
            self._save_user_profile()
    
    def _load_user_profile(self) -> UserProfile:
        """Load user profile from configuration file."""
        if self.user_config_file.exists():
            try:
                with open(self.user_config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if config_data:
                        # Convert lists back to tuples for specific fields
                        if 'default_figure_size' in config_data and isinstance(config_data['default_figure_size'], list):
                            config_data['default_figure_size'] = tuple(config_data['default_figure_size'])
                        return UserProfile(**config_data)
            except Exception as e:
                log.warning(f"Failed to load user config: {e}")

        # Return default profile
        return UserProfile()
    
    def _save_user_profile(self):
        """Save user profile to configuration file."""
        try:
            config_dict = asdict(self.user_profile)
            # Convert tuples to lists for YAML compatibility
            config_dict = self._convert_to_yaml_safe(config_dict)
            with open(self.user_config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        except Exception as e:
            log.error(f"Failed to save user config: {e}")

    def _convert_to_yaml_safe(self, obj):
        """Convert Python objects to YAML-safe types."""
        if isinstance(obj, dict):
            return {k: self._convert_to_yaml_safe(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_yaml_safe(item) for item in obj]
        elif hasattr(obj, 'value'):  # Enum
            return obj.value
        return obj
    
    def get_user_profile(self) -> UserProfile:
        """Get the current user profile."""
        return self.user_profile
    
    def update_user_profile(self, **kwargs):
        """
        Update user profile with new values.
        
        Args:
            **kwargs: Profile fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self.user_profile, key):
                setattr(self.user_profile, key, value)
            else:
                log.warning(f"Unknown profile field: {key}")
        
        self._save_user_profile()
    
    def get_download_directory(self, specific_path: Optional[str] = None) -> Path:
        """
        Get the appropriate download directory.
        
        Args:
            specific_path: Specific path to use instead of default
            
        Returns:
            Path object for the download directory
        """
        if specific_path:
            download_dir = Path(specific_path)
        else:
            download_dir = Path(self.user_profile.preferred_download_directory)
        
        # Create directory if it doesn't exist
        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir
    
    def setup_initial_profile(self):
        """Interactive setup for initial user profile."""
        log.info("Welcome to Siege Utilities!")
        log.info("Let's set up your user profile.")
        
        # Get user information
        username = input("Username (for file naming): ").strip()
        email = input("Email address: ").strip()
        full_name = input("Full name: ").strip()
        github_login = input("GitHub login (optional): ").strip()
        organization = input("Organization (optional): ").strip()
        
        # Get preferences
        default_dir = _default_download_directory()
        download_dir = input(f"Preferred download directory (default: {default_dir}): ").strip()
        if not download_dir:
            download_dir = str(default_dir)
        
        # Update profile
        self.update_user_profile(
            username=username,
            email=email,
            full_name=full_name,
            github_login=github_login,
            organization=organization,
            preferred_download_directory=download_dir
        )
        
        log.info("User profile created successfully!")
        log.info(f"Configuration saved to: {self.user_config_file}")
    
    def get_api_key(self, service: str) -> str:
        """
        Get API key for a specific service.
        
        Args:
            service: Service name (e.g., 'google_analytics', 'census')
            
        Returns:
            API key string
        """
        key_map = {
            'google_analytics': 'google_analytics_key',
            'facebook_business': 'facebook_business_key',
            'census': 'census_api_key'
        }
        
        key_field = key_map.get(service)
        if key_field:
            return getattr(self.user_profile, key_field, "")
        return ""
    
    def set_api_key(self, service: str, api_key: str):
        """
        Set API key for a specific service.
        
        Args:
            service: Service name
            api_key: API key value
        """
        key_map = {
            'google_analytics': 'google_analytics_key',
            'facebook_business': 'facebook_business_key',
            'census': 'census_api_key'
        }
        
        key_field = key_map.get(service)
        if key_field:
            self.update_user_profile(**{key_field: api_key})
        else:
            log.warning(f"Unknown service: {service}")
    
    def get_database_connection(self, database_type: str = None) -> str:
        """
        Get database connection string.
        
        Args:
            database_type: Type of database (postgresql, duckdb)
            
        Returns:
            Connection string
        """
        if not database_type:
            database_type = self.user_profile.default_database
        
        if database_type == "postgresql":
            return self.user_profile.postgresql_connection
        elif database_type == "duckdb":
            return self.user_profile.duckdb_path
        else:
            log.warning(f"Unknown database type: {database_type}")
            return ""
    
    def set_database_connection(self, database_type: str, connection_string: str):
        """
        Set database connection string.
        
        Args:
            database_type: Type of database
            connection_string: Connection string or path
        """
        if database_type == "postgresql":
            self.update_user_profile(postgresql_connection=connection_string)
        elif database_type == "duckdb":
            self.update_user_profile(duckdb_path=connection_string)
        else:
            log.warning(f"Unknown database type: {database_type}")
    
    def export_config(self, output_path: str):
        """
        Export user configuration to a file.
        
        Args:
            output_path: Path to export configuration
        """
        try:
            config_data = asdict(self.user_profile)
            # Remove sensitive information
            config_data.pop('google_analytics_key', None)
            config_data.pop('facebook_business_key', None)
            config_data.pop('census_api_key', None)
            
            with open(output_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            log.info(f"Configuration exported to: {output_path}")
        except Exception as e:
            log.error(f"Failed to export configuration: {e}")
    
    def import_config(self, input_path: str):
        """
        Import user configuration from a file.
        
        Args:
            input_path: Path to import configuration from
        """
        try:
            with open(input_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Update profile with imported data
            for key, value in config_data.items():
                if hasattr(self.user_profile, key):
                    setattr(self.user_profile, key, value)
            
            self._save_user_profile()
            log.info(f"Configuration imported from: {input_path}")
        except Exception as e:
            log.error(f"Failed to import configuration: {e}")

# Global instance
user_config = UserConfigManager()

def get_user_config() -> UserConfigManager:
    """Get the global user configuration manager."""
    return user_config

def get_download_directory(specific_path: Optional[str] = None, client_code: Optional[str] = None, config_dir: Optional[Path] = None) -> Path:
    """
    Get the appropriate download directory with hierarchical resolution.

    Priority order:
    1. specific_path if provided
    2. Client-specific directory if client_code provided and client profile exists
    3. User's preferred download directory from profile
    4. Default fallback (platform-aware: ``/tmp/siege_utilities/downloads``
       on Databricks, ``~/Downloads/siege_utilities`` elsewhere)

    On Databricks the default ``~/Downloads/siege_utilities`` path resolves to
    ``/root/Downloads/siege_utilities`` which is blocked by the cluster
    filesystem policy. The Databricks-aware default avoids this.

    Args:
        specific_path: Specific path override (highest priority)
        client_code: Client code for client-specific directory
        config_dir: Configuration directory (unused, kept for compatibility)

    Returns:
        Path object for download directory

    Raises:
        OSError: If the resolved directory cannot be created or is not writable
    """
    download_dir: Optional[Path] = None

    # Priority 1: Specific path override
    if specific_path:
        download_dir = Path(specific_path)

    # Priority 2: Client-specific directory
    if download_dir is None and client_code:
        try:
            from .enhanced_config import load_client_profile
            client_profile = load_client_profile(client_code, config_dir)
            if client_profile:
                # Client profiles don't have download_directory anymore,
                # use a client-specific subdirectory instead
                download_dir = user_config.get_download_directory() / "clients" / client_code.lower()
        except Exception as e:
            log.debug(f"Could not load client profile for {client_code}: {e}")

    # Priority 3 & 4: User's preferred directory or default
    if download_dir is None:
        download_dir = user_config.get_download_directory()

    # Ensure the directory exists and is writable
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # will be caught by the writability check below

    if not download_dir.is_dir() or not os.access(download_dir, os.W_OK):
        # On Databricks, auto-remediate persisted legacy paths (e.g.
        # /root/Downloads/siege_utilities) that are blocked by the cluster
        # filesystem policy.  This covers users whose config was written
        # before the Databricks-aware default was introduced.
        if _is_databricks_runtime() and not specific_path:
            safe_dir = Path("/tmp/siege_utilities/downloads")
            log.warning(
                "Download directory %s is not writable on Databricks; "
                "auto-remediating to %s",
                download_dir,
                safe_dir,
            )
            safe_dir.mkdir(parents=True, exist_ok=True)
            return safe_dir

        raise OSError(
            f"Download directory is not writable: {download_dir}. "
            f"Set a writable path via specific_path parameter or "
            f"user_config preferred_download_directory."
        )

    return download_dir
