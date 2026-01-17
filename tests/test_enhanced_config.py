"""
Comprehensive unit tests for the enhanced configuration system with Pydantic validation.
"""

import pytest

pytestmark = pytest.mark.config
import tempfile
import yaml
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open
from typing import Dict, Any

# Import the enhanced config system
from siege_utilities.config.enhanced_config import (
    UserProfile, ClientProfile, SiegeConfig,
    load_user_profile, save_user_profile,
    load_client_profile, save_client_profile,
    list_client_profiles, get_download_directory,
    export_config_yaml, import_config_yaml
)
from siege_utilities.config.models import (
    ContactInfo, BrandingConfig, ReportPreferences
)


# ============================================================================
# Helper functions for creating valid test fixtures
# ============================================================================

def create_valid_contact_info(**kwargs) -> ContactInfo:
    """Create a valid ContactInfo instance for testing."""
    defaults = {
        "email": "test@example.com",
        "phone": "1234567890",
        "address": "123 Test Street",
        "website": "https://example.com",
    }
    defaults.update(kwargs)
    return ContactInfo(**defaults)


def create_valid_branding_config(**kwargs) -> BrandingConfig:
    """Create a valid BrandingConfig instance for testing."""
    defaults = {
        "primary_color": "#1f77b4",
        "secondary_color": "#ff7f0e",
        "accent_color": "#2ca02c",
        "text_color": "#000000",
        "background_color": "#ffffff",
        "primary_font": "Arial",
        "secondary_font": "Helvetica",
    }
    defaults.update(kwargs)
    return BrandingConfig(**defaults)


def create_valid_report_preferences(**kwargs) -> ReportPreferences:
    """Create a valid ReportPreferences instance for testing."""
    return ReportPreferences(**kwargs)


def create_valid_client_profile(**kwargs) -> ClientProfile:
    """Create a valid ClientProfile instance for testing."""
    defaults = {
        "client_id": "testclient",
        "client_name": "Test Client",
        "client_code": "TSTCLT",  # Not reserved (TEST is reserved)
        "contact_info": create_valid_contact_info(),
        "industry": "Technology",
        "project_count": 5,
        "status": "active",
        "branding_config": create_valid_branding_config(),
        "report_preferences": create_valid_report_preferences(),
    }
    defaults.update(kwargs)
    return ClientProfile(**defaults)


# ============================================================================
# UserProfile Tests
# ============================================================================

class TestUserProfile:
    """Test UserProfile Pydantic model."""

    def test_user_profile_defaults(self):
        """Test UserProfile with default values."""
        profile = UserProfile()

        assert profile.username == ""
        assert profile.email == ""
        assert profile.full_name == ""
        assert profile.preferred_download_directory == Path.home() / "Downloads" / "siege_utilities"
        assert profile.default_output_format == "pptx"  # Fixed: model defaults to pptx
        assert profile.default_dpi == 300
        assert profile.enable_logging is True
        assert profile.log_level == "INFO"

    def test_user_profile_validation(self):
        """Test UserProfile field validation."""
        # Test valid values
        profile = UserProfile(
            username="testuser",
            email="test@example.com",
            default_output_format="pptx",
            default_dpi=150,
            log_level="DEBUG"
        )

        assert profile.username == "testuser"
        assert profile.email == "test@example.com"
        assert profile.default_output_format == "pptx"
        assert profile.default_dpi == 150
        assert profile.log_level == "DEBUG"

    def test_user_profile_invalid_values(self):
        """Test UserProfile validation with invalid values."""
        # Test invalid output format
        with pytest.raises(ValueError, match="String should match pattern"):
            UserProfile(default_output_format="invalid")

        # Test invalid DPI
        with pytest.raises(ValueError, match="Input should be greater than or equal to 72"):
            UserProfile(default_dpi=50)

        with pytest.raises(ValueError, match="Input should be less than or equal to 600"):
            UserProfile(default_dpi=800)

        # Test invalid log level
        with pytest.raises(ValueError, match="String should match pattern"):
            UserProfile(log_level="INVALID")

    def test_user_profile_path_validation(self):
        """Test UserProfile Path object validation."""
        profile = UserProfile(preferred_download_directory="/tmp/test")

        assert isinstance(profile.preferred_download_directory, Path)
        assert str(profile.preferred_download_directory) == "/tmp/test"


