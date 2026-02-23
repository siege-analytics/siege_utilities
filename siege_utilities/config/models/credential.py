"""
Credential management model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import re


class CredentialType(str, Enum):
    """Types of credentials supported."""
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    USERNAME_PASSWORD = "username_password"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    SECRET = "secret"


class CredentialStatus(str, Enum):
    """Status of credentials."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class Credential(BaseModel):
    """
    Credential management with comprehensive validation.
    
    Provides type-safe, validated credential storage with
    detailed field constraints and security validation.
    """
    
    model_config = ConfigDict()
    
    # Basic Information
    name: str = Field(
        min_length=1,
        max_length=100,
        description="Credential name/identifier"
    )
    credential_type: CredentialType = Field(
        description="Type of credential"
    )
    service: str = Field(
        min_length=1,
        max_length=50,
        description="Service this credential is for (e.g., 'google_analytics', 'github')"
    )
    
    # Credential Data (encrypted in production)
    username: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Username (if applicable)"
    )
    password: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Password (if applicable)"
    )
    api_key: Optional[str] = Field(
        default=None,
        max_length=500,
        description="API key (if applicable)"
    )
    token: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="OAuth token or other token (if applicable)"
    )
    secret: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Secret key (if applicable)"
    )
    
    # Metadata
    status: CredentialStatus = Field(
        default=CredentialStatus.ACTIVE,
        description="Credential status"
    )
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Creation date"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration date (if applicable)"
    )
    last_used: Optional[datetime] = Field(
        default=None,
        description="Last time this credential was used"
    )
    
    # Additional Data
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the credential"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notes about this credential"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate credential name."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Credential name must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('service')
    @classmethod
    def validate_service(cls, v):
        """Validate service name."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Service name must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength if provided."""
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format if provided."""
        if v and len(v) < 10:
            raise ValueError('API key must be at least 10 characters')
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v):
        """Validate expiration date."""
        if v and v <= datetime.now():
            raise ValueError('Expiration date must be in the future')
        return v
    
    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if credential is valid (active and not expired)."""
        return (self.status == CredentialStatus.ACTIVE and 
                not self.is_expired())
    
    def update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used = datetime.now()
    
    def get_credential_data(self) -> Dict[str, Any]:
        """Get credential data as dictionary (excluding sensitive fields for logging)."""
        return {
            'name': self.name,
            'credential_type': self.credential_type,
            'service': self.service,
            'status': self.status,
            'created_date': self.created_date.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'is_valid': self.is_valid(),
            'metadata': self.metadata,
            'notes': self.notes
        }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for this credential."""
        info = {
            'service': self.service,
            'credential_type': self.credential_type,
            'status': self.status
        }
        
        if self.username:
            info['username'] = self.username
        if self.api_key:
            info['has_api_key'] = True
        if self.token:
            info['has_token'] = True
        if self.secret:
            info['has_secret'] = True
            
        return info
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }


class OnePasswordCredential(BaseModel):
    """
    Specialized credential model for 1Password integration.
    """
    
    model_config = ConfigDict()
    
    # 1Password specific fields
    vault_id: str = Field(
        min_length=1,
        max_length=50,
        description="1Password vault ID"
    )
    item_id: str = Field(
        min_length=1,
        max_length=50,
        description="1Password item ID"
    )
    title: str = Field(
        min_length=1,
        max_length=100,
        description="1Password item title"
    )
    
    # Credential reference
    credential_name: str = Field(
        min_length=1,
        max_length=100,
        description="Name of the credential in 1Password"
    )
    service: str = Field(
        min_length=1,
        max_length=50,
        description="Service this credential is for"
    )
    
    # Access information
    last_synced: datetime = Field(
        default_factory=datetime.now,
        description="Last time this credential was synced from 1Password"
    )
    auto_sync: bool = Field(
        default=True,
        description="Whether to automatically sync this credential"
    )
    
    @field_validator('vault_id', 'item_id')
    @classmethod
    def validate_1password_id(cls, v):
        """Validate 1Password ID format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('1Password ID must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    def get_1password_reference(self) -> str:
        """Get 1Password reference string."""
        return f"op://{self.vault_id}/{self.item_id}/{self.credential_name}"
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
