"""Error-path coverage (SU-4b) for siege_utilities.config.user_config.

Every except block in user_config.py has a matching test that forces
the exception and asserts on the handler's behavior. Line refs below
match user_config.py at the time of writing:

- L117 (__init__ mkdir):        PermissionError/OSError -> TMPDIR fallback
- L126 (__init__ fallback mkdir): TMPDIR fallback also fails -> read-only
- L144 (_resolve_config_dir):   Path.home() RuntimeError/KeyError -> TMPDIR
- L158 (_load_user_profile):    OSError/YAMLError/ValueError/KeyError -> defaults
- L174 (_save_user_profile):    OSError/YAMLError/TypeError -> log.error
- L361 (export_config):         OSError/YAMLError -> log.error, no raise
- L382 (import_config):         OSError/YAMLError/AttributeError -> log.error
- L439 (get_download_directory): ImportError/OSError/YAMLError/ValueError -> log.debug
- L449 (get_download_directory): OSError on mkdir -> pass (writability check owns)

Companion to tests/test_user_config_unwritable_home.py, which covers
the mkdir-permission case for the __init__ path; this file covers the
remaining eight handlers plus a complementary L117 permutation.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from siege_utilities.config.user_config import (
    UserConfigManager,
    UserProfile,
    get_download_directory,
)


# ---------------------------------------------------------------------------
# L117 — __init__: primary config_dir.mkdir raises → TMPDIR fallback
# ---------------------------------------------------------------------------


def test_line_117_permission_error_on_primary_mkdir_falls_back_to_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L117: PermissionError on primary mkdir → warning logged + TMPDIR fallback."""
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmpdir))

    original_mkdir = Path.mkdir
    calls: list[Path] = []

    def selective_raise(self: Path, *args: Any, **kwargs: Any) -> None:
        calls.append(self)
        if len(calls) == 1:
            raise PermissionError(f"denied: {self}")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", selective_raise)

    with caplog.at_level(logging.WARNING, logger="siege_utilities.config.user_config"):
        mgr = UserConfigManager(config_dir=tmp_path / "denied")

    assert str(tmpdir) in str(mgr.config_dir)
    assert mgr._read_only is False
    assert any("Cannot create config dir" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# L126 — __init__: TMPDIR fallback mkdir also raises → read-only mode
# ---------------------------------------------------------------------------


def test_line_126_permission_error_on_fallback_mkdir_sets_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L126: both primary and fallback mkdir raise → mgr._read_only is True."""
    monkeypatch.setenv("TMPDIR", str(tmp_path / "unreachable"))

    def always_raise(self: Path, *args: Any, **kwargs: Any) -> None:
        raise PermissionError(f"denied: {self}")

    monkeypatch.setattr(Path, "mkdir", always_raise)

    with caplog.at_level(logging.WARNING, logger="siege_utilities.config.user_config"):
        mgr = UserConfigManager(config_dir=tmp_path / "denied")

    assert mgr._read_only is True
    assert any("unwritable" in r.message and "read-only" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# L144 — _resolve_config_dir: Path.home() raises RuntimeError → TMPDIR
# ---------------------------------------------------------------------------


def test_line_144_home_raises_runtime_error_falls_back_to_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L144: Path.home() raises RuntimeError → TMPDIR fallback."""
    monkeypatch.delenv("SIEGE_USER_CONFIG_DIR", raising=False)
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    def boom() -> Path:
        raise RuntimeError("could not determine home directory")

    monkeypatch.setattr(Path, "home", staticmethod(boom))

    resolved = UserConfigManager._resolve_config_dir()

    assert str(tmp_path) in str(resolved)
    assert "siege_utilities" in str(resolved)


def test_line_144_home_raises_key_error_falls_back_to_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L144: Path.home() raises KeyError (missing HOME env) → TMPDIR fallback."""
    monkeypatch.delenv("SIEGE_USER_CONFIG_DIR", raising=False)
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    def boom() -> Path:
        raise KeyError("HOME")

    monkeypatch.setattr(Path, "home", staticmethod(boom))

    resolved = UserConfigManager._resolve_config_dir()

    assert str(tmp_path) in str(resolved)


# ---------------------------------------------------------------------------
# L158 — _load_user_profile: YAML/OSError/ValueError/KeyError → defaults
# ---------------------------------------------------------------------------


def test_line_158_malformed_yaml_returns_default_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L158: YAMLError parsing user_config.yaml → default UserProfile + warning."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "user_config.yaml").write_text("this: is: not: valid: yaml: [\n")

    with caplog.at_level(logging.WARNING, logger="siege_utilities.config.user_config"):
        mgr = UserConfigManager()

    assert isinstance(mgr.user_profile, UserProfile)
    assert any("Failed to load user config" in r.message for r in caplog.records)


def test_line_158_unknown_field_raises_type_error_returns_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L158: YAML with unknown UserProfile field triggers dataclass TypeError.

    TypeError is not in the except tuple (OSError/YAMLError/ValueError/KeyError).
    The handler catches ValueError/KeyError shapes; TypeError propagates. This
    test documents the current contract — the handler does NOT swallow every
    error shape.
    """
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "user_config.yaml").write_text("nonexistent_field: value\n")

    with pytest.raises(TypeError):
        UserConfigManager()


