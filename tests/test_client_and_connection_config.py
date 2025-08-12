"""
Tests for client and connection configuration functionality.
"""

import pytest
import tempfile
import pathlib
import json
from unittest.mock import patch, MagicMock

# Import the functions to test
from siege_utilities.config.clients import (
    create_client_profile, save_client_profile, load_client_profile,
    update_client_profile, list_client_profiles, search_client_profiles,
    associate_client_with_project, get_client_project_associations, validate_client_profile
)

from siege_utilities.config.connections import (
    create_connection_profile, save_connection_profile, load_connection_profile,
    find_connection_by_name, list_connection_profiles, update_connection_profile,
    test_connection, get_connection_status, cleanup_old_connections
)


class TestClientConfiguration:
    """Test client profile management functionality."""
    
    def test_create_client_profile_basic(self):
        """Test creating a basic client profile."""
        contact_info = {
            "primary_contact": "John Doe",
            "email": "john@example.com"
        }
        
        profile = create_client_profile("Test Client", "TEST001", contact_info)
        
        assert profile['client_name'] == "Test Client"
        assert profile['client_code'] == "TEST001"
        assert profile['contact_info'] == contact_info
        assert profile['metadata']['status'] == 'active'
        assert 'client_id' in profile
        assert profile['metadata']['created_date']
    
    def test_create_client_profile_with_optional_fields(self):
        """Test creating a client profile with optional fields."""
        contact_info = {
            "primary_contact": "Jane Smith",
            "email": "jane@example.com",
            "phone": "+1-555-0123"
        }
        
        profile = create_client_profile(
            "Premium Client", 
            "PREMIUM001", 
            contact_info,
            industry="Technology",
            project_count=10,
            logo_path="/path/to/logo.png",
            brand_colors=["#FF0000", "#00FF00"]
        )
        
        assert profile['metadata']['industry'] == "Technology"
        assert profile['metadata']['project_count'] == 10
        assert profile['design_artifacts']['logo_path'] == "/path/to/logo.png"
        assert profile['design_artifacts']['brand_colors'] == ["#FF0000", "#00FF00"]
    
    def test_create_client_profile_missing_required_fields(self):
        """Test that creating a profile with missing required fields raises an error."""
        contact_info = {"primary_contact": "John Doe"}  # Missing email
        
        with pytest.raises(ValueError, match="Missing required contact fields"):
            create_client_profile("Test Client", "TEST001", contact_info)
    
    def test_save_and_load_client_profile(self, tmp_path):
        """Test saving and loading a client profile."""
        contact_info = {
            "primary_contact": "Test User",
            "email": "test@example.com"
        }
        
        profile = create_client_profile("Test Client", "TEST001", contact_info)
        config_dir = tmp_path / "config"
        
        # Save profile
        saved_path = save_client_profile(profile, str(config_dir))
        assert pathlib.Path(saved_path).exists()
        
        # Load profile
        loaded_profile = load_client_profile(profile['client_code'], str(config_dir))
        assert loaded_profile is not None
        assert loaded_profile['client_name'] == profile['client_name']
        assert loaded_profile['contact_info'] == profile['contact_info']
    
    def test_update_client_profile(self, tmp_path):
        """Test updating a client profile."""
        contact_info = {
            "primary_contact": "Test User",
            "email": "test@example.com"
        }
        
        profile = create_client_profile("Test Client", "TEST001", contact_info)
        config_dir = tmp_path / "config"
        save_client_profile(profile, str(config_dir))
        
        # Update profile
        updates = {
            "contact_info": {"phone": "+1-555-9999"},
            "metadata": {"project_count": 5}
        }
        
        success = update_client_profile(profile['client_code'], updates, str(config_dir))
        assert success is True
        
        # Verify updates
        updated_profile = load_client_profile(profile['client_code'], str(config_dir))
        assert updated_profile['contact_info']['phone'] == "+1-555-9999"
        assert updated_profile['metadata']['project_count'] == 5
    
    def test_list_client_profiles(self, tmp_path):
        """Test listing client profiles."""
        config_dir = tmp_path / "config"
        
        # Create multiple profiles
        profiles = []
        for i in range(3):
            contact_info = {
                "primary_contact": f"User {i}",
                "email": f"user{i}@example.com"
            }
            profile = create_client_profile(f"Client {i}", f"CLIENT{i:03d}", contact_info)
            save_client_profile(profile, str(config_dir))
            profiles.append(profile)
        
        # List profiles
        client_list = list_client_profiles(str(config_dir))
        assert len(client_list) == 3
        
        # Check that all profiles are listed
        client_codes = [client['code'] for client in client_list]
        expected_codes = [profile['client_code'] for profile in profiles]
        assert set(client_codes) == set(expected_codes)
    
    def test_search_client_profiles(self, tmp_path):
        """Test searching client profiles."""
        config_dir = tmp_path / "config"
        
        # Create profiles with different industries
        contact_info = {"primary_contact": "Test", "email": "test@example.com"}
        
        tech_client = create_client_profile("Tech Corp", "TECH001", contact_info, industry="Technology")
        finance_client = create_client_profile("Finance Inc", "FIN001", contact_info, industry="Finance")
        
        save_client_profile(tech_client, str(config_dir))
        save_client_profile(finance_client, str(config_dir))
        
        # Search by industry
        tech_results = search_client_profiles("Technology", ["metadata.industry"], str(config_dir))
        assert len(tech_results) == 1
        assert tech_results[0]['client_name'] == "Tech Corp"
        
        # Search by name
        name_results = search_client_profiles("Tech", ["client_name"], str(config_dir))
        assert len(name_results) == 1
        assert name_results[0]['client_name'] == "Tech Corp"
    
    def test_validate_client_profile(self):
        """Test client profile validation."""
        # Valid profile
        contact_info = {
            "primary_contact": "Test User",
            "email": "test@example.com"
        }
        valid_profile = create_client_profile("Test Client", "TEST001", contact_info)
        
        validation = validate_client_profile(valid_profile)
        assert validation['is_valid'] is True
        assert len(validation['issues']) == 0
        
        # Invalid profile (missing email)
        invalid_profile = create_client_profile("Test Client", "TEST001", {"primary_contact": "Test User"})
        invalid_profile['contact_info'].pop('email')
        
        validation = validate_client_profile(invalid_profile)
        assert validation['is_valid'] is False
        assert len(validation['issues']) > 0


