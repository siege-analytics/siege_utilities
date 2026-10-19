"""Database connection configuration with validation by connection type."""

from ipaddress import IPv6Address
import re
from typing import Self
from urllib.parse import quote_plus

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

__all__ = ["DatabaseConnection"]


class DatabaseConnection(BaseModel):
    """Validated settings for existing server and file database connections."""

    model_config = ConfigDict(
        hide_input_in_errors=True,
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
        default="",
        max_length=255,
        description="Database host (required for server connections)"
    )
    port: int = Field(
        default=0,
        ge=0,
        le=65535,
        description="Database port (1-65535 for servers, 0 allowed for files)"
    )
    database: str = Field(
        min_length=1,
        description="Database name or filesystem path for sqlite and duckdb"
    )
    username: str = Field(
        default="",
        max_length=50,
        description="Database username (required for server connections)"
    )
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        json_schema_extra={"sensitive": True},
        description="Stored database password (required for server connections)"
    )
    ssl_enabled: bool = Field(
        default=True,
        description="Enable SSL connection"
    )
    connection_timeout: int = Field(
        json_schema_extra={"sensitive": False},
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
    def validate_host(cls, v: str) -> str:
        """Allow empty file hosts, hostnames, and bare or bracketed IPv6."""
        if not v or v.lower() in ('localhost', '127.0.0.1', '::1'):
            return v.lower()
        if ':' in v or '[' in v or ']' in v:
            address = v[1:-1] if v.startswith('[') and v.endswith(']') else v
            try:
                IPv6Address(address)
            except ValueError:
                raise ValueError('Invalid IPv6 host format') from None
            return v
        if not re.fullmatch(r'[a-zA-Z0-9.-]+', v):
            raise ValueError(
                'Invalid host format - expected a hostname or IP address'
            )
        return v

    @model_validator(mode='after')
    def validate_connection_requirements(self) -> Self:
        """Require server settings without imposing a stored-password policy."""
        if self.connection_type in ('sqlite', 'duckdb'):
            return self

        if not self.host:
            raise ValueError('Server host must not be empty')
        if self.port < 1:
            raise ValueError('Server port must be greater than or equal to 1')
        if not self.username:
            raise ValueError('String should have at least 1 character for server username')
        if not self.password.get_secret_value():
            raise ValueError('Server password must not be empty')
        if len(self.database) > 50:
            raise ValueError('Server database name must have at most 50 characters')
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]*', self.database):
            raise ValueError(
                'Database name must start with a letter and contain only '
                'alphanumeric characters, underscores, and hyphens'
            )
        return self

    def get_connection_string(self) -> str:
        """Generate connection string for the database."""
        user = quote_plus(self.username)
        pw = quote_plus(self.password.get_secret_value())
        host = self.host
        if ':' in host and not host.startswith('['):
            host = f'[{host}]'
        if self.connection_type == 'postgresql':
            ssl_mode = '?sslmode=require' if self.ssl_enabled else ''
            return f"postgresql://{user}:{pw}@{host}:{self.port}/{self.database}{ssl_mode}"
        elif self.connection_type == 'mysql':
            ssl_mode = '?ssl=true' if self.ssl_enabled else ''
            return f"mysql://{user}:{pw}@{host}:{self.port}/{self.database}{ssl_mode}"
        elif self.connection_type == 'sqlite':
            return f"sqlite:///{self.database}"
        elif self.connection_type == 'duckdb':
            return f"duckdb:///{self.database}"
        else:
            raise ValueError(f"Unsupported connection type: {self.connection_type}")
