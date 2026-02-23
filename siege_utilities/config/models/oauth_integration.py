"""
OAuth integration model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import re


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    SALESFORCE = "salesforce"
    SLACK = "slack"
    ZOOM = "zoom"
    CUSTOM = "custom"


class OAuthScope(str, Enum):
    """Common OAuth scopes."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    PROFILE = "profile"
    EMAIL = "email"
    ANALYTICS = "analytics"
    FILES = "files"
    CALENDAR = "calendar"
    CONTACTS = "contacts"


class OAuthIntegration(BaseModel):
    """
    OAuth integration configuration with comprehensive validation.
    
    Provides type-safe, validated OAuth settings with
    detailed field constraints and security validation.
    """
    
    model_config = ConfigDict()
    
    # Basic Information
    name: str = Field(
        min_length=1,
        max_length=100,
        description="Integration name/identifier"
    )
    provider: OAuthProvider = Field(
        description="OAuth provider"
    )
    service: str = Field(
        min_length=1,
        max_length=50,
        description="Service this integration is for"
    )
    
    # OAuth Configuration
    client_id: str = Field(
        min_length=10,
        max_length=200,
        description="OAuth client ID"
    )
    client_secret: str = Field(
        min_length=10,
        max_length=200,
        description="OAuth client secret"
    )
    redirect_uri: str = Field(
        description="OAuth redirect URI"
    )
    scopes: List[OAuthScope] = Field(
        default_factory=list,
        description="OAuth scopes requested"
    )
    
    # Token Information
    access_token: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="OAuth access token"
    )
    refresh_token: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="OAuth refresh token"
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type (usually 'Bearer')"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration time"
    )
    
    # Status and Metadata
    is_active: bool = Field(
        default=True,
        description="Whether this integration is active"
    )
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Integration creation date"
    )
    last_used: Optional[datetime] = Field(
        default=None,
        description="Last time this integration was used"
    )
    last_refreshed: Optional[datetime] = Field(
        default=None,
        description="Last time tokens were refreshed"
    )
    
    # Additional Configuration
    auto_refresh: bool = Field(
        default=True,
        description="Whether to automatically refresh tokens"
    )
    refresh_threshold: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Seconds before expiration to refresh token"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the integration"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notes about this integration"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate integration name."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Integration name must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('service')
    @classmethod
    def validate_service(cls, v):
        """Validate service name."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Service name must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('redirect_uri')
    @classmethod
    def validate_redirect_uri(cls, v):
        """Validate redirect URI format."""
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', v):
            raise ValueError('Invalid redirect URI format')
        return v
    
    @field_validator('client_id', 'client_secret')
    @classmethod
    def validate_oauth_credentials(cls, v):
        """Validate OAuth credentials."""
        if len(v) < 10:
            raise ValueError('OAuth credentials must be at least 10 characters')
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v):
        """Validate token expiration date."""
        if v and v <= datetime.now():
            raise ValueError('Token expiration must be in the future')
        return v
    
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    def needs_refresh(self) -> bool:
        """Check if token needs refresh based on threshold."""
        if not self.expires_at or not self.auto_refresh:
            return False
        
        threshold_time = self.expires_at - timedelta(seconds=self.refresh_threshold)
        return datetime.now() >= threshold_time
    
    def is_valid(self) -> bool:
        """Check if integration is valid (active and has valid token)."""
        return (self.is_active and 
                self.access_token is not None and 
                not self.is_token_expired())
    
    def update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used = datetime.now()
    
    def update_tokens(self, access_token: str, refresh_token: Optional[str] = None, 
                     expires_in: Optional[int] = None) -> None:
        """Update OAuth tokens."""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        
        if expires_in:
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        self.last_refreshed = datetime.now()
        self.update_last_used()
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate OAuth authorization URL."""
        base_urls = {
            OAuthProvider.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
            OAuthProvider.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            OAuthProvider.GITHUB: "https://github.com/login/oauth/authorize",
            OAuthProvider.LINKEDIN: "https://www.linkedin.com/oauth/v2/authorization",
            OAuthProvider.FACEBOOK: "https://www.facebook.com/v18.0/dialog/oauth",
            OAuthProvider.TWITTER: "https://twitter.com/i/oauth2/authorize",
            OAuthProvider.SALESFORCE: "https://login.salesforce.com/services/oauth2/authorize",
            OAuthProvider.SLACK: "https://slack.com/oauth/v2/authorize",
            OAuthProvider.ZOOM: "https://zoom.us/oauth/authorize"
        }
        
        if self.provider not in base_urls:
            raise ValueError(f"Authorization URL not configured for provider: {self.provider}")
        
        base_url = base_urls[self.provider]
        scope_str = " ".join(self.scopes) if self.scopes else "read"
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope_str,
            "response_type": "code"
        }
        
        if state:
            params["state"] = state
        
        # Build query string
        query_parts = [f"{k}={v}" for k, v in params.items()]
        return f"{base_url}?{'&'.join(query_parts)}"
    
    def get_integration_info(self) -> Dict[str, Any]:
        """Get integration information (excluding sensitive data)."""
        return {
            'name': self.name,
            'provider': self.provider,
            'service': self.service,
            'is_active': self.is_active,
            'has_access_token': self.access_token is not None,
            'has_refresh_token': self.refresh_token is not None,
            'is_valid': self.is_valid(),
            'needs_refresh': self.needs_refresh(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'last_refreshed': self.last_refreshed.isoformat() if self.last_refreshed else None,
            'scopes': [scope.value for scope in self.scopes],
            'metadata': self.metadata,
            'notes': self.notes
        }
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
