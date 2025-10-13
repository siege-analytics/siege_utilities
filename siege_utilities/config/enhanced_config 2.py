"""
Enhanced configuration management with Pydantic validation.
Provides type-safe config models while maintaining functional API compatibility.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import yaml

# Import profile location management
try:
    from ..admin.profile_manager import get_default_profile_location, get_profile_location
except ImportError:
    # Fallback if admin module not available
    def get_default_profile_location():
        return Path.home() / ".siege_utilities" / "config"
    
    def get_profile_location(profile_type: str = "default"):
        return get_default_profile_location()

# Custom YAML representer for Path objects
def path_representer(dumper, data):
    return dumper.represent_str(str(data))

yaml.add_representer(Path, path_representer)

log = logging.getLogger(__name__)

class UserProfile(BaseModel):
    """Enhanced user profile with validation."""
    
    # Personal Information
    username: str = ""
    email: str = ""
    full_name: str = ""
    github_login: str = ""
    organization: str = ""
    
    # Preferences
    preferred_download_directory: Path = Field(
        default_factory=lambda: Path.home() / "Downloads" / "siege_utilities"
    )
    default_output_format: str = Field(default="pdf", pattern="^(pdf|pptx|html)$")
    preferred_map_style: str = Field(default="open-street-map")
    default_color_scheme: str = Field(default="YlOrRd")
    
    # Technical Preferences
    default_dpi: int = Field(default=300, ge=72, le=600)
    default_figure_size: tuple = Field(default=(10, 8))
    enable_logging: bool = True
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # API Keys (will be handled securely)
    google_analytics_key: str = ""
    facebook_business_key: str = ""
    census_api_key: str = ""
    
    # Database Preferences
    default_database: str = Field(default="postgresql", pattern="^(postgresql|mysql|sqlite|duckdb)$")
    postgresql_connection: str = ""
    duckdb_path: str = ""
    
    @field_validator('preferred_download_directory', mode='before')
    @classmethod
    def validate_download_directory(cls, v):
        """Ensure download directory is a Path object."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    model_config = {
        "json_schema_serialization_mode": "json"
    }

class ClientProfile(BaseModel):
    """Enhanced client profile with validation."""
    
    client_id: str = ""
    client_name: str
    client_code: str
    
    # Contact Information
    contact_info: Dict[str, str] = Field(default_factory=dict)
    
    # Client-specific preferences
    download_directory: Optional[Path] = None
    data_format: str = Field(default="parquet", pattern="^(parquet|csv|json|xlsx)$")
    report_style: str = Field(default="standard")
    
    # Design artifacts
    logo_path: str = ""
    brand_colors: List[str] = Field(default_factory=list)
    style_guide: str = ""
    templates: List[str] = Field(default_factory=list)
    
    # Metadata
    industry: str = ""
    project_count: int = Field(default=0, ge=0)
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")
    notes: str = ""
    
    @field_validator('download_directory', mode='before')
    @classmethod
    def validate_download_directory(cls, v):
        """Ensure download directory is a Path object."""
        if v and isinstance(v, str):
            return Path(v)
        return v
    
    model_config = {
        "json_schema_serialization_mode": "json"
    }

class SiegeConfig(BaseModel):
    """Unified configuration container."""
    
    user: UserProfile = Field(default_factory=UserProfile)
    clients: Dict[str, ClientProfile] = Field(default_factory=dict)
    
    model_config = {
        "json_schema_serialization_mode": "json"
    }

# Functional API functions (maintaining backward compatibility)
def load_user_profile(config_dir: Optional[Path] = None) -> UserProfile:
    """
    Load user profile with Pydantic validation.
    
    Args:
        config_dir: Configuration directory (defaults to project profiles directory)
    
    Returns:
        Validated UserProfile object
    """
    if config_dir is None:
        config_dir = get_default_profile_location() / "users"
    
    config_file = config_dir / "user_config.yaml"
    
    if config_file.exists():
        try:
            # Use manual YAML loading and Pydantic parsing (Pydantic v2 compatible)
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            return UserProfile(**data)
        except Exception as e:
            log.warning(f"Failed to load user config: {e}, using defaults")
    
    # Create default profile
    profile = UserProfile()
    
    # Save default profile
    try:
        save_user_profile(profile, config_dir)
    except Exception as e:
        log.warning(f"Failed to save default user config: {e}")
    
    return profile

