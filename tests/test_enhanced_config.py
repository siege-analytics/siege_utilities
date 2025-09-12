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


class TestUserProfile:
    """Test UserProfile Pydantic model."""
    
    def test_user_profile_defaults(self):
        """Test UserProfile with default values."""
        profile = UserProfile()
        
        assert profile.username == ""
        assert profile.email == ""
        assert profile.full_name == ""
        assert profile.preferred_download_directory == Path.home() / "Downloads" / "siege_utilities"
        assert profile.default_output_format == "pdf"
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


class TestClientProfile:
    """Test ClientProfile Pydantic model."""
    
    def test_client_profile_required_fields(self):
        """Test ClientProfile with required fields."""
        profile = ClientProfile(
            client_name="Test Client",
            client_code="TEST"
        )
        
        assert profile.client_name == "Test Client"
        assert profile.client_code == "TEST"
        assert profile.client_id == ""
        assert profile.download_directory is None
        assert profile.data_format == "parquet"
        assert profile.status == "active"
        assert profile.project_count == 0
    
    def test_client_profile_full(self):
        """Test ClientProfile with all fields."""
        profile = ClientProfile(
            client_name="Acme Corp",
            client_code="ACME",
            client_id="acme-001",
            download_directory="/tmp/acme",
            data_format="csv",
            industry="Technology",
            project_count=10,
            status="active",
            contact_info={"email": "contact@acme.com", "phone": "555-0123"},
            brand_colors=["#FF0000", "#00FF00"],
            templates=["template1", "template2"]
        )
        
        assert profile.client_name == "Acme Corp"
        assert profile.client_code == "ACME"
        assert profile.client_id == "acme-001"
        assert str(profile.download_directory) == "/tmp/acme"
        assert profile.data_format == "csv"
        assert profile.industry == "Technology"
        assert profile.project_count == 10
        assert profile.status == "active"
        assert profile.contact_info["email"] == "contact@acme.com"
        assert len(profile.brand_colors) == 2
        assert len(profile.templates) == 2
    
    def test_client_profile_validation(self):
        """Test ClientProfile field validation."""
        # Test invalid data format
        with pytest.raises(ValueError, match="String should match pattern"):
            ClientProfile(
                client_name="Test",
                client_code="TEST",
                data_format="invalid"
            )
        
        # Test invalid status
        with pytest.raises(ValueError, match="String should match pattern"):
            ClientProfile(
                client_name="Test",
                client_code="TEST",
                status="invalid"
            )
        
        # Test negative project count
        with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
            ClientProfile(
                client_name="Test",
                client_code="TEST",
                project_count=-1
            )
    
    def test_client_profile_path_validation(self):
        """Test ClientProfile Path object validation."""
        profile = ClientProfile(
            client_name="Test",
            client_code="TEST",
            download_directory="/tmp/client"
        )
        
        assert isinstance(profile.download_directory, Path)
        assert str(profile.download_directory) == "/tmp/client"


