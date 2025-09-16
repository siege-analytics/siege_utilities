#!/usr/bin/env python3
"""
Comprehensive example demonstrating the Hydra + Pydantic configuration system.

This example shows how to use the new configuration system for various
use cases including user profiles, client configurations, and validation.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from siege_utilities.config import HydraConfigManager
from siege_utilities.config.models import (
    UserProfile, ClientProfile, ContactInfo, BrandingConfig,
    ReportPreferences, DatabaseConnection, SocialMediaAccount
)


def example_user_profile():
    """Example of creating and using a UserProfile."""
    print("=" * 60)
    print("USER PROFILE EXAMPLE")
    print("=" * 60)
    
    # Create a user profile with validation
    try:
        user_profile = UserProfile(
            username="john_doe",
            email="john@example.com",
            full_name="John Doe",
            github_login="johndoe",
            organization="Acme Corporation",
            default_output_format="pptx",
            default_dpi=300,
            preferred_map_style="satellite",
            default_color_scheme="viridis"
        )
        
        print(f"✅ User Profile Created Successfully:")
        print(f"  Username: {user_profile.username}")
        print(f"  Email: {user_profile.email}")
        print(f"  Organization: {user_profile.organization}")
        print(f"  Default Format: {user_profile.default_output_format}")
        print(f"  Default DPI: {user_profile.default_dpi}")
        print(f"  Download Directory: {user_profile.preferred_download_directory}")
        
    except Exception as e:
        print(f"❌ User Profile Creation Failed: {e}")
    
    # Demonstrate validation
    print("\n🔍 Validation Example:")
    try:
        invalid_profile = UserProfile(
            username="",  # Empty username
            email="invalid-email",  # Invalid email format
            full_name="Test User",
            github_login="testuser"
        )
    except Exception as e:
        print(f"✅ Validation correctly rejected invalid data: {e}")


def example_client_profile():
    """Example of creating and using a ClientProfile."""
    print("\n" + "=" * 60)
    print("CLIENT PROFILE EXAMPLE")
    print("=" * 60)
    
    try:
        # Create contact information
        contact = ContactInfo(
            email="client@acme.com",
            phone="+1-555-123-4567",
            website="https://acme.com",
            linkedin="https://linkedin.com/company/acme-corp"
        )
        
        # Create branding configuration
        branding = BrandingConfig(
            primary_color="#1f77b4",
            secondary_color="#ff7f0e",
            accent_color="#2ca02c",
            text_color="#000000",
            background_color="#ffffff",
            primary_font="Arial",
            secondary_font="Arial",
            title_font_size=24,
            subtitle_font_size=18
        )
        
        # Create report preferences
        report_prefs = ReportPreferences(
            default_format="pptx",
            include_executive_summary=True,
            chart_style="professional",
            page_size="A4",
            orientation="landscape"
        )
        
        # Create client profile
        client = ClientProfile(
            client_id="acme_corp",
            client_name="Acme Corporation",
            client_code="ACME",
            contact_info=contact,
            industry="Technology",
            project_count=5,
            status="active",
            branding_config=branding,
            report_preferences=report_prefs
        )
        
        print(f"✅ Client Profile Created Successfully:")
        print(f"  Client Code: {client.client_code}")
        print(f"  Client Name: {client.client_name}")
        print(f"  Industry: {client.industry}")
        print(f"  Contact Email: {client.contact_info.email}")
        print(f"  Brand Color: {client.branding_config.primary_color}")
        print(f"  Report Format: {client.report_preferences.default_format}")
        
        # Demonstrate helper methods
        print(f"\n📊 Client Summary:")
        summary = client.get_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ Client Profile Creation Failed: {e}")


def example_database_connection():
    """Example of creating and using a DatabaseConnection."""
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION EXAMPLE")
    print("=" * 60)
    
    try:
        # Create a database connection with validation
        db_conn = DatabaseConnection(
            name="production_db",
            connection_type="postgresql",
            host="prod-db.acme.com",
            port=5432,
            database="acme_production",
            username="admin",
            password="SecurePassword123",  # Must meet strength requirements
            ssl_enabled=True,
            connection_timeout=30,
            max_connections=20
        )
        
        print(f"✅ Database Connection Created Successfully:")
        print(f"  Name: {db_conn.name}")
        print(f"  Type: {db_conn.connection_type}")
        print(f"  Host: {db_conn.host}")
        print(f"  Port: {db_conn.port}")
        print(f"  Database: {db_conn.database}")
        print(f"  SSL Enabled: {db_conn.ssl_enabled}")
        print(f"  Connection String: {db_conn.get_connection_string()[:50]}...")
        
    except Exception as e:
        print(f"❌ Database Connection Creation Failed: {e}")
    
    # Demonstrate password validation
    print("\n🔍 Password Validation Example:")
    try:
        weak_db = DatabaseConnection(
            name="test_db",
            connection_type="postgresql",
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="123"  # Too weak
        )
    except Exception as e:
        print(f"✅ Password validation correctly rejected weak password: {e}")


def example_social_media_account():
    """Example of creating and using a SocialMediaAccount."""
    print("\n" + "=" * 60)
    print("SOCIAL MEDIA ACCOUNT EXAMPLE")
    print("=" * 60)
    
    try:
        # Create a social media account
        social_account = SocialMediaAccount(
            platform="facebook",
            account_id="123456789",
            account_name="Acme Corporation",
            access_token="valid_facebook_access_token_123456789",
            is_active=True,
            api_version="v2.0"
        )
        
        print(f"✅ Social Media Account Created Successfully:")
        print(f"  Platform: {social_account.platform}")
        print(f"  Account ID: {social_account.account_id}")
        print(f"  Account Name: {social_account.account_name}")
        print(f"  API Version: {social_account.api_version}")
        print(f"  Is Active: {social_account.is_active}")
        print(f"  Auth Headers: {social_account.get_auth_headers()}")
        print(f"  API Base URL: {social_account.get_api_base_url()}")
        
    except Exception as e:
        print(f"❌ Social Media Account Creation Failed: {e}")


def example_hydra_config_manager():
    """Example of using the HydraConfigManager."""
    print("\n" + "=" * 60)
    print("HYDRA CONFIG MANAGER EXAMPLE")
    print("=" * 60)
    
    try:
        with HydraConfigManager() as manager:
            print("✅ HydraConfigManager Initialized Successfully")
            
            # Load user profile
            print("\n📋 Loading User Profile:")
            user_profile = manager.load_user_profile()
            print(f"  Username: '{user_profile.username}'")
            print(f"  Email: '{user_profile.email}'")
            print(f"  Default Format: {user_profile.default_output_format}")
            print(f"  Default DPI: {user_profile.default_dpi}")
            
            # Load default branding
            print("\n🎨 Loading Default Branding:")
            default_branding = manager.load_branding_config()
            print(f"  Primary Color: {default_branding.primary_color}")
            print(f"  Primary Font: {default_branding.primary_font}")
            print(f"  Title Font Size: {default_branding.title_font_size}")
            
            # Load client-specific branding
            print("\n🎨 Loading Client-Specific Branding:")
            try:
                client_a_branding = manager.load_branding_config("client_a")
                print(f"  Client A Primary Color: {client_a_branding.primary_color}")
                print(f"  Client A Primary Font: {client_a_branding.primary_font}")
            except Exception as e:
                print(f"  ⚠️  Client A branding not available: {e}")
            
            try:
                client_b_branding = manager.load_branding_config("client_b")
                print(f"  Client B Primary Color: {client_b_branding.primary_color}")
                print(f"  Client B Primary Font: {client_b_branding.primary_font}")
            except Exception as e:
                print(f"  ⚠️  Client B branding not available: {e}")
            
            # Load database connections
            print("\n🗄️  Loading Database Connections:")
            db_connections = manager.load_database_connections()
            print(f"  Found {len(db_connections)} database connections")
            for conn in db_connections:
                print(f"    - {conn.name}: {conn.connection_type} @ {conn.host}:{conn.port}")
            
            # Load social media accounts
            print("\n📱 Loading Social Media Accounts:")
            social_accounts = manager.load_social_media_accounts()
            print(f"  Found {len(social_accounts)} social media accounts")
            for account in social_accounts:
                print(f"    - {account.platform}: {account.account_name}")
            
    except Exception as e:
        print(f"❌ HydraConfigManager Failed: {e}")
        import traceback
        traceback.print_exc()


def example_configuration_validation():
    """Example of comprehensive configuration validation."""
    print("\n" + "=" * 60)
    print("CONFIGURATION VALIDATION EXAMPLE")
    print("=" * 60)
    
    # Test various validation scenarios
    validation_tests = [
        {
            "name": "Valid Email",
            "test": lambda: UserProfile(
                username="test",
                email="valid@example.com",
                full_name="Test User",
                github_login="testuser"
            )
        },
        {
            "name": "Invalid Email",
            "test": lambda: UserProfile(
                username="test",
                email="invalid-email",
                full_name="Test User",
                github_login="testuser"
            )
        },
        {
            "name": "Valid Hex Color",
            "test": lambda: BrandingConfig(
                primary_color="#FF0000",
                secondary_color="#00FF00",
                accent_color="#0000FF",
                text_color="#000000",
                background_color="#FFFFFF",
                primary_font="Arial",
                secondary_font="Arial"
            )
        },
        {
            "name": "Invalid Color Format",
            "test": lambda: BrandingConfig(
                primary_color="red",  # Not hex format
                secondary_color="#00FF00",
                accent_color="#0000FF",
                text_color="#000000",
                background_color="#FFFFFF",
                primary_font="Arial",
                secondary_font="Arial"
            )
        }
    ]
    
    for test in validation_tests:
        print(f"\n🧪 Testing: {test['name']}")
        try:
            result = test['test']()
            print(f"  ✅ Validation Passed")
        except Exception as e:
            print(f"  ❌ Validation Failed: {e}")


def example_complete_workflow():
    """Example of a complete workflow using the configuration system."""
    print("\n" + "=" * 60)
    print("COMPLETE WORKFLOW EXAMPLE")
    print("=" * 60)
    
    def generate_client_report(client_code: str):
        """Simulate generating a report for a client."""
        print(f"\n📊 Generating Report for Client: {client_code}")
        
        try:
            with HydraConfigManager() as manager:
                # Load client-specific configuration
                try:
                    client_profile = manager.load_client_profile(client_code)
                    branding = manager.load_branding_config(client_code)
                    db_connections = manager.load_database_connections(client_code)
                except Exception:
                    # Fall back to default if client-specific not available
                    print(f"  ⚠️  Client-specific config not found, using defaults")
                    branding = manager.load_branding_config()
                    db_connections = manager.load_database_connections()
                
                # Use configuration for report generation
                print(f"  📋 Report Configuration:")
                print(f"    - Client: {getattr(client_profile, 'client_name', 'Default Client')}")
                print(f"    - Brand Color: {branding.primary_color}")
                print(f"    - Primary Font: {branding.primary_font}")
                print(f"    - Available Databases: {[conn.name for conn in db_connections]}")
                
                # Simulate report generation
                print(f"  ✅ Report generated successfully with {client_code} branding")
                
        except Exception as e:
            print(f"  ❌ Report generation failed: {e}")
    
    # Test with different clients
    generate_client_report("client_a")
    generate_client_report("client_b")
    generate_client_report("nonexistent_client")


def main():
    """Run all examples."""
    print("🚀 Hydra + Pydantic Configuration System Examples")
    print("=" * 60)
    
    # Run all examples
    example_user_profile()
    example_client_profile()
    example_database_connection()
    example_social_media_account()
    example_hydra_config_manager()
    example_configuration_validation()
    example_complete_workflow()
    
    print("\n" + "=" * 60)
    print("✅ All Examples Completed Successfully!")
    print("=" * 60)
    
    print("\n📚 Next Steps:")
    print("1. Review the configuration files in siege_utilities/configs/")
    print("2. Create your own client-specific configurations")
    print("3. Use the migration script to migrate from legacy systems")
    print("4. Explore the comprehensive documentation")
    print("\n🎉 Happy configuring!")


if __name__ == "__main__":
    main()