def save_user_profile(profile: UserProfile, config_dir: Optional[Path] = None) -> None:
    """
    Save user profile with validation.
    
    Args:
        profile: UserProfile object to save
        config_dir: Configuration directory (defaults to project profiles/users)
    """
    if config_dir is None:
        config_dir = get_default_profile_location() / "users"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "user_config.yaml"
    
    try:
        # Convert Path objects and tuples to strings for YAML serialization
        profile_data = profile.model_dump()
        if 'preferred_download_directory' in profile_data:
            profile_data['preferred_download_directory'] = str(profile_data['preferred_download_directory'])
        if 'default_figure_size' in profile_data:
            profile_data['default_figure_size'] = list(profile_data['default_figure_size'])
        
        with open(config_file, 'w') as f:
            yaml.dump(profile_data, f, default_flow_style=False)
        log.info(f"User profile saved to {config_file}")
    except Exception as e:
        log.error(f"Failed to save user config: {e}")
        raise

def load_client_profile(client_code: str, config_dir: Optional[Path] = None) -> Optional[ClientProfile]:
    """
    Load client profile with validation.
    
    Args:
        client_code: Client code to load
        config_dir: Configuration directory (defaults to project profiles/clients)
    
    Returns:
        Validated ClientProfile object or None if not found
    """
    if config_dir is None:
        config_dir = get_default_profile_location() / "clients"
    
    client_file = config_dir / f"{client_code}.yaml"
    
    if client_file.exists():
        try:
            # Add a small delay to ensure file is fully written
            import time
            time.sleep(0.1)
            
            # Read file content first to debug
            with open(client_file, 'r') as f:
                content = f.read()
                if not content.strip():
                    log.warning(f"Client config file {client_code} is empty")
                    return None
            
            # Use manual YAML loading and Pydantic parsing
            with open(client_file, 'r') as f:
                data = yaml.safe_load(f)
            return ClientProfile(**data)
        except Exception as e:
            log.warning(f"Failed to load client config for {client_code}: {e}")
            # Try to read file content for debugging
            try:
                with open(client_file, 'r') as f:
                    content = f.read()
                    log.debug(f"File content length: {len(content)}")
            except Exception as debug_e:
                log.debug(f"Could not read file for debugging: {debug_e}")
    
    return None

def save_client_profile(profile: ClientProfile, config_dir: Optional[Path] = None) -> None:
    """
    Save client profile with validation.
    
    Args:
        profile: ClientProfile object to save
        config_dir: Configuration directory (defaults to project profiles/clients)
    """
    if config_dir is None:
        config_dir = get_default_profile_location() / "clients"
    
    client_dir = config_dir
    client_dir.mkdir(parents=True, exist_ok=True)
    client_file = client_dir / f"{profile.client_code}.yaml"
    
    try:
        # Convert Path objects to strings for YAML serialization
        profile_data = profile.model_dump()
        if 'download_directory' in profile_data and profile_data['download_directory']:
            profile_data['download_directory'] = str(profile_data['download_directory'])
        
        # Write to temporary file first, then rename (atomic operation)
        temp_file = client_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            yaml.dump(profile_data, f, default_flow_style=False)
        
        # Atomic rename
        temp_file.rename(client_file)
        log.info(f"Client profile saved to {client_file}")
    except Exception as e:
        log.error(f"Failed to save client config: {e}")
        raise

