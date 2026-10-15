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
import tempfile
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


@pytest.fixture(autouse=True)
def isolated_config_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep constructor side effects and cached tempfile paths inside the test."""
    monkeypatch.setenv("SIEGE_USER_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setattr(tempfile, "tempdir", None)


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

    def disk_full(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", disk_full)

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

    with patch(
        "siege_utilities.config.user_config.yaml.dump",
        side_effect=TypeError("unserialisable object"),
    ), caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
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


def test_export_config_scrubs_database_secrets_and_writes_0600(tmp_path: Path) -> None:
    """Shareable exports must omit database secrets and be private under umask 022."""
    mgr = UserConfigManager(config_dir=tmp_path / "config")
    password = "export-sentinel-password"
    connection = f"postgresql://test:{password}@localhost/test"
    duckdb_path = "/private/export-sentinel.duckdb"
    mgr.update_user_profile(
        username="export-user",
        postgresql_connection=connection,
        duckdb_path=duckdb_path,
        google_analytics_key="google-test-key",
        facebook_business_key="facebook-test-key",
        census_api_key="census-test-key",
    )
    original_profile = mgr.user_config_file.read_bytes()
    output = tmp_path / "export.yaml"
    previous_umask = os.umask(0o022)
    try:
        mgr.export_config(str(output))
    finally:
        os.umask(previous_umask)

    exported = output.read_text(encoding="utf-8")
    # Report both defects even when scrubbing fails before the mode check.
    assert {
        "password_present": password in exported,
        "dsn_present": connection in exported,
        "duckdb_path_present": duckdb_path in exported,
        "mode": oct(stat.S_IMODE(output.stat().st_mode)),
    } == {
        "password_present": False,
        "dsn_present": False,
        "duckdb_path_present": False,
        "mode": oct(0o600),
    }
    assert "postgresql_connection:" not in exported
    assert "duckdb_path:" not in exported
    assert "google_analytics_key:" not in exported
    assert "facebook_business_key:" not in exported
    assert "census_api_key:" not in exported
    assert "username: export-user" in exported
    assert mgr.user_profile.postgresql_connection == connection
    assert mgr.user_profile.duckdb_path == duckdb_path
    assert mgr.user_config_file.read_bytes() == original_profile


@pytest.mark.parametrize(
    ("operation", "error"),
    [
        ("yaml.dump", yaml.YAMLError("serialization failed")),
        ("os.replace", PermissionError("replacement denied")),
    ],
)
def test_failed_export_preserves_file_and_removes_temporary_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
    operation: str, error: Exception,
) -> None:
    """Serialization or replacement failure must log and leave the old export intact."""
    mgr = UserConfigManager(config_dir=tmp_path / "config")
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    output = export_dir / "export.yaml"
    output.write_text("username: original\n", encoding="utf-8")

    with patch(
        f"siege_utilities.config.user_config.{operation}", side_effect=error,
    ), caplog.at_level(logging.INFO, logger="siege_utilities.config.user_config"):
        mgr.export_config(str(output))

    assert output.read_text(encoding="utf-8") == "username: original\n"
    assert list(export_dir.iterdir()) == [output]
    assert "Failed to export configuration" in caplog.text
    assert "Configuration exported to:" not in caplog.text


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


@pytest.mark.parametrize("service", ["census", "google_analytics", "facebook_business"])
def test_api_key_file_and_directory_modes_under_umask_022(
    tmp_path: Path, service: str,
) -> None:
    """Credential files must be 0600 even with the usual 022 process umask."""
    previous_umask = os.umask(0o022)
    try:
        mgr = UserConfigManager(config_dir=tmp_path / "private-config")
        mgr.set_api_key(service, "test-key")
    finally:
        os.umask(previous_umask)

    file_mode = os.stat(mgr.user_config_file).st_mode & 0o777
    assert file_mode == 0o600, f"file mode is {file_mode:04o}, expected 0600"
    assert os.stat(mgr.config_dir).st_mode & 0o777 == 0o700
    assert UserConfigManager(config_dir=mgr.config_dir).get_api_key(service) == "test-key"


def test_initial_config_file_and_directory_are_private(tmp_path: Path) -> None:
    """First construction writes a private file before any credential setter."""
    previous_umask = os.umask(0o022)
    try:
        mgr = UserConfigManager(config_dir=tmp_path / "private-config")
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(mgr.config_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(mgr.user_config_file.stat().st_mode) == 0o600


def test_database_save_tightens_existing_file_and_directory(tmp_path: Path) -> None:
    """Previously world-readable configs become private when saved again."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(mode=0o755)
    config_dir.chmod(0o755)
    config_file = config_dir / "user_config.yaml"
    config_file.write_text("preferred_download_directory: /unused\n", encoding="utf-8")
    config_file.chmod(0o644)
    mgr = UserConfigManager(config_dir=config_dir)
    connection = "postgresql://test:dummy-password@localhost/test"
    mgr.set_database_connection("postgresql", connection)

    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(config_dir.stat().st_mode) == 0o700
    assert yaml.safe_load(config_file.read_text())["postgresql_connection"] == connection


