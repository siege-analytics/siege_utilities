"""
Enhanced Pydantic models for siege_utilities configuration system.

This module provides comprehensive data validation models for all
configurable entities in the siege_utilities system.
"""

from .user_profile import UserProfile
from .client_profile import ClientProfile, ContactInfo
from .database_connection import DatabaseConnection
from .social_media_account import SocialMediaAccount
from .branding_config import BrandingConfig
from .report_preferences import ReportPreferences
from .data_sources import (
    JurisdictionLevel,
    Jurisdiction,
    DataSourceType,
    DataSourceStatus,
    DataSource,
    SourceCredential,
)
from .google_account import GoogleAccount, GoogleAccountType, GoogleAccountStatus

__all__ = [
    "UserProfile",
    "ClientProfile",
    "ContactInfo",
    "DatabaseConnection",
    "SocialMediaAccount",
    "BrandingConfig",
    "ReportPreferences",
    "JurisdictionLevel",
    "Jurisdiction",
    "DataSourceType",
    "DataSourceStatus",
    "DataSource",
    "SourceCredential",
    "GoogleAccount",
    "GoogleAccountType",
    "GoogleAccountStatus",
]

# Pydantic v2: rebuild models that reference other models from sibling modules
# so that validators resolve to the correct class identity regardless of import order.
ClientProfile.model_rebuild()
UserProfile.model_rebuild()
DatabaseConnection.model_rebuild()
DataSource.model_rebuild()
