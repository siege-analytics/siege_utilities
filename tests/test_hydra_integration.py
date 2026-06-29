"""
Tests for Hydra + Pydantic integration system.

This module tests the complete Hydra configuration loading and Pydantic validation
system for siege_utilities.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml

from siege_utilities.config.hydra_manager import HydraConfigManager
from siege_utilities.config.models import (
    UserProfile, ClientProfile, BrandingConfig, ReportPreferences,
    DatabaseConnection, SocialMediaAccount
)
from siege_utilities.config.migration import ConfigurationMigrator


class TestHydraConfigManager:
    """Test the HydraConfigManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "configs"
        self._create_test_configs()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def _create_test_configs(self):
        """Create test configuration files."""
        # Create directory structure
        (self.config_dir / "default").mkdir(parents=True)
        (self.config_dir / "client" / "test_client").mkdir(parents=True)
        
        # Default user profile
        user_profile = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "github_login": "testuser",
            "organization": "Test Org",
            "default_output_format": "pptx",
            "default_dpi": 300
        }
        
        with open(self.config_dir / "default" / "user_profile.yaml", "w") as f:
            yaml.dump(user_profile, f)
        
        # Default branding config
        branding_config = {
            "colors": {
                "primary_color": "#1f77b4",
                "secondary_color": "#ff7f0e",
                "accent_color": "#2ca02c",
                "text_color": "#000000",
                "background_color": "#ffffff"
            },
            "typography": {
                "primary_font": "Arial",
                "secondary_font": "Arial"
            }
        }
        
        with open(self.config_dir / "default" / "branding_config.yaml", "w") as f:
            yaml.dump(branding_config, f)
        
        # Client-specific branding
        client_branding = {
            "colors": {
                "primary_color": "#2E86AB",
                "secondary_color": "#A23B72",
                "accent_color": "#F18F01",
                "text_color": "#2D3436",
                "background_color": "#FFFFFF"
            },
            "typography": {
                "primary_font": "Helvetica",
                "secondary_font": "Georgia"
            }
        }
        
        with open(self.config_dir / "client" / "test_client" / "branding.yaml", "w") as f:
            yaml.dump(client_branding, f)
    
    def test_hydra_manager_initialization(self):
        """Test HydraConfigManager initialization."""
        manager = HydraConfigManager(self.config_dir)
        assert manager.config_dir == self.config_dir
        assert not manager._hydra_initialized
    
    def test_load_user_profile(self):
        """Test loading user profile."""
        with HydraConfigManager(self.config_dir) as manager:
            profile = manager.load_user_profile()
            
            assert isinstance(profile, UserProfile)
            assert profile.username == "testuser"
            assert profile.email == "test@example.com"
            assert profile.full_name == "Test User"
            assert profile.default_output_format == "pptx"
            assert profile.default_dpi == 300
    
    def test_load_branding_config_default(self):
        """Test loading default branding configuration."""
        with HydraConfigManager(self.config_dir) as manager:
            branding = manager.load_branding_config()
            
            assert isinstance(branding, BrandingConfig)
            assert branding.primary_color == "#1f77b4"
            assert branding.secondary_color == "#ff7f0e"
            assert branding.primary_font == "Arial"
    
    def test_load_branding_config_client_specific(self):
        """Test loading client-specific branding configuration."""
        with HydraConfigManager(self.config_dir) as manager:
            branding = manager.load_branding_config("test_client")
            
            assert isinstance(branding, BrandingConfig)
            assert branding.primary_color == "#2E86AB"  # Client-specific
            assert branding.secondary_color == "#A23B72"  # Client-specific
            assert branding.primary_font == "Helvetica"  # Client-specific
            assert branding.text_color == "#2D3436"  # Client-specific
    
    def test_load_config_with_overrides(self):
        """Test loading configuration with overrides."""
        with HydraConfigManager(self.config_dir) as manager:
            config_data = manager.load_config(
                "default/user_profile",
                overrides=["default.default_output_format=pdf"]
            )
            
            assert config_data["default"]["default_output_format"] == "pdf"
    
    def test_config_directory_not_found(self):
        """Test error handling when config directory doesn't exist."""
        non_existent_dir = self.temp_dir / "nonexistent"
        
        with pytest.raises(FileNotFoundError):
            HydraConfigManager(non_existent_dir)
    
    def test_context_manager_cleanup(self):
        """Test that context manager properly cleans up."""
        manager = HydraConfigManager(self.config_dir)
        
        with manager:
            # Load a config to trigger initialization
            manager.load_config("default/user_profile")
            assert manager._hydra_initialized
        
        assert not manager._hydra_initialized