class TestConfigFunctions:
    """Test configuration management functions."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(parents=True)
        yield config_dir
        shutil.rmtree(temp_dir)
    
    def test_load_user_profile_default(self, temp_config_dir):
        """Test loading user profile with defaults."""
        with patch('siege_utilities.config.enhanced_config.Path.home') as mock_home:
            mock_home.return_value = temp_config_dir.parent
            
            profile = load_user_profile(temp_config_dir)
            
            assert isinstance(profile, UserProfile)
            assert profile.username == ""
            assert profile.full_name == ""
            assert profile.preferred_download_directory == Path.home() / "Downloads" / "siege_utilities"
    
    def test_save_and_load_user_profile(self, temp_config_dir):
        """Test saving and loading user profile."""
        # Create a user profile
        original_profile = UserProfile(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            preferred_download_directory="/tmp/test",
            default_output_format="pptx",
            default_dpi=150
        )
        
        # Save the profile
        save_user_profile(original_profile, temp_config_dir)
        
        # Load the profile
        loaded_profile = load_user_profile(temp_config_dir)
        
        # Verify the loaded profile matches the original
        assert loaded_profile.username == "testuser"
        assert loaded_profile.email == "test@example.com"
        assert loaded_profile.full_name == "Test User"
        assert str(loaded_profile.preferred_download_directory) == "/tmp/test"
        assert loaded_profile.default_output_format == "pptx"
        assert loaded_profile.default_dpi == 150
    
    def test_save_and_load_client_profile(self, temp_config_dir):
        """Test saving and loading client profile."""
        # Create a client profile
        original_profile = ClientProfile(
            client_name="Test Client",
            client_code="TEST",
            download_directory="/tmp/client",
            data_format="csv",
            industry="Technology",
            project_count=5
        )
        
        # Save the profile
        save_client_profile(original_profile, temp_config_dir)
        
        # Load the profile
        loaded_profile = load_client_profile("TEST", temp_config_dir)
        
        # Verify the loaded profile matches the original
        assert loaded_profile is not None
        assert loaded_profile.client_name == "Test Client"
        assert loaded_profile.client_code == "TEST"
        assert str(loaded_profile.download_directory) == "/tmp/client"
        assert loaded_profile.data_format == "csv"
        assert loaded_profile.industry == "Technology"
        assert loaded_profile.project_count == 5
    
    def test_load_nonexistent_client_profile(self, temp_config_dir):
        """Test loading a non-existent client profile."""
        profile = load_client_profile("NONEXISTENT", temp_config_dir)
        assert profile is None
    
    def test_list_client_profiles(self, temp_config_dir):
        """Test listing client profiles."""
        # Create multiple client profiles
        clients = [
            ClientProfile(client_name="Client 1", client_code="CLIENT1"),
            ClientProfile(client_name="Client 2", client_code="CLIENT2"),
            ClientProfile(client_name="Client 3", client_code="CLIENT3")
        ]
        
        for client in clients:
            save_client_profile(client, temp_config_dir)
        
        # List profiles
        profile_list = list_client_profiles(temp_config_dir)
        
        assert len(profile_list) == 3
        assert "CLIENT1" in profile_list
        assert "CLIENT2" in profile_list
        assert "CLIENT3" in profile_list
    
    def test_get_download_directory_hierarchy(self, temp_config_dir):
        """Test hierarchical download directory resolution."""
        # Create user profile
        user_profile = UserProfile(
            preferred_download_directory="/tmp/user"
        )
        save_user_profile(user_profile, temp_config_dir)
        
        # Create client profile
        client_profile = ClientProfile(
            client_name="Test Client",
            client_code="TEST",
            download_directory="/tmp/client"
        )
        save_client_profile(client_profile, temp_config_dir)
        
        # Test specific path (highest priority)
        specific_dir = get_download_directory(
            specific_path="/tmp/specific",
            config_dir=temp_config_dir
        )
        assert str(specific_dir) == "/tmp/specific"
        
        # Test client directory
        client_dir = get_download_directory(
            client_code="TEST",
            config_dir=temp_config_dir
        )
        assert str(client_dir) == "/tmp/client"
        
        # Test user directory (fallback)
        user_dir = get_download_directory(config_dir=temp_config_dir)
        assert str(user_dir) == "/tmp/user"
        
        # Test non-existent client (fallback to user)
        fallback_dir = get_download_directory(
            client_code="NONEXISTENT",
            config_dir=temp_config_dir
        )
        assert str(fallback_dir) == "/tmp/user"
    
    def test_export_config_yaml(self, temp_config_dir):
        """Test configuration export to YAML."""
        # Create user profile
        user_profile = UserProfile(
            username="testuser",
            email="test@example.com",
            preferred_download_directory="/tmp/user"
        )
        save_user_profile(user_profile, temp_config_dir)
        
        # Create client profiles
        clients = [
            ClientProfile(
                client_name="Client 1",
                client_code="CLIENT1",
                download_directory="/tmp/client1"
            ),
            ClientProfile(
                client_name="Client 2",
                client_code="CLIENT2",
                download_directory="/tmp/client2"
            )
        ]
        
        for client in clients:
            save_client_profile(client, temp_config_dir)
        
        # Export configuration
        export_path = temp_config_dir / "export.yaml"
        export_config_yaml(str(export_path), include_api_keys=False, config_dir=temp_config_dir)
        
        # Verify export file exists and has content
        assert export_path.exists()
        assert export_path.stat().st_size > 0
        
        # Verify YAML content
        with open(export_path, 'r') as f:
            data = yaml.safe_load(f)
        
        assert 'user' in data
        assert 'clients' in data
        assert data['user']['username'] == "testuser"
        assert data['user']['email'] == "test@example.com"
        assert data['user']['preferred_download_directory'] == "/tmp/user"
        assert 'CLIENT1' in data['clients']
        assert 'CLIENT2' in data['clients']
        assert data['clients']['CLIENT1']['client_name'] == "Client 1"
        assert data['clients']['CLIENT1']['download_directory'] == "/tmp/client1"
    
    def test_import_config_yaml(self, temp_config_dir):
        """Test configuration import from YAML."""
        # Create test YAML data
        test_data = {
            'user': {
                'username': 'importuser',
                'email': 'import@example.com',
                'preferred_download_directory': '/tmp/import_user',
                'default_output_format': 'html',
                'default_dpi': 200
            },
            'clients': {
                'IMPORT_CLIENT': {
                    'client_name': 'Import Client',
                    'client_code': 'IMPORT_CLIENT',
                    'download_directory': '/tmp/import_client',
                    'data_format': 'json',
                    'industry': 'Finance',
                    'project_count': 7
                }
            }
        }
        
        # Write test YAML file
        import_path = temp_config_dir / "import.yaml"
        with open(import_path, 'w') as f:
            yaml.dump(test_data, f, default_flow_style=False)
        
        # Import configuration
        import_config_yaml(str(import_path), config_dir=temp_config_dir)
        
        # Verify user profile was imported
        user_profile = load_user_profile(temp_config_dir)
        assert user_profile.username == "importuser"
        assert user_profile.email == "import@example.com"
        assert str(user_profile.preferred_download_directory) == "/tmp/import_user"
        assert user_profile.default_output_format == "html"
        assert user_profile.default_dpi == 200
        
        # Verify client profile was imported
        client_profile = load_client_profile("IMPORT_CLIENT", temp_config_dir)
        assert client_profile is not None
        assert client_profile.client_name == "Import Client"
        assert client_profile.client_code == "IMPORT_CLIENT"
        assert str(client_profile.download_directory) == "/tmp/import_client"
        assert client_profile.data_format == "json"
        assert client_profile.industry == "Finance"
        assert client_profile.project_count == 7


class TestSiegeConfig:
    """Test SiegeConfig unified configuration container."""
    
    def test_siege_config_default(self):
        """Test SiegeConfig with default values."""
        config = SiegeConfig()
        
        assert isinstance(config.user, UserProfile)
        assert isinstance(config.clients, dict)
        assert len(config.clients) == 0
    
    def test_siege_config_with_data(self):
        """Test SiegeConfig with user and client data."""
        user_profile = UserProfile(username="testuser")
        client_profile = ClientProfile(
            client_name="Test Client",
            client_code="TEST"
        )
        
        config = SiegeConfig(
            user=user_profile,
            clients={"TEST": client_profile}
        )
        
        assert config.user.username == "testuser"
        assert len(config.clients) == 1
        assert "TEST" in config.clients
        assert config.clients["TEST"].client_name == "Test Client"


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
    
    def test_complete_config_workflow(self, temp_config_dir):
        """Test complete configuration workflow."""
        # Step 1: Create and save user profile
        user_profile = UserProfile(
            username="workflowuser",
            email="workflow@example.com",
            full_name="Workflow User",
            preferred_download_directory="/tmp/workflow/user"
        )
        save_user_profile(user_profile, temp_config_dir)
        
        # Step 2: Create and save multiple client profiles
        clients_data = [
            ("Acme Corp", "ACME", "/tmp/workflow/acme", "Technology", 10),
            ("Beta Inc", "BETA", "/tmp/workflow/beta", "Manufacturing", 5),
            ("Gamma LLC", "GAMMA", None, "Finance", 3)  # No specific directory
        ]
        
        for name, code, directory, industry, projects in clients_data:
            client = ClientProfile(
                client_name=name,
                client_code=code,
                download_directory=directory,
                industry=industry,
                project_count=projects
            )
            save_client_profile(client, temp_config_dir)
        
        # Step 3: Test directory resolution for each client
        acme_dir = get_download_directory(client_code="ACME", config_dir=temp_config_dir)
        beta_dir = get_download_directory(client_code="BETA", config_dir=temp_config_dir)
        gamma_dir = get_download_directory(client_code="GAMMA", config_dir=temp_config_dir)
        user_dir = get_download_directory(config_dir=temp_config_dir)
        
        assert str(acme_dir) == "/tmp/workflow/acme"
        assert str(beta_dir) == "/tmp/workflow/beta"
        assert str(gamma_dir) == "/tmp/workflow/user"  # Fallback to user
        assert str(user_dir) == "/tmp/workflow/user"
        
        # Step 4: Export configuration
        export_path = temp_config_dir / "workflow_export.yaml"
        export_config_yaml(str(export_path), include_api_keys=False, config_dir=temp_config_dir)
        
        # Step 5: Verify export contains all data
        with open(export_path, 'r') as f:
            exported_data = yaml.safe_load(f)
        
        assert exported_data['user']['username'] == "workflowuser"
        assert len(exported_data['clients']) == 3
        assert exported_data['clients']['ACME']['industry'] == "Technology"
        assert exported_data['clients']['BETA']['industry'] == "Manufacturing"
        assert exported_data['clients']['GAMMA']['industry'] == "Finance"
        
        # Step 6: Test import into new config directory
        new_config_dir = temp_config_dir.parent / "new_config"
        new_config_dir.mkdir()
        
        import_config_yaml(str(export_path), config_dir=new_config_dir)
        
        # Step 7: Verify imported data
        imported_user = load_user_profile(new_config_dir)
        assert imported_user.username == "workflowuser"
        
        imported_clients = list_client_profiles(new_config_dir)
        assert len(imported_clients) == 3
        assert "ACME" in imported_clients
        assert "BETA" in imported_clients
        assert "GAMMA" in imported_clients
        
        # Clean up
        shutil.rmtree(new_config_dir)


class TestConfigErrorHandling:
    """Test error handling in configuration system."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory for testing."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(parents=True)
        yield config_dir
        shutil.rmtree(temp_dir)
    
    def test_invalid_yaml_handling(self, temp_config_dir):
        """Test handling of invalid YAML files."""
        # Create invalid YAML file
        invalid_file = temp_config_dir / "user_config.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should not crash, should use defaults
        profile = load_user_profile(temp_config_dir)
        assert isinstance(profile, UserProfile)
        assert profile.username == ""  # Default value
    
    def test_missing_config_directory(self, temp_config_dir):
        """Test handling of missing configuration directory."""
        # Remove config directory
        shutil.rmtree(temp_config_dir)
        
        # Should create directory and use defaults
        profile = load_user_profile(temp_config_dir)
        assert isinstance(profile, UserProfile)
        assert temp_config_dir.exists()
    
    def test_permission_errors(self, temp_config_dir):
        """Test handling of permission errors."""
        # Make directory read-only
        temp_config_dir.chmod(0o444)
        
        try:
            # Should handle permission error gracefully
            with pytest.raises(PermissionError):
                save_user_profile(UserProfile(username="test"), temp_config_dir)
        finally:
            # Restore permissions for cleanup
            temp_config_dir.chmod(0o755)
