"""Tests for config model validation error paths."""

from __future__ import annotations


import pytest
from pydantic import ValidationError

from siege_utilities.config.models.user_profile import UserProfile
from siege_utilities.config.models.client_profile import ClientProfile, ContactInfo
from siege_utilities.config.models.database_connection import DatabaseConnection
from siege_utilities.config.models.data_sources import (
    DataSource,
    DataSourceType,
    Jurisdiction,
    JurisdictionLevel,
)
from siege_utilities.config.models.oauth_integration import (
    OAuthIntegration,
    OAuthProvider,
)
from siege_utilities.config.models.social_media_account import SocialMediaAccount
from siege_utilities.config.models.report_preferences import ReportPreferences
from siege_utilities.config.models.branding_config import BrandingConfig
from siege_utilities.config.models.actor_types import (
    User,
    Client,
    Collaborator,
    Organization,
    Collaboration,
)


# ---------------------------------------------------------------------------
# Helpers — minimal valid kwargs for models with many required fields
# ---------------------------------------------------------------------------

def _person_kw(**overrides):
    """Minimal valid kwargs for a Person-derived model."""
    base = dict(
        person_id="test-user",
        name="Test User",
        email="test@example.com",
    )
    base.update(overrides)
    return base


def _user_kw(**overrides):
    kw = _person_kw(username="testuser")
    kw.update(overrides)
    return kw


def _client_kw(**overrides):
    kw = _person_kw(
        client_code="AB",
        industry="Tech",
        project_count=0,
        client_status="active",
    )
    kw.update(overrides)
    return kw


def _collab_kw(**overrides):
    kw = _person_kw(external_organization="Masai Interactive")
    kw.update(overrides)
    return kw


def _org_kw(**overrides):
    base = dict(
        org_id="siege",
        name="Siege Analytics",
        org_type="vendor",
        primary_email="info@siege.com",
    )
    base.update(overrides)
    return base


def _collab_model_kw(**overrides):
    base = dict(
        collab_id="proj-1",
        name="Joint Project",
    )
    base.update(overrides)
    return base


def _db_kw(**overrides):
    base = dict(
        name="mydb",
        connection_type="postgresql",
        host="db.example.com",
        port=5432,
        database="appdb",
        username="admin",
        password="Str0ngP@ss1",
    )
    base.update(overrides)
    return base


def _social_kw(**overrides):
    base = dict(
        platform="facebook",
        account_id="123456789",
        account_name="TestPage",
        access_token="abcdefghij1234567890",
    )
    base.update(overrides)
    return base


def _oauth_kw(**overrides):
    base = dict(
        name="my-integration",
        provider=OAuthProvider.GOOGLE,
        service="analytics",
        client_id="0123456789abcdef",
        client_secret="secret12345secret",
        redirect_uri="https://example.com/callback",
    )
    base.update(overrides)
    return base


def _branding_kw(**overrides):
    base = dict(
        primary_color="#1f77b4",
        secondary_color="#ff7f0e",
        accent_color="#2ca02c",
        text_color="#000000",
        background_color="#ffffff",
        primary_font="Arial",
        secondary_font="Helvetica",
    )
    base.update(overrides)
    return base


def _contact_kw(**overrides):
    base = dict(email="test@example.com")
    base.update(overrides)
    return base


def _client_profile_kw(**overrides):
    base = dict(
        client_id="acme",
        client_name="ACME Corp",
        client_code="AC",
        contact_info=ContactInfo(**_contact_kw()),
        industry="Tech",
        project_count=0,
        status="active",
        branding_config=BrandingConfig(**_branding_kw()),
        report_preferences=ReportPreferences(),
    )
    base.update(overrides)
    return base


# ===========================================================================
# UserProfile
# ===========================================================================

