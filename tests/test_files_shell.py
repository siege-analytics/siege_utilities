"""Error-path tests for siege_utilities.files.shell (SU-4b)."""

import pytest

from siege_utilities.files.shell import (
    SecurityError,
    validate_command_safety,
    run_subprocess,
)


class TestValidateCommandSafetyErrors:
    """Error paths for validate_command_safety."""

    def test_empty_string_raises(self):
        """Empty command string must raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            validate_command_safety("")

    def test_empty_list_raises(self):
        """Empty command list must raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            validate_command_safety([])

    def test_none_raises(self):
        """None command must raise ValueError."""
        with pytest.raises((ValueError, TypeError)):
            validate_command_safety(None)

    def test_disallowed_command_raises_security_error(self):
        """Command not in whitelist must raise SecurityError."""
        with pytest.raises(SecurityError, match="not allowed"):
            validate_command_safety("rm -rf /")

    def test_semicolon_injection_raises(self):
        """Semicolon in argument must raise SecurityError."""
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety(["ls", "foo;bar"])

    def test_pipe_injection_raises(self):
        """Pipe in argument must raise SecurityError."""
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety(["ls", "foo|bar"])

    def test_backtick_injection_raises(self):
        """Backtick in argument must raise SecurityError."""
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety(["ls", "foo`id`"])

    def test_dollar_injection_raises(self):
        """Dollar sign in argument must raise SecurityError."""
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety(["ls", "$HOME"])

    def test_path_traversal_raises(self):
        """Path traversal (..) must raise SecurityError."""
        with pytest.raises(SecurityError, match="Path traversal"):
            validate_command_safety(["ls", "../../../etc"])

    def test_sensitive_path_raises(self):
        """Access to /etc/passwd must raise SecurityError."""
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(["cat", "/etc/passwd"])

    def test_invalid_shell_syntax_raises(self):
        """Unterminated quote must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid command syntax"):
            validate_command_safety("ls 'unterminated")


class TestValidateCommandSafetyHappyPath:
    """Sanity checks for validate_command_safety."""

    def test_allowed_command_returns_list(self):
        """Allowed command returns validated list."""
        result = validate_command_safety("ls -la")
        assert result == ["ls", "-la"]

    def test_custom_allow_list(self):
        """Custom allow_list overrides defaults."""
        result = validate_command_safety("python --version", allow_list={"python"})
        assert result[0] == "python"


class TestRunSubprocessErrors:
    """Error paths for run_subprocess."""

    def test_disallowed_command_raises(self):
        """Disallowed command propagates SecurityError."""
        with pytest.raises(SecurityError):
            run_subprocess("rm -rf /tmp/test")

    def test_empty_command_raises(self):
        """Empty command propagates ValueError."""
        with pytest.raises(ValueError):
            run_subprocess("")
