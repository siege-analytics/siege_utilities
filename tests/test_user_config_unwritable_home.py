"""Tests for UserConfigManager resilience to unwritable HOME. Ref: #1117."""

import os
from pathlib import Path
from unittest import mock


from siege_utilities.config.user_config import UserConfigManager


class TestUnwritableHome:
    def test_unwritable_home_falls_back_to_tmpdir(self, tmp_path):
        unwritable = tmp_path / "nope"
        unwritable.mkdir()
        unwritable.chmod(0o000)
        try:
            config_dir = unwritable / ".siege_utilities" / "config"
            mgr = UserConfigManager(config_dir=config_dir)
            assert mgr.config_dir != config_dir
            assert mgr.user_profile is not None
        finally:
            unwritable.chmod(0o755)

    def test_explicit_config_dir_works(self, tmp_path):
        config_dir = tmp_path / "custom_config"
        mgr = UserConfigManager(config_dir=config_dir)
        assert mgr.config_dir == config_dir
        assert config_dir.exists()

    def test_siege_user_config_dir_env_override(self, tmp_path):
        custom = tmp_path / "env_override"
        with mock.patch.dict(os.environ, {"SIEGE_USER_CONFIG_DIR": str(custom)}):
            mgr = UserConfigManager()
            assert mgr.config_dir == custom
            assert custom.exists()

    def test_read_only_mode_does_not_crash(self):
        mgr = UserConfigManager.__new__(UserConfigManager)
        mgr._read_only = True
        mgr.config_dir = Path("/nonexistent/path")
        mgr.user_config_file = mgr.config_dir / "user_config.yaml"
        mgr.user_profile = type(mgr)._load_user_profile(mgr)
        mgr._save_user_profile()