# ============================================================================
# ClientProfile Tests (Rewritten for current API)
# ============================================================================

class TestClientProfile:
    """Test ClientProfile Pydantic model with required nested types."""

    def test_client_profile_with_all_required_fields(self):
        """Test ClientProfile with all required fields."""
        profile = create_valid_client_profile()

        assert profile.client_id == "testclient"
        assert profile.client_name == "Test Client"
        assert profile.client_code == "TSTCLT"
        assert profile.industry == "Technology"
        assert profile.project_count == 5
        assert profile.status == "active"
        assert isinstance(profile.contact_info, ContactInfo)
        assert isinstance(profile.branding_config, BrandingConfig)
        assert isinstance(profile.report_preferences, ReportPreferences)

    def test_client_profile_contact_info_validation(self):
        """Test ClientProfile with contact info validation."""
        profile = create_valid_client_profile()

        assert profile.contact_info.email == "test@example.com"
        assert profile.contact_info.phone == "1234567890"
        assert profile.contact_info.website == "https://example.com"

    def test_client_profile_branding_config_validation(self):
        """Test ClientProfile with branding config."""
        profile = create_valid_client_profile()

        assert profile.branding_config.primary_color == "#1f77b4"
        assert profile.branding_config.secondary_color == "#ff7f0e"
        assert profile.branding_config.primary_font == "Arial"

    def test_client_profile_reserved_code_validation(self):
        """Test that reserved client codes are rejected."""
        reserved_codes = ["TEST", "DEFAULT", "ADMIN", "SYSTEM"]

        for reserved_code in reserved_codes:
            with pytest.raises(ValueError, match="reserved"):
                create_valid_client_profile(client_code=reserved_code)

    def test_client_profile_status_validation(self):
        """Test ClientProfile status field validation."""
        # Valid statuses
        for status in ["active", "inactive", "archived"]:
            profile = create_valid_client_profile(status=status)
            assert profile.status == status

        # Invalid status
        with pytest.raises(ValueError, match="String should match pattern"):
            create_valid_client_profile(status="invalid")

    def test_client_profile_client_code_uppercase(self):
        """Test that client code must be uppercase."""
        with pytest.raises(ValueError, match="pattern"):
            create_valid_client_profile(client_code="lowercase")

    def test_client_profile_project_count_validation(self):
        """Test project count must be non-negative."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            create_valid_client_profile(project_count=-1)

    def test_client_profile_summary_method(self):
        """Test ClientProfile get_summary method."""
        profile = create_valid_client_profile()
        summary = profile.get_summary()

        assert summary["client_id"] == "testclient"
        assert summary["client_name"] == "Test Client"
        assert summary["client_code"] == "TSTCLT"
        assert summary["industry"] == "Technology"
        assert summary["status"] == "active"
        assert summary["project_count"] == 5


# ============================================================================
# Config Functions Tests (Rewritten for current API)
# ============================================================================

class TestConfigFunctions:
    """Test configuration management functions with current API signatures.

    Current signatures:
    - load_user_profile(username: str, config_dir) -> Optional[UserProfile]
    - save_user_profile(profile, username, config_dir) -> bool
    - load_client_profile(client_code: str, config_dir) -> Optional[ClientProfile]
    - save_client_profile(profile: ClientProfile, config_dir) -> bool
    """

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(parents=True)
        yield config_dir
        shutil.rmtree(temp_dir)

    def test_load_nonexistent_user_profile(self, temp_config_dir):
        """Test loading user profile that doesn't exist returns None."""
        profile = load_user_profile("nonexistent_user", temp_config_dir)
        assert profile is None

    def test_save_and_load_user_profile(self, temp_config_dir):
        """Test saving and loading user profile with username parameter."""
        # Create a user profile
        original_profile = UserProfile(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            preferred_download_directory="/tmp/test",
            default_output_format="pptx",
            default_dpi=150
        )

        # Save the profile with username
        result = save_user_profile(original_profile, "testuser", temp_config_dir)
        assert result is True

        # Load the profile by username
        loaded_profile = load_user_profile("testuser", temp_config_dir)

        # Verify the loaded profile matches the original
        assert loaded_profile is not None
        assert loaded_profile.username == "testuser"
        assert loaded_profile.email == "test@example.com"
        assert loaded_profile.full_name == "Test User"
        assert str(loaded_profile.preferred_download_directory) == "/tmp/test"
        assert loaded_profile.default_output_format == "pptx"
        assert loaded_profile.default_dpi == 150

    def test_save_and_load_client_profile(self, temp_config_dir):
        """Test saving and loading client profile with current model."""
        # Create a client profile with all required fields
        original_profile = create_valid_client_profile(
            client_id="acme",
            client_name="Acme Corporation",
            client_code="ACME01",
            industry="Manufacturing",
            project_count=10
        )

        # Save the profile
        result = save_client_profile(original_profile, temp_config_dir)
        assert result is True

        # Load the profile
        loaded_profile = load_client_profile("ACME01", temp_config_dir)

        # Verify the loaded profile matches the original
        assert loaded_profile is not None
        assert loaded_profile.client_name == "Acme Corporation"
        assert loaded_profile.client_code == "ACME01"
        assert loaded_profile.industry == "Manufacturing"
        assert loaded_profile.project_count == 10

    def test_load_nonexistent_client_profile(self, temp_config_dir):
        """Test loading a non-existent client profile."""
        profile = load_client_profile("NONEXISTENT", temp_config_dir)
        assert profile is None

    def test_list_client_profiles(self, temp_config_dir):
        """Test listing client profiles."""
        # Create multiple client profiles
        clients = [
            create_valid_client_profile(client_id="client1", client_name="Client 1", client_code="CLIENT1"),
            create_valid_client_profile(client_id="client2", client_name="Client 2", client_code="CLIENT2"),
            create_valid_client_profile(client_id="client3", client_name="Client 3", client_code="CLIENT3"),
        ]

        for client in clients:
            save_client_profile(client, temp_config_dir)

        # List profiles
        profile_list = list_client_profiles(temp_config_dir)

        assert len(profile_list) == 3
        assert "CLIENT1" in profile_list
        assert "CLIENT2" in profile_list
        assert "CLIENT3" in profile_list

    def test_list_client_profiles_empty(self, temp_config_dir):
        """Test listing client profiles when directory is empty."""
        profile_list = list_client_profiles(temp_config_dir)
        assert profile_list == []

    def test_get_download_directory(self, temp_config_dir):
        """Test get_download_directory function with username."""
        # Create and save user profile with custom download directory
        user_profile = UserProfile(
            username="testuser",
            preferred_download_directory="/tmp/custom_downloads"
        )
        save_user_profile(user_profile, "testuser", temp_config_dir)

        # Get download directory for user
        download_dir = get_download_directory("testuser", temp_config_dir)

        assert str(download_dir) == "/tmp/custom_downloads"

    def test_get_download_directory_nonexistent_user(self, temp_config_dir):
        """Test get_download_directory for non-existent user returns default."""
        download_dir = get_download_directory("nonexistent", temp_config_dir)

        # Should return default fallback
        assert "siege_utilities" in str(download_dir)

    def test_export_config_yaml(self, temp_config_dir):
        """Test configuration export to YAML file."""
        # Create test data
        config_data = {
            "user": {
                "username": "exportuser",
                "email": "export@example.com"
            },
            "settings": {
                "theme": "dark"
            }
        }

        # Export to file
        export_path = temp_config_dir / "export.yaml"
        result = export_config_yaml(config_data, export_path)

        assert result is True
        assert export_path.exists()

        # Verify content
        with open(export_path, 'r') as f:
            loaded_data = yaml.safe_load(f)

        assert loaded_data["user"]["username"] == "exportuser"
        assert loaded_data["settings"]["theme"] == "dark"

    def test_import_config_yaml(self, temp_config_dir):
        """Test configuration import from YAML file."""
        # Create test YAML data
        test_data = {
            "user": {
                "username": "importuser",
                "email": "import@example.com"
            },
            "clients": {
                "IMPORTCLT": {
                    "client_name": "Import Client"
                }
            }
        }

        # Write test YAML file
        import_path = temp_config_dir / "import.yaml"
        with open(import_path, 'w') as f:
            yaml.dump(test_data, f, default_flow_style=False)

        # Import configuration
        imported_data = import_config_yaml(import_path)

        assert imported_data is not None
        assert imported_data["user"]["username"] == "importuser"
        assert imported_data["clients"]["IMPORTCLT"]["client_name"] == "Import Client"

    def test_import_config_yaml_nonexistent_file(self, temp_config_dir):
        """Test importing from non-existent file returns None."""
        nonexistent_path = temp_config_dir / "nonexistent.yaml"
        result = import_config_yaml(nonexistent_path)
        assert result is None


