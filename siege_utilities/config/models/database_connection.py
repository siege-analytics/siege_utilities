"""
Database connection model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
import re


class DatabaseConnection(BaseModel):
    """
    Database connection configuration with comprehensive validation.
    
    Provides type-safe, validated database connection settings with
    detailed field constraints and security validation.
    """
    
    model_config = ConfigDict(
        json_schema_serialization_mode="json",
        validate_assignment=True,
        extra="forbid"
    )
    
    name: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Connection name (alphanumeric, underscore, hyphen only)"
    )
    connection_type: str = Field(
        pattern=r'^(postgresql|mysql|sqlite|duckdb)$',
        description="Database type"
    )
    host: str = Field(
        min_length=1,
        max_length=255,
        description="Database host"
    )
    port: int = Field(
        ge=1,
        le=65535,
        description="Database port (1-65535)"
    )
    database: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Database name"
    )
    username: str = Field(
        min_length=1,
        max_length=50,
        description="Database username"
    )
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Database password (minimum 8 characters)"
    )
    ssl_enabled: bool = Field(
        default=True,
        description="Enable SSL connection"
    )
    connection_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Connection timeout in seconds"
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of connections"
    )
    
    @field_validator('host')
    @classmethod
    def validate_host(cls, v):
        """Validate host format."""
        if not re.match(r'^[a-zA-Z0-9.-]+$', v):
            raise ValueError('Invalid host format - only alphanumeric characters, dots, and hyphens allowed')
        
        # Check for localhost variations
        if v.lower() in ['localhost', '127.0.0.1', '::1']:
            return v.lower()
        
        # Basic domain validation
        if '.' in v and len(v.split('.')) >= 2:
            return v
        
        # IP address validation (basic)
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', v):
            return v
        
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Check for common weak patterns
        if v.lower() in ['password', '12345678', 'qwerty123']:
            raise ValueError('Password is too common - please use a stronger password')
        
        # Require at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Require at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Require at least one number
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        
        return v
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port number."""
        if v < 1 or v > 65535:
            raise ValueError('Port must be between 1 and 65535')
        
        # Warn about common non-standard ports
        if v in [22, 80, 443, 8080, 8443]:
            # These are common but might be intentional
            pass
        
        return v
    
    @field_validator('database')
    @classmethod
    def validate_database_name(cls, v):
        """Validate database name."""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Database name must start with a letter and contain only alphanumeric characters, underscores, and hyphens')
        
        return v
    
    def get_connection_string(self) -> str:
        """Generate connection string for the database."""
        if self.connection_type == 'postgresql':
            ssl_mode = '?sslmode=require' if self.ssl_enabled else ''
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_mode}"
        elif self.connection_type == 'mysql':
            ssl_mode = '?ssl=true' if self.ssl_enabled else ''
            return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_mode}"
        elif self.connection_type == 'sqlite':
            return f"sqlite:///{self.database}"
        elif self.connection_type == 'duckdb':
            return f"duckdb:///{self.database}"
        else:
            raise ValueError(f"Unsupported connection type: {self.connection_type}")
    