class TestUserProfileValidation:
    def test_invalid_username_raises_error(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            UserProfile(username="bad user!")

    def test_invalid_email_raises_error(self):
        with pytest.raises(ValidationError, match="email"):
            UserProfile(email="not-an-email")

    def test_invalid_github_login_raises_error(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            UserProfile(github_login="bad user!")

    def test_invalid_output_format_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            UserProfile(default_output_format="docx")

    def test_invalid_map_style_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            UserProfile(preferred_map_style="unknown-style")

    def test_invalid_color_scheme_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            UserProfile(default_color_scheme="rainbow")

    def test_invalid_log_level_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            UserProfile(log_level="TRACE")

    def test_invalid_database_type_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            UserProfile(default_database="oracle")

    def test_dpi_too_low_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            UserProfile(default_dpi=10)

    def test_dpi_too_high_raises_error(self):
        with pytest.raises(ValidationError, match="less than or equal"):
            UserProfile(default_dpi=9999)

    def test_invalid_figure_size_width_raises_error(self):
        with pytest.raises(ValidationError, match="width"):
            UserProfile(default_figure_size=(0, 8))

    def test_invalid_figure_size_height_raises_error(self):
        with pytest.raises(ValidationError, match="height"):
            UserProfile(default_figure_size=(10, 0))

    def test_invalid_api_key_format_raises_error(self):
        with pytest.raises(ValidationError, match="API key"):
            UserProfile(google_analytics_key="short")


# ===========================================================================
# DatabaseConnection
# ===========================================================================

class TestDatabaseConnectionValidation:
    def test_empty_name_raises_error(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            DatabaseConnection(**_db_kw(name=""))

    def test_invalid_connection_type_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            DatabaseConnection(**_db_kw(connection_type="oracle"))

    def test_invalid_host_format_raises_error(self):
        with pytest.raises(ValidationError, match="host"):
            DatabaseConnection(**_db_kw(host="bad host with spaces"))

    def test_port_zero_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            DatabaseConnection(**_db_kw(port=0))

    def test_port_too_high_raises_error(self):
        with pytest.raises(ValidationError, match="less than or equal"):
            DatabaseConnection(**_db_kw(port=70000))

    def test_database_name_starting_with_number_raises_error(self):
        with pytest.raises(ValidationError, match="Database name must start with a letter"):
            DatabaseConnection(**_db_kw(database="1badname"))

    def test_password_too_short_raises_error(self):
        with pytest.raises(ValidationError, match="at least 8 characters"):
            DatabaseConnection(**_db_kw(password="Sh0rt"))

    def test_password_common_raises_error(self):
        with pytest.raises(ValidationError, match="too common"):
            DatabaseConnection(**_db_kw(password="password"))

    def test_password_missing_uppercase_raises_error(self):
        with pytest.raises(ValidationError, match="uppercase"):
            DatabaseConnection(**_db_kw(password="alllowercase1"))

    def test_password_missing_lowercase_raises_error(self):
        with pytest.raises(ValidationError, match="lowercase"):
            DatabaseConnection(**_db_kw(password="ALLUPPERCASE1"))

    def test_password_missing_number_raises_error(self):
        with pytest.raises(ValidationError, match="number"):
            DatabaseConnection(**_db_kw(password="NoNumbersHere"))

    def test_empty_username_raises_error(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            DatabaseConnection(**_db_kw(username=""))

    def test_invalid_name_pattern_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            DatabaseConnection(**_db_kw(name="bad name!"))


# ===========================================================================
# ContactInfo
# ===========================================================================

class TestContactInfoValidation:
    def test_invalid_email_raises_error(self):
        with pytest.raises(ValidationError, match="email"):
            ContactInfo(email="not-valid")

    def test_phone_too_few_digits_raises_error(self):
        with pytest.raises(ValidationError, match="10-15 digits"):
            ContactInfo(phone="12345")

    def test_invalid_website_raises_error(self):
        with pytest.raises(ValidationError, match="website"):
            ContactInfo(website="not-a-url")

    def test_invalid_linkedin_raises_error(self):
        with pytest.raises(ValidationError, match="LinkedIn"):
            ContactInfo(linkedin="https://linkedin.com/wrong/format")


# ===========================================================================
# ClientProfile
# ===========================================================================

class TestClientProfileValidation:
    def test_empty_client_id_raises_error(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            ClientProfile(**_client_profile_kw(client_id=""))

    def test_client_code_too_short_raises_error(self):
        with pytest.raises(ValidationError, match="at least 2 character"):
            ClientProfile(**_client_profile_kw(client_code="A"))

    def test_client_code_reserved_raises_error(self):
        with pytest.raises(ValidationError, match="reserved"):
            ClientProfile(**_client_profile_kw(client_code="TEST"))

    def test_client_code_lowercase_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            ClientProfile(**_client_profile_kw(client_code="abc"))

    def test_invalid_status_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            ClientProfile(**_client_profile_kw(status="deleted"))

    def test_negative_project_count_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            ClientProfile(**_client_profile_kw(project_count=-1))

    def test_duplicate_db_connection_names_raises_error(self):
        conn = DatabaseConnection(**_db_kw())
        with pytest.raises(ValidationError, match="unique"):
            ClientProfile(**_client_profile_kw(database_connections=[conn, conn]))

    def test_duplicate_social_media_platforms_raises_error(self):
        acct = SocialMediaAccount(**_social_kw())
        with pytest.raises(ValidationError, match="unique"):
            ClientProfile(**_client_profile_kw(social_media_accounts=[acct, acct]))


# ===========================================================================
# SocialMediaAccount
# ===========================================================================

class TestSocialMediaAccountValidation:
    def test_invalid_platform_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            SocialMediaAccount(**_social_kw(platform="myspace"))

    def test_access_token_too_short_raises_error(self):
        with pytest.raises(ValidationError, match="at least 20 characters"):
            SocialMediaAccount(**_social_kw(access_token="short"))

    def test_access_token_invalid_chars_raises_error(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            SocialMediaAccount(**_social_kw(access_token="aaaaaaaaaa!@#$%^&*()bbbbb"))

    def test_facebook_account_id_non_numeric_raises_error(self):
        with pytest.raises(ValidationError, match="numeric"):
            SocialMediaAccount(**_social_kw(platform="facebook", account_id="notanumber"))

    def test_twitter_account_id_invalid_raises_error(self):
        with pytest.raises(ValidationError, match="handle"):
            SocialMediaAccount(**_social_kw(platform="twitter", account_id="bad handle!"))

    def test_invalid_api_version_for_twitter_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid API version"):
            SocialMediaAccount(**_social_kw(
                platform="twitter",
                account_id="@handle",
                api_version="v9.0",
            ))

    def test_invalid_api_version_format_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            SocialMediaAccount(**_social_kw(api_version="1.0"))


# ===========================================================================
# OAuthIntegration
# ===========================================================================

class TestOAuthIntegrationValidation:
    def test_invalid_name_raises_error(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            OAuthIntegration(**_oauth_kw(name="bad name!"))

    def test_invalid_service_raises_error(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            OAuthIntegration(**_oauth_kw(service="bad service!"))

    def test_invalid_redirect_uri_raises_error(self):
        with pytest.raises(ValidationError, match="redirect URI"):
            OAuthIntegration(**_oauth_kw(redirect_uri="not-a-url"))

    def test_client_id_too_short_raises_error(self):
        with pytest.raises(ValidationError, match="at least 10 characters"):
            OAuthIntegration(**_oauth_kw(client_id="short"))

    def test_client_secret_too_short_raises_error(self):
        with pytest.raises(ValidationError, match="at least 10 characters"):
            OAuthIntegration(**_oauth_kw(client_secret="short"))

    def test_refresh_threshold_too_low_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            OAuthIntegration(**_oauth_kw(refresh_threshold=10))

    def test_refresh_threshold_too_high_raises_error(self):
        with pytest.raises(ValidationError, match="less than or equal"):
            OAuthIntegration(**_oauth_kw(refresh_threshold=9999))

    def test_get_authorization_url_custom_provider_raises_error(self):
        oauth = OAuthIntegration(**_oauth_kw(provider=OAuthProvider.CUSTOM))
        with pytest.raises(ValueError, match="not configured"):
            oauth.get_authorization_url()


# ===========================================================================
# ReportPreferences
# ===========================================================================

class TestReportPreferencesValidation:
    def test_invalid_chart_style_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            ReportPreferences(chart_style="funky")

    def test_invalid_page_size_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            ReportPreferences(page_size="B5")

    def test_invalid_chart_quality_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            ReportPreferences(chart_quality="extreme")

    def test_chart_dpi_too_low_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            ReportPreferences(chart_dpi=10)

    def test_chart_dpi_too_high_raises_error(self):
        with pytest.raises(ValidationError, match="less than or equal"):
            ReportPreferences(chart_dpi=9999)

    def test_invalid_section_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid section"):
            ReportPreferences(sections=["executive_summary", "nonexistent"])

    def test_watermark_enabled_missing_text_raises_error(self):
        with pytest.raises(ValidationError, match="required when watermark"):
            ReportPreferences(include_watermark=True, watermark_text=None)

    def test_watermark_text_empty_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            ReportPreferences(include_watermark=True, watermark_text="   ")


# ===========================================================================
# BrandingConfig
# ===========================================================================

class TestBrandingConfigValidation:
    def test_invalid_hex_color_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            BrandingConfig(**_branding_kw(primary_color="red"))

    def test_invalid_font_name_raises_error(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            BrandingConfig(**_branding_kw(primary_font="Font@Name!"))

    def test_invalid_logo_extension_raises_error(self):
        with pytest.raises(ValidationError, match="valid image extension"):
            BrandingConfig(**_branding_kw(logo_path="/path/to/logo.txt"))

    def test_logo_width_too_small_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            BrandingConfig(**_branding_kw(logo_width=1))

    def test_header_height_too_small_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            BrandingConfig(**_branding_kw(header_height=5))

    def test_title_font_size_too_small_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            BrandingConfig(**_branding_kw(title_font_size=5))

    def test_invalid_chart_palette_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            BrandingConfig(**_branding_kw(chart_color_palette="rainbow"))


# ===========================================================================
# DataSources: Jurisdiction
# ===========================================================================

class TestJurisdictionValidation:
    def test_non_numeric_state_fips_raises_error(self):
        with pytest.raises(ValidationError, match="numeric"):
            Jurisdiction(level=JurisdictionLevel.STATE, name="Texas",
                         state_fips="TX", state_abbreviation="TX")

    def test_non_numeric_county_fips_raises_error(self):
        with pytest.raises(ValidationError, match="numeric"):
            Jurisdiction(level=JurisdictionLevel.COUNTY, name="Travis",
                         state_fips="48", county_fips="abc",
                         state_abbreviation="TX")

    def test_federal_with_state_fips_raises_error(self):
        with pytest.raises(ValidationError, match="must not have state_fips"):
            Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal",
                         state_fips="48")

    def test_state_missing_state_fips_raises_error(self):
        with pytest.raises(ValidationError, match="require state_fips"):
            Jurisdiction(level=JurisdictionLevel.STATE, name="Texas")

    def test_county_missing_county_fips_raises_error(self):
        with pytest.raises(ValidationError, match="require county_fips"):
            Jurisdiction(level=JurisdictionLevel.COUNTY, name="Travis",
                         state_fips="48")

    def test_empty_name_raises_error(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Jurisdiction(level=JurisdictionLevel.FEDERAL, name="")


# ===========================================================================
# DataSources: DataSource
# ===========================================================================

class TestDataSourceValidation:
    def test_invalid_auth_type_raises_error(self):
        j = Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal")
        with pytest.raises(ValidationError, match="auth_type must be one of"):
            DataSource(
                source_id="fec",
                name="FEC",
                source_type=DataSourceType.CAMPAIGN_FINANCE,
                jurisdiction=j,
                auth_type="cookie",
            )

    def test_empty_source_id_raises_error(self):
        j = Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal")
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            DataSource(
                source_id="",
                name="FEC",
                source_type=DataSourceType.CAMPAIGN_FINANCE,
                jurisdiction=j,
            )


# ===========================================================================
# Actor Types: User
# ===========================================================================

class TestActorUserValidation:
    def test_invalid_username_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            User(**_user_kw(username="bad user!"))

    def test_invalid_role_raises_error(self):
        with pytest.raises(ValidationError, match="Role must be one of"):
            User(**_user_kw(role="superadmin"))

    def test_duplicate_permissions_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            User(**_user_kw(permissions=["read", "read"]))

    def test_invalid_github_login_raises_error(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            User(**_user_kw(github_login="bad login!"))

    def test_invalid_output_format_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            User(**_user_kw(default_output_format="docx"))

    def test_invalid_log_level_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            User(**_user_kw(log_level="TRACE"))

    def test_dpi_too_low_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            User(**_user_kw(default_dpi=10))

    def test_duplicate_assigned_clients_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            User(**_user_kw(assigned_clients=["AB", "AB"]))

    def test_primary_client_not_in_assigned_raises_error(self):
        with pytest.raises(ValidationError, match="must be in assigned_clients"):
            User(**_user_kw(assigned_clients=["AB"], primary_client="XY"))


# ===========================================================================
# Actor Types: Client
# ===========================================================================

class TestActorClientValidation:
    def test_client_code_too_short_raises_error(self):
        with pytest.raises(ValidationError, match="at least 2 character"):
            Client(**_client_kw(client_code="A"))

    def test_client_code_lowercase_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            Client(**_client_kw(client_code="abc"))

    def test_client_code_reserved_raises_error(self):
        with pytest.raises(ValidationError, match="reserved"):
            Client(**_client_kw(client_code="TEST"))

    def test_invalid_client_status_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            Client(**_client_kw(client_status="deleted"))

    def test_negative_project_count_raises_error(self):
        with pytest.raises(ValidationError, match="greater than or equal"):
            Client(**_client_kw(project_count=-1))

    def test_duplicate_assigned_users_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Client(**_client_kw(assigned_users=["u1", "u1"]))

    def test_primary_user_not_in_assigned_raises_error(self):
        with pytest.raises(ValidationError, match="must be in assigned_users"):
            Client(**_client_kw(assigned_users=["u1"], primary_user="u2"))


# ===========================================================================
# Actor Types: Collaborator
# ===========================================================================

class TestCollaboratorValidation:
    def test_empty_external_organization_raises_error(self):
        with pytest.raises(ValidationError, match="empty"):
            Collaborator(**_collab_kw(external_organization="   "))

    def test_invalid_collaboration_level_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            Collaborator(**_collab_kw(collaboration_level="superuser"))

    def test_duplicate_allowed_services_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Collaborator(**_collab_kw(allowed_services=["svc", "svc"]))

    def test_duplicate_restricted_credentials_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Collaborator(**_collab_kw(restricted_credentials=["c1", "c1"]))


# ===========================================================================
# Actor Types: Organization
# ===========================================================================

class TestOrganizationValidation:
    def test_invalid_email_raises_error(self):
        with pytest.raises(ValidationError, match="email"):
            Organization(**_org_kw(primary_email="not-an-email"))

    def test_invalid_org_type_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            Organization(**_org_kw(org_type="ngo"))

    def test_duplicate_members_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Organization(**_org_kw(members=["p1", "p1"]))

    def test_invalid_status_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            Organization(**_org_kw(status="deleted"))

    def test_empty_org_id_raises_error(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Organization(**_org_kw(org_id=""))


# ===========================================================================
# Actor Types: Collaboration
# ===========================================================================

class TestCollaborationValidation:
    def test_invalid_status_raises_error(self):
        with pytest.raises(ValidationError, match="pattern"):
            Collaboration(**_collab_model_kw(status="deleted"))

    def test_duplicate_participants_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Collaboration(**_collab_model_kw(participants=["p1", "p1"]))

    def test_duplicate_organizations_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Collaboration(**_collab_model_kw(organizations=["o1", "o1"]))

    def test_duplicate_clients_raises_error(self):
        with pytest.raises(ValidationError, match="unique"):
            Collaboration(**_collab_model_kw(clients=["c1", "c1"]))

    def test_empty_collab_id_raises_error(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Collaboration(**_collab_model_kw(collab_id=""))