# ---------------------------------------------------------------------------
# L174 — _save_user_profile: OSError/YAMLError/TypeError → log.error, no raise
# ---------------------------------------------------------------------------


def test_line_174_save_os_error_logged_not_raised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L174: OSError during save is logged; caller does not see the exception."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    mgr = UserConfigManager()

    original_open = open

    def boom_open(path: Any, *args: Any, **kwargs: Any) -> Any:
        if str(path).endswith("user_config.yaml"):
            raise OSError("disk full")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", boom_open)

    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr._save_user_profile()

    assert any("Failed to save user config" in r.message for r in caplog.records)


def test_line_174_save_type_error_logged_not_raised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L174: TypeError from yaml.dump is logged, not raised."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    mgr = UserConfigManager()

    def raise_type_error(*args: Any, **kwargs: Any) -> None:
        raise TypeError("unserialisable object")

    monkeypatch.setattr(
        "siege_utilities.config.user_config.yaml.dump",
        raise_type_error,
    )

    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr._save_user_profile()

    assert any("Failed to save user config" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# L361 — export_config: OSError/YAMLError → log.error, no raise
# ---------------------------------------------------------------------------


def test_line_361_export_os_error_logged_not_raised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L361: export to unwritable path is logged; caller sees no exception."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    mgr = UserConfigManager()

    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr.export_config(str(tmp_path / "nonexistent-dir" / "out.yaml"))

    assert any("Failed to export configuration" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# L382 — import_config: OSError/YAMLError/AttributeError → log.error
# ---------------------------------------------------------------------------


def test_line_382_import_missing_file_logged_not_raised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L382: import from missing path logs error, does not raise FileNotFoundError."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    mgr = UserConfigManager()

    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr.import_config(str(tmp_path / "does-not-exist.yaml"))

    assert any("Failed to import configuration" in r.message for r in caplog.records)


def test_line_382_import_malformed_yaml_logged_not_raised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L382: malformed YAML during import is logged, not raised."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    mgr = UserConfigManager()

    bad = tmp_path / "bad.yaml"
    bad.write_text("this: is: not: valid: [\n")

    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr.import_config(str(bad))

    assert any("Failed to import configuration" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# L439 — get_download_directory: client-profile load failure → log.debug
# ---------------------------------------------------------------------------


def test_line_439_client_profile_import_error_falls_through_to_user_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L439: enhanced_config ImportError → fall-through to user default."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))

    with patch(
        "siege_utilities.config.enhanced_config.load_client_profile",
        side_effect=ImportError("simulated missing extra"),
    ), caplog.at_level(logging.DEBUG, logger="siege_utilities.config.user_config"):
        result = get_download_directory(client_code="ACME")

    assert isinstance(result, Path)
    assert any("Could not load client profile" in r.message for r in caplog.records)


def test_line_439_client_profile_value_error_falls_through_to_user_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """L439: enhanced_config ValueError → fall-through to user default."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))

    with patch(
        "siege_utilities.config.enhanced_config.load_client_profile",
        side_effect=ValueError("bad client code"),
    ), caplog.at_level(logging.DEBUG, logger="siege_utilities.config.user_config"):
        result = get_download_directory(client_code="BAD")

    assert isinstance(result, Path)
    assert any("Could not load client profile" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# L449 — get_download_directory: mkdir OSError → pass (writability check owns)
# ---------------------------------------------------------------------------


def test_line_449_mkdir_os_error_falls_through_to_writability_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L449: mkdir OSError is silently swallowed; writability check downstream owns the outcome.

    Documents the current contract: L449 uses `except OSError: pass` and
    defers to the `is_dir() / os.access(W_OK)` guard on the next lines
    to decide the fallback path. This test verifies that a mkdir failure
    does not raise but does route through the writability check.
    """
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path))
    unwritable = tmp_path / "readonly-target"
    unwritable.mkdir()
    unwritable.chmod(stat.S_IREAD | stat.S_IEXEC)  # 0500

    try:
        # The L449 handler is `except OSError: pass` — it does NOT raise. The
        # subsequent writability check (`is_dir() / os.access(W_OK)`) owns the
        # outcome and raises OSError with an actionable message. Asserting that
        # raise proves the L449 handler routed through correctly (rather than
        # bubbling the original mkdir OSError).
        with pytest.raises(OSError, match="Download directory is not writable"):
            get_download_directory(specific_path=str(unwritable / "subdir"))
    finally:
        unwritable.chmod(stat.S_IRWXU)
