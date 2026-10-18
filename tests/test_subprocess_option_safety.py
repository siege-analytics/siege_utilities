"""Reject caller values that external commands could interpret as options."""

import subprocess
from unittest.mock import patch

import pytest

from siege_utilities.config import credential_manager as credentials
from siege_utilities.distributed.hdfs_config import HDFSConfig
from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
from siege_utilities.files.operations import run_command
from siege_utilities.files.shell import SecurityError, run_subprocess
from siege_utilities.git import git_operations, git_workflow
from siege_utilities.git.validation import GitSecurityError


@pytest.mark.parametrize('method, args, name', [
    ('_get_from_1password', ('--help', 'password'), 'service'),
    ('_get_from_keychain', ('--help', 'user'), 'service'),
    ('_get_from_keychain', ('service', '-w'), 'username'),
    ('_store_in_1password', ('--help', 'user', 'secret', 'password'), 'service'),
    ('_store_in_1password', ('service', 'user', 'secret', '--help'), 'field'),
    ('_store_in_keychain', ('--help', 'user', 'secret'), 'service'),
    ('_store_in_keychain', ('service', '-w', 'secret'), 'username'),
])
def test_credential_option_value_raises_before_execution(method, args, name):
    manager = credentials.CredentialManager(
        detect_backends=False, include_default_paths=False, create_default_paths=False,
    )
    with patch.object(credentials.subprocess, 'run') as execute:
        with pytest.raises(ValueError, match=f"{name} must not start with '-'"):
            getattr(manager, method)(*args)
        execute.assert_not_called()


@pytest.mark.parametrize('getter', [
    credentials.get_google_service_account_from_1password,
    credentials.get_google_oauth_from_1password,
    credentials.get_google_oauth_document_from_1password,
])
def test_google_item_option_raises_before_execution(getter):
    with patch.object(credentials.subprocess, 'run') as execute:
        with pytest.raises(ValueError, match="item_title must not start with '-'"):
            getter(item_title='--help')
        execute.assert_not_called()


@pytest.mark.parametrize('local, destination, message', [
    ('-source', '/data/', 'local_path'),
    ('source', '-destination/', 'hdfs_directory'),
])
def test_hdfs_option_path_raises_before_execution(tmp_path, monkeypatch, local, destination, message):
    monkeypatch.chdir(tmp_path)
    (tmp_path / local).write_text('data')
    config = HDFSConfig(cache_directory=str(tmp_path / 'cache'), hdfs_base_directory=destination)
    ops = AbstractHDFSOperations(config)
    with patch('siege_utilities.distributed.hdfs_operations.subprocess.run') as execute:
        with pytest.raises(ValueError, match=f"{message} must not start with '-'"):
            ops.sync_directory_to_hdfs(local)
        execute.assert_not_called()


def test_hdfs_ordinary_paths_still_sync(tmp_path):
    local = tmp_path / 'source.txt'
    local.write_text('data')
    ops = AbstractHDFSOperations(HDFSConfig(cache_directory=str(tmp_path / 'cache')))
    with patch.object(ops, 'check_hdfs_status', return_value=True), patch(
        'siege_utilities.distributed.hdfs_operations.subprocess.run',
        return_value=subprocess.CompletedProcess([], 0),
    ) as execute:
        destination, manifest = ops.sync_directory_to_hdfs(str(local))
    assert destination == '/data/inputs/source.txt'
    assert manifest == {'source.txt': {'path': str(local)}}
    assert execute.call_args_list[1].args[0] == [
        'hdfs', 'dfs', '-put', '-f', str(local), destination,
    ]


def test_feature_branch_option_raises_before_execution():
    with patch.object(git_operations, 'run_git_command') as execute:
        with pytest.raises(ValueError, match='Invalid branch name'):
            git_operations.create_feature_branch('--help')
        execute.assert_not_called()


@pytest.mark.parametrize('function, kwargs', [
    (git_operations.create_feature_branch, {'branch_name': 'feature/test', 'base_branch': '--help'}),
    (git_operations.pull_branch, {'remote': '--upload-pack=bad'}),
    (git_operations.pull_branch, {'branch_name': '--help'}),
    (git_operations.push_branch, {'remote': '--help'}),
])
def test_git_option_value_raises_before_execution(function, kwargs):
    with patch.object(git_operations, 'run_git_command') as execute:
        with pytest.raises(GitSecurityError, match="(?:cannot|must not) start with '-'"):
            function(**kwargs)
        execute.assert_not_called()


@pytest.mark.parametrize('function, kwargs', [
    (git_workflow.start_feature_workflow, {'feature_name': 'test', 'base_branch': '--help'}),
    (git_workflow.hotfix_workflow, {'hotfix_name': 'test', 'base_branch': '--help'}),
    (git_workflow.release_workflow, {'version': '1.2.3', 'base_branch': '--help'}),
    (git_workflow.complete_feature_workflow, {'feature_branch': '--help'}),
    (git_workflow.complete_feature_workflow, {'feature_branch': 'feature/test', 'target_branch': '--help'}),
])
def test_git_workflow_option_raises_before_execution(function, kwargs):
    with patch.object(git_workflow, 'run_git_command') as execute:
        with pytest.raises(GitSecurityError, match="cannot start with '-'"):
            function(**kwargs)
        execute.assert_not_called()


@pytest.mark.parametrize('runner', [run_subprocess, run_command])
@pytest.mark.parametrize('command', ['find . -delete', 'cat /etc//passwd'])
def test_default_runner_rejects_unsafe_command_before_execution(runner, command):
    with patch('subprocess.run') as run, patch('subprocess.Popen') as popen:
        with pytest.raises(SecurityError):
            runner(command)
        run.assert_not_called()
        popen.assert_not_called()
