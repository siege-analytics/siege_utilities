"""Tests for siege_utilities.files.validation — path security validation (#578)."""

import shutil

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


class TestDirectoryControlCharacters:
    """New directory names must not contain control characters (#1692)."""

    @pytest.fixture(autouse=True)
    def _remove_tmp_path(self, tmp_path):
        # Some cases create control-character names on purpose; never leave
        # them in pytest's basetemp for file watchers to trip on (#1690).
        yield
        shutil.rmtree(tmp_path, ignore_errors=True)

    @pytest.mark.parametrize("name", ["a\nb", "\x1b[31m", "\x16", "x\x7f", "\x9a"])
    def test_new_component_rejected(self, tmp_path, name):
        with pytest.raises(PathSecurityError, match="Control character"):
            validate_directory_path(str(tmp_path / name / "child"), must_exist=False)

    def test_message_escapes_the_name(self, tmp_path):
        with pytest.raises(PathSecurityError) as excinfo:
            validate_directory_path(str(tmp_path / "\x1b[31m"), must_exist=False)
        assert "\x1b" not in str(excinfo.value)
        assert "\\x1b" in str(excinfo.value)

    def test_existing_directory_still_validates(self, tmp_path):
        existing = tmp_path / "odd\x16name"
        existing.mkdir()
        assert validate_directory_path(str(existing), must_exist=True) == existing.resolve()
        assert validate_directory_path(str(existing), must_exist=False) == existing.resolve()

    def test_clean_child_of_existing_odd_directory_allowed(self, tmp_path):
        existing = tmp_path / "odd\x16name"
        existing.mkdir()
        child = existing / "reports"
        assert validate_directory_path(str(child), must_exist=False) == child.resolve()

    def test_file_validation_unaffected(self, tmp_path):
        assert validate_file_path(str(tmp_path / "a\nb.txt")).name == "a\nb.txt"

    def test_printable_unicode_allowed(self, tmp_path):
        target = tmp_path / "données é 日本"
        assert validate_directory_path(str(target), must_exist=False) == target.resolve()

    def test_over_long_new_component_is_left_to_mkdir(self, tmp_path):
        """Path.exists raises ENAMETOOLONG on 3.11; the walk must not."""
        target = tmp_path / ("a" * 300) / "b"
        assert validate_directory_path(str(target), must_exist=False) == target.resolve()

    def test_debug_log_escapes_the_name(self, tmp_path, caplog):
        caplog.set_level("DEBUG", logger="siege_utilities.files.validation")
        with pytest.raises(PathSecurityError):
            validate_directory_path(str(tmp_path / "esc\x1b[31m"), must_exist=False)
        assert "\x1b" not in caplog.text
        assert "\\x1b" in caplog.text

    def test_zip_named_subdirectory_is_validated(self, tmp_path):
        import zipfile
        from siege_utilities.files.paths import unzip_file_to_directory

        archive = tmp_path / "evil\x1b[31m.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("x.txt", "x")
        out = tmp_path / "out"
        with pytest.raises(PathSecurityError, match="Control character"):
            unzip_file_to_directory(archive, out)
        assert not (out / "evil\x1b[31m").exists()

    def test_dot_dot_zip_stem_no_longer_escapes_extract_dir(self, tmp_path):
        """'...zip' has stem '..' before Python 3.14 (3.14 parses it as having
        no suffix); with stem '..' it used to extract into extract_to's parent."""
        import zipfile
        from siege_utilities.files.paths import unzip_file_to_directory

        archive = tmp_path / "...zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("x.txt", "x")
        out = tmp_path / "out"
        out.mkdir()
        # On main, is_path_traversal_attempt matches ".." anywhere in the
        # string, so "...zip" is refused on every Python version; the stem-'..'
        # case must be refused. Either way nothing may land outside out/.
        try:
            extracted = unzip_file_to_directory(archive, out)
        except PathSecurityError as exc:
            assert "traversal" in str(exc)
        else:
            assert archive.stem != ".."
            assert extracted.parent == out.resolve()
        assert not (tmp_path / "x.txt").exists()

    @pytest.mark.parametrize("path", ["esc\x1b[31m\x00", "../esc\x1b[31m"])
    def test_rejection_messages_escape_the_path(self, path):
        with pytest.raises(PathSecurityError) as excinfo:
            validate_safe_path(path)
        assert "\x1b" not in str(excinfo.value)
        assert "\\x1b" in str(excinfo.value)


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
