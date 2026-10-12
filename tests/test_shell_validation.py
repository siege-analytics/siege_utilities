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

    @pytest.mark.parametrize("command", [
        'find . -delete',
        'find / -maxdepth 0 -exec sh -c "echo probe" {} +',
        'find . -fprint ~/.bashrc',
        'cat /etc//passwd',
        'cat /etc/./shadow',
        'grep -r password /home/u/.ssh',
    ])
    def test_command_safety_rejects_issue_1491_probes(self, command):
        with pytest.raises(SecurityError, match="not allowed|sensitive path"):
            validate_command_safety(command)

    @pytest.mark.parametrize("path", [
        '/etc///sudoers', '~/.ssh/id_rsa', '/home/other//.ssh/id_ed25519',
        '/root//config', '/var/./log/auth.log', '--file=/etc//passwd',
        '/etc/passwd', '/etc//passwd', '/etc/./shadow',
    ])
    def test_sensitive_path_alias_raises(self, path):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', path])

    @pytest.mark.parametrize("filename", ['report..final.csv', 'a..b.csv'])
    def test_filename_with_double_dots_is_allowed(self, filename):
        command = ['cat', filename]
        assert validate_command_safety(command) == command

    @pytest.mark.parametrize("path", [
        '/etc/passwd.bak', '/var/logrotate.conf', '/rootfs/data.csv',
    ])
    def test_sensitive_path_neighbor_is_allowed(self, path):
        command = ['cat', path]
        assert validate_command_safety(command) == command

    def test_traversal_to_sensitive_path_raises(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path.anchor)
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', '../../etc/passwd'])

    def test_expanded_home_alias_raises(self, monkeypatch, tmp_path):
        monkeypatch.setenv('HOME', str(tmp_path))
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', str(tmp_path / '.ssh' / 'id_rsa')])

    def test_sensitive_symlink_raises(self, tmp_path):
        alias = tmp_path / 'public.txt'
        alias.symlink_to('/etc/passwd')
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', str(alias)])

    def test_ordinary_path_is_returned_unchanged(self, tmp_path):
        command = ['cat', str(tmp_path) + '/./public.txt']
        assert validate_command_safety(command) == command

    @pytest.mark.parametrize('character', ['<', '>'])
    def test_redirection_character_raises(self, character):
        with pytest.raises(SecurityError, match="Forbidden character"):
            validate_command_safety(['echo', character, 'file'])

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

    def test_default_allow_list_excludes_command_runners_and_writers(self):
        dangerous = {"rm", "mv", "dd", "mkfs", "python", "bash", "sh", "find"}
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
