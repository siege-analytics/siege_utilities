"""
Profile location management for siege_utilities.
Handles default locations, custom locations, and profile migration.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from ..config.enhanced_config import (
    UserProfile, ClientProfile,
    save_user_profile, save_client_profile
)
from ..config.models import ContactInfo, BrandingConfig, ReportPreferences

log = logging.getLogger(__name__)

# Global profile location registry
PROFILE_LOCATIONS: Dict[str, Path] = {}

def get_default_profile_location() -> Path:
    """
    Get the default profile location (project-local profiles directory).
    
    Returns:
        Path to the default profiles directory
    """
    # Get the siege_utilities package root
    package_root = Path(__file__).parent.parent.parent
    return package_root / "profiles"

def get_profile_location(profile_type: str = "default") -> Path:
    """
    Get the current profile location for a given type.
    
    Args:
        profile_type: Type of profile location ('default', 'user', 'client', etc.)
    
    Returns:
        Path to the profile location
    """
    if profile_type in PROFILE_LOCATIONS:
        return PROFILE_LOCATIONS[profile_type]
    
    # Return default location if not explicitly set
    return get_default_profile_location()

def set_profile_location(location: Path, profile_type: str = "default") -> None:
    """
    Set a custom profile location for a given type.
    
    Args:
        location: Path to the profile directory
        profile_type: Type of profile location ('default', 'user', 'client', etc.)
    """
    location = Path(location).resolve()
    
    # Validate the location
    if not validate_profile_location(location):
        raise ValueError(f"Invalid profile location: {location}")
    
    PROFILE_LOCATIONS[profile_type] = location
    log.info(f"Profile location set for {profile_type}: {location}")

def list_profile_locations() -> Dict[str, Path]:
    """
    List all configured profile locations.
    
    Returns:
        Dictionary mapping profile types to their locations
    """
    locations = dict(PROFILE_LOCATIONS)
    locations['default'] = get_default_profile_location()
    return locations

def validate_profile_location(location: Path) -> bool:
    """
    Validate that a profile location is usable.
    
    Args:
        location: Path to validate
    
    Returns:
        True if location is valid, False otherwise
    """
    try:
        # Check if it's a valid path
        location = Path(location).resolve()
        
        # Check if parent directory exists and is writable
        parent = location.parent
        if not parent.exists():
            return False
        
        # Try to create the directory if it doesn't exist
        location.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = location / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        
        return True
    except Exception as e:
        log.debug(f"Profile location validation failed: {e}")
        return False

def create_default_profiles(profile_location: Optional[Path] = None) -> Tuple[UserProfile, List[ClientProfile]]:
    """
    Create default user and client profiles in the specified location.

    Args:
        profile_location: Where to create profiles (defaults to default location)

    Returns:
        Tuple of (created_user_profile, list_of_created_client_profiles)
    """
    if profile_location is None:
        profile_location = get_default_profile_location()

    # Ensure directory structure exists
    user_dir = profile_location / "users"
    client_dir = profile_location / "clients"
    user_dir.mkdir(parents=True, exist_ok=True)
    client_dir.mkdir(parents=True, exist_ok=True)

    # Create default user profile
    user_profile = UserProfile(username="default")
    save_user_profile(user_profile, "default", user_dir)
    log.info(f"Created default user profile at {user_dir}")

    # Create example client profiles
    client_profiles = []

    # Example client 1: Government Agency
    gov_client = ClientProfile(
        client_id="gov001",
        client_name="Government Agency",
        client_code="GOV001",
        industry="Government",
        project_count=0,
        status="active",
        contact_info=ContactInfo(
            email="contact@govagency.gov",
            phone="5551234567"
        ),
        branding_config=BrandingConfig(
            primary_color="#003366",
            secondary_color="#FFFFFF",
            accent_color="#CC0000",
            text_color="#000000",
            background_color="#ffffff",
            primary_font="Arial",
            secondary_font="Helvetica"
        ),
        report_preferences=ReportPreferences()
    )
    save_client_profile(gov_client, client_dir)
    client_profiles.append(gov_client)

    # Example client 2: Private Business
    biz_client = ClientProfile(
        client_id="biz001",
        client_name="Private Business Inc",
        client_code="BIZ001",
        industry="Private Sector",
        project_count=0,
        status="active",
        contact_info=ContactInfo(
            email="analytics@privatebiz.com",
            phone="5559876543"
        ),
        branding_config=BrandingConfig(
            primary_color="#2E8B57",
            secondary_color="#FFFFFF",
            accent_color="#FFD700",
            text_color="#000000",
            background_color="#ffffff",
            primary_font="Arial",
            secondary_font="Helvetica"
        ),
        report_preferences=ReportPreferences()
    )
    save_client_profile(biz_client, client_dir)
    client_profiles.append(biz_client)

    log.info(f"Created {len(client_profiles)} example client profiles at {client_dir}")

    return user_profile, client_profiles

def migrate_profiles(
    source_location: Path, 
    target_location: Path,
    backup: bool = True
) -> Dict[str, int]:
    """
    Migrate profiles from one location to another.
    
    Args:
        source_location: Source profile directory
        target_location: Destination profile directory
        backup: Whether to create a backup of target location
    
    Returns:
        Dictionary with migration statistics
    """
    source_location = Path(source_location).resolve()
    target_location = Path(target_location).resolve()
    
    if not source_location.exists():
        raise FileNotFoundError(f"Source location does not exist: {source_location}")
    
    # Create backup if requested and target exists
    if backup and target_location.exists():
        backup_location = target_location.parent / f"{target_location.name}.backup"
        if backup_location.exists():
            shutil.rmtree(backup_location)
        shutil.copytree(target_location, backup_location)
        log.info(f"Created backup at {backup_location}")
    
    # Ensure target directory exists
    target_location.mkdir(parents=True, exist_ok=True)
    
    stats = {
        "users_migrated": 0,
        "clients_migrated": 0,
        "files_copied": 0,
        "errors": 0
    }
    
    try:
        # Migrate user profiles
        source_users = source_location / "users"
        if source_users.exists():
            target_users = target_location / "users"
            target_users.mkdir(parents=True, exist_ok=True)
            
            for user_file in source_users.glob("*.yaml"):
                try:
                    shutil.copy2(user_file, target_users / user_file.name)
                    stats["users_migrated"] += 1
                    stats["files_copied"] += 1
                except Exception as e:
                    log.error(f"Failed to migrate user file {user_file}: {e}")
                    stats["errors"] += 1
        
        # Migrate client profiles
        source_clients = source_location / "clients"
        if source_clients.exists():
            target_clients = target_location / "clients"
            target_clients.mkdir(parents=True, exist_ok=True)
            
            for client_file in source_clients.glob("*.yaml"):
                try:
                    shutil.copy2(client_file, target_clients / client_file.name)
                    stats["clients_migrated"] += 1
                    stats["files_copied"] += 1
                except Exception as e:
                    log.error(f"Failed to migrate client file {client_file}: {e}")
                    stats["errors"] += 1
        
        # Copy any other configuration files
        for config_file in source_location.glob("*.yaml"):
            if config_file.name not in ["user_config.yaml"]:
                try:
                    shutil.copy2(config_file, target_location / config_file.name)
                    stats["files_copied"] += 1
                except Exception as e:
                    log.error(f"Failed to migrate config file {config_file}: {e}")
                    stats["errors"] += 1
        
        log.info(f"Migration completed: {stats}")
        return stats
        
    except Exception as e:
        log.error(f"Migration failed: {e}")
        raise

def get_profile_summary(profile_location: Optional[Path] = None) -> Dict[str, any]:
    """
    Get a summary of profiles in a location.
    
    Args:
        profile_location: Location to summarize (defaults to default location)
    
    Returns:
        Dictionary with profile summary statistics
    """
    if profile_location is None:
        profile_location = get_default_profile_location()
    
    summary = {
        "location": str(profile_location),
        "exists": profile_location.exists(),
        "user_profiles": 0,
        "client_profiles": 0,
        "client_codes": [],
        "total_size_mb": 0
    }
    
    if not profile_location.exists():
        return summary
    
    # Count user profiles
    user_dir = profile_location / "users"
    if user_dir.exists():
        user_files = list(user_dir.glob("*.yaml"))
        summary["user_profiles"] = len(user_files)
    
    # Count client profiles
    client_dir = profile_location / "clients"
    if client_dir.exists():
        client_files = list(client_dir.glob("*.yaml"))
        summary["client_profiles"] = len(client_files)
        summary["client_codes"] = [f.stem for f in client_files]
    
    # Calculate total size
    try:
        total_size = sum(
            f.stat().st_size for f in profile_location.rglob("*") if f.is_file()
        )
        summary["total_size_mb"] = round(total_size / (1024 * 1024), 2)
    except Exception:
        summary["total_size_mb"] = 0
    
    return summary
