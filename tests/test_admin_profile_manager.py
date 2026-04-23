"""First tests for siege_utilities.admin.profile_manager (ELE-2419).

This module had zero test coverage prior to ELE-2419. Focus here is the
pure-path API surface and filesystem-backed behavior; heavier integration
(create_default_profiles / migrate_profiles with real YAML serialization)
is covered indirectly and will grow as needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from siege_utilities.admin import profile_manager as pm


@pytest.fixture(autouse=True)
def _reset_registry():
    """Ensure module-level PROFILE_LOCATIONS doesn't leak between tests."""
    snapshot = dict(pm.PROFILE_LOCATIONS)
    yield
    pm.PROFILE_LOCATIONS.clear()
    pm.PROFILE_LOCATIONS.update(snapshot)


class TestGetDefaultProfileLocation:
    def test_returns_path_under_package_root(self):
        loc = pm.get_default_profile_location()
        assert isinstance(loc, Path)
        assert loc.name == "profiles"

    def test_is_deterministic(self):
        assert pm.get_default_profile_location() == pm.get_default_profile_location()


class TestValidateProfileLocation:
    def test_writable_tmp_path_is_valid(self, tmp_path):
        target = tmp_path / "profiles"
        assert pm.validate_profile_location(target) is True
        assert target.exists()

    def test_parent_missing_is_invalid(self, tmp_path):
        # Parent of a path whose parent doesn't exist
        target = tmp_path / "no_such_dir" / "deeper" / "profiles"
        # /tmp/.../no_such_dir does not exist → parent check fails
        assert pm.validate_profile_location(target) is False

    def test_existing_writable_dir_is_valid(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        assert pm.validate_profile_location(target) is True


class TestProfileLocationRegistry:
    def test_get_unknown_type_returns_default(self):
        assert pm.get_profile_location("never_set") == pm.get_default_profile_location()

    def test_set_then_get_roundtrips(self, tmp_path):
        custom = tmp_path / "custom"
        pm.set_profile_location(custom, profile_type="user")
        result = pm.get_profile_location("user")
        assert result == custom.resolve()

    def test_set_invalid_location_raises(self, tmp_path):
        bad = tmp_path / "no_such_dir" / "deeper" / "profiles"
        with pytest.raises(ValueError, match="Invalid profile location"):
            pm.set_profile_location(bad)

    def test_list_always_includes_default(self, tmp_path):
        pm.set_profile_location(tmp_path / "x", profile_type="custom")
        listing = pm.list_profile_locations()
        assert "default" in listing
        assert "custom" in listing
        assert listing["default"] == pm.get_default_profile_location()


class TestCreateDefaultProfiles:
    def test_creates_yaml_files_on_disk(self, tmp_path):
        user, clients = pm.create_default_profiles(tmp_path)
        assert (tmp_path / "users").is_dir()
        assert (tmp_path / "clients").is_dir()
        assert user.username == "default"
        assert len(clients) == 2
        # Example clients have expected codes
        codes = {c.client_code for c in clients}
        assert codes == {"GOV001", "BIZ001"}

    def test_defaults_location_to_package(self, tmp_path, monkeypatch):
        called = {}
        real_save_user = pm.save_user_profile
        real_save_client = pm.save_client_profile

        def fake_save_user(profile, name, location):
            called.setdefault("user", []).append(Path(location))

        def fake_save_client(profile, location):
            called.setdefault("client", []).append(Path(location))

        monkeypatch.setattr(pm, "save_user_profile", fake_save_user)
        monkeypatch.setattr(pm, "save_client_profile", fake_save_client)
        monkeypatch.setattr(
            pm, "get_default_profile_location", lambda: tmp_path / "dflt"
        )

        pm.create_default_profiles()
        assert any("dflt" in str(p) for p in called.get("user", []))


class TestMigrateProfiles:
    def test_missing_source_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            pm.migrate_profiles(tmp_path / "does_not_exist", tmp_path / "target")

    def test_copies_user_and_client_yaml_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "users").mkdir(parents=True)
        (src / "clients").mkdir(parents=True)
        (src / "users" / "alice.yaml").write_text("username: alice\n")
        (src / "clients" / "acme.yaml").write_text("client_id: acme\n")
        (src / "users" / "ignoreme.txt").write_text("nope")

        stats = pm.migrate_profiles(src, dst, backup=False)
        assert stats["users_migrated"] == 1
        assert stats["clients_migrated"] == 1
        assert stats["errors"] == 0
        assert (dst / "users" / "alice.yaml").exists()
        assert (dst / "clients" / "acme.yaml").exists()
        assert not (dst / "users" / "ignoreme.txt").exists()

    def test_backup_created_when_target_exists(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "users").mkdir()
        dst.mkdir()
        (dst / "existing.txt").write_text("before")

        pm.migrate_profiles(src, dst, backup=True)
        backup = dst.parent / f"{dst.name}.backup"
        assert backup.exists()
        assert (backup / "existing.txt").read_text() == "before"


class TestGetProfileSummary:
    def test_missing_location(self, tmp_path):
        summary = pm.get_profile_summary(tmp_path / "nope")
        assert summary["exists"] is False
        assert summary["user_profiles"] == 0
        assert summary["client_profiles"] == 0

    def test_counts_yaml_files(self, tmp_path):
        (tmp_path / "users").mkdir()
        (tmp_path / "clients").mkdir()
        (tmp_path / "users" / "alice.yaml").write_text("x: 1")
        (tmp_path / "users" / "bob.yaml").write_text("x: 2")
        (tmp_path / "clients" / "acme.yaml").write_text("x: 3")

        summary = pm.get_profile_summary(tmp_path)
        assert summary["exists"] is True
        assert summary["user_profiles"] == 2
        assert summary["client_profiles"] == 1
        assert summary["client_codes"] == ["acme"]
        assert summary["total_size_mb"] >= 0
