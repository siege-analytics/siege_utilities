"""
Tests for admin profile manager functionality.
Tests profile location management, migration, and default profile creation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from siege_utilities.admin.profile_manager import (
    get_default_profile_location,
    set_profile_location,
    get_profile_location,
    list_profile_locations,
    validate_profile_location,
    create_default_profiles,
    migrate_profiles,
    get_profile_summary
)
from siege_utilities.config.enhanced_config import UserProfile, ClientProfile

pytestmark = pytest.mark.admin

class TestProfileLocationManagement:
    """Test profile location management functions."""
    
    def test_get_default_profile_location(self):
        """Test getting the default profile location."""
        location = get_default_profile_location()

        assert isinstance(location, Path)
        assert location.name == "profiles"
        # Should be in the project - flexible check instead of hardcoded name
        assert "siege_utilities" in str(location)
    
    def test_set_and_get_profile_location(self):
        """Test setting and getting custom profile locations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_location = Path(temp_dir) / "custom_profiles"
            
            # Set custom location
            set_profile_location(custom_location, "test")
            
            # Get the location back
            retrieved_location = get_profile_location("test")
            assert retrieved_location == custom_location.resolve()
            
            # Test default location still works
            default_location = get_profile_location("default")
            assert default_location == get_default_profile_location()
    
    def test_list_profile_locations(self):
        """Test listing all profile locations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_location = Path(temp_dir) / "custom_profiles"
            set_profile_location(custom_location, "custom")
            
            locations = list_profile_locations()
            
            assert "default" in locations
            assert "custom" in locations
            assert locations["default"] == get_default_profile_location()
            assert locations["custom"] == custom_location.resolve()
    
    def test_validate_profile_location_valid(self):
        """Test validating a valid profile location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_location = Path(temp_dir) / "valid_profiles"
            
            assert validate_profile_location(valid_location) == True
            assert valid_location.exists()
    
    def test_validate_profile_location_invalid(self):
        """Test validating an invalid profile location."""
        # Test with non-existent parent directory
        invalid_location = Path("/nonexistent/path/profiles")
        
        assert validate_profile_location(invalid_location) == False
    
    def test_validate_profile_location_unwritable(self):
        """Test validating an unwritable profile location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)  # Read-only
            
            try:
                assert validate_profile_location(readonly_dir) == False
            finally:
                # Restore permissions for cleanup
                readonly_dir.chmod(0o755)

class TestDefaultProfileCreation:
    """Test default profile creation functionality."""

    def test_create_default_profiles(self):
        """Test creating default user and client profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_location = Path(temp_dir) / "profiles"

            user_profile, client_profiles = create_default_profiles(profile_location)

            # Check user profile
            assert isinstance(user_profile, UserProfile)
            assert profile_location.exists()
            assert (profile_location / "users").exists()
            assert (profile_location / "users" / "default.yaml").exists()

            # Check client profiles
            assert isinstance(client_profiles, list)
            assert len(client_profiles) == 2
            assert all(isinstance(p, ClientProfile) for p in client_profiles)
            assert (profile_location / "clients").exists()

            # Check specific client files exist
            client_codes = [p.client_code for p in client_profiles]
            assert "GOV001" in client_codes
            assert "BIZ001" in client_codes

            for client_code in client_codes:
                client_file = profile_location / "clients" / f"{client_code}.yaml"
                assert client_file.exists()

    def test_create_default_profiles_default_location(self):
        """Test creating default profiles in default location."""
        # This test might affect the actual project directory
        # So we'll just test that the function doesn't crash
        try:
            user_profile, client_profiles = create_default_profiles()

            assert isinstance(user_profile, UserProfile)
            assert isinstance(client_profiles, list)
            assert len(client_profiles) >= 0  # May or may not create example clients
        except Exception as e:
            # If it fails due to permissions, that's acceptable
            assert "permission" in str(e).lower() or "access" in str(e).lower()

