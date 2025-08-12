"""
Client configuration management for siege_utilities.
Handles client profiles, contact information, and associated design artifacts.
"""

import json
import pathlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


def create_client_profile(
    client_name: str,
    client_code: str,
    contact_info: Dict[str, str],
    **kwargs
) -> Dict[str, Any]:
    """
    Create a client profile with contact information and metadata.
    
    Args:
        client_name: Human-readable client name
        client_code: Short client code (e.g., "CLIENT001")
        contact_info: Dictionary containing contact details
        **kwargs: Additional client settings and metadata
        
    Returns:
        Dictionary with client profile configuration
        
    Example:
        >>> import siege_utilities
        >>> client = siege_utilities.create_client_profile(
        ...     "Acme Corporation",
        ...     "ACME001",
        ...     {
        ...         "primary_contact": "John Doe",
        ...         "email": "john.doe@acme.com",
        ...         "phone": "+1-555-0123",
        ...         "address": "123 Business St, City, State"
        ...     },
        ...     industry="Technology",
        ...     project_count=5
        ... )
    """
    
    # Validate required contact info
    required_fields = ['primary_contact', 'email']
    missing_fields = [field for field in required_fields if field not in contact_info]
    
    if missing_fields:
        raise ValueError(f"Missing required contact fields: {missing_fields}")
    
    # Generate unique client ID
    client_id = str(uuid.uuid4())
    
    profile = {
        'client_id': client_id,
        'client_name': client_name,
        'client_code': client_code,
        'contact_info': contact_info,
        'metadata': {
            'created_date': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'status': kwargs.get('status', 'active'),
            'industry': kwargs.get('industry', ''),
            'project_count': kwargs.get('project_count', 0),
            'notes': kwargs.get('notes', '')
        },
        'design_artifacts': {
            'logo_path': kwargs.get('logo_path', ''),
            'brand_colors': kwargs.get('brand_colors', []),
            'style_guide': kwargs.get('style_guide', ''),
            'templates': kwargs.get('templates', [])
        },
        'preferences': {
            'data_format': kwargs.get('data_format', 'parquet'),
            'report_style': kwargs.get('report_style', 'standard'),
            'notification_preferences': kwargs.get('notification_preferences', {})
        }
    }
    
    # Add any custom fields
    for key, value in kwargs.items():
        if key not in ['status', 'industry', 'project_count', 'notes', 'logo_path', 
                       'brand_colors', 'style_guide', 'templates', 'data_format', 
                       'report_style', 'notification_preferences']:
            profile['metadata'][key] = value
    
    log_info(f"Created client profile: {client_name} ({client_code})")
    return profile


def save_client_profile(
    profile: Dict[str, Any], 
    config_directory: str = "config"
) -> str:
    """
    Save client profile to JSON file.
    
    Args:
        profile: Client profile dictionary
        config_directory: Directory to save config files
        
    Returns:
        Path to saved config file
        
    Example:
        >>> client = create_client_profile("Test Client", "TEST001", {"email": "test@example.com"})
        >>> file_path = siege_utilities.save_client_profile(client)
        >>> print(f"Profile saved to: {file_path}")
    """
    
    config_dir = pathlib.Path(config_directory)
    config_dir.mkdir(parents=True, exist_ok=True)
    
    client_code = profile['client_code']
    config_file = config_dir / f"client_{client_code}.json"
    
    # Update last_updated timestamp
    profile['metadata']['last_updated'] = datetime.now().isoformat()
    
    with open(config_file, 'w') as f:
        json.dump(profile, f, indent=2)
    
    log_info(f"Saved client profile to: {config_file}")
    return str(config_file)


