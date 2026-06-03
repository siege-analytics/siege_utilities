"""Tests for siege_utilities.files.validation — path security validation (#578)."""

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

    def test_url_encoded_traversal_detected(self):
        assert is_path_traversal_attempt("data/%2e%2e/etc") is True

    def test_url_encoded_slash_detected(self):
        assert is_path_traversal_attempt("data%2ffile.txt") is True

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
