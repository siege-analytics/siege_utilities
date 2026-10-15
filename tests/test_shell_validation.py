"""Tests for siege_utilities.files.shell — command security validation (#578)."""

import os
import subprocess
from unittest.mock import patch

import pytest

from siege_utilities.files.operations import run_command
from siege_utilities.files.shell import (
    SecurityError,
    ALLOWED_COMMANDS,
    validate_command_safety,
    run_subprocess,
)


class TestValidateCommandSafety:

    @pytest.mark.parametrize("command", [
        pytest.param(['date', '-uf/etc/passwd'], id='date-uf'),
        pytest.param(['date', '-Rf/etc//passwd'], id='date-Rf'),
        pytest.param(['grep', '-rf/etc/shadow', '.'], id='grep-rf'),
        pytest.param(['grep', '-hf/proc/self/environ', 'x'], id='grep-hf'),
    ])
    def test_clustered_short_option_sensitive_path_raises(self, command):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(command)

    @pytest.mark.parametrize("command", [
        ['date', '-ufpasswd'], ['grep', '-rhfpasswd', 'input.txt'],
    ])
    def test_clustered_short_option_cwd_relative_path_raises(self, command):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(command, cwd='/etc')

    @pytest.mark.parametrize("path", [
        '/etc/shadow-', '/etc/shadow.bak', '/etc/shadow.old',
        '/etc/gshadow', '/etc/gshadow-', '/etc/gshadow.bak',
        '/etc/passwd-', '/etc//passwd-',
        '/etc/sudoers.d', '/etc/sudoers.d/90-cloud-init-users',
    ])
    def test_review_sensitive_sibling_raises(self, path):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', path])

    @pytest.mark.parametrize("command", ['date', 'grep'])
    @pytest.mark.parametrize("path", ['/etc/shadow', '/etc/passwd', '/etc//passwd'])
    def test_review_attached_short_option_raises(self, command, path):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety([command, '-f' + path])

    @pytest.mark.parametrize("target", ['/etc/gshadow', '/proc/self/environ'])
    def test_review_short_option_symlink_raises(self, monkeypatch, tmp_path, target):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'patterns').symlink_to(target)
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['grep', '-fpatterns', 'input.txt'])

    @pytest.mark.parametrize("path", [
        '/proc/self/environ', '/proc/1/environ', '/proc//self/./environ',
    ])
    def test_review_proc_environ_raises(self, path):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', path])

    @pytest.mark.parametrize("path", [
        '/proc/self/cmdline', '/proc/1/cmdline', '/proc//self/./cmdline',
    ])
    def test_proc_cmdline_raises(self, path):
        with pytest.raises(SecurityError, match="sensitive path"):
            validate_command_safety(['cat', path])

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

    @pytest.mark.parametrize("argument", [
        '-f/var/logrotate.conf', '-f/rootfs/data.csv',
        '/etc/sudoers.draft', '/proc/self/status', '/tmp/proc/self/environ',
        '-rf/var/logrotate.conf', '-uf/rootfs/data.csv',
        '/tmp/proc/self/cmdline', '/proc/self/cmdline.bak',
    ])
    def test_sensitive_family_neighbor_is_allowed(self, argument):
        command = ['grep', argument]
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

    @pytest.mark.parametrize("command", [
        ['date', '-f/etc/passwd'], ['date', '-f/etc//passwd'],
        ['grep', '-f/etc/shadow', '-r', '.'],
        ['cat', '/proc/self/environ'], ['cat', '/proc/1/environ'],
        ['date', '-uf/etc/passwd'], ['date', '-Rf/etc//passwd'],
        ['grep', '-rf/etc/shadow', '.'], ['grep', '-hf/proc/self/environ', 'x'],
        ['cat', '/proc/self/cmdline'],
    ])
    def test_review_read_bypass_raises_before_execution(self, command):
        result = subprocess.CompletedProcess(command, 0, stdout='', stderr='')
        with patch('subprocess.run', return_value=result) as run, patch('subprocess.Popen') as popen:
            popen.return_value.communicate.return_value = (b'', b'')
            popen.return_value.returncode = 0
            with pytest.raises(SecurityError):
                run_subprocess(command)
            run.assert_not_called()
            popen.assert_not_called()

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


_NOT_A_LIVE_PID = 2 ** 22 + 1  # above default pid_max; resolves only in a future child


@pytest.mark.skipif(not os.path.isdir('/proc/self'), reason='needs Linux procfs')
@pytest.mark.parametrize('argv', [
    ['cat', '/proc/self/cwd/passwd'],
    ['cat', '/proc/thread-self/cwd/passwd'],
    ['cat', f'/proc/{_NOT_A_LIVE_PID}/cwd/passwd'],
    ['cat', f'/proc/{_NOT_A_LIVE_PID}/root/etc/passwd'],
    ['grep', '--file=/proc/self/cwd/passwd', 'x'],
    ['cat', '{tmp}/here/passwd'],
])
def test_proc_context_link_raises_before_execution(tmp_path, monkeypatch, argv):
    from siege_utilities.files import validation
    monkeypatch.setattr(validation, 'SENSITIVE_PATHS', validation.SENSITIVE_PATHS - {'/private/etc'})
    (tmp_path / 'here').symlink_to('/proc/self/cwd')
    argv = [a.format(tmp=tmp_path) for a in argv]
    done = subprocess.CompletedProcess(argv, 0, stdout='', stderr='')
    with patch('subprocess.run', return_value=done) as run:
        with pytest.raises(SecurityError):
            run_command(argv, cwd='/etc')
        run.assert_not_called()


@pytest.mark.parametrize('argv', [['cat', '~/passwd'], ['grep', '-f~/passwd', 'x']])
def test_literal_tilde_entry_raises_before_execution(tmp_path, argv):
    # argv is not shell-expanded: the child opens <cwd>/~/passwd literally.
    (tmp_path / '~').symlink_to('/etc')
    done = subprocess.CompletedProcess(argv, 0, stdout='', stderr='')
    with patch('subprocess.run', return_value=done) as run:
        with pytest.raises(SecurityError):
            run_command(argv, cwd=tmp_path)
        run.assert_not_called()


@pytest.mark.parametrize('argv', [
    ['cat', '/proc/self/status'], ['cat', '/proc/cpuinfo'],
    ['ls', '-la', '~'], ['cat', 'report~'], ['ls', '-la'],
])
def test_proc_and_tilde_neighbors_allowed(tmp_path, argv):
    assert validate_command_safety(argv, cwd=tmp_path) == argv


def test_proc_context_link_readlink_error_fails_closed(tmp_path):
    from siege_utilities.files.shell import _crosses_proc_context_link

    alias = tmp_path.resolve() / 'alias'
    alias.symlink_to('/proc/self/cwd')
    with patch('os.readlink', side_effect=OSError('link unavailable')) as readlink:
        assert _crosses_proc_context_link(str(alias)) is True
    readlink.assert_called_once_with(str(alias))