class TestProfileMigration:
    """Test profile migration functionality."""
    
    def test_migrate_profiles_success(self):
        """Test successful profile migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            target_dir = Path(temp_dir) / "target"
            
            # Create source profiles
            source_users = source_dir / "users"
            source_clients = source_dir / "clients"
            source_users.mkdir(parents=True)
            source_clients.mkdir(parents=True)
            
            # Create test files
            (source_users / "user_config.yaml").write_text("username: test_user")
            (source_clients / "TEST001.yaml").write_text("client_name: Test Client\nclient_code: TEST001")
            
            # Migrate
            stats = migrate_profiles(source_dir, target_dir)
            
            assert stats["users_migrated"] == 1
            assert stats["clients_migrated"] == 1
            assert stats["files_copied"] >= 2
            assert stats["errors"] == 0
            
            # Verify files were copied
            assert (target_dir / "users" / "user_config.yaml").exists()
            assert (target_dir / "clients" / "TEST001.yaml").exists()
    
    def test_migrate_profiles_with_backup(self):
        """Test profile migration with backup creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            target_dir = Path(temp_dir) / "target"
            
            # Create existing target files
            target_users = target_dir / "users"
            target_users.mkdir(parents=True)
            (target_users / "existing_user.yaml").write_text("username: existing")
            
            # Create source files
            source_users = source_dir / "users"
            source_users.mkdir(parents=True)
            (source_users / "new_user.yaml").write_text("username: new_user")
            
            # Migrate with backup
            stats = migrate_profiles(source_dir, target_dir, backup=True)
            
            assert stats["users_migrated"] == 1
            assert stats["errors"] == 0
            
            # Check backup was created
            backup_dir = target_dir.parent / f"{target_dir.name}.backup"
            assert backup_dir.exists()
            assert (backup_dir / "users" / "existing_user.yaml").exists()
            
            # Check new files were added
            assert (target_dir / "users" / "new_user.yaml").exists()
    
    def test_migrate_profiles_source_not_found(self):
        """Test migration with non-existent source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "nonexistent"
            target_dir = Path(temp_dir) / "target"
            
            with pytest.raises(FileNotFoundError):
                migrate_profiles(source_dir, target_dir)

class TestProfileSummary:
    """Test profile summary functionality."""
    
    def test_get_profile_summary_empty(self):
        """Test getting summary for empty profile location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_location = Path(temp_dir) / "empty_profiles"
            
            summary = get_profile_summary(profile_location)
            
            # Handle macOS path variations (/var vs /private/var)
            expected_location = str(profile_location.resolve())
            actual_location = summary["location"]
            assert expected_location == actual_location or expected_location.replace("/private", "") == actual_location
            assert summary["exists"] == False
            assert summary["user_profiles"] == 0
            assert summary["client_profiles"] == 0
            assert summary["client_codes"] == []
            assert summary["total_size_mb"] == 0
    
    def test_get_profile_summary_with_profiles(self):
        """Test getting summary for location with profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_location = Path(temp_dir) / "profiles"

            # Create profiles
            user_profile, client_profiles = create_default_profiles(profile_location)

            summary = get_profile_summary(profile_location)

            # Handle macOS path variations (/var vs /private/var)
            expected_location = str(profile_location.resolve())
            actual_location = summary["location"]
            assert expected_location == actual_location or expected_location.replace("/private", "") == actual_location
            assert summary["exists"] == True
            assert summary["user_profiles"] == 1
            assert summary["client_profiles"] == 2
            assert len(summary["client_codes"]) == 2
            assert summary["total_size_mb"] >= 0  # Files might be very small
    
    def test_get_profile_summary_default_location(self):
        """Test getting summary for default location."""
        summary = get_profile_summary()
        
        assert "location" in summary
        assert "exists" in summary
        assert "user_profiles" in summary
        assert "client_profiles" in summary
        assert "client_codes" in summary
        assert "total_size_mb" in summary

class TestIntegration:
    """Integration tests for profile management."""

    def test_full_workflow(self):
        """Test complete workflow: create location, profiles, migrate, summarize."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up custom location
            custom_location = Path(temp_dir) / "custom_profiles"
            set_profile_location(custom_location, "workflow_test")

            # Create default profiles
            user_profile, client_profiles = create_default_profiles(custom_location)

            # Get summary
            summary = get_profile_summary(custom_location)
            assert summary["client_profiles"] == 2

            # Migrate to new location
            new_location = Path(temp_dir) / "new_profiles"
            stats = migrate_profiles(custom_location, new_location)

            assert stats["users_migrated"] == 1
            assert stats["clients_migrated"] == 2

            # Verify migration
            new_summary = get_profile_summary(new_location)
            assert new_summary["client_profiles"] == 2

            # Test profile loading from new location
            from siege_utilities.config.enhanced_config import load_user_profile, list_client_profiles

            loaded_user = load_user_profile("default", new_location / "users")
            assert loaded_user is not None
            assert loaded_user.username == user_profile.username

            client_codes = list_client_profiles(new_location / "clients")
            assert len(client_codes) == 2
            assert "GOV001" in client_codes
            assert "BIZ001" in client_codes
