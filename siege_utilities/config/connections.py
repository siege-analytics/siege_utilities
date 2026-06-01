"""
Connection management and persistence for siege_utilities.
Handles notebook connections, Spark connections, and their persistence.
"""

import json
import os
import pathlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

__all__ = [
    'create_connection_profile',
    'save_connection_profile',
    'load_connection_profile',
    'find_connection_by_name',
    'list_connection_profiles',
    'update_connection_profile',
    'verify_connection_profile',
    'get_connection_status',
    'cleanup_old_connections',
]

logger = logging.getLogger(__name__)


def create_connection_profile(
    name: str,
    connection_type: str,
    connection_params: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    Create a connection profile for various connection types.
    
    Args:
        name: Friendly name for the connection
        connection_type: Type of connection (notebook, spark, database, api, etc.)
        connection_params: Connection-specific parameters
        **kwargs: Additional connection settings
        
    Returns:
        Dictionary with connection profile configuration
        
    Example:
        >>> import siege_utilities  # doctest: +SKIP
        >>> notebook_conn = siege_utilities.create_connection_profile(  # doctest: +SKIP
        ...     "Jupyter Lab",
        ...     "notebook",
        ...     {
        ...         "url": "http://localhost:8888",
        ...         "token": "abc123",
        ...         "workspace": "/home/user/notebooks"
        ...     },
        ...     auto_connect=True
        ... )
    """
    
    # Validate required parameters
    if not connection_params:
        raise ValueError("Connection parameters cannot be empty")
    
    # Generate unique connection ID
    connection_id = str(uuid.uuid4())
    
    profile = {
        'connection_id': connection_id,
        'name': name,
        'connection_type': connection_type,
        'connection_params': connection_params,
        'metadata': {
            'created_date': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat(),
            'last_connected': None,
            'connection_count': 0,
            'status': kwargs.get('status', 'active'),
            'auto_connect': kwargs.get('auto_connect', False),
            'timeout': kwargs.get('timeout', 30),
            'retry_attempts': kwargs.get('retry_attempts', 3)
        },
        'security': {
            'encrypted': kwargs.get('encrypted', False),
            'encryption_method': kwargs.get('encryption_method', ''),
            'credentials_stored': kwargs.get('credentials_stored', False)
        },
        'tags': kwargs.get('tags', []),
        'notes': kwargs.get('notes', '')
    }
    
    # Add connection-specific metadata
    if connection_type == 'notebook':
        profile['notebook_specific'] = {
            'kernel_type': kwargs.get('kernel_type', 'python3'),
            'auto_start': kwargs.get('auto_start', True),
            'workspace_path': kwargs.get('workspace_path', ''),
            'preferred_browser': kwargs.get('preferred_browser', 'default')
        }
    elif connection_type == 'spark':
        profile['spark_specific'] = {
            'master_url': kwargs.get('master_url', 'local[*]'),
            'app_name': kwargs.get('app_name', 'SiegeAnalytics'),
            'driver_memory': kwargs.get('driver_memory', '2g'),
            'executor_memory': kwargs.get('executor_memory', '2g'),
            'spark_home': kwargs.get('spark_home', ''),
            'hadoop_conf_dir': kwargs.get('hadoop_conf_dir', '')
        }
    elif connection_type == 'database':
        profile['database_specific'] = {
            'connection_pool_size': kwargs.get('connection_pool_size', 5),
            'ssl_mode': kwargs.get('ssl_mode', 'prefer'),
            'read_timeout': kwargs.get('read_timeout', 30),
            'write_timeout': kwargs.get('write_timeout', 30)
        }
    
    log_info(f"Created connection profile: {name} ({connection_type})")
    return profile


def save_connection_profile(
    profile: Dict[str, Any], 
    config_directory: str = "config"
) -> str:
    """
    Save connection profile to JSON file.
    
    Args:
        profile: Connection profile dictionary
        config_directory: Directory to save config files
        
    Returns:
        Path to saved config file
        
    Example:
        >>> conn = create_connection_profile("Test", "notebook", {"url": "http://test"})  # doctest: +SKIP
        >>> file_path = siege_utilities.save_connection_profile(conn)  # doctest: +SKIP
    """
    
    config_dir = pathlib.Path(config_directory)
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create connections subdirectory
    connections_dir = config_dir / "connections"
    connections_dir.mkdir(exist_ok=True)
    
    connection_id = profile['connection_id']
    config_file = connections_dir / f"connection_{connection_id}.json"
    
    # Update last_used timestamp
    profile['metadata']['last_used'] = datetime.now().isoformat()
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)
    os.chmod(config_file, 0o600)

    log_info(f"Saved connection profile to: {config_file}")
    return str(config_file)


def load_connection_profile(
    connection_id: str,
    config_directory: str = "config"
) -> Dict[str, Any]:
    """
    Load connection profile from JSON file.

    Args:
        connection_id: Connection ID to load
        config_directory: Directory containing config files

    Returns:
        Connection profile dictionary.

    Raises:
        FileNotFoundError: If the connection profile does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        OSError: If the file cannot be read.

    Example:
        >>> profile = siege_utilities.load_connection_profile("uuid-here")  # doctest: +SKIP
        >>> print(f"Loaded: {profile['name']}")  # doctest: +SKIP
    """

    connections_dir = pathlib.Path(config_directory) / "connections"
    config_file = connections_dir / f"connection_{connection_id}.json"

    if not config_file.exists():
        raise FileNotFoundError(f"Connection profile not found: {config_file}")

    with open(config_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)

    log_info(f"Loaded connection profile: {connection_id}")
    return profile


def find_connection_by_name(
    name: str, 
    config_directory: str = "config"
) -> Optional[Dict[str, Any]]:
    """
    Find a connection profile by name.
    
    Args:
        name: Connection name to search for
        config_directory: Directory containing config files
        
    Returns:
        Connection profile dictionary or None if not found
        
    Example:
        >>> profile = siege_utilities.find_connection_by_name("Jupyter Lab")  # doctest: +SKIP
        >>> if profile:  # doctest: +SKIP
        ...     print(f"Found connection: {profile['connection_id']}")
    """
    
    connections_dir = pathlib.Path(config_directory) / "connections"
    
    if not connections_dir.exists():
        return None
    
    for config_file in connections_dir.glob("connection_*.json"):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            if profile['name'] == name:
                return profile
                
        except (OSError, json.JSONDecodeError, KeyError):
            logger.warning("Skipping unreadable connection config: %s", config_file, exc_info=True)
            continue

    return None


def list_connection_profiles(
    connection_type: str = None,
    config_directory: str = "config"
) -> List[Dict[str, Any]]:
    """
    List all available connection profiles, optionally filtered by type.
    
    Args:
        connection_type: Optional filter by connection type
        config_directory: Directory containing config files
        
    Returns:
        List of dictionaries with connection profile info
        
    Example:
        >>> connections = siege_utilities.list_connection_profiles("notebook")  # doctest: +SKIP
        >>> for conn in connections:  # doctest: +SKIP
        ...     print(f"{conn['name']}: {conn['status']}")
    """
    
    connections_dir = pathlib.Path(config_directory) / "connections"
    
    if not connections_dir.exists():
        log_info("Connections directory does not exist")
        return []
    
    connections = []
    
    for config_file in connections_dir.glob("connection_*.json"):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            # Filter by type if specified
            if connection_type and profile['connection_type'] != connection_type:
                continue
            
            connections.append({
                'connection_id': profile['connection_id'],
                'name': profile['name'],
                'type': profile['connection_type'],
                'status': profile['metadata']['status'],
                'last_used': profile['metadata']['last_used'],
                'connection_count': profile['metadata']['connection_count'],
                'config_file': str(config_file)
            })
            
        except (OSError, json.JSONDecodeError, KeyError) as e:
            log_error(f"Error reading connection profile {config_file}: {e}")
    
    log_info(f"Found {len(connections)} connection profiles")
    return connections


def update_connection_profile(
    connection_id: str,
    updates: Dict[str, Any],
    config_directory: str = "config"
) -> None:
    """
    Update an existing connection profile.

    Args:
        connection_id: Connection ID to update
        updates: Dictionary of updates to apply
        config_directory: Directory containing config files

    Raises:
        FileNotFoundError: If the connection profile does not exist.
        OSError: If the profile cannot be read or written.

    Example:
        >>> siege_utilities.update_connection_profile(  # doctest: +SKIP
        ...     "uuid-here",
        ...     {"metadata": {"status": "inactive"}}
        ... )
    """

    profile = load_connection_profile(connection_id, config_directory)

    def update_nested_dict(target: Dict, source: Dict):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                update_nested_dict(target[key], value)
            else:
                target[key] = value

    update_nested_dict(profile, updates)

    save_connection_profile(profile, config_directory)
    log_info(f"Updated connection profile: {connection_id}")


def verify_connection_profile(
    connection_id: str,
    config_directory: str = "config"
) -> Dict[str, Any]:
    """
    Test a connection to verify it's working.
    
    Args:
        connection_id: Connection ID to test
        config_directory: Directory containing config files
        
    Returns:
        Dictionary with test results
        
    Example:
        >>> result = siege_utilities.test_connection_profile("uuid-here")  # doctest: +SKIP
        >>> if result['success']:  # doctest: +SKIP
        ...     print("Connection successful!")
    """
    
    profile = load_connection_profile(connection_id, config_directory)

    connection_type = profile['connection_type']
    test_result = {
        'success': False,
        'connection_type': connection_type,
        'timestamp': datetime.now().isoformat(),
        'error': None,
        'response_time_ms': None
    }
    
    try:
        start_time = datetime.now()
        
        if connection_type == 'notebook':
            # Test notebook connection
            import requests
            url = profile['connection_params']['url']
            token = profile['connection_params'].get('token', '')
            
            headers = {}
            if token:
                headers['Authorization'] = f'token {token}'
            
            response = requests.get(f"{url}/api/status", headers=headers, timeout=10)
            test_result['success'] = response.status_code == 200
            
        elif connection_type == 'spark':
            # Test Spark connection
            try:
                from pyspark.sql import SparkSession
                spark = SparkSession.builder.appName("ConnectionTest").getOrCreate()
                # Simple test - get Spark version
                version = spark.version
                test_result['success'] = True
                test_result['spark_version'] = version
                spark.stop()
            except ImportError:
                test_result['error'] = 'PySpark not available'
            except (RuntimeError, ValueError, OSError) as e:
                test_result['error'] = str(e)

        elif connection_type == 'database':
            # Test database connection
            try:
                from sqlalchemy import create_engine
                conn_string = profile['connection_params'].get('connection_string')
                if conn_string:
                    engine = create_engine(conn_string)
                    with engine.connect() as conn:
                        result = conn.execute("SELECT 1")
                        result.fetchone()
                    test_result['success'] = True
                    engine.dispose()
                else:
                    test_result['error'] = 'No connection string provided'
            except ImportError:
                test_result['error'] = 'SQLAlchemy not available'
            except (RuntimeError, ValueError, OSError) as e:
                test_result['error'] = str(e)

        else:
            test_result['error'] = f'Connection testing not implemented for {connection_type}'
        
        # Calculate response time
        end_time = datetime.now()
        test_result['response_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        # Update connection profile with test results
        if test_result['success']:
            profile['metadata']['last_connected'] = datetime.now().isoformat()
            profile['metadata']['connection_count'] += 1
            save_connection_profile(profile, config_directory)
        
        log_info(f"Connection test for {connection_id}: {'SUCCESS' if test_result['success'] else 'FAILED'}")
        
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
        test_result['error'] = str(e)
        log_error(f"Error testing connection {connection_id}: {e}")
    
    return test_result


def get_connection_status(
    connection_id: str,
    config_directory: str = "config"
) -> Dict[str, Any]:
    """
    Get the current status and health of a connection.
    
    Args:
        connection_id: Connection ID to check
        config_directory: Directory containing config files
        
    Returns:
        Dictionary with connection status information
        
    Example:
        >>> status = siege_utilities.get_connection_status("uuid-here")  # doctest: +SKIP
        >>> print(f"Status: {status['status']}, Last connected: {status['last_connected']}")  # doctest: +SKIP
    """
    
    profile = load_connection_profile(connection_id, config_directory)

    metadata = profile['metadata']
    last_connected = metadata.get('last_connected')
    
    # Determine connection health
    if last_connected:
        last_connected_dt = datetime.fromisoformat(last_connected)
        now = datetime.now(last_connected_dt.tzinfo)
        time_since_connection = now - last_connected_dt
        
        if time_since_connection < timedelta(hours=1):
            health = 'excellent'
        elif time_since_connection < timedelta(hours=24):
            health = 'good'
        elif time_since_connection < timedelta(days=7):
            health = 'fair'
        else:
            health = 'poor'
    else:
        health = 'unknown'
    
    status_info = {
        'connection_id': connection_id,
        'name': profile['name'],
        'type': profile['connection_type'],
        'status': metadata['status'],
        'health': health,
        'last_connected': last_connected,
        'connection_count': metadata['connection_count'],
        'auto_connect': metadata['auto_connect'],
        'created_date': metadata['created_date'],
        'last_used': metadata['last_used']
    }
    
    return status_info


def cleanup_old_connections(
    days_old: int = 90,
    config_directory: str = "config"
) -> int:
    """
    Remove old, unused connection profiles.
    
    Args:
        days_old: Remove connections older than this many days
        config_directory: Directory containing config files
        
    Returns:
        Number of connections removed
        
    Example:
        >>> removed = siege_utilities.cleanup_old_connections(30)  # doctest: +SKIP
        >>> print(f"Removed {removed} old connections")  # doctest: +SKIP
    """
    
    connections_dir = pathlib.Path(config_directory) / "connections"
    
    if not connections_dir.exists():
        return 0
    
    removed_count = 0

    for config_file in connections_dir.glob("connection_*.json"):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            created_date = datetime.fromisoformat(profile['metadata']['created_date'])
            last_used = datetime.fromisoformat(profile['metadata']['last_used'])
            cutoff_date = datetime.now(created_date.tzinfo) - timedelta(days=days_old)

            # Remove if old and unused
            if (created_date < cutoff_date and
                last_used < cutoff_date and 
                profile['metadata']['connection_count'] == 0):
                
                config_file.unlink()
                removed_count += 1
                log_info(f"Removed old connection: {profile['name']}")
                
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            log_error(f"Error processing connection file {config_file}: {e}")
    
    log_info(f"Cleaned up {removed_count} old connections")
    return removed_count


# Import logging functions at the end to avoid circular imports
try:
    from ..core.logging import log_info, log_warning, log_error
except ImportError:
    # Fallback if core logging not available
    def log_info(message): logger.info(message)
    def log_warning(message): logger.warning(message)
    def log_error(message): logger.error(message)
