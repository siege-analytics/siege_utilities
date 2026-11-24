"""
User configuration management for siege_utilities.
Handles user preferences, default settings, and personal information.
Enhanced with Pydantic validation while maintaining backward compatibility.
"""

import logging
import stat
import tempfile
import threading
import warnings
import yaml
from pathlib import Path
from typing import Optional
import os
from dataclasses import dataclass, asdict, field
from pydantic import SecretStr

from ._home import _fallback_home_directory, _home_directory

# Import enhanced config for validation

__all__ = [
    'UserProfile',
    'UserConfigManager',
    'get_user_config',
    'get_download_directory',
]

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

    On all other platforms, we use ``~/Downloads/siege_utilities``. If home
    lookup fails, the home substitute documented in ``config._home`` is used.
    """
    if _is_databricks_runtime():
        return Path("/tmp/siege_utilities/downloads")
    return _home_directory() / "Downloads" / "siege_utilities"

@dataclass
class UserProfile:
    """User profile information and preferences.

    .. deprecated::
        Use ``User`` from ``siege_utilities.config.models.actor_types`` instead.
    """

    def __post_init__(self):
        warnings.warn(
            "UserProfile (dataclass) is deprecated and will be removed in v4.0.0. Use User from siege_utilities.config.models.actor_types instead.",
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
    
    # API Keys (stored in plaintext; protected by filesystem permissions)
    google_analytics_key: str = field(default="", repr=False)
    facebook_business_key: str = field(default="", repr=False)
    census_api_key: str = field(default="", repr=False)
    
    # Database Preferences
    default_database: str = "postgresql"
    postgresql_connection: str = field(default="", repr=False)
    duckdb_path: str = ""

class UserConfigManager:
    """
    Manages user configuration and preferences.
    Handles user profiles, default settings, and configuration persistence.
    POSIX writes enforce 0700 directories and 0600 files. On Windows, the
    per-user AppData default inherits the user's ACL; chmod is not an ACL check.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the user configuration manager.

        Args:
            config_dir: Directory containing user configuration files

        Raises:
            ValueError: If a safe per-user fallback cannot be determined.
        """
        self._read_only = False
        self.config_dir = Path(config_dir) if config_dir is not None else self._resolve_config_dir()
        # An explicit, writable directory must never depend on a POSIX uid.
        fallback = self._fallback_config_dir() if config_dir is None else None
        try:
            self._prepare_config_dir(
                self.config_dir,
                fallback=(
                    (fallback is not None and self.config_dir == fallback)
                    or self._is_posix_temp_fallback_path(self.config_dir)
                ),
            )
        except (PermissionError, OSError) as exc:
            if fallback is None:
                fallback = self._fallback_config_dir()
            log.warning(
                "Cannot create config dir %s (%s); falling back to %s",
                self.config_dir, exc, fallback,
            )
            self.config_dir = fallback
            try:
                self._prepare_config_dir(self.config_dir, fallback=True)
            except (PermissionError, OSError):
                log.warning("Fallback config dir %s also unwritable; running read-only", fallback)
                self._read_only = True

        self.user_config_file = self.config_dir / "user_config.yaml"
        self.user_profile = self._load_user_profile()

        if not self.user_profile.preferred_download_directory:
            self.user_profile.preferred_download_directory = str(_default_download_directory())
            self._save_user_profile()

    @staticmethod
    def _fallback_config_dir() -> Path:
        if not hasattr(os, "getuid"):
            # On Windows, the per-user AppData directory carries the user's ACL.
            # A shared %TEMP% path has no portable POSIX uid/mode to validate.
            for name in ("LOCALAPPDATA", "APPDATA"):
                root = os.environ.get(name)
                if root and Path(root).is_absolute():
                    return Path(root) / "siege_utilities" / "config"
            try:
                return Path.home() / "AppData" / "Local" / "siege_utilities" / "config"
            except (RuntimeError, KeyError, OSError) as exc:
                raise ValueError(
                    "Cannot locate a private user config directory; set "
                    "SIEGE_USER_CONFIG_DIR to a private path."
                ) from exc
        return _fallback_home_directory()

    @staticmethod
    def _is_posix_temp_fallback_path(config_dir: Path) -> bool:
        """Recognize the predictable uid path even when supplied explicitly."""
        if os.name != "posix" or not hasattr(os, "getuid"):
            return False
        return (
            config_dir.name == f"siege_utilities-{os.getuid()}"
            and config_dir.parent.resolve() == Path(tempfile.gettempdir()).resolve()
        )

    @staticmethod
    def _prepare_config_dir(config_dir: Path, *, fallback: bool) -> None:
        """Prepare a config directory; validate fallback paths before reading."""
        try:
            config_dir.mkdir(mode=0o700, parents=True)
        except FileExistsError:
            # A pre-existing fallback must be validated before chmod or reads.
            if not fallback and not config_dir.is_dir():
                raise
        if fallback:
            metadata = config_dir.lstat()
            if not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f"Unsafe fallback config directory {config_dir}: not a real directory")
            if hasattr(os, "getuid") and (
                metadata.st_uid != os.getuid() or metadata.st_mode & 0o022
            ):
                raise ValueError(
                    f"Unsafe fallback config directory {config_dir}: must be owned "
                    f"by uid {os.getuid()} and not group/other-writable. "
                    "Set SIEGE_USER_CONFIG_DIR to a private directory."
                )
        # chmod is not an ACL guarantee on Windows; AppData inherits the user's ACL.
        if os.name == "posix":
            config_dir.chmod(0o700)

    @staticmethod
    def _resolve_config_dir() -> Path:
        env_override = os.environ.get("SIEGE_USER_CONFIG_DIR")
        if env_override:
            return Path(env_override)
        if not hasattr(os, "getuid"):
            return UserConfigManager._fallback_config_dir()
        try:
            return Path.home() / ".siege_utilities" / "config"
        except (RuntimeError, KeyError):
            return UserConfigManager._fallback_config_dir()
    
    def _load_user_profile(self) -> UserProfile:
        """Load user profile from configuration file."""
        if self._read_only:
            # Directory preparation failed; do not read an unvalidated fallback.
            return UserProfile()
        if self.user_config_file.exists():
            try:
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    if config_data:
                        # Convert lists back to tuples for specific fields
                        if 'default_figure_size' in config_data and isinstance(config_data['default_figure_size'], list):
                            config_data['default_figure_size'] = tuple(config_data['default_figure_size'])
                        return UserProfile(**config_data)
            except (OSError, yaml.YAMLError, ValueError, KeyError) as e:
                log.warning(f"Failed to load user config: {e}")

        # Return default profile
        return UserProfile()
    
    def _save_user_profile(self, *, raise_on_error: bool = False):
        """Save the profile; explicit imports require write failures to propagate."""
        if self._read_only:
            if raise_on_error:
                raise PermissionError(f"Configuration directory is read-only: {self.config_dir}")
            return
        temporary_file = None
        try:
            config_dict = asdict(self.user_profile)
            # Convert tuples to lists for YAML compatibility
            config_dict = self._convert_to_yaml_safe(config_dict)
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', dir=self.config_dir,
                    prefix='.user_config.', suffix='.tmp', delete=False,
                ) as f:
                    temporary_file = Path(f.name)
                    if os.name == "posix":
                        os.fchmod(f.fileno(), 0o600)
                    yaml.dump(config_dict, f, default_flow_style=False)
                os.replace(temporary_file, self.user_config_file)
            finally:
                if temporary_file is not None:
                    temporary_file.unlink(missing_ok=True)
        except (OSError, yaml.YAMLError, TypeError) as e:
            log.error(f"Failed to save user config: {e}")
            if raise_on_error:
                raise

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
            **kwargs: Fields on :class:`UserProfile` to overwrite. Accepted
                keys include ``username``, ``email``, ``full_name``,
                ``preferred_download_directory``, ``default_output_format``,
                ``preferred_map_style``, ``default_color_scheme``, and any
                other ``UserProfile`` attribute. Unknown keys are logged as
                warnings and ignored.
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
            connection = self.user_profile.postgresql_connection
            return connection.get_secret_value() if isinstance(connection, SecretStr) else connection
        elif database_type == "duckdb":
            return self.user_profile.duckdb_path
        else:
            raise ValueError(
                f"Unknown database type: {database_type!r}. "
                f"Supported types: postgresql, duckdb"
            )
    
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
            raise ValueError(
                f"Unknown database type: {database_type!r}. "
                f"Supported types: postgresql, duckdb"
            )
    
    def export_config(self, output_path: str):
        """
        Export user configuration without secrets (POSIX 0600; Windows parent ACL).
        
        Args:
            output_path: Path to export configuration

        Raises:
            OSError: If the export cannot be written or replaced.
            yaml.YAMLError: If the profile cannot be serialized.
        """
        temporary_file = None
        try:
            config_data = asdict(self.user_profile)
            # Remove sensitive information
            config_data.pop('google_analytics_key', None)
            config_data.pop('facebook_business_key', None)
            config_data.pop('census_api_key', None)
            config_data.pop('postgresql_connection', None)
            config_data.pop('duckdb_path', None)
            
            target = Path(output_path)
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', dir=target.parent,
                    prefix='.user_config.', suffix='.tmp', delete=False,
                ) as f:
                    temporary_file = Path(f.name)
                    if os.name == "posix":
                        os.fchmod(f.fileno(), 0o600)
                    yaml.dump(config_data, f, default_flow_style=False)
                os.replace(temporary_file, target)
            finally:
                if temporary_file is not None:
                    temporary_file.unlink(missing_ok=True)

            log.info(f"Configuration exported to: {output_path}")
        except (OSError, yaml.YAMLError) as e:
            log.error(f"Failed to export configuration: {e}")
            raise
    
    def import_config(self, input_path: str):
        """
        Import user configuration from a file.
        
        Args:
            input_path: Path to import configuration from

        Raises:
            OSError: If the input cannot be read or the profile cannot be saved.
            yaml.YAMLError: If parsing or serialization fails.
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            # Update profile with imported data
            for key, value in config_data.items():
                if hasattr(self.user_profile, key):
                    setattr(self.user_profile, key, value)
            
            self._save_user_profile(raise_on_error=True)
            log.info(f"Configuration imported from: {input_path}")
        except (OSError, yaml.YAMLError, AttributeError) as e:
            log.error(f"Failed to import configuration: {e}")
            raise

_user_config = None
_user_config_lock = threading.Lock()


def get_user_config() -> UserConfigManager:
    """Get or create the global user configuration manager."""
    global _user_config
    if _user_config is None:
        with _user_config_lock:
            if _user_config is None:
                _user_config = UserConfigManager()
    return _user_config

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
                download_dir = get_user_config().get_download_directory() / "clients" / client_code.lower()
        except (ImportError, OSError, yaml.YAMLError, ValueError) as e:
            log.debug(f"Could not load client profile for {client_code}: {e}")

    # Priority 3 & 4: User's preferred directory or default
    if download_dir is None:
        download_dir = get_user_config().get_download_directory()

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
