"""Regression tests for #1117: import-time UserConfigManager mkdir must not
hard-fail on an unwritable/nonexistent HOME (the non-root Spark/Kubernetes
pod case, HOME=/nonexistent).
"""

import os
import sys
import subprocess
import tempfile

import pytest

from siege_utilities.config.user_config import _resolve_config_dir


def test_import_and_construct_with_unwritable_home_does_not_crash():
    """The exact #1117 repro: HOME=/nonexistent must not crash import/construct.

    Runs in a subprocess so the unwritable HOME is process-global (matches the
    Spark-pod environment) without mutating this test process. Root-safe: if the
    test runs as root (which can write under /), construction simply succeeds
    without the fallback — either way the process must exit 0, never raise
    PermissionError at import.
    """
    env = {k: v for k, v in os.environ.items()}
    env["HOME"] = "/nonexistent"
    env.pop("SIEGE_USER_CONFIG", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import siege_utilities.config.user_config as m; "
            "mgr = m.UserConfigManager(); "
            "print('OK', mgr.config_dir)",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"import/construct crashed on unwritable HOME:\n{result.stderr}"
    )
    assert "OK" in result.stdout


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root can write anywhere, so an unwritable parent cannot be simulated",
)
def test_resolve_config_dir_falls_back_to_tempdir_when_unwritable(tmp_path, monkeypatch):
    """When the resolved dir's parent is unwritable, fall back to the temp dir
    (and never raise). Exercises the except path directly (writing-tests:5)."""
    monkeypatch.delenv("SIEGE_USER_CONFIG", raising=False)
    read_only = tmp_path / "ro"
    read_only.mkdir()
    os.chmod(read_only, 0o500)  # r-x: cannot create children
    target = read_only / ".siege_utilities" / "config"

    result = _resolve_config_dir(target)

    assert result.exists(), "fallback dir should have been created"
    assert tempfile.gettempdir() in str(result), (
        f"expected a temp-dir fallback, got {result}"
    )


def test_resolve_config_dir_honors_siege_user_config_override(tmp_path, monkeypatch):
    """SIEGE_USER_CONFIG overrides the default location."""
    override = tmp_path / "custom_cfg"
    monkeypatch.setenv("SIEGE_USER_CONFIG", str(override))

    result = _resolve_config_dir()

    assert result == override
    assert result.exists()


def test_resolve_config_dir_uses_explicit_arg_over_env(tmp_path, monkeypatch):
    """An explicit config_dir argument wins over the env override."""
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("SIEGE_USER_CONFIG", str(tmp_path / "from_env"))

    result = _resolve_config_dir(explicit)

    assert result == explicit
    assert result.exists()
