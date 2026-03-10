"""
Google Account model for multi-account management.

Represents a Google account (OAuth or Service Account) with metadata
for credential resolution, scope tracking, and default selection.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


class GoogleAccountType(str, Enum):
    """Type of Google account authentication."""
    OAUTH = "oauth"
    SERVICE_ACCOUNT = "service_account"


class GoogleAccountStatus(str, Enum):
    """Status of a Google account."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"


class GoogleAccount(BaseModel):
    """
    A Google account with credential references and scope tracking.

    For OAuth accounts, ``oauth_integration_name`` references an
    OAuthIntegration on the owning Person. For service accounts,
    ``service_account_ref`` points to a 1Password item or file path.
    """

    model_config = ConfigDict(
        json_schema_serialization_mode="json",
        validate_assignment=True,
        extra="forbid",
    )

    # Identity
    google_account_id: str = Field(
        min_length=1,
        max_length=200,
        description="Google 'sub' claim or service-account client_email",
    )
    email: str = Field(
        description="Gmail or Workspace email address",
    )
    display_name: str = Field(
        min_length=1,
        max_length=200,
        description="Human-readable label for this account",
    )

    # Type and status
    account_type: GoogleAccountType = Field(
        default=GoogleAccountType.OAUTH,
        description="Authentication type",
    )
    status: GoogleAccountStatus = Field(
        default=GoogleAccountStatus.ACTIVE,
        description="Account status",
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default account",
    )

    # Scopes granted (Google API scope URLs)
    scopes_granted: List[str] = Field(
        default_factory=list,
        description="Google API scope URLs granted to this account",
    )

    # Credential references (one set based on account_type)
    oauth_integration_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Name of OAuthIntegration on the owning Person",
    )
    service_account_ref: Optional[str] = Field(
        default=None,
        max_length=500,
        description="1Password item reference or file path for service account JSON",
    )
    token_file: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path to cached OAuth token file",
    )

    # Metadata
    created_date: datetime = Field(
        default_factory=datetime.now,
        description="Account registration date",
    )
    last_used: Optional[datetime] = Field(
        default=None,
        description="Last time this account was used",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()):
            raise ValueError("Invalid email format")
        return v.strip()

    @field_validator("google_account_id")
    @classmethod
    def validate_google_account_id(cls, v: str) -> str:
        """Validate account ID is non-empty after stripping."""
        v = v.strip()
        if not v:
            raise ValueError("google_account_id must not be blank")
        return v

    @model_validator(mode="after")
    def validate_credential_refs(self) -> "GoogleAccount":
        """Ensure the credential reference matches account_type."""
        if self.account_type == GoogleAccountType.OAUTH:
            if self.service_account_ref is not None:
                raise ValueError(
                    "OAuth accounts must not set service_account_ref"
                )
        elif self.account_type == GoogleAccountType.SERVICE_ACCOUNT:
            if self.oauth_integration_name is not None:
                raise ValueError(
                    "Service accounts must not set oauth_integration_name"
                )
            if self.token_file is not None:
                raise ValueError(
                    "Service accounts must not set token_file"
                )
        return self

    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == GoogleAccountStatus.ACTIVE

    def update_last_used(self) -> None:
        """Update the last-used timestamp."""
        self.last_used = datetime.now()

    def get_info(self) -> Dict[str, Any]:
        """Get account info (excluding sensitive credential data)."""
        return {
            "google_account_id": self.google_account_id,
            "email": self.email,
            "display_name": self.display_name,
            "account_type": self.account_type.value,
            "status": self.status.value,
            "is_default": self.is_default,
            "scopes_granted": list(self.scopes_granted),
            "has_oauth_integration": self.oauth_integration_name is not None,
            "has_service_account_ref": self.service_account_ref is not None,
            "has_token_file": self.token_file is not None,
            "created_date": self.created_date.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "notes": self.notes,
        }
