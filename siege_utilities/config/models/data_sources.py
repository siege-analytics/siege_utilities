"""
Data source models for multi-source data ingestion.

Provides Jurisdiction, DataSource, and SourceCredential models
for tracking external data providers and their authentication.
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class JurisdictionLevel(str, Enum):
    """Level of government a data source covers."""
    FEDERAL = "federal"
    STATE = "state"
    COUNTY = "county"
    MUNICIPAL = "municipal"
    TRIBAL = "tribal"


class Jurisdiction(BaseModel):
    """Geographic/governmental jurisdiction for a data source."""
    level: JurisdictionLevel
    state_fips: Optional[str] = Field(
        default=None,
        max_length=2,
        description="FIPS code (e.g. '48' for TX). None for federal."
    )
    state_abbreviation: Optional[str] = Field(
        default=None,
        max_length=2,
        description="State abbreviation (e.g. 'TX')"
    )
    county_fips: Optional[str] = Field(
        default=None,
        max_length=5,
        description="County FIPS code"
    )
    name: str = Field(
        min_length=1,
        description="Human-readable name (e.g. 'Federal', 'Texas', 'Travis County')"
    )

    @field_validator('state_fips')
    @classmethod
    def validate_state_fips_format(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('state_fips must be numeric')
        return v

    @field_validator('county_fips')
    @classmethod
    def validate_county_fips_format(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('county_fips must be numeric')
        return v

    @model_validator(mode='after')
    def validate_jurisdiction_consistency(self):
        if self.level == JurisdictionLevel.FEDERAL and self.state_fips is not None:
            raise ValueError('Federal jurisdictions must not have state_fips')
        if self.level in (JurisdictionLevel.STATE, JurisdictionLevel.COUNTY) and self.state_fips is None:
            raise ValueError(f'{self.level.value} jurisdictions require state_fips')
        if self.level == JurisdictionLevel.COUNTY and self.county_fips is None:
            raise ValueError('County jurisdictions require county_fips')
        return self


class DataSourceType(str, Enum):
    """Category of data a source provides."""
    CAMPAIGN_FINANCE = "campaign_finance"
    VOTER_FILE = "voter_file"
    BOUNDARY = "boundary"
    DEMOGRAPHIC = "demographic"
    EDUCATION = "education"
    LABOR = "labor"
    ELECTION_ADMIN = "election_admin"


class DataSourceStatus(str, Enum):
    """Lifecycle status of a data source integration."""
    ACTIVE = "active"
    PLANNED = "planned"
    DEPRECATED = "deprecated"
    UNAVAILABLE = "unavailable"


class DataSource(BaseModel):
    """Registry entry for an external data provider."""
    source_id: str = Field(
        min_length=1,
        max_length=50,
        description="Unique identifier (e.g. 'fec', 'tx_ethics', 'census')"
    )
    name: str = Field(
        min_length=1,
        max_length=200,
        description="Full name (e.g. 'Federal Election Commission')"
    )
    source_type: DataSourceType
    jurisdiction: Jurisdiction
    base_url: Optional[str] = Field(
        default=None,
        description="API or download root URL"
    )
    documentation_url: Optional[str] = Field(
        default=None,
        description="Link to source documentation"
    )
    status: DataSourceStatus = DataSourceStatus.PLANNED
    auth_required: bool = False
    auth_type: Optional[str] = Field(
        default=None,
        description="Authentication type: 'api_key', 'oauth2', 'basic', or None"
    )
    file_formats: List[str] = Field(
        default_factory=list,
        description="Supported file formats (e.g. ['csv', 'fec', 'xml'])"
    )
    update_frequency: Optional[str] = Field(
        default=None,
        description="How often data is updated: 'daily', 'quarterly', 'annual'"
    )
    notes: Optional[str] = None

    @field_validator('auth_type')
    @classmethod
    def validate_auth_type(cls, v):
        if v is not None:
            valid = {'api_key', 'oauth2', 'basic', 'bearer'}
            if v not in valid:
                raise ValueError(f'auth_type must be one of {valid}')
        return v


class SourceCredential(BaseModel):
    """Per-source authentication credential reference (not the secret itself)."""
    source_id: str = Field(
        min_length=1,
        description="References DataSource.source_id"
    )
    credential_type: str = Field(
        min_length=1,
        description="Type: 'api_key', 'oauth2_client', 'basic_auth'"
    )
    credential_ref: str = Field(
        min_length=1,
        description="Reference to secret store (1Password item name, env var, etc.)"
    )
    environment: str = Field(
        default="production",
        description="Target environment: 'production', 'staging', 'development'"
    )
    last_verified: Optional[datetime] = None
