"""
Base Person model with comprehensive validation and credential management.
"""

from pydantic import SecretStr, SecretBytes, BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
import re

import yaml

from siege_utilities.files.secure_write import secure_write_text

from siege_utilities.core._http import redact_url_secrets

from .credential import Credential, OnePasswordCredential
from .google_account import GoogleAccount
from .oauth_integration import OAuthIntegration
from .database_connection import DatabaseConnection
from ._sensitivity import SECRET_FIELD_NAME, field_has_sensitive_name

__all__ = ["Person"]


class Person(BaseModel):
    """
    Base person/actor model with common capabilities.
    
    Provides the foundation for all person types (User, Client, Collaborator)
    with shared credential management, relationships, and common fields.
    """
    
    model_config = ConfigDict()
    
    # Core Identity
    person_id: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Unique person identifier"
    )
    name: str = Field(
        min_length=1,
        max_length=100,
        description="Full name"
    )
    email: str = Field(
        description="Primary email address"
    )
    
    # Contact Information
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Phone number"
    )
    address: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Physical address"
    )
    website: Optional[str] = Field(
        default=None,
        description="Website URL"
    )
    linkedin: Optional[str] = Field(
        default=None,
        description="LinkedIn profile URL"
    )
    
    # Credentials & Access
    credentials: List[Credential] = Field(
        json_schema_extra={"sensitive": False},
        default_factory=list,
        description="List of credentials for this person"
    )
    oauth_integrations: List[OAuthIntegration] = Field(
        default_factory=list,
        description="OAuth integrations for this person"
    )
    database_connections: List[DatabaseConnection] = Field(
        default_factory=list,
        description="Database connections for this person"
    )
    onepassword_credentials: List[OnePasswordCredential] = Field(
        json_schema_extra={"sensitive": False},
        default_factory=list,
        description="1Password credential references"
    )
    google_accounts: List[GoogleAccount] = Field(
        default_factory=list,
        description="Google accounts for this person"
    )

    # Organizational Relationships
    organizations: List[str] = Field(
        default_factory=list,
        description="List of organization IDs this person belongs to"
    )
    primary_organization: Optional[str] = Field(
        default=None,
        description="Primary organization ID"
    )
    collaborations: List[str] = Field(
        default_factory=list,
        description="List of collaboration IDs this person participates in"
    )
    
    # Metadata
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Person creation date"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update date"
    )
    status: str = Field(
        default="active",
        pattern=r'^(active|inactive|suspended|archived)$',
        description="Person status"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes about this person"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v.strip()):
            raise ValueError('Invalid email format')
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and len(v.strip()) > 0:
            digits = ''.join(filter(str.isdigit, v))
            if len(digits) < 10 or len(digits) > 15:
                raise ValueError('Phone number must have 10-15 digits')
        return v.strip() if v else None
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        """Validate website URL format."""
        if v and len(v.strip()) > 0:
            if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', v.strip()):
                raise ValueError('Invalid website URL format')
        return v.strip() if v else None
    
    @field_validator('linkedin')
    @classmethod
    def validate_linkedin(cls, v):
        """Validate LinkedIn URL format."""
        if v and len(v.strip()) > 0:
            # Accept both personal profiles (/in/) and company pages (/company/)
            if not re.match(r'^https?://(www\.)?linkedin\.com/(in|company)/[a-zA-Z0-9-]+/?$', v.strip()):
                raise ValueError('Invalid LinkedIn URL format - must be a LinkedIn profile or company page')
        return v.strip() if v else None
    
    @field_validator('organizations')
    @classmethod
    def validate_organizations(cls, v):
        """Validate organizations list."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Organizations must be unique')
        return v
    
    @field_validator('collaborations')
    @classmethod
    def validate_collaborations(cls, v):
        """Validate collaborations list."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Collaborations must be unique')
        return v
    
    # Credential Management Methods
    def add_credential(self, credential: Credential) -> None:
        """Add a credential to this person."""
        # Check for name conflicts
        if any(cred.name == credential.name for cred in self.credentials):
            raise ValueError(f'Credential "{credential.name}" already exists')
        
        self.credentials.append(credential)
        self.last_updated = datetime.now()
    
    def remove_credential(self, credential_name: str) -> bool:
        """Remove a credential by name."""
        for i, cred in enumerate(self.credentials):
            if cred.name == credential_name:
                del self.credentials[i]
                self.last_updated = datetime.now()
                return True
        return False
    
    def get_credential(self, credential_name: str) -> Optional[Credential]:
        """Get a credential by name."""
        for cred in self.credentials:
            if cred.name == credential_name:
                return cred
        return None
    
    def get_credentials_for_service(self, service: str) -> List[Credential]:
        """Get all credentials for a specific service."""
        return [cred for cred in self.credentials if cred.service == service]
    
    def get_valid_credentials(self) -> List[Credential]:
        """Get all valid (active and not expired) credentials."""
        return [cred for cred in self.credentials if cred.is_valid()]
    
    # OAuth Integration Methods
    def add_oauth_integration(self, integration: OAuthIntegration) -> None:
        """Add an OAuth integration to this person."""
        # Check for name conflicts
        if any(integration.name == oauth.name for oauth in self.oauth_integrations):
            raise ValueError(f'OAuth integration "{integration.name}" already exists')
        
        self.oauth_integrations.append(integration)
        self.last_updated = datetime.now()
    
    def remove_oauth_integration(self, integration_name: str) -> bool:
        """Remove an OAuth integration by name."""
        for i, oauth in enumerate(self.oauth_integrations):
            if oauth.name == integration_name:
                del self.oauth_integrations[i]
                self.last_updated = datetime.now()
                return True
        return False
    
    def get_oauth_integration(self, integration_name: str) -> Optional[OAuthIntegration]:
        """Get an OAuth integration by name."""
        for oauth in self.oauth_integrations:
            if oauth.name == integration_name:
                return oauth
        return None
    
    def get_valid_oauth_integrations(self) -> List[OAuthIntegration]:
        """Get all valid OAuth integrations."""
        return [oauth for oauth in self.oauth_integrations if oauth.is_valid()]
    
    # Database Connection Methods
    def add_database_connection(self, connection: DatabaseConnection) -> None:
        """Add a database connection to this person."""
        # Check for name conflicts
        if any(conn.name == connection.name for conn in self.database_connections):
            raise ValueError(f'Database connection "{connection.name}" already exists')
        
        self.database_connections.append(connection)
        self.last_updated = datetime.now()
    
    def remove_database_connection(self, connection_name: str) -> bool:
        """Remove a database connection by name."""
        for i, conn in enumerate(self.database_connections):
            if conn.name == connection_name:
                del self.database_connections[i]
                self.last_updated = datetime.now()
                return True
        return False
    
    def get_database_connection(self, connection_name: str) -> Optional[DatabaseConnection]:
        """Get a database connection by name."""
        for conn in self.database_connections:
            if conn.name == connection_name:
                return conn
        return None
    
    # 1Password Integration Methods
    def add_onepassword_credential(self, credential: OnePasswordCredential) -> None:
        """Add a 1Password credential reference to this person."""
        # Check for conflicts
        if any(cred.credential_name == credential.credential_name and 
               cred.vault_id == credential.vault_id for cred in self.onepassword_credentials):
            raise ValueError(f'1Password credential "{credential.credential_name}" already exists in vault {credential.vault_id}')
        
        self.onepassword_credentials.append(credential)
        self.last_updated = datetime.now()
    
    def remove_onepassword_credential(self, credential_name: str, vault_id: str) -> bool:
        """Remove a 1Password credential reference."""
        for i, cred in enumerate(self.onepassword_credentials):
            if cred.credential_name == credential_name and cred.vault_id == vault_id:
                del self.onepassword_credentials[i]
                self.last_updated = datetime.now()
                return True
        return False
    
    def get_onepassword_credentials_for_service(self, service: str) -> List[OnePasswordCredential]:
        """Get all 1Password credentials for a specific service."""
        return [cred for cred in self.onepassword_credentials if cred.service == service]
    
    # Google Account Management Methods
    def add_google_account(self, account: GoogleAccount) -> None:
        """Add a Google account to this person."""
        if any(a.google_account_id == account.google_account_id for a in self.google_accounts):
            raise ValueError(f'Google account "{account.google_account_id}" already exists')
        # Enforce single default
        if account.is_default:
            for a in self.google_accounts:
                a.is_default = False
        self.google_accounts.append(account)
        # Ensure we always have a default if any account exists.
        if not any(a.is_default for a in self.google_accounts):
            self.google_accounts[0].is_default = True
        self.last_updated = datetime.now()

    def remove_google_account(self, google_account_id: str) -> bool:
        """Remove a Google account by ID."""
        for i, a in enumerate(self.google_accounts):
            if a.google_account_id == google_account_id:
                removed_default = a.is_default
                del self.google_accounts[i]
                if removed_default and self.google_accounts:
                    # Promote first remaining account as default.
                    self.google_accounts[0].is_default = True
                self.last_updated = datetime.now()
                return True
        return False

    def get_google_account(self, google_account_id: str) -> Optional[GoogleAccount]:
        """Get a Google account by ID."""
        for a in self.google_accounts:
            if a.google_account_id == google_account_id:
                return a
        return None

    def get_google_account_by_email(self, email: str) -> Optional[GoogleAccount]:
        """Get a Google account by email address."""
        for a in self.google_accounts:
            if a.email == email:
                return a
        return None

    def get_default_google_account(self) -> Optional[GoogleAccount]:
        """Get the default Google account."""
        for a in self.google_accounts:
            if a.is_default:
                return a
        return None

    def set_default_google_account(self, google_account_id: str) -> None:
        """Set a Google account as the default."""
        found = False
        for a in self.google_accounts:
            if a.google_account_id == google_account_id:
                a.is_default = True
                found = True
            else:
                a.is_default = False
        if not found:
            raise ValueError(f'Google account "{google_account_id}" not found')
        self.last_updated = datetime.now()

    def list_google_accounts(self, active_only: bool = False) -> List[GoogleAccount]:
        """List Google accounts, optionally filtering to active only."""
        if active_only:
            return [a for a in self.google_accounts if a.is_active()]
        return list(self.google_accounts)

    # Organization Management Methods
    def add_organization(self, org_id: str) -> None:
        """Add an organization to this person."""
        if org_id not in self.organizations:
            self.organizations.append(org_id)
            self.last_updated = datetime.now()
    
    def remove_organization(self, org_id: str) -> None:
        """Remove an organization from this person."""
        if org_id in self.organizations:
            self.organizations.remove(org_id)
            if self.primary_organization == org_id:
                self.primary_organization = None
            self.last_updated = datetime.now()
    
    def set_primary_organization(self, org_id: str) -> None:
        """Set the primary organization for this person."""
        if org_id not in self.organizations:
            self.organizations.append(org_id)
        self.primary_organization = org_id
        self.last_updated = datetime.now()
    
    # Collaboration Management Methods
    def add_collaboration(self, collab_id: str) -> None:
        """Add a collaboration to this person."""
        if collab_id not in self.collaborations:
            self.collaborations.append(collab_id)
            self.last_updated = datetime.now()
    
    def remove_collaboration(self, collab_id: str) -> None:
        """Remove a collaboration from this person."""
        if collab_id in self.collaborations:
            self.collaborations.remove(collab_id)
            self.last_updated = datetime.now()
    
    # Utility Methods
    def get_summary(self) -> Dict[str, Any]:
        """Get person summary information."""
        return {
            'person_id': self.person_id,
            'name': self.name,
            'email': self.email,
            'status': self.status,
            'organizations': len(self.organizations),
            'primary_organization': self.primary_organization,
            'collaborations': len(self.collaborations),
            'credentials': len(self.credentials),
            'valid_credentials': len(self.get_valid_credentials()),
            'oauth_integrations': len(self.oauth_integrations),
            'valid_oauth_integrations': len(self.get_valid_oauth_integrations()),
            'database_connections': len(self.database_connections),
            'onepassword_credentials': len(self.onepassword_credentials),
            'google_accounts': len(self.google_accounts),
            'active_google_accounts': len(self.list_google_accounts(active_only=True)),
            'created_date': self.created_date.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    def is_active(self) -> bool:
        """Check if person is active."""
        return self.status == "active"
    
    def has_organization(self, org_id: str) -> bool:
        """Check if person belongs to an organization."""
        return org_id in self.organizations
    
    def has_collaboration(self, collab_id: str) -> bool:
        """Check if person participates in a collaboration."""
        return collab_id in self.collaborations
    
    # 1Password Credential Management Methods
    def get_onepassword_credential(self, credential_name: str) -> Optional[OnePasswordCredential]:
        """Get a 1Password credential by name."""
        for cred in self.onepassword_credentials:
            if cred.credential_name == credential_name:
                return cred
        return None
    
    def get_onepassword_credentials_for_service(self, service: str) -> List[OnePasswordCredential]:
        """Get all 1Password credentials for a specific service."""
        return [cred for cred in self.onepassword_credentials if cred.service == service]
    
    def get_onepassword_credentials_for_vault(self, vault_id: str) -> List[OnePasswordCredential]:
        """Get all 1Password credentials for a specific vault."""
        return [cred for cred in self.onepassword_credentials if cred.vault_id == vault_id]
    
    def has_onepassword_credential(self, credential_name: str) -> bool:
        """Check if person has a specific 1Password credential."""
        return any(cred.credential_name == credential_name for cred in self.onepassword_credentials)
    
    def has_onepassword_credentials_for_service(self, service: str) -> bool:
        """Check if person has 1Password credentials for a specific service."""
        return any(cred.service == service for cred in self.onepassword_credentials)
    
    def get_onepassword_services(self) -> List[str]:
        """Get list of services that have 1Password credentials."""
        services = set(cred.service for cred in self.onepassword_credentials)
        return sorted(list(services))
    
    def get_onepassword_vaults(self) -> List[str]:
        """Get list of 1Password vaults used by this person."""
        vaults = set(cred.vault_id for cred in self.onepassword_credentials)
        return sorted(list(vaults))
    
    def get_credential_coverage(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive credential coverage analysis."""
        coverage = {
            'direct_credentials': {
                'total': len(self.credentials),
                'valid': len(self.get_valid_credentials()),
                'services': list(set(cred.service for cred in self.credentials)),
                'types': list(set(cred.credential_type for cred in self.credentials))
            },
            'oauth_integrations': {
                'total': len(self.oauth_integrations),
                'valid': len(self.get_valid_oauth_integrations()),
                'providers': list(set(oauth.provider for oauth in self.oauth_integrations)),
                'services': list(set(oauth.service for oauth in self.oauth_integrations))
            },
            'onepassword_credentials': {
                'total': len(self.onepassword_credentials),
                'services': self.get_onepassword_services(),
                'vaults': self.get_onepassword_vaults(),
                'auto_sync_enabled': len([cred for cred in self.onepassword_credentials if cred.auto_sync])
            },
            'database_connections': {
                'total': len(self.database_connections),
                'types': list(set(conn.connection_type for conn in self.database_connections)),
                'hosts': list(set(conn.host for conn in self.database_connections))
            },
            'google_accounts': {
                'total': len(self.google_accounts),
                'active': len(self.list_google_accounts(active_only=True)),
                'types': list(set(a.account_type.value for a in self.google_accounts)),
                'has_default': self.get_default_google_account() is not None,
            }
        }
        
        # Calculate coverage overlap
        all_services = set()
        all_services.update(coverage['direct_credentials']['services'])
        all_services.update(coverage['oauth_integrations']['services'])
        all_services.update(coverage['onepassword_credentials']['services'])
        
        coverage['summary'] = {
            'total_services': len(all_services),
            'services_with_direct_creds': len(coverage['direct_credentials']['services']),
            'services_with_oauth': len(coverage['oauth_integrations']['services']),
            'services_with_1password': len(coverage['onepassword_credentials']['services']),
            'services_with_multiple_types': len([
                service for service in all_services 
                if sum([
                    service in coverage['direct_credentials']['services'],
                    service in coverage['oauth_integrations']['services'],
                    service in coverage['onepassword_credentials']['services']
                ]) > 1
            ])
        }
        
        return coverage
    
    def get_security_recommendations(self) -> List[str]:
        """Get security recommendations based on credential analysis."""
        recommendations = []
        
        # Check for expired credentials
        expired_creds = [cred for cred in self.credentials if cred.status == "expired"]
        if expired_creds:
            recommendations.append(f"Remove {len(expired_creds)} expired credentials")
        
        # Check for weak passwords
        weak_passwords = [
            cred for cred in self.credentials
            if cred.credential_type == "username_password"
            and cred.password is not None
            and len(cred.password.get_secret_value()) < 12
        ]
        if weak_passwords:
            recommendations.append(f"Strengthen {len(weak_passwords)} weak passwords")
        
        # Check for missing 1Password coverage
        direct_services = set(cred.service for cred in self.credentials)
        onepassword_services = set(cred.service for cred in self.onepassword_credentials)
        uncovered_services = direct_services - onepassword_services
        if uncovered_services:
            recommendations.append(f"Consider moving {len(uncovered_services)} services to 1Password: {', '.join(sorted(uncovered_services))}")
        
        # Check for auto-sync disabled
        manual_sync_creds = [cred for cred in self.onepassword_credentials if not cred.auto_sync]
        if manual_sync_creds:
            recommendations.append(f"Enable auto-sync for {len(manual_sync_creds)} 1Password credentials")
        
        # Check for OAuth tokens needing refresh
        oauth_needing_refresh = [oauth for oauth in self.oauth_integrations if oauth.needs_refresh()]
        if oauth_needing_refresh:
            recommendations.append(f"Refresh {len(oauth_needing_refresh)} OAuth tokens")
        
        return recommendations
    
    # YAML Serialization Methods
    def to_dict(self, exclude_sensitive: bool = False) -> dict:
        """Convert to dictionary, optionally stripping sensitive credential data."""
        data = _strip_sensitive_fields(self) if exclude_sensitive else self.model_dump()
        return _convert_to_yaml_safe(data)

    def to_yaml(self, path: Optional[Path] = None, exclude_sensitive: bool = False) -> str:
        """Serialize to YAML string, optionally writing to a file."""
        data = self.to_dict(exclude_sensitive=exclude_sensitive)
        yaml_str = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
        if path is not None:
            path = Path(path)
            secure_write_text(path, yaml_str)
        return yaml_str

    @classmethod
    def from_yaml(cls, yaml_str_or_path: Union[str, Path]) -> 'Person':
        """Deserialize from a YAML string or file path.

        Raises
        ------
        ValueError
            If the document contains redacted placeholders. Use an
            unredacted export to restore credentials.
        """
        source = yaml_str_or_path
        if isinstance(source, Path) or (isinstance(source, str) and '\n' not in source and Path(source).exists()):
            source = Path(source).read_text()
        data = yaml.safe_load(source)
        _reject_redacted_values(data)
        return cls(**data)

    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "hide_input_in_errors": True,
        "extra": "forbid"
    }


def _convert_to_yaml_safe(obj: Any) -> Any:
    """Recursively convert Python objects to YAML-safe types."""
    if isinstance(obj, SecretStr):
        return obj.get_secret_value()
    if isinstance(obj, dict):
        return {k: _convert_to_yaml_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_yaml_safe(item) for item in obj]
    elif is_dataclass(obj) and not isinstance(obj, type):
        return {field.name: _convert_to_yaml_safe(getattr(obj, field.name))
                for field in fields(obj)}
    elif isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, '__dict__') and not isinstance(obj, type):
        return _convert_to_yaml_safe(vars(obj))
    else:
        return obj


_REDACTED = '***REDACTED***'


# Exact builtin types whose genuinely empty/zero value carries no secret and is
# preserved in a sensitive position (matching develop's empty-value behaviour).
_EMPTY_SENTINELS = {
    str: '', bytes: b'', list: [], dict: {}, tuple: (),
    set: set(), frozenset: frozenset(), int: 0, float: 0.0, bool: False,
}


def _redact_sensitive_value(value: Any) -> Any:
    """Redact a value whose field or key is classified sensitive.

    Fail-closed allowlist, not truthiness. ``None`` stays ``None``. A value is
    otherwise preserved only in two cases, both decided by EXACT type
    (``type(v) is``, never ``isinstance``):

    * its exact builtin type holds its genuinely empty/zero form -- ``''``,
      ``b''``, ``[]``, ``{}``, ``()``, ``set()``, ``frozenset()``, ``0``,
      ``0.0``, ``False``; or
    * it is exactly ``SecretStr('')`` or ``SecretBytes(b'')`` -- an empty
      Pydantic secret, which carries no secret and which the model defaults
      rely on for a working export -> import round-trip. This matches what
      develop did for exact empties and is not a behaviour change.

    Everything else is redacted regardless of what ``__bool__``/``__len__``
    report: any non-empty value, any custom object, and -- critically -- any
    SUBCLASS of ``SecretStr``/``SecretBytes`` even if it unwraps to empty. The
    exact-type check gates the unwrap, so a hostile subclass's
    ``get_secret_value()`` (which could return ``''`` while the real secret
    lives in another attribute) is never consulted. A sensitive position
    therefore cannot export a wrapped or custom-object credential as plaintext.
    """
    if value is None:
        return None
    exact = type(value)
    if exact in _EMPTY_SENTINELS and value == _EMPTY_SENTINELS[exact]:
        return value
    if exact is SecretStr and value.get_secret_value() == '':
        return value
    if exact is SecretBytes and value.get_secret_value() == b'':
        return value
    return _REDACTED
_URL_PASSWORD = re.compile(r'([a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:?#@]*:)[^\s/?#]*(@)')


def _sensitive_name(name: Any) -> bool:
    """Classify metadata keys without changing their output representation."""
    if isinstance(name, (bytes, bytearray)):
        try:
            name = name.decode('utf-8')
        except UnicodeDecodeError:
            return True
    if isinstance(name, str):
        return SECRET_FIELD_NAME.search(name) is not None
    # Numeric/null keys cannot name credentials; unknown key types fail closed.
    return not isinstance(name, (int, float, bool, type(None)))


def _strip_sensitive_fields(data: Any) -> Any:
    """Walk live model fields before serialization so subclass markers survive.

    A field's ``json_schema_extra['sensitive']`` declares its policy. True
    redacts the entire value; False explicitly permits a non-secret field.
    Unmarked secret-like names and aliases fail closed. Metadata keys also
    fail closed for unknown types or bytes that cannot be decoded as UTF-8.
    Secrets with innocuous names (e.g. ``pin`` or ``material``) are covered
    only by an explicit ``sensitive`` marker, not by the name floor.
    Empty values remain empty, and public containers are still traversed.
    URL userinfo passwords and secret query/fragment parameters are redacted
    in string values regardless of the field name. Secrets inside JSON-encoded
    strings are NOT redacted by name: store them in dict fields or explicitly
    marked sensitive fields.
    """
    if isinstance(data, BaseModel):
        result = {}
        for name, field in type(data).model_fields.items():
            if field.exclude:
                continue
            value = getattr(data, name)
            extra = field.json_schema_extra
            policy = extra.get('sensitive') if isinstance(extra, dict) else None
            sensitive = policy is True or (policy is not False and field_has_sensitive_name(name, field))
            # A sensitive field is redacted via _redact_sensitive_value (a
            # fail-closed allowlist that preserves only a genuinely empty
            # builtin and redacts the whole value otherwise); a non-sensitive
            # value is recursed, including falsey ones.
            result[name] = _redact_sensitive_value(value) if sensitive else _strip_sensitive_fields(value)
        if data.model_extra is not None:
            result.update(_strip_sensitive_fields(data.model_extra))
        return result
    if is_dataclass(data) and not isinstance(data, type):
        return _strip_sensitive_fields({field.name: getattr(data, field.name)
                                        for field in fields(data)})
    if isinstance(data, dict):
        return {
            # A sensitive mapping key redacts its value via _redact_sensitive_value
            # (fail-closed allowlist: only a genuinely empty builtin is kept); a
            # non-sensitive key recurses, including falsey values.
            name: _redact_sensitive_value(value) if _sensitive_name(name)
            else _strip_sensitive_fields(value)
            for name, value in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [_strip_sensitive_fields(item) for item in data]
    if isinstance(data, str):
        data = _URL_PASSWORD.sub(lambda match: match[1] + _REDACTED + match[2], data)
        return redact_url_secrets(data, replacement=_REDACTED)
    if hasattr(data, '__dict__') and not isinstance(data, type):
        return _strip_sensitive_fields(vars(data))
    return data


def _reject_redacted_values(data: Any) -> None:
    """Reject placeholders anywhere in an import before constructing models."""
    if isinstance(data, str) and _REDACTED in data:
        raise ValueError(
            'Cannot import redacted values (***REDACTED***); use an unredacted export.'
        )
    if isinstance(data, dict):
        for value in data.values():
            _reject_redacted_values(value)
    elif isinstance(data, (list, tuple)):
        for value in data:
            _reject_redacted_values(value)
