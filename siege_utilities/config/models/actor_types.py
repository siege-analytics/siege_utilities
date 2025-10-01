"""
Specific actor types that extend the base Person model.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import re

from .person import Person


class User(Person):
    """
    User actor - Siege/Masai team members and internal users.
    
    Extends Person with user-specific fields and capabilities.
    """
    
    model_config = ConfigDict()
    
    # User-specific fields
    username: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Username (alphanumeric, underscore, hyphen only)"
    )
    github_login: Optional[str] = Field(
        default=None,
        max_length=50,
        description="GitHub username"
    )
    role: str = Field(
        default="analyst",
        description="User role (analyst, manager, developer, admin)"
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="List of permissions for this user"
    )
    
    # User preferences
    preferred_download_directory: Path = Field(
        default_factory=lambda: Path.home() / "Downloads" / "siege_utilities",
        description="Default download directory"
    )
    default_output_format: str = Field(
        default="pdf",
        pattern=r'^(pdf|pptx|html)$',
        description="Default output format"
    )
    preferred_map_style: str = Field(
        default="open-street-map",
        pattern=r'^(open-street-map|satellite|terrain)$',
        description="Preferred map style"
    )
    default_color_scheme: str = Field(
        default="YlOrRd",
        pattern=r'^(YlOrRd|viridis|plasma|inferno|Blues|Greens|Reds|Purples)$',
        description="Default color scheme"
    )
    
    # Technical preferences
    default_dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="Default DPI for output (72-600)"
    )
    default_figure_size: tuple[int, int] = Field(
        default=(10, 8),
        description="Default figure size (width, height)"
    )
    enable_logging: bool = Field(
        default=True,
        description="Enable logging"
    )
    log_level: str = Field(
        default="INFO",
        pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$',
        description="Logging level"
    )
    
    # API Keys (moved from base Person for user-specific access)
    google_analytics_key: str = Field(
        default="",
        max_length=100,
        description="Google Analytics API key"
    )
    facebook_business_key: str = Field(
        default="",
        max_length=100,
        description="Facebook Business API key"
    )
    census_api_key: str = Field(
        default="",
        max_length=100,
        description="Census API key"
    )
    
    # Database preferences
    default_database: str = Field(
        default="postgresql",
        pattern=r'^(postgresql|mysql|sqlite|duckdb)$',
        description="Default database type"
    )
    postgresql_connection: str = Field(
        default="",
        max_length=500,
        description="PostgreSQL connection string"
    )
    duckdb_path: str = Field(
        default="",
        max_length=500,
        description="DuckDB database path"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('github_login')
    @classmethod
    def validate_github_login(cls, v):
        """Validate GitHub login format if provided."""
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('GitHub login must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        valid_roles = ['analyst', 'manager', 'developer', 'admin', 'collaborator']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v):
        """Validate permissions list."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Permissions must be unique')
        return v
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def add_permission(self, permission: str) -> None:
        """Add a permission to this user."""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.last_updated = datetime.now()
    
    def remove_permission(self, permission: str) -> None:
        """Remove a permission from this user."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.last_updated = datetime.now()


class Client(Person):
    """
    Client actor - External client organizations.
    
    Extends Person with client-specific fields and capabilities.
    """
    
    model_config = ConfigDict()
    
    # Client-specific fields
    client_code: str = Field(
        min_length=2,
        max_length=10,
        pattern=r'^[A-Z0-9]+$',
        description="Short client code (uppercase letters and numbers)"
    )
    industry: str = Field(
        min_length=1,
        max_length=50,
        description="Client industry"
    )
    project_count: int = Field(
        ge=0,
        description="Number of projects for this client"
    )
    client_status: str = Field(
        pattern=r'^(active|inactive|archived)$',
        description="Client status"
    )
    
    # Client-specific configurations
    branding_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Client branding configuration"
    )
    report_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Report generation preferences"
    )
    
    @field_validator('client_code')
    @classmethod
    def validate_client_code(cls, v):
        """Validate client code format and uniqueness."""
        if len(v) < 2:
            raise ValueError('Client code must be at least 2 characters')
        
        if not v.isupper():
            raise ValueError('Client code must be uppercase')
        
        # Check for reserved codes
        reserved_codes = {'DEFAULT', 'ADMIN', 'SYSTEM', 'TEST'}
        if v in reserved_codes:
            raise ValueError(f'Client code {v} is reserved')
        
        return v
    
    def increment_project_count(self) -> None:
        """Increment the project count."""
        self.project_count += 1
        self.last_updated = datetime.now()
    
    def decrement_project_count(self) -> None:
        """Decrement the project count."""
        if self.project_count > 0:
            self.project_count -= 1
            self.last_updated = datetime.now()
    
    def is_active_client(self) -> bool:
        """Check if client is active."""
        return self.client_status == "active" and self.is_active()


class Collaborator(Person):
    """
    Collaborator actor - External collaborators (e.g., Tony from Masai).
    
    Extends Person with collaboration-specific fields and capabilities.
    """
    
    model_config = ConfigDict()
    
    # Collaborator-specific fields
    external_organization: str = Field(
        min_length=1,
        max_length=100,
        description="External organization name (e.g., Masai Interactive)"
    )
    collaboration_level: str = Field(
        default="read",
        pattern=r'^(read|write|admin)$',
        description="Collaboration access level"
    )
    access_expires: Optional[datetime] = Field(
        default=None,
        description="When collaboration access expires"
    )
    invitation_sent: Optional[datetime] = Field(
        default=None,
        description="When invitation was sent"
    )
    invitation_accepted: Optional[datetime] = Field(
        default=None,
        description="When invitation was accepted"
    )
    
    # Collaboration-specific permissions
    allowed_services: List[str] = Field(
        default_factory=list,
        description="Services this collaborator can access"
    )
    restricted_credentials: List[str] = Field(
        default_factory=list,
        description="Credentials this collaborator cannot access"
    )
    
    @field_validator('external_organization')
    @classmethod
    def validate_external_organization(cls, v):
        """Validate external organization name."""
        if not v.strip():
            raise ValueError('External organization name cannot be empty')
        return v.strip()
    
    @field_validator('access_expires')
    @classmethod
    def validate_access_expires(cls, v):
        """Validate access expiration date."""
        if v and v <= datetime.now():
            raise ValueError('Access expiration must be in the future')
        return v
    
    @field_validator('allowed_services')
    @classmethod
    def validate_allowed_services(cls, v):
        """Validate allowed services list."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Allowed services must be unique')
        return v
    
    @field_validator('restricted_credentials')
    @classmethod
    def validate_restricted_credentials(cls, v):
        """Validate restricted credentials list."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Restricted credentials must be unique')
        return v
    
    def is_access_expired(self) -> bool:
        """Check if collaboration access has expired."""
        if not self.access_expires:
            return False
        return datetime.now() > self.access_expires
    
    def is_collaboration_active(self) -> bool:
        """Check if collaboration is active (not expired and person is active)."""
        return (self.is_active() and 
                not self.is_access_expired() and
                self.invitation_accepted is not None)
    
    def can_access_service(self, service: str) -> bool:
        """Check if collaborator can access a specific service."""
        if not self.is_collaboration_active():
            return False
        
        # If no restrictions, allow all services
        if not self.allowed_services:
            return True
        
        return service in self.allowed_services
    
    def can_access_credential(self, credential_name: str) -> bool:
        """Check if collaborator can access a specific credential."""
        if not self.is_collaboration_active():
            return False
        
        return credential_name not in self.restricted_credentials
    
    def accept_invitation(self) -> None:
        """Accept collaboration invitation."""
        self.invitation_accepted = datetime.now()
        self.last_updated = datetime.now()
    
    def extend_access(self, days: int) -> None:
        """Extend collaboration access by specified days."""
        if self.access_expires:
            self.access_expires = self.access_expires + timedelta(days=days)
        else:
            self.access_expires = datetime.now() + timedelta(days=days)
        self.last_updated = datetime.now()


class Organization(BaseModel):
    """
    Organization model for companies (Siege, Masai, Hillcrest).
    """
    
    model_config = ConfigDict()
    
    # Basic Information
    org_id: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Unique organization identifier"
    )
    name: str = Field(
        min_length=1,
        max_length=100,
        description="Organization name"
    )
    org_type: str = Field(
        pattern=r'^(vendor|client|partner|internal)$',
        description="Organization type"
    )
    
    # Contact Information
    primary_email: str = Field(
        description="Primary organization email"
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Primary phone number"
    )
    address: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Organization address"
    )
    website: Optional[str] = Field(
        default=None,
        description="Organization website"
    )
    
    # Organization Data
    members: List[str] = Field(
        default_factory=list,
        description="List of person IDs belonging to this organization"
    )
    primary_contact: Optional[str] = Field(
        default=None,
        description="Primary contact person ID"
    )
    
    # Metadata
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Organization creation date"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update date"
    )
    status: str = Field(
        default="active",
        pattern=r'^(active|inactive|archived)$',
        description="Organization status"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes about the organization"
    )
    
    @field_validator('primary_email')
    @classmethod
    def validate_primary_email(cls, v):
        """Validate primary email format."""
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v.strip()):
            raise ValueError('Invalid primary email format')
        return v.strip()
    
    @field_validator('members')
    @classmethod
    def validate_members(cls, v):
        """Validate members list."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Members must be unique')
        return v
    
    def add_member(self, person_id: str) -> None:
        """Add a member to this organization."""
        if person_id not in self.members:
            self.members.append(person_id)
            self.last_updated = datetime.now()
    
    def remove_member(self, person_id: str) -> None:
        """Remove a member from this organization."""
        if person_id in self.members:
            self.members.remove(person_id)
            if self.primary_contact == person_id:
                self.primary_contact = None
            self.last_updated = datetime.now()
    
    def set_primary_contact(self, person_id: str) -> None:
        """Set the primary contact for this organization."""
        if person_id not in self.members:
            self.members.append(person_id)
        self.primary_contact = person_id
        self.last_updated = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get organization summary information."""
        return {
            'org_id': self.org_id,
            'name': self.name,
            'org_type': self.org_type,
            'status': self.status,
            'member_count': len(self.members),
            'primary_contact': self.primary_contact,
            'created_date': self.created_date.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }


class Collaboration(BaseModel):
    """
    Collaboration model for joint projects between organizations.
    """
    
    model_config = ConfigDict()
    
    # Basic Information
    collab_id: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Unique collaboration identifier"
    )
    name: str = Field(
        min_length=1,
        max_length=100,
        description="Collaboration name"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Collaboration description"
    )
    
    # Participants
    organizations: List[str] = Field(
        default_factory=list,
        description="List of organization IDs participating"
    )
    clients: List[str] = Field(
        default_factory=list,
        description="List of client organization IDs"
    )
    participants: List[str] = Field(
        default_factory=list,
        description="List of person IDs participating"
    )
    
    # Project Information
    status: str = Field(
        default="planning",
        pattern=r'^(planning|active|on_hold|completed|cancelled)$',
        description="Collaboration status"
    )
    start_date: datetime = Field(
        default_factory=datetime.now,
        description="Collaboration start date"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Collaboration end date"
    )
    
    # Access Control
    shared_credentials: List[str] = Field(
        default_factory=list,
        description="List of credential names shared in this collaboration"
    )
    shared_databases: List[str] = Field(
        default_factory=list,
        description="List of database connection names shared"
    )
    
    # Metadata
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Collaboration creation date"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update date"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes about the collaboration"
    )
    
    @field_validator('organizations', 'clients', 'participants')
    @classmethod
    def validate_participants(cls, v):
        """Validate participant lists."""
        if v:
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError('Participants must be unique')
        return v
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v):
        """Validate end date."""
        if v and v <= datetime.now():
            raise ValueError('End date must be in the future')
        return v
    
    def add_organization(self, org_id: str) -> None:
        """Add an organization to this collaboration."""
        if org_id not in self.organizations:
            self.organizations.append(org_id)
            self.last_updated = datetime.now()
    
    def add_client(self, client_id: str) -> None:
        """Add a client to this collaboration."""
        if client_id not in self.clients:
            self.clients.append(client_id)
            self.last_updated = datetime.now()
    
    def add_participant(self, person_id: str) -> None:
        """Add a participant to this collaboration."""
        if person_id not in self.participants:
            self.participants.append(person_id)
            self.last_updated = datetime.now()
    
    def is_active(self) -> bool:
        """Check if collaboration is active."""
        return (self.status == "active" and 
                (not self.end_date or datetime.now() < self.end_date))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get collaboration summary information."""
        return {
            'collab_id': self.collab_id,
            'name': self.name,
            'status': self.status,
            'organization_count': len(self.organizations),
            'client_count': len(self.clients),
            'participant_count': len(self.participants),
            'is_active': self.is_active(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_date': self.created_date.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