# ============================================================================
# SiegeConfig Tests (Rewritten for current API)
# ============================================================================

class TestSiegeConfig:
    """Test SiegeConfig class for unified configuration management.

    Current API:
    - __init__(config_dir: Optional[Path] = None)
    - get_user_profile(username: str) -> Optional[UserProfile]
    - get_client_profile(client_code: str) -> Optional[ClientProfile]
    - save_user_profile(profile: UserProfile, username: str) -> bool
    - save_client_profile(profile: ClientProfile) -> bool
    """

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(parents=True)
        yield config_dir
        shutil.rmtree(temp_dir)

    def test_siege_config_initialization(self, temp_config_dir):
        """Test SiegeConfig initialization."""
        config = SiegeConfig(config_dir=temp_config_dir)

        assert config.config_dir == temp_config_dir
        assert config.config_dir.exists()

    def test_siege_config_default_initialization(self):
        """Test SiegeConfig with default config directory."""
        config = SiegeConfig()

        # Should create config directory in home
        assert "siege_utilities" in str(config.config_dir)

    def test_siege_config_save_and_get_user_profile(self, temp_config_dir):
        """Test saving and getting user profile via SiegeConfig."""
        config = SiegeConfig(config_dir=temp_config_dir)

        # Create and save user profile
        user_profile = UserProfile(
            username="siegeuser",
            email="siege@example.com",
            full_name="Siege User"
        )
        result = config.save_user_profile(user_profile, "siegeuser")
        assert result is True

        # Get the user profile back
        loaded_profile = config.get_user_profile("siegeuser")
        assert loaded_profile is not None
        assert loaded_profile.username == "siegeuser"
        assert loaded_profile.email == "siege@example.com"

    def test_siege_config_get_nonexistent_user_profile(self, temp_config_dir):
        """Test getting non-existent user profile."""
        config = SiegeConfig(config_dir=temp_config_dir)

        profile = config.get_user_profile("nonexistent")
        assert profile is None

    def test_siege_config_save_and_get_client_profile(self, temp_config_dir):
        """Test saving and getting client profile via SiegeConfig."""
        config = SiegeConfig(config_dir=temp_config_dir)

        # Create and save client profile
        client_profile = create_valid_client_profile(
            client_id="siegeclient",
            client_name="Siege Client",
            client_code="SIEGE01"
        )
        result = config.save_client_profile(client_profile)
        assert result is True

        # Get the client profile back
        loaded_profile = config.get_client_profile("SIEGE01")
        assert loaded_profile is not None
        assert loaded_profile.client_name == "Siege Client"
        assert loaded_profile.client_code == "SIEGE01"

    def test_siege_config_get_nonexistent_client_profile(self, temp_config_dir):
        """Test getting non-existent client profile."""
        config = SiegeConfig(config_dir=temp_config_dir)

        profile = config.get_client_profile("NONEXISTENT")
        assert profile is None


