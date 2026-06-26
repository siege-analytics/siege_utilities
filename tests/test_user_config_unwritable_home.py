"""Regression tests for #1117: import-time UserConfigManager mkdir must not
hard-fail on an unwritable/nonexistent HOME (the non-root Spark/Kubernetes
pod case, HOME=/nonexistent).

The error-path tests below each force one of the ``except`` handlers added to
``_resolve_config_dir`` — the outer mkdir failure, the inner temp-dir-fallback
failure, and the ``RuntimeError`` from ``Path.home()`` when HOME is
unresolvable — per writing-tests:5.
"""

import os
import sys
import subprocess
import tempfile

import pytest

import siege_utilities.config.user_config as user_config
from siege_utilities.config.user_config import _resolve_config_dir

_IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


def test_import_and_construct_with_unwritable_home_does_not_crash():
    """The exact #1117 repro: HOME=/nonexistent must not crash import/construct.

    Runs in a subprocess so the unwritable HOME is process-global (matching the
    Spark-pod environment). Root-safe: if the test runs as root, construction
    simply succeeds without the fallback — either way the process must exit 0.
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


@pytest.mark.skipif(_IS_ROOT, reason="root can write anywhere; cannot simulate an unwritable parent")
def test_resolve_config_dir_falls_back_to_tempdir_on_mkdir_failure(tmp_path, monkeypatch):
    """An unwritable resolved dir forces the OUTER except → temp-dir fallback."""
    monkeypatch.delenv("SIEGE_USER_CONFIG", raising=False)
    read_only = tmp_path / "ro"
    read_only.mkdir()
    os.chmod(read_only, 0o500)  # r-x: cannot create children
    target = read_only / ".siege_utilities" / "config"

    result = _resolve_config_dir(target)

    assert result.exists(), "fallback dir should have been created"
    assert tempfile.gettempdir() in str(result)


@pytest.mark.skipif(_IS_ROOT, reason="root can write anywhere; cannot simulate an unwritable parent")
def test_resolve_config_dir_returns_resolved_when_both_paths_fail(tmp_path, monkeypatch):
    """BOTH the resolved dir and the temp-dir fallback unwritable forces the
    INNER except: warn and return the resolved path without raising."""
    monkeypatch.delenv("SIEGE_USER_CONFIG", raising=False)
    read_only = tmp_path / "ro"
    read_only.mkdir()
    os.chmod(read_only, 0o500)
    target = read_only / ".siege_utilities" / "config"

    ro_tmp = tmp_path / "ro_tmp"
    ro_tmp.mkdir()
    os.chmod(ro_tmp, 0o500)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(ro_tmp))

    result = _resolve_config_dir(target)

    assert result == target, "best-effort: returns the resolved path, never raises"


def test_resolve_config_dir_handles_missing_home(monkeypatch):
    """``Path.home()`` raising ``RuntimeError`` (HOME unresolvable) is caught and
    falls back to the temp dir, exercising the RuntimeError except."""
    monkeypatch.delenv("SIEGE_USER_CONFIG", raising=False)

    def _no_home():
        raise RuntimeError("HOME unresolvable")

    monkeypatch.setattr(user_config.Path, "home", staticmethod(_no_home))

    result = _resolve_config_dir()  # config_dir=None, no env → Path.home() raises

    assert tempfile.gettempdir() in str(result)


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
