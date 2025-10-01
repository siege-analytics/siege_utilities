"""
Base Person model with comprehensive validation and credential management.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import re

from .credential import Credential, OnePasswordCredential
from .oauth_integration import OAuthIntegration
from .database_connection import DatabaseConnection


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
        default_factory=list,
        description="1Password credential references"
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
        weak_passwords = [cred for cred in self.credentials if cred.credential_type == "username_password" and len(cred.password) < 12]
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
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