class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_user_profile_validation(self):
        """Test UserProfile validation."""
        # Valid profile
        profile = UserProfile(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            github_login="testuser"
        )
        
        assert profile.username == "testuser"
        assert profile.email == "test@example.com"
        assert profile.default_output_format == "pptx"
    
    def test_user_profile_invalid_email(self):
        """Test UserProfile email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            UserProfile(
                username="testuser",
                email="invalid-email",
                full_name="Test User",
                github_login="testuser"
            )
    
    def test_database_connection_validation(self):
        """Test DatabaseConnection validation."""
        conn = DatabaseConnection(
            name="test_db",
            connection_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="TestPassword123"
        )
        
        assert conn.name == "test_db"
        assert conn.connection_type == "postgresql"
        assert conn.get_connection_string().startswith("postgresql://")
    
    def test_database_connection_weak_password(self):
        """Test DatabaseConnection password validation."""
        with pytest.raises(Exception, match="String should have at least 8 characters"):
            DatabaseConnection(
                name="test_db",
                connection_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="testuser",
                password="123"
            )
    
    def test_branding_config_validation(self):
        """Test BrandingConfig validation."""
        branding = BrandingConfig(
            primary_color="#1f77b4",
            secondary_color="#ff7f0e",
            accent_color="#2ca02c",
            text_color="#000000",
            background_color="#ffffff",
            primary_font="Arial",
            secondary_font="Arial"
        )
        
        assert branding.primary_color == "#1f77b4"
        assert branding.get_color_scheme()["primary"] == "#1f77b4"
    
    def test_branding_config_invalid_color(self):
        """Test BrandingConfig color validation."""
        with pytest.raises(ValueError, match="String should match pattern"):
            BrandingConfig(
                primary_color="red",  # Invalid hex format
                secondary_color="#ff7f0e",
                accent_color="#2ca02c",
                text_color="#000000",
                background_color="#ffffff",
                primary_font="Arial",
                secondary_font="Arial"
            )
    
    def test_social_media_account_validation(self):
        """Test SocialMediaAccount validation."""
        account = SocialMediaAccount(
            platform="facebook",
            account_id="123456789",
            account_name="Test Account",
            access_token="valid_access_token_123456789"
        )
        
        assert account.platform == "facebook"
        assert account.account_id == "123456789"
        assert account.get_auth_headers()["Authorization"] == "Bearer valid_access_token_123456789"
    
    def test_client_profile_validation(self):
        """Test ClientProfile validation."""
        from siege_utilities.config.models import ContactInfo
        
        contact = ContactInfo(email="test@example.com")
        
        profile = ClientProfile(
            client_id="test_client",
            client_name="Test Client",
            client_code="DEMO",  # Changed from TEST (reserved)
            contact_info=contact,
            industry="Technology",
            project_count=0,  # Added required field
            status="active",  # Added required field
            branding_config=BrandingConfig(
                primary_color="#1f77b4",
                secondary_color="#ff7f0e",
                accent_color="#2ca02c",
                text_color="#000000",
                background_color="#ffffff",
                primary_font="Arial",
                secondary_font="Arial"
            ),
            report_preferences=ReportPreferences()
        )
        
        assert profile.client_code == "DEMO"
        assert profile.contact_info.email == "test@example.com"
        assert profile.get_summary()["client_name"] == "Test Client"


class TestMigrationSystem:
    """Test the migration system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.legacy_config_dir = self.temp_dir / "legacy_config"
        self.new_config_dir = self.temp_dir / "new_config"
        
        # Create legacy config structure
        self.legacy_config_dir.mkdir()
        (self.legacy_config_dir / "clients").mkdir()
        
        # Create test legacy user config
        legacy_user_config = {
            "username": "legacy_user",
            "email": "legacy@example.com",
            "full_name": "Legacy User",
            "default_output_format": "pdf"
        }
        
        with open(self.legacy_config_dir / "user_config.yaml", "w") as f:
            yaml.dump(legacy_user_config, f)
        
        # Create test legacy client config
        legacy_client_config = {
            "client_name": "Legacy Client",
            "industry": "Technology",
            "contact_email": "client@example.com",
            "branding": {
                "primary_color": "#FF0000",
                "primary_font": "Times New Roman"
            }
        }
        
        with open(self.legacy_config_dir / "clients" / "legacy_client.yaml", "w") as f:
            yaml.dump(legacy_client_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_migrator_initialization(self):
        """Test ConfigurationMigrator initialization."""
        migrator = ConfigurationMigrator(self.legacy_config_dir, self.new_config_dir)
        
        assert migrator.legacy_config_dir == self.legacy_config_dir
        assert migrator.new_config_dir == self.new_config_dir
    
    def test_migrate_user_profile(self):
        """Test user profile migration."""
        migrator = ConfigurationMigrator(self.legacy_config_dir)
        
        profile = migrator.migrate_user_profile()
        
        assert isinstance(profile, UserProfile)
        assert profile.username == "legacy_user"
        assert profile.email == "legacy@example.com"
        assert profile.full_name == "Legacy User"
        assert profile.default_output_format == "pdf"
    
    def test_migrate_client_profile(self):
        """Test client profile migration."""
        migrator = ConfigurationMigrator(self.legacy_config_dir)
        
        client_file = self.legacy_config_dir / "clients" / "legacy_client.yaml"
        profile = migrator.migrate_client_profile(client_file, "LEGACY")
        
        assert isinstance(profile, ClientProfile)
        assert profile.client_code == "LEGACY"
        assert profile.client_name == "Legacy Client"
        assert profile.contact_info.email == "client@example.com"
        assert profile.branding_config.primary_color == "#FF0000"
        assert profile.branding_config.primary_font == "Times New Roman"
    
    def test_migrate_all_configurations_dry_run(self):
        """Test dry run migration."""
        migrator = ConfigurationMigrator(self.legacy_config_dir)
        
        results = migrator.migrate_all_configurations(dry_run=True)
        
        assert results["dry_run"] is True
        assert results["user_profile"]["migrated"] is False  # Dry run doesn't actually migrate
        assert len(results["client_profiles"]["migrated"]) == 0
        # In dry run, errors are not captured the same way
        assert results["total_migrated"] == 0
    
    def test_backup_legacy_configurations(self):
        """Test backup creation."""
        migrator = ConfigurationMigrator(self.legacy_config_dir)
        
        backup_dir = migrator.backup_legacy_configurations()
        
        assert backup_dir.exists()
        assert (backup_dir / "config").exists()
        assert (backup_dir / "config" / "user_config.yaml").exists()
        assert (backup_dir / "config" / "clients" / "legacy_client.yaml").exists()


class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_complete_workflow(self):
        """Test complete workflow from migration to configuration loading."""
        # This would be a comprehensive test that:
        # 1. Migrates legacy configurations
        # 2. Loads them with HydraConfigManager
        # 3. Validates them with Pydantic
        # 4. Tests client-specific overrides
        
        # For now, we'll test the basic integration
        with HydraConfigManager() as manager:
            # Test that we can load configurations
            user_profile = manager.load_user_profile()
            assert isinstance(user_profile, UserProfile)
            
            # Test that we can load branding configs
            branding = manager.load_branding_config()
            assert isinstance(branding, BrandingConfig)


if __name__ == "__main__":
    pytest.main([__file__])
