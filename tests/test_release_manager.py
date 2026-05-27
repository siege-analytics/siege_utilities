"""Tests for scripts/release_manager.py — focused on security properties."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from release_manager import upload_to_pypi


class TestUploadToPypiTokenSafety:
    """PyPI token must never appear in subprocess argv (visible in ps aux)."""

    @patch("release_manager.subprocess.run")
    def test_token_not_in_command_args(self, mock_run, tmp_path):
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "pkg-1.0.tar.gz").touch()

        mock_run.return_value = MagicMock(returncode=0)

        with patch("release_manager.PROJECT_ROOT", tmp_path):
            upload_to_pypi(repository="pypi", token="pypi-SECRET-TOKEN-12345")

        args, kwargs = mock_run.call_args
        cmd = args[0]
        cmd_str = " ".join(cmd)
        assert "pypi-SECRET-TOKEN-12345" not in cmd_str, (
            "Token must not appear in subprocess command (visible in ps aux)"
        )

    @patch("release_manager.subprocess.run")
    def test_token_passed_via_env(self, mock_run, tmp_path):
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "pkg-1.0.tar.gz").touch()

        mock_run.return_value = MagicMock(returncode=0)

        with patch("release_manager.PROJECT_ROOT", tmp_path):
            upload_to_pypi(repository="pypi", token="pypi-SECRET-TOKEN-12345")

        _, kwargs = mock_run.call_args
        env = kwargs.get("env", {})
        assert env.get("TWINE_PASSWORD") == "pypi-SECRET-TOKEN-12345"
        assert env.get("TWINE_USERNAME") == "__token__"

    @patch("release_manager.subprocess.run")
    def test_testpypi_repository_flag(self, mock_run, tmp_path):
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "pkg-1.0.tar.gz").touch()

        mock_run.return_value = MagicMock(returncode=0)

        with patch("release_manager.PROJECT_ROOT", tmp_path):
            upload_to_pypi(repository="testpypi", token="pypi-TEST-TOKEN")

        cmd = mock_run.call_args[0][0]
        assert "--repository" in cmd
        assert "testpypi" in cmd