def load_client_profile(
    client_code: str, 
    config_directory: str = "config"
) -> Optional[Dict[str, Any]]:
    """
    Load client profile from JSON file.
    
    Args:
        client_code: Client code to load
        config_directory: Directory containing config files
        
    Returns:
        Client profile dictionary or None if not found
        
    Example:
        >>> profile = siege_utilities.load_client_profile("ACME001")
        >>> if profile:
        ...     print(f"Loaded: {profile['client_name']}")
    """
    
    config_file = pathlib.Path(config_directory) / f"client_{client_code}.json"
    
    if not config_file.exists():
        log_warning(f"Client profile not found: {config_file}")
        return None
    
    try:
        with open(config_file, 'r') as f:
            profile = json.load(f)
        
        log_info(f"Loaded client profile: {client_code}")
        return profile
        
    except Exception as e:
        log_error(f"Error loading client profile {config_file}: {e}")
        return None


def update_client_profile(
    client_code: str,
    updates: Dict[str, Any],
    config_directory: str = "config"
) -> bool:
    """
    Update an existing client profile.
    
    Args:
        client_code: Client code to update
        updates: Dictionary of updates to apply
        config_directory: Directory containing config files
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> success = siege_utilities.update_client_profile(
        ...     "ACME001",
        ...     {
        ...         "contact_info": {"phone": "+1-555-9999"},
        ...         "metadata": {"project_count": 10}
        ...     }
        ... )
    """
    
    profile = load_client_profile(client_code, config_directory)
    
    if profile is None:
        log_error(f"Cannot update - client profile not found: {client_code}")
        return False
    
    try:
        # Apply updates recursively
        def update_nested_dict(target: Dict, updates: Dict):
            for key, value in updates.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    update_nested_dict(target[key], value)
                else:
                    target[key] = value
        
        update_nested_dict(profile, updates)
        
        # Save updated profile
        save_client_profile(profile, config_directory)
        log_info(f"Updated client profile: {client_code}")
        return True
        
    except Exception as e:
        log_error(f"Error updating client profile {client_code}: {e}")
        return False


def list_client_profiles(
    config_directory: str = "config"
) -> List[Dict[str, Any]]:
    """
    List all available client profiles.
    
    Args:
        config_directory: Directory containing config files
        
    Returns:
        List of dictionaries with client profile info
        
    Example:
        >>> clients = siege_utilities.list_client_profiles()
        >>> for client in clients:
        ...     print(f"{client['code']}: {client['name']}")
    """
    
    config_dir = pathlib.Path(config_directory)
    
    if not config_dir.exists():
        log_info("Config directory does not exist")
        return []
    
    clients = []
    
    for config_file in config_dir.glob("client_*.json"):
        try:
            with open(config_file, 'r') as f:
                profile = json.load(f)
            
            clients.append({
                'code': profile['client_code'],
                'name': profile['client_name'],
                'status': profile['metadata']['status'],
                'industry': profile['metadata']['industry'],
                'project_count': profile['metadata']['project_count'],
                'config_file': str(config_file)
            })
            
        except Exception as e:
            log_error(f"Error reading client profile {config_file}: {e}")
    
    log_info(f"Found {len(clients)} client profiles")
    return clients


def search_client_profiles(
    search_term: str,
    search_fields: List[str] = None,
    config_directory: str = "config"
) -> List[Dict[str, Any]]:
    """
    Search client profiles by various criteria.
    
    Args:
        search_term: Term to search for
        search_fields: List of fields to search in (default: all text fields)
        config_directory: Directory containing config files
        
    Returns:
        List of matching client profiles
        
    Example:
        >>> results = siege_utilities.search_client_profiles(
        ...     "Technology",
        ...     ["metadata.industry", "client_name"]
        ... )
    """
    
    if search_fields is None:
        search_fields = ['client_name', 'client_code', 'metadata.industry', 'contact_info.primary_contact']
    
    all_profiles = []
    search_term_lower = search_term.lower()
    
    # Load all profiles
    for config_file in pathlib.Path(config_directory).glob("client_*.json"):
        try:
            with open(config_file, 'r') as f:
                profile = json.load(f)
            all_profiles.append(profile)
        except Exception:
            continue
    
    matching_profiles = []
    
    for profile in all_profiles:
        for field_path in search_fields:
            # Navigate nested dictionary
            value = profile
            for key in field_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            
            if value and search_term_lower in str(value).lower():
                matching_profiles.append(profile)
                break
    
    log_info(f"Found {len(matching_profiles)} profiles matching '{search_term}'")
    return matching_profiles


