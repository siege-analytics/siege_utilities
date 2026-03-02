"""Tests for Databricks-aware download directory resolution."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.databricks

from siege_utilities.config.user_config import (
    _is_databricks_runtime,
    _default_download_directory,
    get_download_directory,
)


# ---------------------------------------------------------------------------
# _is_databricks_runtime detection
# ---------------------------------------------------------------------------


class TestIsDatabricksRuntime:
    """Tests for Databricks environment detection."""

    def test_detects_databricks_runtime_version_env(self):
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            assert _is_databricks_runtime() is True

    def test_not_databricks_without_env_or_dbfs(self):
        env = {k: v for k, v in os.environ.items() if k != "DATABRICKS_RUNTIME_VERSION"}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(Path, "is_dir", return_value=False):
            assert _is_databricks_runtime() is False

    def test_detects_dbfs_directory(self):
        env = {k: v for k, v in os.environ.items() if k != "DATABRICKS_RUNTIME_VERSION"}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(Path, "is_dir", return_value=True):
            assert _is_databricks_runtime() is True


# ---------------------------------------------------------------------------
# _default_download_directory
# ---------------------------------------------------------------------------


class TestDefaultDownloadDirectory:
    """Tests for platform-aware default directory selection."""

    def test_databricks_default_is_tmp(self):
        with patch("siege_utilities.config.user_config._is_databricks_runtime", return_value=True):
            result = _default_download_directory()
            assert result == Path("/tmp/siege_utilities/downloads")

    def test_non_databricks_default_is_home_downloads(self):
        with patch("siege_utilities.config.user_config._is_databricks_runtime", return_value=False):
            result = _default_download_directory()
            assert result == Path.home() / "Downloads" / "siege_utilities"


# ---------------------------------------------------------------------------
# get_download_directory — writability validation
# ---------------------------------------------------------------------------


class TestGetDownloadDirectory:
    """Tests for the module-level get_download_directory function."""

    def test_specific_path_overrides_everything(self, tmp_path):
        """specific_path should take priority regardless of environment."""
        custom = tmp_path / "custom_dl"
        result = get_download_directory(specific_path=str(custom))
        assert result == custom
        assert custom.is_dir()

    def test_raises_on_unwritable_directory(self, tmp_path, monkeypatch):
        """Should raise OSError when directory is not writable."""
        unwritable = tmp_path / "locked"
        unwritable.mkdir()
        monkeypatch.setattr(os, "access", lambda path, mode: False)
        with pytest.raises(OSError, match="not writable"):
            get_download_directory(specific_path=str(unwritable))

    def test_user_override_respected_on_databricks(self, tmp_path):
        """Even on Databricks, a user-supplied specific_path wins."""
        custom = tmp_path / "user_chosen"
        with patch("siege_utilities.config.user_config._is_databricks_runtime", return_value=True):
            result = get_download_directory(specific_path=str(custom))
            assert result == custom
