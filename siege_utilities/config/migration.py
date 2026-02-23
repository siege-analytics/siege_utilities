"""
Migration utilities for transitioning from legacy configuration system to Hydra + Pydantic.

This module provides tools to migrate existing configurations to the new system
while maintaining backward compatibility.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .models import UserProfile, ClientProfile, BrandingConfig, ReportPreferences
from .hydra_manager import HydraConfigManager

logger = logging.getLogger(__name__)


class ConfigurationMigrator:
    """
    Handles migration from legacy configuration system to Hydra + Pydantic.
    
    Provides utilities to migrate existing user profiles, client profiles,
    and other configuration data to the new system.
    """
    
    def __init__(self, legacy_config_dir: Optional[Path] = None, new_config_dir: Optional[Path] = None):
        """
        Initialize the migrator.
        
        Args:
            legacy_config_dir: Directory containing legacy configuration files
            new_config_dir: Directory for new Hydra configuration files
        """
        self.legacy_config_dir = legacy_config_dir or Path.home() / ".siege_utilities" / "config"
        self.new_config_dir = new_config_dir or Path(__file__).parent.parent / "configs"
        
        logger.info(f"Initialized migrator: {self.legacy_config_dir} -> {self.new_config_dir}")
    
    def migrate_user_profile(self, legacy_file: Optional[Path] = None) -> UserProfile:
        """
        Migrate legacy user profile to new system.
        
        Args:
            legacy_file: Path to legacy user config file
            
        Returns:
            New UserProfile instance
        """
        if legacy_file is None:
            legacy_file = self.legacy_config_dir / "user_config.yaml"
        
        if not legacy_file.exists():
            logger.warning(f"Legacy user profile not found: {legacy_file}")
            return self._create_default_user_profile()
        
        try:
            with open(legacy_file, 'r') as f:
                legacy_data = yaml.safe_load(f)
            
            logger.info(f"Loading legacy user profile from: {legacy_file}")
            
            # Map legacy fields to new UserProfile fields
            new_data = self._map_user_profile_fields(legacy_data)
            
            # Create new UserProfile
            profile = UserProfile(**new_data)
            
            logger.info("Successfully migrated user profile")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to migrate user profile: {e}")
            return self._create_default_user_profile()
    
    def migrate_client_profile(self, legacy_file: Path, client_code: str) -> ClientProfile:
        """
        Migrate legacy client profile to new system.
        
        Args:
            legacy_file: Path to legacy client config file
            client_code: Client code for the profile
            
        Returns:
            New ClientProfile instance
        """
        if not legacy_file.exists():
            logger.warning(f"Legacy client profile not found: {legacy_file}")
            return self._create_default_client_profile(client_code)
        
        try:
            with open(legacy_file, 'r') as f:
                legacy_data = yaml.safe_load(f) if legacy_file.suffix in ['.yaml', '.yml'] else json.load(f)
            
            logger.info(f"Loading legacy client profile from: {legacy_file}")
            
            # Map legacy fields to new ClientProfile fields
            new_data = self._map_client_profile_fields(legacy_data, client_code)
            
            # Create new ClientProfile
            profile = ClientProfile(**new_data)
            
            logger.info(f"Successfully migrated client profile for: {client_code}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to migrate client profile for {client_code}: {e}")
            return self._create_default_client_profile(client_code)
    
    def migrate_all_configurations(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate all configurations from legacy system to new system.
        
        Args:
            dry_run: If True, only show what would be migrated without making changes
            
        Returns:
            Dictionary with migration results
        """
        results = {
            "user_profile": {"migrated": False, "error": None},
            "client_profiles": {"migrated": [], "errors": []},
            "total_migrated": 0,
            "dry_run": dry_run
        }
        
        logger.info(f"Starting migration {'(dry run)' if dry_run else ''}")
        
        try:
            # Migrate user profile
            if not dry_run:
                user_profile = self.migrate_user_profile()
                results["user_profile"]["migrated"] = True
                logger.info("User profile migrated successfully")
            else:
                logger.info("Would migrate user profile")
            
            # Find and migrate client profiles
            legacy_client_dir = self.legacy_config_dir / "clients"
            if legacy_client_dir.exists():
                for client_file in legacy_client_dir.glob("*.yaml"):
                    client_code = client_file.stem
                    
                    if not dry_run:
                        try:
                            client_profile = self.migrate_client_profile(client_file, client_code)
                            results["client_profiles"]["migrated"].append(client_code)
                            logger.info(f"Client profile migrated: {client_code}")
                        except Exception as e:
                            results["client_profiles"]["errors"].append(f"{client_code}: {e}")
                            logger.error(f"Failed to migrate client {client_code}: {e}")
                    else:
                        logger.info(f"Would migrate client profile: {client_code}")
            
            results["total_migrated"] = len(results["client_profiles"]["migrated"])
            
            if not dry_run:
                logger.info(f"Migration completed: {results['total_migrated']} profiles migrated")
            else:
                logger.info(f"Dry run completed: {results['total_migrated']} profiles would be migrated")
            
            return results
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            results["error"] = str(e)
            return results
    
    def _map_user_profile_fields(self, legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map legacy user profile fields to new UserProfile fields."""
        field_mapping = {
            "username": "username",
            "email": "email",
            "full_name": "full_name",
            "github_login": "github_login",
            "organization": "organization",
            "preferred_download_directory": "preferred_download_directory",
            "default_output_format": "default_output_format",
            "preferred_map_style": "preferred_map_style",
            "default_color_scheme": "default_color_scheme",
            "default_dpi": "default_dpi",
            "default_figure_size": "default_figure_size",
            "enable_logging": "enable_logging",
            "log_level": "log_level",
            "google_analytics_key": "google_analytics_key",
            "facebook_business_key": "facebook_business_key",
            "census_api_key": "census_api_key",
            "default_database": "default_database",
            "postgresql_connection": "postgresql_connection",
            "duckdb_path": "duckdb_path"
        }
        
        new_data = {}
        for legacy_field, new_field in field_mapping.items():
            if legacy_field in legacy_data:
                new_data[new_field] = legacy_data[legacy_field]
        
        return new_data
    
    def _map_client_profile_fields(self, legacy_data: Dict[str, Any], client_code: str) -> Dict[str, Any]:
        """Map legacy client profile fields to new ClientProfile fields."""
        # Basic client information
        new_data = {
            "client_id": client_code.lower(),
            "client_name": legacy_data.get("client_name", client_code.title()),
            "client_code": client_code.upper(),
            "industry": legacy_data.get("industry", ""),
            "project_count": legacy_data.get("project_count", 0),
            "status": legacy_data.get("status", "active"),
            "notes": legacy_data.get("notes", "")
        }
        
        # Contact information
        contact_info = {
            "email": legacy_data.get("contact_email", ""),
            "phone": legacy_data.get("contact_phone", ""),
            "address": legacy_data.get("contact_address", ""),
            "website": legacy_data.get("website", ""),
            "linkedin": legacy_data.get("linkedin", "")
        }
        new_data["contact_info"] = contact_info
        
        # Branding configuration
        branding_data = {
            "primary_color": legacy_data.get("branding", {}).get("primary_color", "#1f77b4"),
            "secondary_color": legacy_data.get("branding", {}).get("secondary_color", "#ff7f0e"),
            "accent_color": legacy_data.get("branding", {}).get("accent_color", "#2ca02c"),
            "text_color": legacy_data.get("branding", {}).get("text_color", "#000000"),
            "background_color": legacy_data.get("branding", {}).get("background_color", "#ffffff"),
            "primary_font": legacy_data.get("branding", {}).get("primary_font", "Arial"),
            "secondary_font": legacy_data.get("branding", {}).get("secondary_font", "Arial")
        }
        new_data["branding_config"] = branding_data
        
        # Report preferences
        report_prefs = {
            "default_format": legacy_data.get("report_format", "pptx"),
            "include_executive_summary": legacy_data.get("include_executive_summary", True),
            "chart_style": legacy_data.get("chart_style", "professional"),
            "page_size": legacy_data.get("page_size", "A4"),
            "orientation": legacy_data.get("orientation", "landscape")
        }
        new_data["report_preferences"] = report_prefs
        
        # Database connections
        new_data["database_connections"] = []
        if "database_connections" in legacy_data:
            for conn_data in legacy_data["database_connections"]:
                new_data["database_connections"].append(conn_data)
        
        # Social media accounts
        new_data["social_media_accounts"] = []
        if "social_media_accounts" in legacy_data:
            for acc_data in legacy_data["social_media_accounts"]:
                new_data["social_media_accounts"].append(acc_data)
        
        return new_data
    
    def _create_default_user_profile(self) -> UserProfile:
        """Create a default user profile."""
        return UserProfile(
            username="",
            email="",
            full_name="",
            github_login="",
            organization=""
        )
    
    def _create_default_client_profile(self, client_code: str) -> ClientProfile:
        """Create a default client profile."""
        from .models import ContactInfo, BrandingConfig, ReportPreferences
        
        # Use a valid client code if the provided one is reserved
        valid_client_code = client_code.upper() if client_code.upper() not in ["TEST", "DEFAULT", "SYSTEM"] else "DEMO"
        
        return ClientProfile(
            client_id=client_code.lower(),
            client_name=client_code.title(),
            client_code=valid_client_code,
            contact_info=ContactInfo(email=""),
            industry="Technology",
            project_count=0,
            status="active",
            branding_config=BrandingConfig(
                primary_color="#1f77b4",
                secondary_color="#ff7f0e",
                accent_color="#2ca02c",
                text_color="#000000",
                background_color="#ffffff",
                primary_font="Arial",
                secondary_font="Arial"
            ),
            report_preferences=ReportPreferences()
        )
    
    def backup_legacy_configurations(self, backup_dir: Optional[Path] = None) -> Path:
        """
        Create a backup of legacy configurations before migration.
        
        Args:
            backup_dir: Directory to store backup files
            
        Returns:
            Path to backup directory
        """
        if backup_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.legacy_config_dir.parent / f"config_backup_{timestamp}"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating backup in: {backup_dir}")
        
        # Copy all configuration files
        if self.legacy_config_dir.exists():
            import shutil
            shutil.copytree(self.legacy_config_dir, backup_dir / "config", dirs_exist_ok=True)
        
        logger.info(f"Backup created successfully: {backup_dir}")
        return backup_dir


def migrate_configurations(legacy_config_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Convenience function to migrate all configurations.
    
    Args:
        legacy_config_dir: Directory containing legacy configuration files
        dry_run: If True, only show what would be migrated without making changes
        
    Returns:
        Dictionary with migration results
    """
    migrator = ConfigurationMigrator(legacy_config_dir)
    return migrator.migrate_all_configurations(dry_run)


def backup_and_migrate(legacy_config_dir: Optional[Path] = None, backup_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Create backup and migrate all configurations.
    
    Args:
        legacy_config_dir: Directory containing legacy configuration files
        backup_dir: Directory to store backup files
        
    Returns:
        Dictionary with migration results including backup location
    """
    migrator = ConfigurationMigrator(legacy_config_dir)
    
    # Create backup first
    backup_path = migrator.backup_legacy_configurations(backup_dir)
    
    # Perform migration
    results = migrator.migrate_all_configurations(dry_run=False)
    results["backup_location"] = str(backup_path)
    
    return results