def associate_client_with_project(
    client_code: str,
    project_code: str,
    config_directory: str = "config"
) -> bool:
    """
    Associate a client with a project.
    
    Args:
        client_code: Client code to associate
        project_code: Project code to associate with
        config_directory: Directory containing config files
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> success = siege_utilities.associate_client_with_project("ACME001", "PROJ001")
    """
    
    # Load client profile
    client_profile = load_client_profile(client_code, config_directory)
    if not client_profile:
        log_error(f"Client profile not found: {client_code}")
        return False
    
    # Load project config
    try:
        from .projects import load_project_config
        project_config = load_project_config(project_code, config_directory)
        if not project_config:
            log_error(f"Project config not found: {project_code}")
            return False
    except ImportError:
        log_error("Projects module not available")
        return False
    
    try:
        # Add project association to client profile
        if 'project_associations' not in client_profile:
            client_profile['project_associations'] = []
        
        if project_code not in client_profile['project_associations']:
            client_profile['project_associations'].append(project_code)
            client_profile['metadata']['project_count'] = len(client_profile['project_associations'])
            
            # Save updated profile
            save_client_profile(client_profile, config_directory)
            log_info(f"Associated client {client_code} with project {project_code}")
            return True
        else:
            log_info(f"Client {client_code} already associated with project {project_code}")
            return True
            
    except Exception as e:
        log_error(f"Error associating client with project: {e}")
        return False


def get_client_project_associations(
    client_code: str,
    config_directory: str = "config"
) -> List[str]:
    """
    Get all projects associated with a client.
    
    Args:
        client_code: Client code to check
        config_directory: Directory containing config files
        
    Returns:
        List of associated project codes
        
    Example:
        >>> projects = siege_utilities.get_client_project_associations("ACME001")
        >>> print(f"Client has {len(projects)} projects")
    """
    
    profile = load_client_profile(client_code, config_directory)
    
    if not profile:
        return []
    
    return profile.get('project_associations', [])


def validate_client_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a client profile and return validation results.
    
    Args:
        profile: Client profile to validate
        
    Returns:
        Dictionary with validation results and any issues found
        
    Example:
        >>> profile = create_client_profile("Test", "TEST001", {"email": "test@example.com"})
        >>> validation = siege_utilities.validate_client_profile(profile)
        >>> if validation['is_valid']:
        ...     print("Profile is valid")
    """
    
    validation_result = {
        'is_valid': True,
        'issues': [],
        'warnings': []
    }
    
    # Check required fields
    required_fields = ['client_name', 'client_code', 'contact_info']
    for field in required_fields:
        if field not in profile:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"Missing required field: {field}")
    
    # Check contact info
    if 'contact_info' in profile:
        contact_info = profile['contact_info']
        if 'email' not in contact_info:
            validation_result['is_valid'] = False
            validation_result['issues'].append("Missing email in contact info")
        
        if 'primary_contact' not in contact_info:
            validation_result['is_valid'] = False
            validation_result['issues'].append("Missing primary contact")
    
    # Check for warnings
    if 'metadata' in profile:
        metadata = profile['metadata']
        if metadata.get('project_count', 0) == 0:
            validation_result['warnings'].append("No projects associated with client")
    
    # Check design artifacts
    if 'design_artifacts' in profile:
        artifacts = profile['design_artifacts']
        if not artifacts.get('logo_path'):
            validation_result['warnings'].append("No logo path specified")
    
    log_info(f"Client profile validation: {len(validation_result['issues'])} issues, {len(validation_result['warnings'])} warnings")
    return validation_result


# Import logging functions at the end to avoid circular imports
try:
    from ..core.logging import log_info, log_warning, log_error
except ImportError:
    # Fallback if core logging not available
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")
