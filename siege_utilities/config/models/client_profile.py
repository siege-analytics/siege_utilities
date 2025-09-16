"""
Enhanced client profile model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

from .database_connection import DatabaseConnection
from .social_media_account import SocialMediaAccount
from .branding_config import BrandingConfig
from .report_preferences import ReportPreferences


class ContactInfo(BaseModel):
    """
    Contact information with validation.
    """
    
    email: str = Field(
        default="",
        description="Contact email address"
    )
    phone: Optional[str] = Field(
        None,
        description="Contact phone number"
    )
    address: Optional[str] = Field(
        None,
        max_length=200,
        description="Contact address"
    )
    website: Optional[str] = Field(
        None,
        description="Website URL"
    )
    linkedin: Optional[str] = Field(
        None,
        description="LinkedIn profile URL"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v and len(v.strip()) > 0:
            import re
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v.strip()):
                raise ValueError('Invalid email format')
        return v.strip() if v else ""
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and len(v.strip()) > 0:
            # Remove all non-digit characters for validation
            digits = ''.join(filter(str.isdigit, v))
            if len(digits) < 10 or len(digits) > 15:
                raise ValueError('Phone number must have 10-15 digits')
        return v.strip() if v else None
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        """Validate website URL format."""
        if v and len(v.strip()) > 0:
            import re
            if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', v.strip()):
                raise ValueError('Invalid website URL format')
        return v.strip() if v else None
    
    @field_validator('linkedin')
    @classmethod
    def validate_linkedin(cls, v):
        """Validate LinkedIn URL format."""
        if v and len(v.strip()) > 0:
            import re
            if not re.match(r'^https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9-]+/?$', v.strip()):
                raise ValueError('Invalid LinkedIn URL format')
        return v.strip() if v else None
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }


class ClientProfile(BaseModel):
    """
    Enhanced client profile with comprehensive validation.
    
    Provides type-safe, validated client configuration with
    detailed field constraints and business logic validation.
    """
    
    # Basic Information
    client_id: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Unique client identifier"
    )
    client_name: str = Field(
        min_length=1,
        max_length=100,
        description="Client company name"
    )
    client_code: str = Field(
        min_length=2,
        max_length=10,
        pattern=r'^[A-Z0-9]+$',
        description="Short client code (uppercase letters and numbers)"
    )
    
    # Contact Information
    contact_info: ContactInfo
    
    # Project Information
    industry: str = Field(
        min_length=1,
        max_length=50,
        description="Client industry"
    )
    project_count: int = Field(
        ge=0,
        description="Number of projects for this client"
    )
    status: str = Field(
        pattern=r'^(active|inactive|archived)$',
        description="Client status"
    )
    
    # Client-specific configurations
    database_connections: List[DatabaseConnection] = Field(
        default_factory=list,
        description="Client-specific database connections"
    )
    social_media_accounts: List[SocialMediaAccount] = Field(
        default_factory=list,
        description="Client social media accounts"
    )
    branding_config: BrandingConfig
    report_preferences: ReportPreferences
    
    # Additional metadata
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Profile creation date"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update date"
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional notes about the client"
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
    
    @field_validator('database_connections')
    @classmethod
    def validate_database_connections(cls, v):
        """Validate database connections for uniqueness."""
        names = [conn.name for conn in v]
        if len(names) != len(set(names)):
            raise ValueError('Database connection names must be unique')
        
        return v
    
    @field_validator('social_media_accounts')
    @classmethod
    def validate_social_media_accounts(cls, v):
        """Validate social media accounts for uniqueness."""
        platforms = [acc.platform for acc in v]
        if len(platforms) != len(set(platforms)):
            raise ValueError('Social media platforms must be unique per client')
        
        return v
    
    def get_active_database_connections(self) -> List[DatabaseConnection]:
        """Get all active database connections."""
        return [conn for conn in self.database_connections]
    
    def get_active_social_media_accounts(self) -> List[SocialMediaAccount]:
        """Get all active social media accounts."""
        return [acc for acc in self.social_media_accounts if acc.is_active]
    
    def get_database_connection_by_name(self, name: str) -> Optional[DatabaseConnection]:
        """Get database connection by name."""
        for conn in self.database_connections:
            if conn.name == name:
                return conn
        return None
    
    def get_social_media_account_by_platform(self, platform: str) -> Optional[SocialMediaAccount]:
        """Get social media account by platform."""
        for acc in self.social_media_accounts:
            if acc.platform.lower() == platform.lower():
                return acc
        return None
    
    def add_database_connection(self, connection: DatabaseConnection) -> None:
        """Add a new database connection."""
        # Check for name conflicts
        if self.get_database_connection_by_name(connection.name):
            raise ValueError(f'Database connection "{connection.name}" already exists')
        
        self.database_connections.append(connection)
        self.last_updated = datetime.now()
    
    def add_social_media_account(self, account: SocialMediaAccount) -> None:
        """Add a new social media account."""
        # Check for platform conflicts
        if self.get_social_media_account_by_platform(account.platform):
            raise ValueError(f'Social media account for "{account.platform}" already exists')
        
        self.social_media_accounts.append(account)
        self.last_updated = datetime.now()
    
    def update_branding_config(self, branding: BrandingConfig) -> None:
        """Update branding configuration."""
        self.branding_config = branding
        self.last_updated = datetime.now()
    
    def update_report_preferences(self, preferences: ReportPreferences) -> None:
        """Update report preferences."""
        self.report_preferences = preferences
        self.last_updated = datetime.now()
    
    def get_summary(self) -> dict:
        """Get client profile summary."""
        return {
            'client_id': self.client_id,
            'client_name': self.client_name,
            'client_code': self.client_code,
            'industry': self.industry,
            'status': self.status,
            'project_count': self.project_count,
            'database_connections': len(self.database_connections),
            'social_media_accounts': len(self.get_active_social_media_accounts()),
            'created_date': self.created_date.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