class TestConnectionConfiguration:
    """Test connection profile management functionality."""
    
    def test_create_connection_profile_notebook(self):
        """Test creating a notebook connection profile."""
        connection_params = {
            "url": "http://localhost:8888",
            "token": "abc123",
            "workspace": "/home/user/notebooks"
        }
        
        profile = create_connection_profile(
            "Jupyter Lab", 
            "notebook", 
            connection_params,
            auto_connect=True,
            kernel_type="python3"
        )
        
        assert profile['name'] == "Jupyter Lab"
        assert profile['connection_type'] == "notebook"
        assert profile['connection_params'] == connection_params
        assert profile['metadata']['auto_connect'] is True
        assert profile['notebook_specific']['kernel_type'] == "python3"
        assert 'connection_id' in profile
    
    def test_create_connection_profile_spark(self):
        """Test creating a Spark connection profile."""
        connection_params = {
            "master_url": "spark://localhost:7077",
            "app_name": "TestApp"
        }
        
        profile = create_connection_profile(
            "Spark Cluster", 
            "spark", 
            connection_params,
            driver_memory="4g",
            executor_memory="2g"
        )
        
        assert profile['connection_type'] == "spark"
        assert profile['spark_specific']['driver_memory'] == "4g"
        assert profile['spark_specific']['executor_memory'] == "2g"
    
    def test_create_connection_profile_database(self):
        """Test creating a database connection profile."""
        connection_params = {
            "connection_string": "postgresql://user:pass@localhost:5432/db"
        }
        
        profile = create_connection_profile(
            "PostgreSQL DB", 
            "database", 
            connection_params,
            connection_pool_size=10,
            ssl_mode="require"
        )
        
        assert profile['connection_type'] == "database"
        assert profile['database_specific']['connection_pool_size'] == 10
        assert profile['database_specific']['ssl_mode'] == "require"
    
    def test_save_and_load_connection_profile(self, tmp_path):
        """Test saving and loading a connection profile."""
        connection_params = {"url": "http://test.com"}
        profile = create_connection_profile("Test Connection", "notebook", connection_params)
        
        config_dir = tmp_path / "config"
        saved_path = save_connection_profile(profile, str(config_dir))
        
        # Verify connections subdirectory was created
        connections_dir = pathlib.Path(config_dir) / "connections"
        assert connections_dir.exists()
        
        # Load profile
        loaded_profile = load_connection_profile(profile['connection_id'], str(config_dir))
        assert loaded_profile is not None
        assert loaded_profile['name'] == profile['name']
    
    def test_find_connection_by_name(self, tmp_path):
        """Test finding a connection by name."""
        config_dir = tmp_path / "config"
        
        connection_params = {"url": "http://test.com"}
        profile = create_connection_profile("My Connection", "notebook", connection_params)
        save_connection_profile(profile, str(config_dir))
        
        # Find by name
        found_profile = find_connection_by_name("My Connection", str(config_dir))
        assert found_profile is not None
        assert found_profile['connection_id'] == profile['connection_id']
        
        # Search for non-existent connection
        not_found = find_connection_by_name("Non-existent", str(config_dir))
        assert not_found is None
    
    def test_list_connection_profiles(self, tmp_path):
        """Test listing connection profiles."""
        config_dir = tmp_path / "config"
        
        # Create profiles of different types
        notebook_params = {"url": "http://notebook.com"}
        spark_params = {"master_url": "spark://localhost:7077"}
        
        notebook_profile = create_connection_profile("Notebook", "notebook", notebook_params)
        spark_profile = create_connection_profile("Spark", "spark", spark_params)
        
        save_connection_profile(notebook_profile, str(config_dir))
        save_connection_profile(spark_profile, str(config_dir))
        
        # List all connections
        all_connections = list_connection_profiles(config_directory=str(config_dir))
        assert len(all_connections) == 2
        
        # List only notebook connections
        notebook_connections = list_connection_profiles("notebook", str(config_dir))
        assert len(notebook_connections) == 1
        assert notebook_connections[0]['type'] == "notebook"
    
    @patch('requests.get')
    def test_test_connection_notebook(self, mock_get, tmp_path):
        """Test testing a notebook connection."""
        config_dir = tmp_path / "config"
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        connection_params = {"url": "http://localhost:8888", "token": "abc123"}
        profile = create_connection_profile("Test Notebook", "notebook", connection_params)
        save_connection_profile(profile, str(config_dir))
        
        # Test connection
        result = test_connection(profile['connection_id'], str(config_dir))
        assert result['success'] is True
        assert result['connection_type'] == "notebook"
        assert result['response_time_ms'] is not None
    
    @patch('pyspark.sql.SparkSession')
    def test_test_connection_spark(self, mock_spark_session, tmp_path):
        """Test testing a Spark connection."""
        config_dir = tmp_path / "config"
        
        # Mock Spark session
        mock_spark = MagicMock()
        mock_spark.version = "3.2.0"
        mock_spark_session.builder.appName.return_value.getOrCreate.return_value = mock_spark
        
        connection_params = {"master_url": "spark://localhost:7077"}
        profile = create_connection_profile("Test Spark", "spark", connection_params)
        save_connection_profile(profile, str(config_dir))
        
        # Test connection
        result = test_connection(profile['connection_id'], str(config_dir))
        assert result['success'] is True
        assert result['connection_type'] == "spark"
        assert result['spark_version'] == "3.2.0"
    
    def test_get_connection_status(self, tmp_path):
        """Test getting connection status."""
        config_dir = tmp_path / "config"
        
        connection_params = {"url": "http://test.com"}
        profile = create_connection_profile("Test Connection", "notebook", connection_params)
        save_connection_profile(profile, str(config_dir))
        
        # Get status
        status = get_connection_status(profile['connection_id'], str(config_dir))
        assert status['connection_id'] == profile['connection_id']
        assert status['name'] == profile['name']
        assert status['type'] == "notebook"
        assert status['health'] == "unknown"  # Never connected
    
    def test_cleanup_old_connections(self, tmp_path):
        """Test cleaning up old connections."""
        config_dir = tmp_path / "config"
        
        # Create an old connection (simulate by setting old dates)
        connection_params = {"url": "http://old.com"}
        profile = create_connection_profile("Old Connection", "notebook", connection_params)
        
        # Set old dates
        from datetime import datetime, timedelta
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        profile['metadata']['created_date'] = old_date
        profile['metadata']['last_used'] = old_date
        profile['metadata']['connection_count'] = 0
        
        save_connection_profile(profile, str(config_dir))
        
        # Cleanup connections older than 30 days
        removed_count = cleanup_old_connections(30, str(config_dir))
        assert removed_count == 1
        
        # Verify connection was removed
        remaining_connections = list_connection_profiles(config_directory=str(config_dir))
        assert len(remaining_connections) == 0


class TestIntegration:
    """Test integration between client and connection systems."""
    
    def test_associate_client_with_project(self, tmp_path):
        """Test associating a client with a project."""
        config_dir = tmp_path / "config"
        
        # Create client profile
        contact_info = {"primary_contact": "Test User", "email": "test@example.com"}
        client_profile = create_client_profile("Test Client", "TEST001", contact_info)
        save_client_profile(client_profile, str(config_dir))
        
        # Create project config (mock)
        project_config = {
            "project_code": "PROJ001",
            "project_name": "Test Project"
        }
        project_file = config_dir / "project_PROJ001.json"
        with open(project_file, 'w') as f:
            json.dump(project_config, f)
        
        # Associate client with project
        success = associate_client_with_project("TEST001", "PROJ001", str(config_dir))
        assert success is True
        
        # Verify association
        associations = get_client_project_associations("TEST001", str(config_dir))
        assert "PROJ001" in associations
        
        # Verify project count was updated
        updated_client = load_client_profile("TEST001", str(config_dir))
        assert updated_client['metadata']['project_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__])