# ============================================================================
# Config Integration Tests (Rewritten for current API)
# ============================================================================

class TestConfigIntegration:
    """Integration tests for the complete config system."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(parents=True)
        yield config_dir
        shutil.rmtree(temp_dir)

    def test_complete_user_workflow(self, temp_config_dir):
        """Test complete user profile workflow: create, save, load, update."""
        # Step 1: Create and save user profile
        user_profile = UserProfile(
            username="workflowuser",
            email="workflow@example.com",
            full_name="Workflow User",
            preferred_download_directory="/tmp/workflow/user"
        )
        result = save_user_profile(user_profile, "workflowuser", temp_config_dir)
        assert result is True

        # Step 2: Load the profile
        loaded_profile = load_user_profile("workflowuser", temp_config_dir)
        assert loaded_profile is not None
        assert loaded_profile.username == "workflowuser"
        assert loaded_profile.email == "workflow@example.com"

        # Step 3: Update and resave
        loaded_profile = UserProfile(
            username="workflowuser",
            email="updated@example.com",
            full_name="Updated User",
            preferred_download_directory="/tmp/workflow/updated"
        )
        result = save_user_profile(loaded_profile, "workflowuser", temp_config_dir)
        assert result is True

        # Step 4: Verify update
        updated_profile = load_user_profile("workflowuser", temp_config_dir)
        assert updated_profile.email == "updated@example.com"
        assert updated_profile.full_name == "Updated User"

    def test_complete_client_workflow(self, temp_config_dir):
        """Test complete client profile workflow with multiple clients."""
        # Step 1: Create and save multiple client profiles
        clients_data = [
            ("acme", "Acme Corp", "ACME01", "Technology", 10),
            ("beta", "Beta Inc", "BETA01", "Manufacturing", 5),
            ("gamma", "Gamma LLC", "GAMMA1", "Finance", 3),
        ]

        for client_id, name, code, industry, projects in clients_data:
            client = create_valid_client_profile(
                client_id=client_id,
                client_name=name,
                client_code=code,
                industry=industry,
                project_count=projects
            )
            save_client_profile(client, temp_config_dir)

        # Step 2: List all clients
        client_list = list_client_profiles(temp_config_dir)
        assert len(client_list) == 3
        assert "ACME01" in client_list
        assert "BETA01" in client_list
        assert "GAMMA1" in client_list

        # Step 3: Load and verify each client
        acme = load_client_profile("ACME01", temp_config_dir)
        assert acme.client_name == "Acme Corp"
        assert acme.industry == "Technology"
        assert acme.project_count == 10

        beta = load_client_profile("BETA01", temp_config_dir)
        assert beta.client_name == "Beta Inc"
        assert beta.industry == "Manufacturing"

    def test_siege_config_integration(self, temp_config_dir):
        """Test SiegeConfig class for unified config management."""
        config = SiegeConfig(config_dir=temp_config_dir)

        # Save user profile
        user = UserProfile(username="integration_user", email="integration@test.com")
        config.save_user_profile(user, "integration_user")

        # Save client profile
        client = create_valid_client_profile(
            client_id="intclient",
            client_name="Integration Client",
            client_code="INTCLT"
        )
        config.save_client_profile(client)

        # Verify both can be retrieved
        loaded_user = config.get_user_profile("integration_user")
        loaded_client = config.get_client_profile("INTCLT")

        assert loaded_user is not None
        assert loaded_user.username == "integration_user"
        assert loaded_client is not None
        assert loaded_client.client_name == "Integration Client"

    def test_export_and_import_roundtrip(self, temp_config_dir):
        """Test that exported config can be imported back."""
        # Create test data
        test_data = {
            "user": {
                "username": "roundtrip_user",
                "email": "roundtrip@example.com"
            },
            "clients": {
                "ROUND01": {
                    "client_name": "Roundtrip Client"
                }
            }
        }

        # Export
        export_path = temp_config_dir / "roundtrip.yaml"
        export_result = export_config_yaml(test_data, export_path)
        assert export_result is True

        # Import
        imported = import_config_yaml(export_path)
        assert imported is not None
        assert imported["user"]["username"] == "roundtrip_user"
        assert imported["clients"]["ROUND01"]["client_name"] == "Roundtrip Client"


# ============================================================================
# Config Error Handling Tests (Rewritten for current API)
# ============================================================================

class TestConfigErrorHandling:
    """Test error handling in configuration system."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(parents=True)
        yield config_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_load_nonexistent_user_returns_none(self, temp_config_dir):
        """Test that loading non-existent user returns None gracefully."""
        # Should not crash, should return None
        profile = load_user_profile("nonexistent_user", temp_config_dir)
        assert profile is None

    def test_load_nonexistent_client_returns_none(self, temp_config_dir):
        """Test that loading non-existent client returns None gracefully."""
        profile = load_client_profile("NONEXISTENT", temp_config_dir)
        assert profile is None

    def test_invalid_yaml_handling(self, temp_config_dir):
        """Test handling of invalid YAML files."""
        # Create the user directory
        user_dir = temp_config_dir
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create invalid YAML file
        invalid_file = user_dir / "baduser.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [")

        # Should not crash, should return None
        profile = load_user_profile("baduser", temp_config_dir)
        assert profile is None

    def test_list_profiles_empty_directory(self, temp_config_dir):
        """Test listing profiles in empty directory returns empty list."""
        profiles = list_client_profiles(temp_config_dir)
        assert profiles == []

    def test_list_profiles_nonexistent_directory(self, temp_config_dir):
        """Test listing profiles in non-existent directory returns empty list."""
        nonexistent = temp_config_dir / "nonexistent"
        profiles = list_client_profiles(nonexistent)
        assert profiles == []

    def test_import_nonexistent_yaml(self, temp_config_dir):
        """Test importing non-existent YAML file returns None."""
        result = import_config_yaml(temp_config_dir / "nonexistent.yaml")
        assert result is None

    def test_export_creates_parent_directories(self, temp_config_dir):
        """Test that export creates parent directories if needed."""
        deep_path = temp_config_dir / "deep" / "nested" / "export.yaml"
        result = export_config_yaml({"test": "data"}, deep_path)
        assert result is True
        assert deep_path.exists()

    def test_client_profile_validation_errors(self):
        """Test that invalid client profile data raises appropriate errors."""
        # Invalid client code (lowercase) - pattern match error
        with pytest.raises(ValueError, match="pattern"):
            create_valid_client_profile(client_code="lowercase")

        # Reserved client code
        with pytest.raises(ValueError, match="reserved"):
            create_valid_client_profile(client_code="TEST")

        # Invalid status
        with pytest.raises(ValueError, match="pattern"):
            create_valid_client_profile(status="invalid_status")

        # Negative project count
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            create_valid_client_profile(project_count=-5)

    def test_user_profile_validation_errors(self):
        """Test that invalid user profile data raises appropriate errors."""
        # Invalid DPI
        with pytest.raises(ValueError):
            UserProfile(default_dpi=10)  # Too low

        with pytest.raises(ValueError):
            UserProfile(default_dpi=1000)  # Too high

        # Invalid log level
        with pytest.raises(ValueError):
            UserProfile(log_level="INVALID_LEVEL")

        # Invalid output format
        with pytest.raises(ValueError):
            UserProfile(default_output_format="invalid_format")
