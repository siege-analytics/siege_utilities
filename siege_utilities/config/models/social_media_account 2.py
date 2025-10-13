"""
Social media account model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class SocialMediaAccount(BaseModel):
    """
    Social media account configuration with comprehensive validation.
    
    Provides type-safe, validated social media account settings with
    platform-specific validation and security constraints.
    """
    
    platform: str = Field(
        pattern=r'^(facebook|twitter|linkedin|instagram|youtube|tiktok|pinterest|snapchat)$',
        description="Social media platform"
    )
    account_id: str = Field(
        min_length=1,
        max_length=100,
        description="Platform-specific account ID"
    )
    account_name: str = Field(
        min_length=1,
        max_length=100,
        description="Display name for the account"
    )
    access_token: str = Field(
        min_length=20,
        max_length=500,
        description="Access token for API authentication"
    )
    refresh_token: Optional[str] = Field(
        None,
        max_length=500,
        description="Refresh token for token renewal"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the account is active"
    )
    api_version: Optional[str] = Field(
        None,
        pattern=r'^v\d+\.\d+$',
        description="API version (e.g., v1.0, v2.1)"
    )
    rate_limit_remaining: Optional[int] = Field(
        None,
        ge=0,
        description="Remaining API rate limit"
    )
    last_updated: Optional[datetime] = Field(
        None,
        description="Last time the account was updated"
    )
    
    @field_validator('access_token')
    @classmethod
    def validate_access_token(cls, v):
        """Validate access token format."""
        if len(v) < 20:
            raise ValueError('Access token must be at least 20 characters')
        
        # Basic token format validation (alphanumeric with some special chars)
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Access token contains invalid characters')
        
        return v
    
    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v, info):
        """Validate account ID based on platform."""
        if not info.data:
            return v
        
        platform = info.data.get('platform', '').lower()
        
        if platform == 'facebook':
            # Facebook IDs are typically numeric
            if not re.match(r'^\d+$', v):
                raise ValueError('Facebook account ID must be numeric')
        elif platform == 'twitter':
            # Twitter handles start with @ and contain alphanumeric + underscore
            if not re.match(r'^@?[a-zA-Z0-9_]+$', v):
                raise ValueError('Twitter account ID must be a valid handle')
        elif platform == 'instagram':
            # Instagram handles are alphanumeric + underscore + period
            if not re.match(r'^[a-zA-Z0-9_.]+$', v):
                raise ValueError('Instagram account ID must be a valid handle')
        elif platform == 'youtube':
            # YouTube channel IDs are alphanumeric with specific format
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('YouTube account ID must be alphanumeric')
        
        return v
    
    @field_validator('api_version')
    @classmethod
    def validate_api_version(cls, v, info):
        """Validate API version based on platform."""
        if not v or not info.data:
            return v
        
        platform = info.data.get('platform', '').lower()
        
        # Platform-specific API version validation
        valid_versions = {
            'facebook': ['v1.0', 'v2.0', 'v3.0', 'v4.0', 'v5.0'],
            'twitter': ['v1.0', 'v2.0'],
            'linkedin': ['v1.0', 'v2.0'],
            'instagram': ['v1.0'],
            'youtube': ['v1.0', 'v2.0', 'v3.0'],
            'tiktok': ['v1.0'],
            'pinterest': ['v1.0', 'v2.0'],
            'snapchat': ['v1.0']
        }
        
        if platform in valid_versions and v not in valid_versions[platform]:
            raise ValueError(f'Invalid API version for {platform}. Valid versions: {valid_versions[platform]}')
        
        return v
    
    def get_api_base_url(self) -> str:
        """Get the API base URL for the platform."""
        base_urls = {
            'facebook': 'https://graph.facebook.com',
            'twitter': 'https://api.twitter.com',
            'linkedin': 'https://api.linkedin.com',
            'instagram': 'https://graph.facebook.com',
            'youtube': 'https://www.googleapis.com/youtube',
            'tiktok': 'https://business-api.tiktok.com',
            'pinterest': 'https://api.pinterest.com',
            'snapchat': 'https://adsapi.snapchat.com'
        }
        
        return base_urls.get(self.platform.lower(), '')
    
    def get_auth_headers(self) -> dict:
        """Get authentication headers for API requests."""
        if self.platform.lower() == 'facebook':
            return {'Authorization': f'Bearer {self.access_token}'}
        elif self.platform.lower() == 'twitter':
            return {'Authorization': f'Bearer {self.access_token}'}
        elif self.platform.lower() == 'linkedin':
            return {'Authorization': f'Bearer {self.access_token}'}
        elif self.platform.lower() == 'instagram':
            return {'Authorization': f'Bearer {self.access_token}'}
        elif self.platform.lower() == 'youtube':
            return {'Authorization': f'Bearer {self.access_token}'}
        else:
            return {'Authorization': f'Bearer {self.access_token}'}
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
