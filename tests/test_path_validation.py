"""Tests for siege_utilities.files.validation and path containment (#1528)."""

import os
from pathlib import Path

import pytest

from siege_utilities.files.validation import (
    PathSecurityError,
    is_path_traversal_attempt,
    is_sensitive_path,
    validate_safe_path,
    validate_file_path,
    validate_directory_path,
    safe_join_paths,
)


class TestIsPathTraversalAttempt:

    def test_double_dot_detected(self):
        assert is_path_traversal_attempt("../../../etc/passwd") is True

    def test_home_tilde_detected(self):
        assert is_path_traversal_attempt("~/secret.txt") is True

    def test_percent_encoded_dots_are_literal(self):
        """Local filenames stay literal (writing-tests:1 correction, #1528)."""
        assert is_path_traversal_attempt("data/%2e%2e/etc") is False

    def test_percent_encoded_slash_is_literal(self):
        """Local filenames stay literal (writing-tests:1 correction, #1528)."""
        assert is_path_traversal_attempt("data%2ffile.txt") is False

    def test_null_byte_detected(self):
        assert is_path_traversal_attempt("file.txt\x00.jpg") is True

    def test_clean_relative_path(self):
        assert is_path_traversal_attempt("data/file.txt") is False

    def test_clean_absolute_path(self):
        assert is_path_traversal_attempt("/tmp/data/file.txt") is False


class TestIsSensitivePath:

    def test_etc_passwd(self):
        assert is_sensitive_path("/etc/passwd") is True

    def test_ssh_in_path(self):
        assert is_sensitive_path("/home/user/.ssh/id_rsa") is True

    def test_private_key_id_rsa(self):
        assert is_sensitive_path("/some/path/id_rsa") is True

    def test_private_key_id_ecdsa(self):
        assert is_sensitive_path("/some/path/id_ecdsa") is True

    def test_tmp_is_safe(self):
        assert is_sensitive_path("/tmp/data.txt") is False

    def test_user_data_is_safe(self, tmp_path):
        p = tmp_path / "my_data.csv"
        assert is_sensitive_path(str(p)) is False


