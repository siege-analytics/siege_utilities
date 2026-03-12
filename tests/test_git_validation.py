"""Tests for siege_utilities.git.validation — git input sanitization."""
import pytest
from siege_utilities.git.validation import (
    GitSecurityError,
    has_dangerous_characters,
    validate_git_ref_name,
    validate_branch_name,
    validate_tag_name,
    validate_commit_message,
    validate_commit_hash,
    validate_remote_name,
    validate_repo_path,
    DANGEROUS_GIT_CHARS,
)


class TestHasDangerousCharacters:
    def test_safe_text(self):
        assert has_dangerous_characters("feature/my-branch") is False

    def test_semicolon(self):
        assert has_dangerous_characters("branch; rm -rf /") is True

    def test_pipe(self):
        assert has_dangerous_characters("name|evil") is True

    def test_dollar(self):
        assert has_dangerous_characters("$HOME") is True

    def test_backtick(self):
        assert has_dangerous_characters("`whoami`") is True

    def test_null_byte(self):
        assert has_dangerous_characters("abc\x00def") is True

    def test_newline(self):
        assert has_dangerous_characters("abc\ndef") is True

    def test_ampersand(self):
        assert has_dangerous_characters("a && b") is True

    def test_all_dangerous_chars(self):
        for ch in DANGEROUS_GIT_CHARS:
            assert has_dangerous_characters(f"x{ch}y") is True


class TestValidateGitRefName:
    def test_valid_branch(self):
        assert validate_git_ref_name("feature/my-branch", "branch") == "feature/my-branch"

    def test_valid_simple(self):
        assert validate_git_ref_name("main") == "main"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_git_ref_name("")

    def test_dangerous_chars_raises(self):
        with pytest.raises(GitSecurityError, match="dangerous"):
            validate_git_ref_name("branch; rm -rf /")

    def test_double_dot_raises(self):
        with pytest.raises(GitSecurityError):
            validate_git_ref_name("branch..name")

    def test_starts_with_dash_raises(self):
        with pytest.raises(GitSecurityError, match="cannot start with"):
            validate_git_ref_name("-badname")

    def test_lock_suffix_raises(self):
        with pytest.raises(GitSecurityError):
            validate_git_ref_name("branch.lock")

    def test_space_raises(self):
        with pytest.raises(GitSecurityError):
            validate_git_ref_name("branch name")

    def test_asterisk_raises(self):
        with pytest.raises(GitSecurityError):
            validate_git_ref_name("branch*")

    def test_tilde_raises(self):
        with pytest.raises(GitSecurityError):
            validate_git_ref_name("branch~1")

    def test_colon_raises(self):
        with pytest.raises(GitSecurityError):
            validate_git_ref_name("branch:name")


class TestValidateBranchName:
    def test_valid(self):
        assert validate_branch_name("develop") == "develop"

    def test_feature_branch(self):
        assert validate_branch_name("feature/en-236") == "feature/en-236"

    def test_injection_raises(self):
        with pytest.raises(GitSecurityError):
            validate_branch_name("$(cat /etc/passwd)")


class TestValidateTagName:
    def test_semver(self):
        assert validate_tag_name("v3.11.0") == "v3.11.0"

    def test_injection_raises(self):
        with pytest.raises(GitSecurityError):
            validate_tag_name("<script>alert(1)</script>")


class TestValidateCommitMessage:
    def test_valid(self):
        assert validate_commit_message("Fix bug") == "Fix bug"

    def test_multiline_ok(self):
        msg = "Title\n\nBody with details"
        assert validate_commit_message(msg) == msg

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_commit_message("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            validate_commit_message("x" * 10001)

    def test_custom_max_length(self):
        with pytest.raises(ValueError):
            validate_commit_message("x" * 100, max_length=50)

    def test_semicolon_raises(self):
        with pytest.raises(GitSecurityError, match="dangerous"):
            validate_commit_message("msg; rm -rf /")

    def test_null_byte_raises(self):
        with pytest.raises(GitSecurityError, match="dangerous"):
            validate_commit_message("msg\x00evil")


class TestValidateCommitHash:
    def test_short_hash(self):
        assert validate_commit_hash("a1b2c3d") == "a1b2c3d"

    def test_full_hash(self):
        h = "a" * 40
        assert validate_commit_hash(h) == h

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_commit_hash("")

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="length invalid"):
            validate_commit_hash("abc")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="length invalid"):
            validate_commit_hash("a" * 41)

    def test_non_hex_raises(self):
        with pytest.raises(ValueError, match="hexadecimal"):
            validate_commit_hash("zzzzzzzz")

    def test_injection_raises(self):
        with pytest.raises(GitSecurityError):
            validate_commit_hash("abc123; rm -rf /")


class TestValidateRemoteName:
    def test_origin(self):
        assert validate_remote_name("origin") == "origin"

    def test_upstream(self):
        assert validate_remote_name("upstream") == "upstream"

    def test_with_hyphen(self):
        assert validate_remote_name("my-remote") == "my-remote"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_remote_name("")

    def test_injection_raises(self):
        with pytest.raises(GitSecurityError):
            validate_remote_name("origin; curl evil.com")

    def test_dots_raises(self):
        with pytest.raises(GitSecurityError):
            validate_remote_name("origin.name")


class TestValidateRepoPath:
    def test_current_dir(self):
        result = validate_repo_path(".")
        assert result is not None
