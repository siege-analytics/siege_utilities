"""
Hydra Configuration Manager for siege_utilities.

This module provides a unified interface for loading and managing
configurations using Hydra with Pydantic validation.
"""

from hydra import initialize_config_dir, compose
from hydra.core.global_hydra import GlobalHydra
from omegaconf import OmegaConf
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

from .models import (
    UserProfile, 
    ClientProfile, 
    ContactInfo,
    DatabaseConnection,
    SocialMediaAccount,
    BrandingConfig,
    ReportPreferences
)

logger = logging.getLogger(__name__)


class HydraConfigManager:
    """
    Hydra Configuration Manager with Pydantic validation.
    
    Provides a unified interface for loading configurations using Hydra
    and validating them with Pydantic models.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the Hydra configuration manager.
        
        Args:
            config_dir: Directory containing Hydra configuration files
        """
        self.config_dir = config_dir or Path(__file__).parent.parent / "configs"
        self._hydra_initialized = False
        
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")
        
        logger.info(f"Initialized HydraConfigManager with config directory: {self.config_dir}")
    
    def _ensure_hydra_initialized(self):
        """Ensure Hydra is initialized."""
        if not self._hydra_initialized:
            try:
                initialize_config_dir(str(self.config_dir), version_base=None)
                self._hydra_initialized = True
                logger.debug("Hydra initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Hydra: {e}")
                raise
    
    def load_config(self, config_name: str, overrides: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load configuration with Hydra.
        
        Args:
            config_name: Name of the configuration to load
            overrides: List of override strings (e.g., ["+client=client_a"])
            
        Returns:
            Dictionary containing the loaded configuration
        """
        self._ensure_hydra_initialized()
        
        overrides = overrides or []
        
        try:
            cfg = compose(config_name=config_name, overrides=overrides)
            config_data = OmegaConf.to_container(cfg, resolve=True)
            logger.debug(f"Loaded configuration: {config_name} with overrides: {overrides}")
            return config_data
        except Exception as e:
            logger.error(f"Failed to load configuration {config_name}: {e}")
            raise
    
    def load_user_profile(self, client_code: Optional[str] = None) -> UserProfile:
        """
        Load user profile with optional client overrides.
        
        Args:
            client_code: Optional client code for client-specific overrides
            
        Returns:
            Validated UserProfile instance
        """
        overrides = []
        if client_code:
            overrides.append(f"+client={client_code}")
        
        config_data = self.load_config("default/user_profile", overrides)
        
        # Extract user profile data from the nested structure
        if 'default' in config_data:
            profile_data = config_data['default']
        else:
            profile_data = config_data
        
        try:
            profile = UserProfile(**profile_data)
            logger.info(f"Loaded user profile for client: {client_code or 'default'}")
            return profile
        except Exception as e:
            logger.error(f"Failed to validate user profile: {e}")
            raise
    
    def load_client_profile(self, client_code: str) -> ClientProfile:
        """
        Load client profile with client-specific overrides.
        
        Args:
            client_code: Client code for the profile to load
            
        Returns:
            Validated ClientProfile instance
        """
        overrides = [f"+client={client_code}"]
        
        # Load base client profile
        config_data = self.load_config("default/client_profile", overrides)
        
        # Load client-specific overrides
        try:
            client_config_data = self.load_config(f"client/{client_code}/branding")
            # Merge client-specific branding
            if 'branding_config' in config_data:
                branding_data = config_data['branding_config']
                client_branding = client_config_data.get('client', {}).get(client_code, {})
                
                # Override branding with client-specific values
                for key, value in client_branding.items():
                    if key in branding_data:
                        branding_data[key] = value
                    else:
                        branding_data[key] = value
        except Exception as e:
            logger.warning(f"Could not load client-specific branding for {client_code}: {e}")
        
        # Extract client profile data
        if 'default' in config_data:
            profile_data = config_data['default']
        else:
            profile_data = config_data
        
        try:
            # Create nested objects
            if 'contact_info' in profile_data:
                profile_data['contact_info'] = ContactInfo(**profile_data['contact_info'])
            
            if 'branding_config' in profile_data:
                profile_data['branding_config'] = BrandingConfig(**profile_data['branding_config'])
            
            if 'report_preferences' in profile_data:
                profile_data['report_preferences'] = ReportPreferences(**profile_data['report_preferences'])
            
            # Create database connections
            if 'database_connections' in profile_data:
                connections = []
                for conn_data in profile_data['database_connections']:
                    connections.append(DatabaseConnection(**conn_data))
                profile_data['database_connections'] = connections
            
            # Create social media accounts
            if 'social_media_accounts' in profile_data:
                accounts = []
                for acc_data in profile_data['social_media_accounts']:
                    accounts.append(SocialMediaAccount(**acc_data))
                profile_data['social_media_accounts'] = accounts
            
            profile = ClientProfile(**profile_data)
            logger.info(f"Loaded client profile for: {client_code}")
            return profile
        except Exception as e:
            logger.error(f"Failed to validate client profile for {client_code}: {e}")
            raise
    
    def load_database_connections(self, client_code: Optional[str] = None) -> List[DatabaseConnection]:
        """
        Load database connections with optional client overrides.
        
        Args:
            client_code: Optional client code for client-specific connections
            
        Returns:
            List of validated DatabaseConnection instances
        """
        overrides = []
        if client_code:
            overrides.append(f"+client={client_code}")
        
        config_data = self.load_config("default/database_connections", overrides)
        
        # Extract connections data
        if 'default' in config_data:
            connections_data = config_data['default'].get('connections', [])
        else:
            connections_data = config_data.get('connections', [])
        
        connections = []
        for conn_data in connections_data:
            try:
                connection = DatabaseConnection(**conn_data)
                connections.append(connection)
            except Exception as e:
                logger.error(f"Failed to validate database connection {conn_data.get('name', 'unknown')}: {e}")
                raise
        
        logger.info(f"Loaded {len(connections)} database connections for client: {client_code or 'default'}")
        return connections
    
    def load_social_media_accounts(self, client_code: Optional[str] = None) -> List[SocialMediaAccount]:
        """
        Load social media accounts with optional client overrides.
        
        Args:
            client_code: Optional client code for client-specific accounts
            
        Returns:
            List of validated SocialMediaAccount instances
        """
        overrides = []
        if client_code:
            overrides.append(f"+client={client_code}")
        
        config_data = self.load_config("default/social_media_accounts", overrides)
        
        # Extract accounts data
        if 'default' in config_data:
            accounts_data = config_data['default'].get('accounts', [])
        else:
            accounts_data = config_data.get('accounts', [])
        
        accounts = []
        for acc_data in accounts_data:
            try:
                account = SocialMediaAccount(**acc_data)
                accounts.append(account)
            except Exception as e:
                logger.error(f"Failed to validate social media account {acc_data.get('platform', 'unknown')}: {e}")
                raise
        
        logger.info(f"Loaded {len(accounts)} social media accounts for client: {client_code or 'default'}")
        return accounts
    
    def load_branding_config(self, client_code: Optional[str] = None) -> BrandingConfig:
        """
        Load branding configuration with optional client overrides.
        
        Args:
            client_code: Optional client code for client-specific branding
            
        Returns:
            Validated BrandingConfig instance
        """
        if client_code:
            # Load client-specific branding
            try:
                config_data = self.load_config(f"client/{client_code}/branding")
                
                # Extract branding data from client config
                if 'client' in config_data and client_code in config_data['client']:
                    client_data = config_data['client'][client_code]
                    
                    # Start with default data if it exists, but flatten it first
                    if 'default' in client_data:
                        branding_data = {}
                        default_data = client_data['default']
                        
                        # Flatten default data first
                        sections_to_flatten = ['colors', 'typography', 'logo', 'layout', 'charts']
                        for section in sections_to_flatten:
                            if section in default_data:
                                section_data = default_data.pop(section)
                                if isinstance(section_data, dict):
                                    branding_data.update(section_data)
                        
                        # Add any remaining default data
                        branding_data.update(default_data)
                    else:
                        branding_data = {}
                    
                    # Apply client-specific overrides (these take precedence)
                    for section, section_data in client_data.items():
                        if section != 'default' and isinstance(section_data, dict):
                            branding_data.update(section_data)
                else:
                    branding_data = config_data
                
                # Flatten all nested structures
                sections_to_flatten = ['colors', 'typography', 'logo', 'layout', 'charts']
                for section in sections_to_flatten:
                    if section in branding_data:
                        section_data = branding_data.pop(section)
                        if isinstance(section_data, dict):
                            branding_data.update(section_data)
                
                branding = BrandingConfig(**branding_data)
                logger.info(f"Loaded client-specific branding for: {client_code}")
                return branding
            except Exception as e:
                logger.warning(f"Could not load client-specific branding for {client_code}: {e}")
                # Fall back to default
        
        # Load default branding
        config_data = self.load_config("default/branding_config")
        
        # Extract branding data
        if 'default' in config_data:
            branding_data = config_data['default']
        else:
            branding_data = config_data
        
        # Flatten all nested structures
        sections_to_flatten = ['colors', 'typography', 'logo', 'layout', 'charts']
        for section in sections_to_flatten:
            if section in branding_data:
                section_data = branding_data.pop(section)
                if isinstance(section_data, dict):
                    branding_data.update(section_data)
        
        branding = BrandingConfig(**branding_data)
        logger.info(f"Loaded default branding for client: {client_code or 'default'}")
        return branding
    
    def cleanup(self):
        """Clean up Hydra instance."""
        if self._hydra_initialized:
            GlobalHydra.instance().clear()
            self._hydra_initialized = False
            logger.debug("Hydra instance cleared")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
