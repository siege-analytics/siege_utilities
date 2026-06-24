"""Tests for error paths in config.hydra_manager and config.enhanced_config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from siege_utilities.config.enhanced_config import (
    ConfigurationMigrator,
    SiegeConfig,
    export_config_yaml,
    import_config_yaml,
    list_client_profiles,
    load_user_profile,
    save_user_profile,
    load_client_profile,
)
from siege_utilities.config.models.user_profile import UserProfile


# ===========================================================================
# ConfigurationMigrator
# ===========================================================================

class TestConfigurationMigratorErrors:
    def test_missing_legacy_file_returns_default_profile(self, tmp_path):
        migrator = ConfigurationMigrator(
            legacy_config_dir=tmp_path / "nonexistent",
            new_config_dir=tmp_path / "new",
        )
        profile = migrator.migrate_user_profile()
        assert isinstance(profile, UserProfile)

    def test_invalid_yaml_returns_default_profile(self, tmp_path):
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        bad_file = legacy_dir / "user_config.yaml"
        bad_file.write_text("- this is a list, not a mapping\n")
        migrator = ConfigurationMigrator(
            legacy_config_dir=legacy_dir,
            new_config_dir=tmp_path / "new",
        )
        profile = migrator.migrate_user_profile(bad_file)
        assert isinstance(profile, UserProfile)

    def test_empty_yaml_returns_default_profile(self, tmp_path):
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        empty_file = legacy_dir / "user_config.yaml"
        empty_file.write_text("")
        migrator = ConfigurationMigrator(
            legacy_config_dir=legacy_dir,
            new_config_dir=tmp_path / "new",
        )
        profile = migrator.migrate_user_profile(empty_file)
        assert isinstance(profile, UserProfile)

    def test_migrate_client_missing_file_returns_default(self, tmp_path):
        migrator = ConfigurationMigrator(
            legacy_config_dir=tmp_path / "nonexistent",
            new_config_dir=tmp_path / "new",
        )
        profile = migrator.migrate_client_profile(
            tmp_path / "no-such-file.yaml", "DEMO"
        )
        assert profile.client_code == "DEMO"

    def test_migrate_client_unsupported_extension_returns_default(self, tmp_path):
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        bad_file = legacy_dir / "client.toml"
        bad_file.write_text("[settings]\nfoo = 1\n")
        migrator = ConfigurationMigrator(
            legacy_config_dir=legacy_dir,
            new_config_dir=tmp_path / "new",
        )
        profile = migrator.migrate_client_profile(bad_file, "DEMO")
        assert profile.client_code == "DEMO"

    def test_migrate_client_non_mapping_yaml_returns_default(self, tmp_path):
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        bad_file = legacy_dir / "client.yaml"
        bad_file.write_text("- list\n- not mapping\n")
        migrator = ConfigurationMigrator(
            legacy_config_dir=legacy_dir,
            new_config_dir=tmp_path / "new",
        )
        profile = migrator.migrate_client_profile(bad_file, "DEMO")
        assert profile.client_code == "DEMO"

    def test_migrate_client_reserved_code_uses_fallback(self, tmp_path):
        migrator = ConfigurationMigrator(
            legacy_config_dir=tmp_path,
            new_config_dir=tmp_path,
        )
        profile = migrator._create_default_client_profile("test")
        assert profile.client_code == "DEMO"

    def test_migrate_all_dry_run_does_not_fail(self, tmp_path):
        migrator = ConfigurationMigrator(
            legacy_config_dir=tmp_path / "nonexistent",
            new_config_dir=tmp_path / "new",
        )
        results = migrator.migrate_all_configurations(dry_run=True)
        assert results["dry_run"] is True


# ===========================================================================
# Legacy compatibility functions
# ===========================================================================

class TestLegacyLoadErrors:
    def test_load_user_profile_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_user_profile("nonexistent", config_dir=tmp_path)

    def test_load_user_profile_non_mapping_raises(self, tmp_path):
        bad_file = tmp_path / "baduser.yaml"
        bad_file.write_text("- not a mapping\n")
        with pytest.raises(ValueError, match="not a YAML mapping"):
            load_user_profile("baduser", config_dir=tmp_path)

    def test_load_client_profile_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_client_profile("NOPE", config_dir=tmp_path)

    def test_load_client_profile_non_mapping_raises(self, tmp_path):
        bad_file = tmp_path / "BAD.yaml"
        bad_file.write_text("42\n")
        with pytest.raises(ValueError, match="not a YAML mapping"):
            load_client_profile("BAD", config_dir=tmp_path)

    def test_save_user_profile_invalid_dir_raises(self):
        profile = UserProfile()
        with pytest.raises(OSError):
            save_user_profile(
                profile, "user",
                config_dir=Path("/proc/nonexistent_9999/profiles")
            )


# ===========================================================================
# Utility functions
# ===========================================================================

class TestUtilityErrors:
    def test_list_client_profiles_missing_dir_returns_empty(self, tmp_path):
        result = list_client_profiles(config_dir=tmp_path / "nonexistent")
        assert result == []

    def test_export_config_yaml_invalid_path_raises(self):
        with pytest.raises(OSError):
            export_config_yaml(
                {"key": "value"},
                Path("/proc/nonexistent_9999/out.yaml"),
            )

    def test_import_config_yaml_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            import_config_yaml(tmp_path / "nonexistent.yaml")

    def test_import_config_yaml_valid_file_returns_data(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(yaml.dump({"key": "value"}))
        result = import_config_yaml(f)
        assert result == {"key": "value"}


# ===========================================================================
# HydraConfigManager
# ===========================================================================

class TestHydraManagerErrors:
    def test_missing_config_dir_raises_error(self, tmp_path):
        from siege_utilities.config.hydra_manager import HydraConfigManager
        with pytest.raises(FileNotFoundError, match="not found"):
            HydraConfigManager(config_dir=tmp_path / "nonexistent")

    def test_load_user_missing_file_raises(self, tmp_path):
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        from siege_utilities.config.hydra_manager import HydraConfigManager
        mgr = HydraConfigManager(config_dir=config_dir)
        with pytest.raises(FileNotFoundError):
            mgr.load_user("nonexistent", profiles_dir=tmp_path / "profiles")

    def test_load_client_missing_file_raises(self, tmp_path):
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        from siege_utilities.config.hydra_manager import HydraConfigManager
        mgr = HydraConfigManager(config_dir=config_dir)
        with pytest.raises(FileNotFoundError):
            mgr.load_client("NOPE", profiles_dir=tmp_path / "profiles")


# ===========================================================================
# SiegeConfig
# ===========================================================================

class TestSiegeConfigErrors:
    def test_get_user_profile_missing_raises(self, tmp_path):
        cfg = SiegeConfig(config_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            cfg.get_user_profile("nonexistent")

    def test_get_client_profile_missing_raises(self, tmp_path):
        cfg = SiegeConfig(config_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            cfg.get_client_profile("NONEXISTENT")
