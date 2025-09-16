"""
Enhanced User Profile model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from typing import Tuple, Optional
import re


class UserProfile(BaseModel):
    """
    Enhanced user profile with comprehensive validation.
    
    Provides type-safe, validated user configuration with
    detailed field constraints and business logic validation.
    """
    
    # Personal Information
    username: str = Field(
        default="",
        min_length=0, 
        max_length=50,
        description="Username (alphanumeric, underscore, hyphen only)"
    )
    email: str = Field(
        default="",
        description="Valid email address"
    )
    full_name: str = Field(
        default="",
        min_length=0, 
        max_length=100,
        description="Full name"
    )
    github_login: str = Field(
        default="",
        min_length=0, 
        max_length=50,
        description="GitHub username"
    )
    organization: str = Field(
        max_length=100,
        default="",
        description="Organization name"
    )
    
    # Preferences with validation
    preferred_download_directory: Path = Field(
        default_factory=lambda: Path.home() / "Downloads" / "siege_utilities",
        description="Default download directory"
    )
    default_output_format: str = Field(
        default="pptx",
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
    
    # Technical Preferences with constraints
    default_dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="Default DPI for output (72-600)"
    )
    default_figure_size: Tuple[int, int] = Field(
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
    
    # API Keys with format validation
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
    
    # Database Preferences
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
    
    @field_validator('default_figure_size')
    @classmethod
    def validate_figure_size(cls, v):
        """Validate figure size constraints."""
        if len(v) != 2:
            raise ValueError('Figure size must be a tuple of (width, height)')
        
        width, height = v
        if width < 1 or width > 50:
            raise ValueError('Figure width must be between 1 and 50')
        if height < 1 or height > 50:
            raise ValueError('Figure height must be between 1 and 50')
        
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format if provided."""
        if v and len(v.strip()) > 0:
            if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
                raise ValueError('Username must contain only alphanumeric characters, underscores, and hyphens')
        return v.strip() if v else ""
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v and len(v.strip()) > 0:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v.strip()):
                raise ValueError('Invalid email format')
        return v.strip() if v else ""
    
    @field_validator('github_login')
    @classmethod
    def validate_github_login(cls, v):
        """Validate GitHub login format if provided."""
        if v and len(v.strip()) > 0:
            if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
                raise ValueError('GitHub login must contain only alphanumeric characters, underscores, and hyphens')
        return v.strip() if v else ""
    
    @field_validator('google_analytics_key', 'facebook_business_key', 'census_api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format if provided."""
        if v and len(v.strip()) > 0:
            # Basic API key validation - should be alphanumeric with some special chars
            if not re.match(r'^[a-zA-Z0-9_-]{10,}$', v.strip()):
                raise ValueError('API key must be at least 10 characters and contain only alphanumeric characters, underscores, and hyphens')
        return v.strip() if v else ""
    
    @field_validator('preferred_download_directory', mode='before')
    @classmethod
    def validate_download_directory(cls, v):
        """Ensure download directory is a Path object."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