def get_download_directory(
    client_code: Optional[str] = None,
    specific_path: Optional[str] = None,
    config_dir: Optional[Path] = None
) -> Path:
    """
    Get download directory with hierarchical resolution.
    
    Priority order:
    1. specific_path (if provided)
    2. client-specific directory (if client_code provided and exists)
    3. user's preferred directory
    4. system default
    
    Args:
        client_code: Client code for client-specific directory
        specific_path: Specific path override
        config_dir: Configuration directory
    
    Returns:
        Path object for download directory
    """
    if specific_path:
        download_dir = Path(specific_path)
    elif client_code:
        # Try loading client profile from clients subdirectory if config_dir is base directory
        if config_dir and (config_dir / "clients").exists():
            client_profile = load_client_profile(client_code, config_dir / "clients")
        else:
            client_profile = load_client_profile(client_code, config_dir)
        
        if client_profile and client_profile.download_directory:
            download_dir = client_profile.download_directory
        else:
            # Try loading user profile from users subdirectory if config_dir is base directory
            if config_dir and (config_dir / "users").exists():
                user_profile = load_user_profile(config_dir / "users")
            else:
                user_profile = load_user_profile(config_dir)
            download_dir = user_profile.preferred_download_directory
    else:
        # Try loading user profile from users subdirectory if config_dir is base directory
        if config_dir and (config_dir / "users").exists():
            user_profile = load_user_profile(config_dir / "users")
        else:
            user_profile = load_user_profile(config_dir)
        download_dir = user_profile.preferred_download_directory
    
    # Ensure directory exists
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir

def list_client_profiles(config_dir: Optional[Path] = None) -> List[str]:
    """
    List available client profile codes.
    
    Args:
        config_dir: Configuration directory (defaults to project profiles/clients)
    
    Returns:
        List of client codes
    """
    if config_dir is None:
        config_dir = get_default_profile_location() / "clients"
    
    client_dir = config_dir
    if not client_dir.exists():
        return []
    
    client_files = list(client_dir.glob("*.yaml"))
    return [f.stem for f in client_files]

def export_config_yaml(output_path: str, include_api_keys: bool = False, config_dir: Optional[Path] = None) -> None:
    """
    Export configuration to YAML file.
    
    Args:
        output_path: Path to save exported config
        include_api_keys: Whether to include API keys in export
        config_dir: Configuration directory (defaults to project profiles directory)
    """
    if config_dir is None:
        config_dir = get_default_profile_location()
    
    config = SiegeConfig()
    config.user = load_user_profile(config_dir / "users")
    
    # Load all client profiles
    for client_code in list_client_profiles(config_dir / "clients"):
        client_profile = load_client_profile(client_code, config_dir / "clients")
        if client_profile:
            config.clients[client_code] = client_profile
    
    # Remove sensitive data if requested
    if not include_api_keys:
        config.user.google_analytics_key = ""
        config.user.facebook_business_key = ""
        config.user.census_api_key = ""
    
    # Convert Path objects to strings for YAML serialization
    config_data = config.model_dump()
    
    # Convert user profile Path objects and tuples
    if 'user' in config_data:
        if 'preferred_download_directory' in config_data['user']:
            config_data['user']['preferred_download_directory'] = str(config_data['user']['preferred_download_directory'])
        if 'default_figure_size' in config_data['user']:
            config_data['user']['default_figure_size'] = list(config_data['user']['default_figure_size'])
    
    # Convert client profile Path objects
    if 'clients' in config_data:
        for client_code, client_data in config_data['clients'].items():
            if 'download_directory' in client_data and client_data['download_directory']:
                client_data['download_directory'] = str(client_data['download_directory'])
    
    with open(output_path, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    log.info(f"Configuration exported to {output_path}")

def import_config_yaml(input_path: str, config_dir: Optional[Path] = None) -> None:
    """
    Import configuration from YAML file.
    
    Args:
        input_path: Path to YAML file to import
        config_dir: Configuration directory (defaults to project profiles directory)
    """
    if config_dir is None:
        config_dir = get_default_profile_location()
    
    with open(input_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Import user profile
    if 'user' in config_data:
        user_profile = UserProfile(**config_data['user'])
        save_user_profile(user_profile, config_dir / "users")
    
    # Import client profiles
    if 'clients' in config_data:
        for client_code, client_data in config_data['clients'].items():
            client_profile = ClientProfile(**client_data)
            save_client_profile(client_profile, config_dir / "clients")
    
    log.info(f"Configuration imported from {input_path}")
