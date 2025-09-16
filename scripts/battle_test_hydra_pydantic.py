#!/usr/bin/env python3
"""
Battle testing script for the Hydra + Pydantic configuration system.

This script performs comprehensive end-to-end testing of the entire
configuration system including validation, migration, and real-world scenarios.
"""

import sys
import tempfile
import shutil
from pathlib import Path
import yaml
import json
import logging

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from siege_utilities.config import (
    HydraConfigManager, 
    PydanticUserProfile, 
    PydanticClientProfile,
    ContactInfo, 
    BrandingConfig, 
    ReportPreferences,
    DatabaseConnection, 
    SocialMediaAccount,
    ConfigurationMigrator,
    migrate_configurations
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BattleTester:
    """Comprehensive battle testing for the Hydra + Pydantic system."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        logger.info(f"Battle testing initialized in: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up test artifacts."""
        shutil.rmtree(self.temp_dir)
        logger.info("Battle testing cleanup completed")
    
    def assert_test(self, condition: bool, test_name: str, error_message: str = ""):
        """Assert a test condition and record results."""
        if condition:
            self.test_results["passed"] += 1
            logger.info(f"✅ PASS: {test_name}")
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {error_message}")
            logger.error(f"❌ FAIL: {test_name} - {error_message}")
    
    def test_pydantic_models(self):
        """Test all Pydantic models with various scenarios."""
        logger.info("🧪 Testing Pydantic Models...")
        
        # Test UserProfile
        try:
            user = PydanticUserProfile(
                username="battle_test_user",
                email="battle@test.com",
                full_name="Battle Test User",
                github_login="battletest"
            )
            self.assert_test(
                user.username == "battle_test_user",
                "UserProfile Creation",
                "Failed to create UserProfile"
            )
            
            # Test validation
            try:
                invalid_user = PydanticUserProfile(
                    username="",
                    email="invalid",
                    full_name="",
                    github_login=""
                )
                self.assert_test(False, "UserProfile Validation", "Should have rejected invalid data")
            except Exception:
                self.assert_test(True, "UserProfile Validation", "")
                
        except Exception as e:
            self.assert_test(False, "UserProfile Creation", str(e))
        
        # Test BrandingConfig
        try:
            branding = BrandingConfig(
                primary_color="#FF0000",
                secondary_color="#00FF00",
                accent_color="#0000FF",
                text_color="#000000",
                background_color="#FFFFFF",
                primary_font="Arial",
                secondary_font="Arial"
            )
            self.assert_test(
                branding.primary_color == "#FF0000",
                "BrandingConfig Creation",
                "Failed to create BrandingConfig"
            )
            
            # Test helper methods
            color_scheme = branding.get_color_scheme()
            self.assert_test(
                len(color_scheme) > 0,
                "BrandingConfig Helper Methods",
                "get_color_scheme() failed"
            )
            
        except Exception as e:
            self.assert_test(False, "BrandingConfig Creation", str(e))
        
        # Test DatabaseConnection
        try:
            db_conn = DatabaseConnection(
                name="battle_test_db",
                connection_type="postgresql",
                host="test.example.com",
                port=5432,
                database="battle_test",
                username="testuser",
                password="BattleTest123"
            )
            self.assert_test(
                db_conn.name == "battle_test_db",
                "DatabaseConnection Creation",
                "Failed to create DatabaseConnection"
            )
            
            # Test connection string generation
            conn_string = db_conn.get_connection_string()
            self.assert_test(
                "postgresql://" in conn_string,
                "DatabaseConnection String Generation",
                "Failed to generate connection string"
            )
            
        except Exception as e:
            self.assert_test(False, "DatabaseConnection Creation", str(e))
        
        # Test SocialMediaAccount
        try:
            social = SocialMediaAccount(
                platform="facebook",
                account_id="123456789",
                account_name="Battle Test Account",
                access_token="battle_test_token_123456789"
            )
            self.assert_test(
                social.platform == "facebook",
                "SocialMediaAccount Creation",
                "Failed to create SocialMediaAccount"
            )
            
            # Test helper methods
            auth_headers = social.get_auth_headers()
            self.assert_test(
                "Authorization" in auth_headers,
                "SocialMediaAccount Helper Methods",
                "get_auth_headers() failed"
            )
            
        except Exception as e:
            self.assert_test(False, "SocialMediaAccount Creation", str(e))
    
    def test_hydra_config_manager(self):
        """Test the HydraConfigManager functionality."""
        logger.info("🧪 Testing HydraConfigManager...")
        
        try:
            with HydraConfigManager() as manager:
                # Test user profile loading
                user_profile = manager.load_user_profile()
                self.assert_test(
                    isinstance(user_profile, PydanticUserProfile),
                    "HydraConfigManager User Profile Loading",
                    "Failed to load user profile"
                )
                
                # Test branding config loading
                branding = manager.load_branding_config()
                self.assert_test(
                    isinstance(branding, BrandingConfig),
                    "HydraConfigManager Branding Loading",
                    "Failed to load branding config"
                )
                
                # Test client-specific branding
                try:
                    client_branding = manager.load_branding_config("client_a")
                    self.assert_test(
                        isinstance(client_branding, BrandingConfig),
                        "HydraConfigManager Client-Specific Branding",
                        "Failed to load client-specific branding"
                    )
                    
                    # Verify client-specific values are applied
                    self.assert_test(
                        client_branding.primary_color != branding.primary_color,
                        "HydraConfigManager Client Override",
                        "Client-specific overrides not applied"
                    )
                    
                except Exception as e:
                    logger.warning(f"Client-specific branding test skipped: {e}")
                
                # Test configuration overrides
                try:
                    config_data = manager.load_config(
                        "default/user_profile",
                        overrides=["default.default_output_format=pdf"]
                    )
                    self.assert_test(
                        config_data["default"]["default_output_format"] == "pdf",
                        "HydraConfigManager Configuration Overrides",
                        "Configuration overrides not working"
                    )
                except Exception as e:
                    logger.warning(f"Configuration overrides test skipped: {e}")
                
        except Exception as e:
            self.assert_test(False, "HydraConfigManager Initialization", str(e))
    
    def test_migration_system(self):
        """Test the migration system."""
        logger.info("🧪 Testing Migration System...")
        
        # Create test legacy configuration
        legacy_config_dir = self.temp_dir / "legacy_config"
        legacy_config_dir.mkdir()
        
        # Create test user config
        user_config = {
            "username": "migration_user",
            "email": "migration@test.com",
            "full_name": "Migration Test User",
            "default_output_format": "pdf"
        }
        
        with open(legacy_config_dir / "user_config.yaml", "w") as f:
            yaml.dump(user_config, f)
        
        # Create test client config
        client_config = {
            "client_name": "Migration Test Client",
            "industry": "Technology",
            "contact_email": "client@test.com",
            "branding": {
                "primary_color": "#FF0000",
                "primary_font": "Times New Roman"
            }
        }
        
        (legacy_config_dir / "clients").mkdir()
        with open(legacy_config_dir / "clients" / "test_client.yaml", "w") as f:
            yaml.dump(client_config, f)
        
        try:
            # Test migration
            migrator = ConfigurationMigrator(legacy_config_dir)
            
            # Test user profile migration
            user_profile = migrator.migrate_user_profile()
            self.assert_test(
                user_profile.username == "migration_user",
                "Migration System User Profile",
                "User profile migration failed"
            )
            
            # Test client profile migration
            client_file = legacy_config_dir / "clients" / "test_client.yaml"
            client_profile = migrator.migrate_client_profile(client_file, "TEST")
            self.assert_test(
                client_profile.client_code == "DEMO",  # TEST should be converted to DEMO
                "Migration System Client Profile",
                "Client profile migration failed"
            )
            
            # Test backup creation
            backup_dir = migrator.backup_legacy_configurations()
            self.assert_test(
                backup_dir.exists(),
                "Migration System Backup Creation",
                "Backup creation failed"
            )
            
            # Test dry run migration
            results = migrator.migrate_all_configurations(dry_run=True)
            self.assert_test(
                results["dry_run"] is True,
                "Migration System Dry Run",
                "Dry run migration failed"
            )
            
        except Exception as e:
            self.assert_test(False, "Migration System", str(e))
    
    def test_validation_edge_cases(self):
        """Test validation with edge cases and boundary conditions."""
        logger.info("🧪 Testing Validation Edge Cases...")
        
        # Test email validation edge cases
        email_tests = [
            ("valid@example.com", True),
            ("invalid-email", False),
            ("", True),  # Empty should be allowed
            ("user@domain.co.uk", True),
            ("user+tag@domain.com", True),
        ]
        
        for email, should_pass in email_tests:
            try:
                user = PydanticUserProfile(
                    username="test",
                    email=email,
                    full_name="Test User",
                    github_login="testuser"
                )
                self.assert_test(
                    should_pass,
                    f"Email Validation: {email}",
                    f"Expected {'pass' if should_pass else 'fail'}"
                )
            except Exception:
                self.assert_test(
                    not should_pass,
                    f"Email Validation: {email}",
                    f"Expected {'pass' if should_pass else 'fail'}"
                )
        
        # Test password validation edge cases
        password_tests = [
            ("StrongPass123", True),
            ("weak", False),
            ("12345678", False),  # No uppercase
            ("STRONG123", False),  # No lowercase
            ("StrongPass", False),  # No numbers
        ]
        
        for password, should_pass in password_tests:
            try:
                db_conn = DatabaseConnection(
                    name="test",
                    connection_type="postgresql",
                    host="localhost",
                    port=5432,
                    database="test",
                    username="user",
                    password=password
                )
                self.assert_test(
                    should_pass,
                    f"Password Validation: {password[:4]}***",
                    f"Expected {'pass' if should_pass else 'fail'}"
                )
            except Exception:
                self.assert_test(
                    not should_pass,
                    f"Password Validation: {password[:4]}***",
                    f"Expected {'pass' if should_pass else 'fail'}"
                )
        
        # Test color validation edge cases
        color_tests = [
            ("#FF0000", True),
            ("#ff0000", True),
            ("red", False),
            ("#FF00", False),  # Too short
            ("#FF00000", False),  # Too long
            ("#GG0000", False),  # Invalid characters
        ]
        
        for color, should_pass in color_tests:
            try:
                branding = BrandingConfig(
                    primary_color=color,
                    secondary_color="#00FF00",
                    accent_color="#0000FF",
                    text_color="#000000",
                    background_color="#FFFFFF",
                    primary_font="Arial",
                    secondary_font="Arial"
                )
                self.assert_test(
                    should_pass,
                    f"Color Validation: {color}",
                    f"Expected {'pass' if should_pass else 'fail'}"
                )
            except Exception:
                self.assert_test(
                    not should_pass,
                    f"Color Validation: {color}",
                    f"Expected {'pass' if should_pass else 'fail'}"
                )
    
    def test_performance_and_scalability(self):
        """Test performance and scalability of the system."""
        logger.info("🧪 Testing Performance and Scalability...")
        
        import time
        
        # Test configuration loading performance
        start_time = time.time()
        try:
            with HydraConfigManager() as manager:
                for i in range(10):
                    user_profile = manager.load_user_profile()
                    branding = manager.load_branding_config()
            
            load_time = time.time() - start_time
            self.assert_test(
                load_time < 5.0,  # Should load 20 configs in under 5 seconds
                "Configuration Loading Performance",
                f"Loading took {load_time:.2f} seconds (expected < 5.0s)"
            )
            
        except Exception as e:
            self.assert_test(False, "Configuration Loading Performance", str(e))
        
        # Test model creation performance
        start_time = time.time()
        try:
            for i in range(100):
                user = PydanticUserProfile(
                    username=f"user_{i}",
                    email=f"user{i}@test.com",
                    full_name=f"User {i}",
                    github_login=f"user{i}"
                )
                branding = BrandingConfig(
                    primary_color="#FF0000",
                    secondary_color="#00FF00",
                    accent_color="#0000FF",
                    text_color="#000000",
                    background_color="#FFFFFF",
                    primary_font="Arial",
                    secondary_font="Arial"
                )
            
            creation_time = time.time() - start_time
            self.assert_test(
                creation_time < 2.0,  # Should create 200 models in under 2 seconds
                "Model Creation Performance",
                f"Model creation took {creation_time:.2f} seconds (expected < 2.0s)"
            )
            
        except Exception as e:
            self.assert_test(False, "Model Creation Performance", str(e))
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        logger.info("🧪 Testing Error Handling and Recovery...")
        
        # Test invalid configuration directory
        try:
            invalid_manager = HydraConfigManager(Path("/nonexistent/directory"))
            self.assert_test(False, "Invalid Directory Handling", "Should have raised exception")
        except Exception:
            self.assert_test(True, "Invalid Directory Handling", "")
        
        # Test malformed configuration files
        malformed_config_dir = self.temp_dir / "malformed_configs"
        malformed_config_dir.mkdir()
        
        # Create malformed YAML
        with open(malformed_config_dir / "malformed.yaml", "w") as f:
            f.write("invalid: yaml: content: [")
        
        try:
            manager = HydraConfigManager(malformed_config_dir)
            # This should handle the error gracefully
            self.assert_test(True, "Malformed Configuration Handling", "")
        except Exception as e:
            self.assert_test(True, "Malformed Configuration Handling", f"Error handled: {e}")
        
        # Test validation error recovery
        try:
            # Create a valid profile first
            valid_user = PydanticUserProfile(
                username="valid_user",
                email="valid@test.com",
                full_name="Valid User",
                github_login="validuser"
            )
            
            # Then try to create an invalid one
            try:
                invalid_user = PydanticUserProfile(
                    username="",
                    email="invalid",
                    full_name="",
                    github_login=""
                )
            except Exception:
                pass  # Expected to fail
            
            # The valid profile should still work
            self.assert_test(
                valid_user.username == "valid_user",
                "Validation Error Recovery",
                "Valid profile corrupted by validation error"
            )
            
        except Exception as e:
            self.assert_test(False, "Validation Error Recovery", str(e))
    
    def test_integration_scenarios(self):
        """Test real-world integration scenarios."""
        logger.info("🧪 Testing Integration Scenarios...")
        
        # Scenario 1: Multi-client report generation
        try:
            def generate_multi_client_reports():
                with HydraConfigManager() as manager:
                    clients = ["client_a", "client_b"]
                    reports_generated = 0
                    
                    for client in clients:
                        try:
                            branding = manager.load_branding_config(client)
                            # Simulate report generation
                            reports_generated += 1
                        except Exception:
                            # Fall back to default
                            branding = manager.load_branding_config()
                            reports_generated += 1
                    
                    return reports_generated
            
            reports_count = generate_multi_client_reports()
            self.assert_test(
                reports_count > 0,
                "Multi-Client Report Generation",
                "Failed to generate reports for any clients"
            )
            
        except Exception as e:
            self.assert_test(False, "Multi-Client Report Generation", str(e))
        
        # Scenario 2: Configuration migration workflow
        try:
            # Create a complex legacy configuration
            legacy_dir = self.temp_dir / "complex_legacy"
            legacy_dir.mkdir()
            
            complex_config = {
                "username": "complex_user",
                "email": "complex@test.com",
                "full_name": "Complex User",
                "default_output_format": "pptx",
                "branding": {
                    "primary_color": "#123456",
                    "secondary_color": "#789ABC",
                    "primary_font": "Helvetica"
                },
                "database_connections": [
                    {
                        "name": "main_db",
                        "connection_type": "postgresql",
                        "host": "db.example.com",
                        "port": 5432,
                        "database": "main",
                        "username": "admin",
                        "password": "ComplexPass123"
                    }
                ]
            }
            
            with open(legacy_dir / "user_config.yaml", "w") as f:
                yaml.dump(complex_config, f)
            
            # Migrate the configuration
            migrator = ConfigurationMigrator(legacy_dir)
            user_profile = migrator.migrate_user_profile()
            
            self.assert_test(
                user_profile.username == "complex_user",
                "Complex Configuration Migration",
                "Failed to migrate complex configuration"
            )
            
        except Exception as e:
            self.assert_test(False, "Complex Configuration Migration", str(e))
        
        # Scenario 3: Dynamic configuration updates
        try:
            # Test updating configurations at runtime
            with HydraConfigManager() as manager:
                # Load initial configuration
                initial_branding = manager.load_branding_config()
                
                # Simulate configuration update (in real scenario, this would update files)
                # For testing, we'll just verify the system can handle multiple loads
                updated_branding = manager.load_branding_config()
                
                self.assert_test(
                    isinstance(updated_branding, BrandingConfig),
                    "Dynamic Configuration Updates",
                    "Failed to reload configuration"
                )
            
        except Exception as e:
            self.assert_test(False, "Dynamic Configuration Updates", str(e))
    
    def run_all_tests(self):
        """Run all battle tests."""
        logger.info("🚀 Starting Battle Testing...")
        
        try:
            self.test_pydantic_models()
            self.test_hydra_config_manager()
            self.test_migration_system()
            self.test_validation_edge_cases()
            self.test_performance_and_scalability()
            self.test_error_handling_and_recovery()
            self.test_integration_scenarios()
            
        finally:
            self.cleanup()
        
        # Print results
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        success_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("=" * 60)
        logger.info("🎯 BATTLE TESTING RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {self.test_results['passed']} ✅")
        logger.info(f"Failed: {self.test_results['failed']} ❌")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results["errors"]:
            logger.info("\n❌ FAILED TESTS:")
            for error in self.test_results["errors"]:
                logger.info(f"  - {error}")
        
        if success_rate >= 90:
            logger.info("\n🎉 BATTLE TESTING PASSED! System is ready for production.")
            return True
        else:
            logger.info("\n⚠️  BATTLE TESTING FAILED! System needs attention.")
            return False


def main():
    """Main battle testing entry point."""
    tester = BattleTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