@pytest.fixture
def fallback_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Both fallback layouts let the same refusal tests expose v4.0.0."""
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    monkeypatch.setenv("TMPDIR", str(temp_root))
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("block primary config directory creation", encoding="utf-8")
    legacy = temp_root / "siege_utilities" / "config"
    fallback = temp_root / f"siege_utilities-{os.getuid()}"
    return blocked, legacy, fallback


def test_fallback_uses_private_per_uid_directory(
    fallback_paths: tuple[Path, Path, Path],
) -> None:
    primary, legacy, fallback = fallback_paths
    previous_umask = os.umask(0o022)
    try:
        mgr = UserConfigManager(config_dir=primary)
        mgr.set_api_key("census", "test-key")
    finally:
        os.umask(previous_umask)

    assert mgr.config_dir == fallback
    assert stat.S_IMODE(fallback.stat().st_mode) == 0o700
    assert fallback.stat().st_uid == os.getuid()
    assert stat.S_IMODE(mgr.user_config_file.stat().st_mode) == 0o600
    assert not legacy.exists()


def test_explicit_private_config_dir_never_needs_posix_uid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit config path still works on platforms without os.getuid."""
    monkeypatch.delattr(os, "getuid")

    def no_fallback() -> Path:
        pytest.fail("An explicit writable config_dir must not resolve a fallback")

    monkeypatch.setattr(UserConfigManager, "_fallback_config_dir", staticmethod(no_fallback))
    mgr = UserConfigManager(config_dir=tmp_path / "private")
    mgr.set_api_key("census", "test-key")
    assert mgr.get_api_key("census") == "test-key"
    assert mgr.user_config_file.exists()


def test_no_uid_default_uses_private_appdata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No POSIX uid uses per-user LocalAppData instead of shared temp."""
    monkeypatch.delattr(os, "getuid")
    monkeypatch.delenv("SIEGE_USER_CONFIG_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    mgr = UserConfigManager()
    assert mgr.config_dir == tmp_path / "LocalAppData" / "siege_utilities" / "config"
    assert mgr.user_config_file.exists()


def test_no_uid_unwritable_explicit_path_falls_back_to_appdata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed explicit path uses private AppData, not a shared temp path."""
    monkeypatch.delattr(os, "getuid")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    mgr = UserConfigManager(config_dir=blocked)
    assert mgr.config_dir == tmp_path / "LocalAppData" / "siege_utilities" / "config"
    assert mgr.user_config_file.exists()


def test_windows_style_os_without_fchmod_can_save_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native Windows lacks getuid/fchmod; save/export must still work."""
    from types import SimpleNamespace
    from siege_utilities.config import user_config as config_module

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.delenv("SIEGE_USER_CONFIG_DIR", raising=False)
    windows_os = SimpleNamespace(
        name="nt", environ=os.environ, replace=os.replace,
        access=os.access, W_OK=os.W_OK,
    )
    monkeypatch.setattr(config_module, "os", windows_os)
    mgr = UserConfigManager()
    mgr.set_api_key("census", "windows-test-secret")
    assert mgr.get_api_key("census") == "windows-test-secret"
    output = tmp_path / "shareable.yaml"
    mgr.export_config(str(output))
    assert "windows-test-secret" not in output.read_text(encoding="utf-8")


def test_no_uid_rejects_symlinked_appdata_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A substituted AppData config leaf must not be read through a symlink."""
    monkeypatch.delattr(os, "getuid")
    monkeypatch.delenv("SIEGE_USER_CONFIG_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    target = tmp_path / "shared"
    target.mkdir()
    config_parent = tmp_path / "LocalAppData" / "siege_utilities"
    config_parent.mkdir(parents=True)
    (config_parent / "config").symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="not a real directory"):
        UserConfigManager()
    assert list(target.iterdir()) == []


def test_no_uid_without_appdata_uses_home_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absent AppData env vars still resolve a per-user home profile path."""
    monkeypatch.delattr(os, "getuid")
    for name in ("SIEGE_USER_CONFIG_DIR", "LOCALAPPDATA", "APPDATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "profile"))
    mgr = UserConfigManager()
    assert mgr.config_dir == tmp_path / "profile" / "AppData" / "Local" / "siege_utilities" / "config"
    assert mgr.user_config_file.exists()


def test_no_uid_without_appdata_or_home_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No guessable shared-temp fallback if a private user location is unknown."""
    monkeypatch.delattr(os, "getuid")
    for name in ("SIEGE_USER_CONFIG_DIR", "LOCALAPPDATA", "APPDATA"):
        monkeypatch.delenv(name, raising=False)

    def no_home(cls):
        raise RuntimeError("home unavailable")

    monkeypatch.setattr(Path, "home", classmethod(no_home))
    with pytest.raises(ValueError, match="Cannot locate a private user config directory"):
        UserConfigManager()


