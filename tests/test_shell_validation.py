"""Tests for siege_utilities.files.shell — command security validation (#578)."""

import subprocess

import pytest

from siege_utilities.files.shell import (
    SecurityError,
    ALLOWED_COMMANDS,
    validate_command_safety,
    run_subprocess,
)


class TestValidateCommandSafety:

    def test_allowed_command_returns_list(self):
        result = validate_command_safety("echo hello")
        assert result == ["echo", "hello"]

    def test_list_input_passes(self):
        result = validate_command_safety(["ls", "-la"])
        assert result == ["ls", "-la"]

    def test_disallowed_command_raises(self):
        with pytest.raises(SecurityError, match="not allowed"):
            validate_command_safety("python --version")

    def test_custom_allow_list(self):
        result = validate_command_safety("git status", allow_list={"git"})
        assert result == ["git", "status"]

    def test_empty_command_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_command_safety("")

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_command_safety([])

    def test_semicolon_blocked(self):
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety("echo ok; rm -rf /")

    def test_pipe_blocked(self):
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety("cat file | grep secret")

    def test_backtick_blocked(self):
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety("echo `whoami`")

    def test_dollar_sign_blocked(self):
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety(["echo", "$HOME"])

    def test_path_traversal_blocked(self):
        with pytest.raises(SecurityError, match="Path traversal"):
            validate_command_safety("cat ../../secret.txt")

    def test_sensitive_etc_passwd_blocked(self):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety("cat /etc/passwd")

    def test_sensitive_ssh_blocked(self):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(["cat", "~/.ssh/id_rsa"])

    def test_default_allow_list_is_read_only(self):
        dangerous = {"rm", "mv", "dd", "mkfs", "python", "bash", "sh"}
        assert ALLOWED_COMMANDS.isdisjoint(dangerous)


class TestRunSubprocess:

    def test_allowed_command_succeeds(self):
        output = run_subprocess("echo hello")
        assert "hello" in output

    def test_disallowed_command_raises(self):
        with pytest.raises(SecurityError):
            run_subprocess("python --version")

    def test_custom_allow_list(self):
        output = run_subprocess("true", allow_list={"true"})
        assert output == ""

    def test_timeout_raises(self):
        with pytest.raises(subprocess.TimeoutExpired):
            run_subprocess("sleep 10", allow_list={"sleep"}, timeout=1)
