"""Credentials must not escape through subprocess argv or diagnostics."""

import errno
import logging
import os
import subprocess
import sys
import traceback
from unittest.mock import Mock

import pytest

from scripts import release_manager
from siege_utilities.files import operations, shell


SECRET = 'sentinel-1402-private-value'


@pytest.fixture(autouse=True)
def capture_diagnostics(caplog, monkeypatch):
    """Capture real log calls even after another test disables logging."""
    logger = logging.getLogger('additional_credential_security_test')
    monkeypatch.setattr(logger, 'disabled', False)
    monkeypatch.setattr(logger, 'propagate', True)
    caplog.set_level(logging.DEBUG, logger=logger.name)
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(operations, 'log', logger)
    monkeypatch.setattr(shell, 'log_info', logger.info)
    monkeypatch.setattr(shell, 'log_error', logger.error)
    monkeypatch.setattr(release_manager, 'logger', logger)


@pytest.fixture
def pypi_upload(tmp_path, monkeypatch):
    (tmp_path / 'dist').mkdir()
    (tmp_path / 'dist' / 'example.whl').write_bytes(b'fixture')
    monkeypatch.setattr(release_manager, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setenv('PYPI_API_TOKEN', SECRET)
    monkeypatch.setenv('TWINE_USERNAME', 'old-user')
    monkeypatch.setenv('TWINE_PASSWORD', 'old-password')
    run = Mock(spec=subprocess.run)
    monkeypatch.setattr(release_manager.subprocess, 'run', run)
    return run


@pytest.mark.parametrize('token_args', [
    ['--token', SECRET],
    [f'--token={SECRET}'],
], ids=['separate-value', 'equals-value'])
def test_release_manager_rejects_cli_token_without_echo(
    monkeypatch, capsys, caplog, token_args,
):
    monkeypatch.setenv('PYPI_API_TOKEN', 'environment-token')
    monkeypatch.setattr(sys, 'argv', ['release_manager.py', '--check', *token_args])

    with pytest.raises(SystemExit) as exc:
        release_manager.main()

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert 'usage:' in captured.err
    assert '--token is no longer supported' in captured.err
    assert 'set PYPI_API_TOKEN in the environment' in captured.err
    diagnostics = captured.out + captured.err + caplog.text
    assert SECRET not in diagnostics
    assert SECRET not in ''.join(traceback.format_exception(exc.value))


def test_release_manager_upload_reads_pypi_token_from_env(
    pypi_upload, monkeypatch, capsys, caplog,
):
    monkeypatch.setattr(sys, 'argv', ['release_manager.py', '--build', '--pypi'])
    monkeypatch.setattr(release_manager, 'build_package', lambda: True)
    monkeypatch.setattr(release_manager, 'validate_build', lambda: True)
    pypi_upload.return_value = subprocess.CompletedProcess(['twine'], 0, '', '')

    release_manager.main()

    pypi_upload.assert_called_once()
    assert pypi_upload.call_args.kwargs['env']['TWINE_PASSWORD'] == SECRET
    assert SECRET not in repr(pypi_upload.call_args.args)
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err + caplog.text
    # --build --pypi now targets TestPyPI; production PyPI is publish-tag.yml only (#1419).
    assert 'Upload to testpypi succeeded' in caplog.text


def test_pypi_upload_missing_token_points_to_env(monkeypatch, caplog):
    monkeypatch.delenv('PYPI_API_TOKEN', raising=False)

    assert release_manager.upload_to_pypi() is False

    assert 'set PYPI_API_TOKEN in the environment' in caplog.text
    assert '--token' not in caplog.text


def test_release_manager_missing_token_points_to_env(monkeypatch, caplog):
    # --release no longer uploads (#1419), so the token check now lives on
    # the TestPyPI upload path: --build --pypi.
    monkeypatch.delenv('PYPI_API_TOKEN', raising=False)
    monkeypatch.setattr(sys, 'argv', ['release_manager.py', '--build', '--pypi'])
    monkeypatch.setattr(release_manager, 'build_package', lambda: True)
    monkeypatch.setattr(release_manager, 'validate_build', lambda: True)

    with pytest.raises(SystemExit) as exc:
        release_manager.main()

    assert exc.value.code == 1
    assert 'set PYPI_API_TOKEN in the environment' in caplog.text
    assert '--token' not in caplog.text


# 'pypi' is refused before any subprocess runs (#1419); see
# tests/test_release_process.py.
@pytest.mark.parametrize('repository', ['testpypi'])
def test_pypi_upload_failure_keeps_token_off_argv(pypi_upload, repository, caplog):
    pypi_upload.return_value = subprocess.CompletedProcess(
        ['twine'], 1, SECRET, SECRET,
    )
    assert release_manager.upload_to_pypi(repository=repository) is False
    assert SECRET not in repr(pypi_upload.call_args.args)
    kwargs = pypi_upload.call_args.kwargs
    assert kwargs['env']['TWINE_PASSWORD'] == SECRET
    assert kwargs['env']['TWINE_USERNAME'] == '__token__'
    assert kwargs['env']['PATH'] == os.environ['PATH']
    assert kwargs['capture_output'] is True
    assert os.environ['TWINE_PASSWORD'] == 'old-password'
    assert os.environ['TWINE_USERNAME'] == 'old-user'
    assert caplog.records
    assert 'failed' in caplog.text
    assert SECRET not in caplog.text


@pytest.mark.parametrize('failure', ['timeout', 'os_error'])
def test_pypi_upload_exception_omits_secret(pypi_upload, failure, caplog):
    def fail(cmd, **kwargs):
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(cmd, 60, output=SECRET, stderr=SECRET)
        raise OSError(errno.EACCES, SECRET)

    pypi_upload.side_effect = fail
    expected = subprocess.TimeoutExpired if failure == 'timeout' else PermissionError
    with pytest.raises(expected) as exc:
        release_manager.upload_to_pypi()
    assert SECRET not in str(exc.value)
    assert SECRET not in ''.join(traceback.format_exception(exc.value))
    assert SECRET not in repr(pypi_upload.call_args.args)
    assert caplog.records
    assert SECRET not in caplog.text


@pytest.mark.parametrize('returncode', [0, 1])
def test_run_command_success_or_failure_omits_secret(monkeypatch, caplog, returncode):
    command = ['echo', '--password', SECRET]
    completed = subprocess.CompletedProcess(command, returncode, SECRET, SECRET)
    run = Mock(spec=subprocess.run, return_value=completed)
    monkeypatch.setattr(operations.subprocess, 'run', run)
    result = operations.run_command(command)
    assert result is completed
    assert run.call_args.args[0] == command
    assert run.call_args.kwargs['shell'] is False
    assert caplog.records
    assert SECRET not in caplog.text


@pytest.mark.parametrize('returncode', [0, 1])
def test_run_subprocess_success_or_failure_omits_secret(monkeypatch, caplog, returncode):
    command = ['echo', '--api-key', SECRET]
    process = Mock(spec=subprocess.Popen, returncode=returncode)
    process.communicate.return_value = (SECRET.encode(), SECRET.encode())
    popen = Mock(spec=subprocess.Popen, return_value=process)
    monkeypatch.setattr(shell.subprocess, 'Popen', popen)
    assert shell.run_subprocess(command) == SECRET
    assert popen.call_args.args[0] == command
    assert popen.call_args.kwargs['shell'] is False
    assert caplog.records
    assert SECRET not in caplog.text


@pytest.mark.parametrize('failure,expected', [
    (subprocess.TimeoutExpired(['echo', SECRET], 3, output=SECRET, stderr=SECRET),
     subprocess.TimeoutExpired),
    (OSError(errno.EACCES, SECRET), PermissionError),
    (ValueError(SECRET), ValueError),
])
def test_run_command_exception_omits_secret(monkeypatch, caplog, failure, expected):
    run = Mock(spec=subprocess.run, side_effect=failure)
    monkeypatch.setattr(operations.subprocess, 'run', run)
    with pytest.raises(expected) as exc:
        operations.run_command(['echo', '--token', SECRET])
    assert SECRET not in str(exc.value)
    assert SECRET not in ''.join(traceback.format_exception(exc.value))
    assert caplog.records
    assert SECRET not in caplog.text


def test_run_subprocess_timeout_omits_secret(monkeypatch, caplog):
    process = Mock(spec=subprocess.Popen)
    process.communicate.side_effect = [
        subprocess.TimeoutExpired(['echo', SECRET], 3, output=SECRET, stderr=SECRET),
        (SECRET.encode(), SECRET.encode()),
    ]
    monkeypatch.setattr(shell.subprocess, 'Popen', Mock(return_value=process))
    with pytest.raises(subprocess.TimeoutExpired) as exc:
        shell.run_subprocess(['echo', '--secret', SECRET], timeout=3)
    process.kill.assert_called_once_with()
    assert process.communicate.call_count == 2
    assert exc.value.timeout == 3
    assert SECRET not in str(exc.value)
    assert SECRET not in ''.join(traceback.format_exception(exc.value))
    assert caplog.records
    assert SECRET not in caplog.text


def test_run_subprocess_os_error_omits_secret(monkeypatch, caplog):
    popen = Mock(spec=subprocess.Popen, side_effect=OSError(errno.EACCES, SECRET))
    monkeypatch.setattr(shell.subprocess, 'Popen', popen)
    with pytest.raises(PermissionError) as exc:
        shell.run_subprocess(['echo', '-w', SECRET])
    assert exc.value.errno == errno.EACCES
    assert SECRET not in str(exc.value)
    assert SECRET not in ''.join(traceback.format_exception(exc.value))
    assert caplog.records
    assert SECRET not in caplog.text


@pytest.mark.parametrize('run', [operations.run_command, shell.run_subprocess])
def test_command_validation_error_omits_secret(run, caplog):
    with pytest.raises(shell.SecurityError) as exc:
        run(['echo', '--password', SECRET + ';'])
    assert SECRET not in str(exc.value)
    assert caplog.records
    assert SECRET not in caplog.text


@pytest.mark.parametrize('run', [operations.run_command, shell.run_subprocess])
def test_command_empty_input_raises_safe_value_error(run, caplog):
    with pytest.raises(ValueError, match='Invalid command'):
        run([])
    assert caplog.records
