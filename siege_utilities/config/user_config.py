"""
User configuration management for siege_utilities.
Handles user preferences, default settings, and personal information.
"""

import logging
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os
from dataclasses import dataclass, asdict
import getpass

log = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """User profile information and preferences."""
    
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
            self.user_profile.preferred_download_directory = str(Path.home() / "Downloads" / "siege_utilities")
            self._save_user_profile()
    
    def _load_user_profile(self) -> UserProfile:
        """Load user profile from configuration file."""
        if self.user_config_file.exists():
            try:
                with open(self.user_config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if config_data:
                        return UserProfile(**config_data)
            except Exception as e:
                log.warning(f"Failed to load user config: {e}")
        
        # Return default profile
        return UserProfile()
    
    def _save_user_profile(self):
        """Save user profile to configuration file."""
        try:
            with open(self.user_config_file, 'w') as f:
                yaml.dump(asdict(self.user_profile), f, default_flow_style=False)
        except Exception as e:
            log.error(f"Failed to save user config: {e}")
    
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
        print("🚀 Welcome to Siege Utilities!")
        print("Let's set up your user profile.\n")
        
        # Get user information
        username = input("Username (for file naming): ").strip()
        email = input("Email address: ").strip()
        full_name = input("Full name: ").strip()
        github_login = input("GitHub login (optional): ").strip()
        organization = input("Organization (optional): ").strip()
        
        # Get preferences
        download_dir = input(f"Preferred download directory (default: {Path.home() / 'Downloads' / 'siege_utilities'}): ").strip()
        if not download_dir:
            download_dir = str(Path.home() / "Downloads" / "siege_utilities")
        
        # Update profile
        self.update_user_profile(
            username=username,
            email=email,
            full_name=full_name,
            github_login=github_login,
            organization=organization,
            preferred_download_directory=download_dir
        )
        
        print(f"\n✅ User profile created successfully!")
        print(f"Configuration saved to: {self.user_config_file}")
    
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
            
            print(f"✅ Configuration exported to: {output_path}")
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
            print(f"✅ Configuration imported from: {input_path}")
        except Exception as e:
            log.error(f"Failed to import configuration: {e}")

# Global instance
user_config = UserConfigManager()

def get_user_config() -> UserConfigManager:
    """Get the global user configuration manager."""
    return user_config

def get_download_directory(specific_path: Optional[str] = None) -> Path:
    """Get the appropriate download directory."""
    return user_config.get_download_directory(specific_path)