@pytest.mark.parametrize("mode", [0o777, 0o770, 0o707], ids=["0777", "0770", "0707"])
def test_unsafe_fallback_permissions_raise(
    fallback_paths: tuple[Path, Path, Path], mode: int,
) -> None:
    """A planted writable fallback must be refused before reading or chmod."""
    primary, legacy, fallback = fallback_paths
    for directory in (legacy, fallback):
        directory.mkdir(parents=True)
        directory.chmod(mode)
        (directory / "user_config.yaml").write_text("username: planted\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsafe fallback config directory.*group/other-writable"):
        UserConfigManager(config_dir=primary)

    assert stat.S_IMODE(fallback.stat().st_mode) == mode
    assert (fallback / "user_config.yaml").read_text() == "username: planted\n"


def test_unsafe_fallback_permissions_raise_when_home_resolution_fails(
    fallback_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, legacy, fallback = fallback_paths
    for directory in (legacy, fallback):
        directory.mkdir(parents=True)
        directory.chmod(0o777)
        (directory / "user_config.yaml").write_text(
            "preferred_download_directory: /unused\n", encoding="utf-8",
        )
    monkeypatch.delenv("SIEGE_USER_CONFIG_DIR")

    def missing_home() -> Path:
        raise RuntimeError("could not determine home directory")

    monkeypatch.setattr(Path, "home", staticmethod(missing_home))
    with pytest.raises(ValueError, match="Unsafe fallback config directory"):
        UserConfigManager()


def test_fallback_symlink_raises_without_touching_target(
    fallback_paths: tuple[Path, Path, Path], tmp_path: Path,
) -> None:
    primary, legacy, fallback = fallback_paths
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    legacy.parent.mkdir()
    legacy.symlink_to(target, target_is_directory=True)
    fallback.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="Unsafe fallback config directory.*real directory"):
        UserConfigManager(config_dir=primary)

    assert list(target.iterdir()) == []
    assert fallback.is_symlink()


def test_fallback_regular_file_raises(fallback_paths: tuple[Path, Path, Path]) -> None:
    primary, legacy, fallback = fallback_paths
    legacy.parent.mkdir()
    legacy.write_text("planted", encoding="utf-8")
    fallback.write_text("planted", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsafe fallback config directory.*real directory"):
        UserConfigManager(config_dir=primary)

    assert fallback.read_text() == "planted"


def test_fallback_wrong_owner_raises(
    fallback_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate a foreign st_uid; a real cross-uid chown needs privileges."""
    primary, legacy, fallback = fallback_paths
    for directory in (legacy, fallback):
        directory.mkdir(mode=0o700, parents=True)
    original_lstat = Path.lstat

    def foreign_owner(path: Path) -> os.stat_result:
        metadata = original_lstat(path)
        if path == fallback:
            fields = list(metadata)
            fields[4] = os.getuid() + 1
            return os.stat_result(fields)
        return metadata

    monkeypatch.setattr(Path, "lstat", foreign_owner)
    with pytest.raises(ValueError, match=f"Unsafe fallback config directory.*owned by uid {os.getuid()}"):
        UserConfigManager(config_dir=primary)

    assert list(fallback.iterdir()) == []


def test_read_only_fallback_does_not_load_unvalidated_config(
    fallback_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An OSError preparing fallback must not permit reading a planted config."""
    primary, legacy, fallback = fallback_paths
    for directory in (legacy, fallback):
        directory.mkdir(parents=True)
        (directory / "user_config.yaml").write_text("username: planted\n", encoding="utf-8")

    def denied(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("directory access denied")

    monkeypatch.setattr(Path, "mkdir", denied)
    mgr = UserConfigManager(config_dir=primary)

    assert mgr._read_only is True
    assert mgr.user_profile.username == ""


@pytest.mark.parametrize("error", [OSError("disk full"), yaml.YAMLError("serialization failed")])
def test_failed_atomic_save_preserves_file_and_removes_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture, error: Exception,
) -> None:
    mgr = UserConfigManager(config_dir=tmp_path / "config")
    mgr.set_api_key("census", "original-key")
    original = mgr.user_config_file.read_bytes()

    def failed_dump(*args: Any, **kwargs: Any) -> None:
        raise error

    monkeypatch.setattr(yaml, "dump", failed_dump)
    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr.set_api_key("census", "replacement-key")

    assert mgr.user_config_file.read_bytes() == original
    assert list(mgr.config_dir.iterdir()) == [mgr.user_config_file]
    assert "Failed to save user config" in caplog.text


def test_atomic_replace_error_preserves_file_and_removes_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    mgr = UserConfigManager(config_dir=tmp_path / "config")
    original = mgr.user_config_file.read_bytes()

    def denied(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("replacement denied")

    monkeypatch.setattr(os, "replace", denied)
    with caplog.at_level(logging.ERROR, logger="siege_utilities.config.user_config"):
        mgr.set_api_key("census", "replacement-key")

    assert mgr.user_config_file.read_bytes() == original
    assert list(mgr.config_dir.iterdir()) == [mgr.user_config_file]
    assert "Failed to save user config" in caplog.text