class TestValidateSafePath:

    def test_clean_path_returns_path(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("ok")
        result = validate_safe_path(str(f))
        assert result == f.resolve()

    def test_empty_path_raises_value_error(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_safe_path("")

    def test_null_byte_raises(self):
        with pytest.raises(PathSecurityError, match="Null byte"):
            validate_safe_path("file\x00.txt")

    def test_traversal_raises(self):
        with pytest.raises(PathSecurityError, match="traversal"):
            validate_safe_path("../../etc/shadow")

    def test_absolute_disallowed_when_flag_false(self):
        with pytest.raises(PathSecurityError, match="Absolute paths not allowed"):
            validate_safe_path("/tmp/file.txt", allow_absolute=False)

    def test_base_directory_enforced(self, tmp_path):
        outside = tmp_path.parent / "outside.txt"
        with pytest.raises(PathSecurityError, match="outside base directory"):
            validate_safe_path(str(outside), base_directory=str(tmp_path))

    def test_within_base_directory_passes(self, tmp_path):
        f = tmp_path / "inside.txt"
        f.write_text("ok")
        result = validate_safe_path(str(f), base_directory=str(tmp_path))
        assert result == f.resolve()


class TestValidateFilePath:

    def test_existing_file_passes(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("col1,col2\n1,2\n")
        result = validate_file_path(str(f), must_exist=True)
        assert result == f.resolve()

    def test_nonexistent_must_exist_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_file_path(str(tmp_path / "nope.txt"), must_exist=True)

    def test_not_required_to_exist(self, tmp_path):
        result = validate_file_path(str(tmp_path / "future.txt"), must_exist=False)
        assert result.name == "future.txt"


class TestValidateDirectoryPath:

    def test_existing_dir_passes(self, tmp_path):
        result = validate_directory_path(str(tmp_path), must_exist=True)
        assert result == tmp_path.resolve()

    def test_nonexistent_must_exist_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_directory_path(str(tmp_path / "nope"), must_exist=True)

    def test_file_not_dir_raises(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("not a dir")
        with pytest.raises(ValueError, match="not a directory"):
            validate_directory_path(str(f), must_exist=True)


class TestSafeJoinPaths:

    def test_clean_join(self):
        result = safe_join_paths("data", "2024", "file.txt")
        assert result.name == "file.txt"

    def test_traversal_in_component_raises(self):
        with pytest.raises(PathSecurityError, match="traversal"):
            safe_join_paths("data", "../secret", "file.txt")

    def test_empty_args_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            safe_join_paths()

    def test_base_directory_enforced(self, tmp_path):
        with pytest.raises(PathSecurityError, match="outside base directory"):
            safe_join_paths("/tmp", "file.txt", base_directory=str(tmp_path))


class TestPathSafetyRegressions:
    """Corrected allow/deny cases must fail with the v4.0.0 validator."""

    @pytest.mark.parametrize("name", [
        "report..final.csv",
        "v1..2/",
        "dl/name%2Fwith.csv",
        "dl/name%2fwith.csv",
        "dl/%2e%2e/data.csv",
        "dl/%2E%2E/data.csv",
        "paid_rsa",
        "paid_dsa",
        "paid_ecdsa",
    ])
    def test_literal_local_names_allowed(self, tmp_path, monkeypatch, name):
        monkeypatch.chdir(tmp_path)
        expected = tmp_path.resolve() / name

        assert validate_safe_path(name, base_directory=tmp_path) == expected
        assert safe_join_paths(tmp_path, name) == expected
        assert is_path_traversal_attempt(name) is False
        assert is_sensitive_path(expected) is False

    @pytest.mark.parametrize("cwd", ["/root", "/dev/shm"])
    @pytest.mark.parametrize("with_base", [False, True])
    def test_container_working_directory_allowed(self, monkeypatch, cwd, with_base):
        # Simulate the container cwd without creating or accessing files there.
        with monkeypatch.context() as patch:
            patch.setattr(os, "getcwd", lambda: cwd)
            result = validate_safe_path(
                "data.csv", base_directory=cwd if with_base else None,
            )

        assert result == Path(cwd) / "data.csv"

    @pytest.mark.parametrize("component", [
        "/etc/cron.d/evil",
        Path("/etc/cron.d/evil"),
        "C:/outside/file.csv",
        r"C:\outside\file.csv",
        "C:outside.csv",
        r"\outside\file.csv",
        r"\\server\share\file.csv",
    ])
    def test_later_absolute_or_drive_component_raises(self, component):
        with pytest.raises(PathSecurityError, match="Absolute or drive-qualified"):
            safe_join_paths("data", component)

    def test_absolute_second_component_with_base_raises(self, tmp_path):
        # Even an absolute component inside the base must not discard its prefix.
        with pytest.raises(PathSecurityError, match="Absolute or drive-qualified"):
            safe_join_paths(tmp_path, tmp_path / "file.csv", base_directory=tmp_path)

    def test_unlisted_absolute_second_component_raises(self, tmp_path):
        # Use a real unblocked destination on every host, including macOS.
        with pytest.raises(PathSecurityError, match="Absolute or drive-qualified"):
            safe_join_paths("data", tmp_path / "outside.csv")

    def test_default_base_rejects_symlink_escape(self, tmp_path):
        base = tmp_path / "data"
        base.mkdir()
        sibling = tmp_path / "data-outside"
        sibling.mkdir()
        (base / "link").symlink_to(sibling, target_is_directory=True)

        with pytest.raises(PathSecurityError, match="outside base directory"):
            safe_join_paths(base, "link", "file.csv")

    @pytest.mark.parametrize("filename", ["name%2Fwith.csv", "%2e%2e.csv"])
    def test_generated_url_filename_is_literal(self, tmp_path, filename):
        from siege_utilities.files.remote import generate_local_path_from_url

        local_path = generate_local_path_from_url(
            f"https://example.com/{filename}", tmp_path, as_string=False,
        )

        assert validate_safe_path(local_path, base_directory=tmp_path) == tmp_path / filename
        assert local_path.name == filename

    def test_ssh_directory_itself_is_sensitive(self, tmp_path):
        with pytest.raises(PathSecurityError, match="sensitive path"):
            validate_safe_path(tmp_path / ".ssh", base_directory=tmp_path)

    def test_empty_base_still_enforces_containment(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(PathSecurityError, match="outside base directory"):
            validate_safe_path(tmp_path.parent / "outside.csv", base_directory="")


class TestPathSafetyProtection:
    """Existing protections remain enforced when false positives are removed."""

    @pytest.mark.parametrize("path", [
        "/etc/cron.d/x", "/home/u/.bashrc", "/etc/sudoers.d/x",
    ])
    def test_base_rejects_absolute_escape(self, tmp_path, path):
        # macOS resolves /etc to the separately blocked /private/etc.
        with pytest.raises(PathSecurityError, match="outside base directory|sensitive path"):
            validate_safe_path(path, base_directory=tmp_path)

    @pytest.mark.parametrize("path", [
        "../../etc/passwd",
        r"..\..\etc\passwd",
        "data/./../outside.csv",
        "C:../outside.csv",
        "//../share/file.csv",
    ])
    def test_real_parent_component_raises(self, tmp_path, path):
        with pytest.raises(PathSecurityError, match="traversal"):
            validate_safe_path(path, base_directory=tmp_path)
        with pytest.raises(PathSecurityError, match="traversal"):
            safe_join_paths(tmp_path, path, base_directory=tmp_path)

    @pytest.mark.parametrize("name", ["id_rsa", "id_dsa", "id_ecdsa", ".ssh/config"])
    def test_sensitive_target_under_base_raises(self, tmp_path, name):
        with pytest.raises(PathSecurityError, match="sensitive path"):
            validate_safe_path(tmp_path / name, base_directory=tmp_path)
        with pytest.raises(PathSecurityError, match="sensitive path"):
            safe_join_paths(tmp_path, name)

    @pytest.mark.parametrize("path", [
        "/root/.bash_history", "/root/.zsh_history",
        "/dev/mem", "/dev/kmem", "/dev/port",
    ])
    def test_explicit_sensitive_files_still_raise(self, path):
        with pytest.raises(PathSecurityError, match="sensitive path"):
            validate_safe_path(path, base_directory=Path(path).parent)

    def test_base_rejects_sibling_with_same_prefix(self, tmp_path):
        base = tmp_path / "data"

        with pytest.raises(PathSecurityError, match="outside base directory"):
            validate_safe_path(tmp_path / "data-outside" / "file.csv", base_directory=base)

    def test_explicit_base_rejects_symlink_escape(self, tmp_path):
        base = tmp_path / "data"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (base / "link").symlink_to(outside, target_is_directory=True)

        with pytest.raises(PathSecurityError, match="outside base directory"):
            validate_safe_path(base / "link" / "file.csv", base_directory=base)
        with pytest.raises(PathSecurityError, match="outside base directory"):
            safe_join_paths(base, "link", "file.csv", base_directory=base)

    def test_symlink_within_base_allowed(self, tmp_path):
        (tmp_path / "target").mkdir()
        (tmp_path / "link").symlink_to(tmp_path / "target", target_is_directory=True)

        assert safe_join_paths(tmp_path, "link", "file.csv") == tmp_path / "target" / "file.csv"

    def test_relative_join_with_explicit_base_uses_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert safe_join_paths("data", "file.csv", base_directory=tmp_path) == (
            tmp_path / "data" / "file.csv"
        )

    @pytest.mark.parametrize("error_type", [OSError, RuntimeError, TypeError])
    def test_resolution_failure_is_reported(self, monkeypatch, error_type):
        def fail_resolve(self, strict=False):
            raise error_type("cannot resolve path")

        monkeypatch.setattr(Path, "resolve", fail_resolve)

        assert is_sensitive_path("data.csv") is True
        with pytest.raises(ValueError, match="Invalid path: data.csv - cannot resolve path") as exc:
            validate_safe_path("data.csv")
        assert isinstance(exc.value.__cause__, error_type)
