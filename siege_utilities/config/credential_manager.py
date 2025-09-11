"""
Centralized Credential Management for siege_utilities

This module provides secure credential storage and retrieval using multiple backends:
- 1Password CLI integration
- Environment variables
- Apple Keychain (macOS)
- Interactive prompts (fallback)

Supports all analytics services (Google Analytics, Facebook Business, etc.)
and database connections with a unified interface.
"""

import subprocess
import json
import os
import tempfile
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path

# Import logging functions
try:
    from ..core.logging import log_info, log_warning, log_error
except ImportError:
    # Fallback if core logging not available
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")


class CredentialManager:
    """
    Unified credential management system with fallback hierarchy.
    
    Fallback priority (mirrors Zsh system):
    1. Local files (JSON, tokens, etc.)
    2. Environment variables (for existing workflows)
    3. 1Password CLI (secure storage)
    4. Apple Keychain (macOS only)
    5. Interactive prompts (fallback)
    """
    
    def __init__(self, 
                 backend_priority: List[str] = None, 
                 default_vault: str = "Private",
                 credential_paths: List[Union[str, Path]] = None):
        """
        Initialize credential manager.
        
        Args:
            backend_priority: List of backends in priority order
                            ['files', 'env', '1password', 'keychain', 'prompt']
            default_vault: Default 1Password vault to use
            credential_paths: Additional paths to search for credential files
        """
        self.backend_priority = backend_priority or ['files', 'env', '1password', 'keychain', 'prompt']
        self.default_vault = default_vault
        self.credential_paths = self._setup_credential_paths(credential_paths)
        self.available_backends = self._detect_available_backends()
        
        log_info(f"Credential manager initialized with backends: {self.available_backends}")
        log_info(f"Credential search paths: {self.credential_paths}")
    
    def _setup_credential_paths(self, additional_paths: Optional[List[Union[str, Path]]]) -> List[Path]:
        """Setup credential file search paths."""
        paths = []
        
        # Current working directory credentials folder
        paths.append(Path.cwd() / "credentials")
        
        # User's siege utilities credentials directory
        home_creds = Path.home() / ".siege_utilities" / "credentials"
        paths.append(home_creds)
        
        # Ensure directories exist
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        
        # Add user-configured paths
        if additional_paths:
            for path in additional_paths:
                paths.append(Path(path))
        
        # Try to get paths from user config
        try:
            from .user_config import get_user_config
            user_config = get_user_config()
            if user_config and hasattr(user_config, 'credential_paths'):
                for path in user_config.credential_paths:
                    paths.append(Path(path))
        except Exception:
            pass  # User config not available or no credential paths configured
        
        return paths
    
    def _detect_available_backends(self) -> Dict[str, bool]:
        """Detect which credential backends are available."""
        backends = {
            'files': True,  # Always available
            'env': True,  # Always available
            'prompt': True,  # Always available
            '1password': self._check_1password_available(),
            'keychain': self._check_keychain_available()
        }
        
        available = [k for k, v in backends.items() if v]
        log_info(f"Available credential backends: {available}")
        return backends
    
    def _check_1password_available(self) -> bool:
        """Check if 1Password CLI is available and authenticated."""
        try:
            result = subprocess.run(['op', 'account', 'list'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _check_keychain_available(self) -> bool:
        """Check if Apple Keychain is available (macOS only)."""
        if os.name != 'posix' or not os.path.exists('/usr/bin/security'):
            return False
        try:
            result = subprocess.run(['security', 'list-keychains'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_credential(self, service: str, username: str, field: str = "password", 
                      search_paths: Optional[List[Path]] = None) -> Optional[str]:
        """
        Retrieve credential using configured backend priority.
        
        Args:
            service: Service name (e.g., 'google-analytics', 'postgres')
            username: Username or identifier
            field: Field to retrieve ('password', 'client_id', 'client_secret', etc.)
            search_paths: Additional paths to search for credential files
            
        Returns:
            Credential value or None if not found
        """
        for backend in self.backend_priority:
            if not self.available_backends.get(backend, False):
                continue
                
            try:
                if backend == 'files':
                    value = self._get_from_files(service, username, field, search_paths)
                elif backend == 'env':
                    value = self._get_from_env(service, username, field)
                elif backend == '1password':
                    value = self._get_from_1password(service, field)
                elif backend == 'keychain':
                    value = self._get_from_keychain(service, username)
                elif backend == 'prompt':
                    value = self._get_from_prompt(service, username, field)
                else:
                    continue
                    
                if value:
                    log_info(f"Retrieved {field} for {service} from {backend}")
                    return value
                    
            except Exception as e:
                log_warning(f"Error retrieving from {backend}: {e}")
                continue
        
        log_warning(f"Could not retrieve {field} for {service} from any backend")
        return None
    
    def _get_from_files(self, service: str, username: str, field: str, 
                       additional_paths: Optional[List[Path]] = None) -> Optional[str]:
        """Get credential from local files."""
        search_paths = self.credential_paths.copy()
        if additional_paths:
            search_paths.extend(additional_paths)
        
        # Common file patterns to look for
        patterns = [
            f"{service}_{field}.txt",
            f"{service}_{field}.json",
            f"{service}_credentials.json",
            f"{service}.json",
            f"client_secret_{service}.json",  # Google-style
            f"client_secret_*.json",  # Google wildcard
            f"{field}.txt",
            f"credentials.json"
        ]
        
        for path in search_paths:
            if not path.exists():
                continue
                
            for pattern in patterns:
                if '*' in pattern:
                    # Handle wildcard patterns
                    matching_files = list(path.glob(pattern))
                    for file_path in matching_files:
                        value = self._extract_from_file(file_path, service, field)
                        if value:
                            return value
                else:
                    file_path = path / pattern
                    if file_path.exists():
                        value = self._extract_from_file(file_path, service, field)
                        if value:
                            return value
        
        return None
    
    def _extract_from_file(self, file_path: Path, service: str, field: str) -> Optional[str]:
        """Extract credential from a specific file."""
        try:
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if 'installed' in data:  # Google OAuth format
                    return data['installed'].get(field)
                elif field in data:  # Direct field access
                    return data[field]
                elif service in data:  # Service-specific section
                    service_data = data[service]
                    if isinstance(service_data, dict):
                        return service_data.get(field)
                    else:
                        return service_data if field == 'password' else None
                else:
                    # Try to find field in nested structure
                    return self._find_field_in_dict(data, field)
            
            else:  # Plain text file
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    return content if content else None
                    
        except Exception as e:
            log_warning(f"Error reading credential file {file_path}: {e}")
            return None
    
    def _find_field_in_dict(self, data: Dict[str, Any], field: str) -> Optional[str]:
        """Recursively search for field in nested dictionary."""
        if isinstance(data, dict):
            if field in data:
                return str(data[field])
            for value in data.values():
                if isinstance(value, dict):
                    result = self._find_field_in_dict(value, field)
                    if result:
                        return result
        return None
    
    def _get_from_env(self, service: str, username: str, field: str) -> Optional[str]:
        """Get credential from environment variables."""
        # Try multiple environment variable patterns
        patterns = [
            f"{service.upper()}_{field.upper()}",
            f"{service.upper()}_{username.upper()}_{field.upper()}",
            f"{field.upper()}_{service.upper()}",
        ]
        
        for pattern in patterns:
            value = os.getenv(pattern.replace('-', '_'))
            if value:
                return value
        return None
    
    def _get_from_1password(self, service: str, field: str) -> Optional[str]:
        """Get credential from 1Password."""
        try:
            # Try to find item by service name
            result = subprocess.run([
                'op', 'item', 'get', service, f'--field={field}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
            # Try with common service name variations
            service_variations = [
                f"{service} API",
                f"{service} Credentials", 
                f"{service.replace('-', ' ').title()} API",
                f"{service.replace('-', ' ').title()} Credentials"
            ]
            
            for variation in service_variations:
                result = subprocess.run([
                    'op', 'item', 'get', variation, f'--field={field}'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    return result.stdout.strip()
                    
            return None
            
        except Exception:
            return None
    
    def _get_from_keychain(self, service: str, username: str) -> Optional[str]:
        """Get credential from Apple Keychain."""
        try:
            result = subprocess.run([
                'security', 'find-generic-password',
                '-s', service,
                '-a', username,
                '-w'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            return None
            
        except Exception:
            return None
    
    def _get_from_prompt(self, service: str, username: str, field: str) -> Optional[str]:
        """Get credential via interactive prompt."""
        # Only prompt in interactive shells
        if not (os.isatty(0) and os.isatty(1)):
            return None
            
        try:
            import getpass
            prompt = f"Enter {field} for {service} ({username}): "
            
            if field.lower() in ['password', 'secret', 'token', 'key']:
                return getpass.getpass(prompt)
            else:
                return input(prompt)
                
        except (EOFError, KeyboardInterrupt):
            return None
    
    def store_credential(self, service: str, username: str, value: str, 
                        field: str = "password", backend: str = "1password") -> bool:
        """
        Store credential in specified backend.
        
        Args:
            service: Service name
            username: Username or identifier  
            value: Credential value
            field: Field name
            backend: Backend to use ('1password', 'keychain', 'env')
            
        Returns:
            True if successful, False otherwise
        """
        if backend == '1password' and self.available_backends.get('1password'):
            return self._store_in_1password(service, username, value, field)
        elif backend == 'keychain' and self.available_backends.get('keychain'):
            return self._store_in_keychain(service, username, value)
        elif backend == 'env':
            return self._store_in_env(service, username, value, field)
        else:
            log_error(f"Backend '{backend}' not available")
            return False
    
    def _store_in_1password(self, service: str, username: str, value: str, field: str) -> bool:
        """Store credential in 1Password."""
        try:
            # Check if item exists, update or create
            existing = self._get_from_1password(service, field)
            
            if existing:
                # Update existing item
                result = subprocess.run([
                    'op', 'item', 'edit', service,
                    f'{field}={value}'
                ], capture_output=True, text=True)
            else:
                # Create new item
                result = subprocess.run([
                    'op', 'item', 'create',
                    '--category=login',
                    f'--title={service}',
                    f'--vault={self.default_vault}',
                    f'username={username}',
                    f'{field}={value}',
                    f'--tags=siege-utilities,{service}'
                ], capture_output=True, text=True)
            
            if result.returncode == 0:
                log_info(f"Stored {field} for {service} in 1Password")
                return True
            else:
                log_error(f"Failed to store in 1Password: {result.stderr}")
                return False
                
        except Exception as e:
            log_error(f"Error storing in 1Password: {e}")
            return False
    
    def _store_in_keychain(self, service: str, username: str, value: str) -> bool:
        """Store credential in Apple Keychain."""
        try:
            result = subprocess.run([
                'security', 'add-generic-password',
                '-s', service,
                '-a', username,
                '-w', value,
                '-U'  # Update if exists
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                log_info(f"Stored credential for {service} in Keychain")
                return True
            else:
                log_error(f"Failed to store in Keychain: {result.stderr}")
                return False
                
        except Exception as e:
            log_error(f"Error storing in Keychain: {e}")
            return False
    
    def _store_in_env(self, service: str, username: str, value: str, field: str) -> bool:
        """Store credential as environment variable (session only)."""
        env_var = f"{service.upper()}_{field.upper()}".replace('-', '_')
        os.environ[env_var] = value
        log_info(f"Stored {field} for {service} as environment variable {env_var}")
        return True
    
    def store_google_analytics_credentials(self, credentials_data: Dict[str, Any],
                                         item_title: str = "Google Analytics API",
                                         vault: Optional[str] = None) -> bool:
        """
        Store Google Analytics OAuth credentials.
        
        Args:
            credentials_data: OAuth2 credentials from Google Cloud Console
            item_title: Title for the credential item
            vault: 1Password vault (uses default if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available_backends.get('1password'):
            log_error("1Password not available for storing GA credentials")
            return False
        
        vault = vault or self.default_vault
        
        try:
            if 'installed' not in credentials_data:
                log_error("Invalid Google Analytics credentials format")
                return False
            
            creds = credentials_data['installed']
            
            # Create comprehensive 1Password item with both individual fields and raw JSON
            import json
            raw_json = json.dumps(credentials_data, indent=2)
            
            cmd = [
                'op', 'item', 'create',
                '--category=API Credential',
                f'--title={item_title}',
                f'--vault={vault}',
                f'client_id={creds["client_id"]}',
                f'client_secret={creds["client_secret"]}',
                f'auth_uri={creds["auth_uri"]}',
                f'token_uri={creds["token_uri"]}',
                f'raw_json[text]={raw_json}',
                '--tags=google-analytics,api,oauth2,siege-utilities'
            ]
            
            # Add redirect URIs if present
            if 'redirect_uris' in creds:
                redirect_uris = ','.join(creds['redirect_uris'])
                cmd.append(f'redirect_uris={redirect_uris}')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                log_info(f"Stored Google Analytics credentials: '{item_title}'")
                
                # Verify storage
                test_client_id = self.get_credential('google-analytics', 'api', 'client_id')
                if test_client_id:
                    log_info("Google Analytics credential storage verified")
                    return True
                else:
                    log_warning("Could not verify GA credential storage")
                    return False
            else:
                log_error(f"Failed to store GA credentials: {result.stderr}")
                return False
                
        except Exception as e:
            log_error(f"Error storing Google Analytics credentials: {e}")
            return False
    
    def get_google_analytics_credentials(self, item_title: str = "Google Analytics API") -> Optional[Tuple[str, str]]:
        """
        Get Google Analytics credentials for GoogleAnalyticsConnector.
        
        Args:
            item_title: Title of the credential item
            
        Returns:
            Tuple of (client_id, client_secret) or None if not found
        """
        try:
            # Try to get from 1Password using item title
            client_id = self._get_from_1password(item_title, 'client_id')
            client_secret = self._get_from_1password(item_title, 'client_secret')
            
            if client_id and client_secret:
                return client_id, client_secret
            
            # Fallback to general credential retrieval
            client_id = self.get_credential('google-analytics', 'api', 'client_id')
            client_secret = self.get_credential('google-analytics', 'api', 'client_secret')
            
            if client_id and client_secret:
                return client_id, client_secret
            
            log_error("Could not retrieve Google Analytics credentials")
            return None
            
        except Exception as e:
            log_error(f"Error retrieving Google Analytics credentials: {e}")
            return None
    
    def list_stored_credentials(self, service_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List stored credentials across all backends.
        
        Args:
            service_filter: Optional service name to filter by
            
        Returns:
            List of credential information dictionaries
        """
        credentials = []
        
        # List from 1Password
        if self.available_backends.get('1password'):
            try:
                tags = 'siege-utilities'
                if service_filter:
                    tags += f',{service_filter}'
                
                result = subprocess.run([
                    'op', 'item', 'list', f'--tags={tags}', '--format=json'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    items = json.loads(result.stdout)
                    for item in items:
                        credentials.append({
                            'backend': '1password',
                            'service': item.get('title', ''),
                            'id': item.get('id', ''),
                            'vault': item.get('vault', {}).get('name', ''),
                            'tags': item.get('tags', [])
                        })
            except Exception as e:
                log_warning(f"Error listing 1Password credentials: {e}")
        
        # List environment variables (siege-utilities related)
        env_credentials = []
        for key, value in os.environ.items():
            if any(pattern in key.lower() for pattern in ['siege', 'analytics', 'postgres', 'mysql']):
                if any(field in key.lower() for field in ['password', 'secret', 'key', 'token']):
                    env_credentials.append({
                        'backend': 'env',
                        'service': key.lower(),
                        'variable': key,
                        'has_value': bool(value)
                    })
        
        credentials.extend(env_credentials)
        
        log_info(f"Found {len(credentials)} stored credentials")
        return credentials
    
    def backend_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all credential backends."""
        status = {}
        
        # Environment variables
        status['env'] = {
            'available': True,
            'status': 'Always available',
            'description': 'Environment variables'
        }
        
        # 1Password CLI
        if self.available_backends.get('1password'):
            try:
                result = subprocess.run(['op', 'account', 'list'], capture_output=True, text=True)
                if result.returncode == 0:
                    accounts = result.stdout.strip().split('\n')
                    status['1password'] = {
                        'available': True,
                        'status': f'Authenticated ({len(accounts)} accounts)',
                        'description': '1Password CLI'
                    }
                else:
                    status['1password'] = {
                        'available': False,
                        'status': 'Not authenticated',
                        'description': '1Password CLI (run: op signin)'
                    }
            except Exception:
                status['1password'] = {
                    'available': False,
                    'status': 'Error checking status',
                    'description': '1Password CLI'
                }
        else:
            status['1password'] = {
                'available': False,
                'status': 'Not installed',
                'description': '1Password CLI (install: brew install 1password-cli)'
            }
        
        # Apple Keychain
        if self.available_backends.get('keychain'):
            status['keychain'] = {
                'available': True,
                'status': 'Available',
                'description': 'Apple Keychain (macOS)'
            }
        else:
            status['keychain'] = {
                'available': False,
                'status': 'Not available',
                'description': 'Apple Keychain (requires macOS)'
            }
        
        # Interactive prompts
        status['prompt'] = {
            'available': True,
            'status': 'Available (fallback)',
            'description': 'Interactive prompts'
        }
        
        return status


# Convenience functions for common operations
def get_credential(service: str, username: str, field: str = "password", 
                  search_paths: Optional[List[Union[str, Path]]] = None) -> Optional[str]:
    """
    Get credential using default credential manager.
    
    Args:
        service: Service name
        username: Username or identifier
        field: Field to retrieve
        search_paths: Additional paths to search for credential files
        
    Returns:
        Credential value or None
    """
    manager = CredentialManager()
    path_objects = [Path(p) for p in search_paths] if search_paths else None
    return manager.get_credential(service, username, field, path_objects)


def store_credential(service: str, username: str, value: str, 
                    field: str = "password", backend: str = "1password") -> bool:
    """
    Store credential using default credential manager.
    
    Args:
        service: Service name
        username: Username or identifier
        value: Credential value
        field: Field name
        backend: Backend to use
        
    Returns:
        True if successful
    """
    manager = CredentialManager()
    return manager.store_credential(service, username, value, field, backend)


def store_ga_credentials_from_file(credentials_file: Union[str, Path],
                                 item_title: str = "Google Analytics API - Multi-Client Reporter",
                                 vault: str = "Private",
                                 delete_file: bool = True) -> bool:
    """
    Store Google Analytics credentials from JSON file.
    
    Args:
        credentials_file: Path to OAuth2 JSON file
        item_title: Title for 1Password item
        vault: 1Password vault
        delete_file: Whether to delete source file
        
    Returns:
        True if successful
    """
    try:
        credentials_file = Path(credentials_file)
        
        if not credentials_file.exists():
            log_error(f"Credentials file not found: {credentials_file}")
            return False
        
        with open(credentials_file, 'r') as f:
            credentials_data = json.load(f)
        
        manager = CredentialManager(default_vault=vault)
        success = manager.store_google_analytics_credentials(
            credentials_data, item_title, vault
        )
        
        if success and delete_file:
            credentials_file.unlink()
            log_info(f"Deleted source credentials file: {credentials_file}")
        
        return success
        
    except Exception as e:
        log_error(f"Error storing GA credentials from file: {e}")
        return False


def get_ga_credentials() -> Optional[Tuple[str, str]]:
    """
    Get Google Analytics credentials for connector.
    
    Returns:
        Tuple of (client_id, client_secret) or None
    """
    manager = CredentialManager()
    return manager.get_google_analytics_credentials()


def credential_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all credential backends."""
    manager = CredentialManager()
    return manager.backend_status()


def store_ga_service_account_from_file(credentials_file: Union[str, Path],
                                      item_title: str = "Google Analytics Service Account", 
                                      vault: str = "Private",
                                      delete_file: bool = False) -> bool:
    """
    Store Google Analytics service account credentials in 1Password.
    
    Args:
        credentials_file: Path to service account JSON file
        item_title: Title for 1Password item
        vault: 1Password vault name
        delete_file: Whether to delete file after storing
        
    Returns:
        True if successful
    """
    try:
        credentials_file = Path(credentials_file)
        
        if not credentials_file.exists():
            log_error(f"Service account file not found: {credentials_file}")
            return False
        
        # Read service account JSON
        with open(credentials_file, 'r') as f:
            service_account_data = json.load(f)
        
        # Validate service account format
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        if not all(field in service_account_data for field in required_fields):
            log_error("Invalid service account credentials format")
            return False
        
        if service_account_data.get('type') != 'service_account':
            log_error("Not a service account credentials file")
            return False
        
        # Create comprehensive 1Password item with service account data
        raw_json = json.dumps(service_account_data, indent=2)
        
        cmd = [
            'op', 'item', 'create',
            '--category=API Credential',
            f'--title={item_title}',
            f'--vault={vault}',
            f'project_id={service_account_data["project_id"]}',
            f'client_email={service_account_data["client_email"]}',
            f'private_key_id={service_account_data["private_key_id"]}',
            f'private_key[password]={service_account_data["private_key"]}',
            f'raw_json[text]={raw_json}',
            '--tags=google-analytics,service-account,ga4,siege-utilities'
        ]
        
        # Add optional fields if present
        if 'client_id' in service_account_data:
            cmd.append(f'client_id={service_account_data["client_id"]}')
        if 'auth_uri' in service_account_data:
            cmd.append(f'auth_uri={service_account_data["auth_uri"]}')
        if 'token_uri' in service_account_data:
            cmd.append(f'token_uri={service_account_data["token_uri"]}')
        
        # Execute 1Password command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        log_info(f"Stored Google Analytics service account: '{item_title}'")
        
        # Verify storage by retrieving client_email
        test_email = get_credential('google-analytics-sa', service_account_data['client_email'], 'client_email')
        if test_email:
            log_info("Service account credential storage verified")
            
            # Delete original file if requested
            if delete_file:
                credentials_file.unlink()
                log_info(f"Deleted original file: {credentials_file}")
            
            return True
        else:
            log_warning("Could not verify service account storage (but likely successful)")
            return True  # Still consider success since 1Password command succeeded
            
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to store service account credentials: {e.stderr}")
        return False
    except Exception as e:
        log_error(f"Error storing service account credentials: {str(e)}")
        return False


def get_ga_service_account_credentials() -> Optional[Dict[str, str]]:
    """
    Get Google Analytics service account credentials.
    
    Returns:
        Dict with service account data or None
    """
    manager = CredentialManager()
    
    # Try to get service account email first
    client_email = manager.get_credential('google-analytics-sa', 'service', 'client_email')
    if not client_email:
        return None
    
    # Get other required fields
    project_id = manager.get_credential('google-analytics-sa', 'service', 'project_id')
    private_key = manager.get_credential('google-analytics-sa', 'service', 'private_key')
    private_key_id = manager.get_credential('google-analytics-sa', 'service', 'private_key_id')
    
    if all([client_email, project_id, private_key, private_key_id]):
        return {
            'client_email': client_email,
            'project_id': project_id,
            'private_key': private_key,
            'private_key_id': private_key_id,
            'type': 'service_account'
        }
    
    return None


def get_google_service_account_from_1password(item_title: str = "Google Analytics Service Account - Multi-Client Reporter") -> Optional[Dict[str, str]]:
    """
    Get Google service account credentials from 1Password.
    Based on working implementation from GA project.
    
    Args:
        item_title: Title of the 1Password item containing service account
        
    Returns:
        Service account credentials dictionary or None if not found
    """
    try:
        import subprocess
        
        def get_field(field_name: str) -> str:
            """Get a specific field from the 1Password item"""
            cmd = ['op', 'item', 'get', item_title, f'--field={field_name}', '--reveal']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            value = result.stdout.strip()
            
            # Clean up private key - remove extra quotes and fix newlines
            if field_name == 'private_key':
                value = value.strip('"')  # Remove surrounding quotes
                value = value.replace('\\n', '\n')  # Fix escaped newlines
            
            return value
        
        service_account = {
            "type": "service_account",
            "project_id": get_field('project_id'),
            "private_key_id": get_field('private_key_id'),
            "private_key": get_field('private_key'),
            "client_email": get_field('client_email'),
            "client_id": get_field('client_id'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
        
        log_info(f"Retrieved Google service account: {service_account['client_email']}")
        return service_account
        
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to get Google service account from 1Password: {e}")
        return None
    except Exception as e:
        log_error(f"Error retrieving Google service account: {e}")
        return None


def create_temporary_service_account_file(service_account_data: Dict[str, str]) -> Optional[str]:
    """
    Create a temporary service account file for Google APIs.
    Useful for APIs that require a file path.
    
    Args:
        service_account_data: Service account credentials dictionary
        
    Returns:
        Path to temporary file or None if failed
    """
    try:
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(service_account_data, f, indent=2)
            temp_file_path = f.name
        
        log_info(f"Created temporary service account file: {temp_file_path}")
        return temp_file_path
        
    except Exception as e:
        log_error(f"Failed to create temporary service account file: {e}")
        return None
