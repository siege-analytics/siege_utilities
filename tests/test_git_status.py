"""Tests for siege_utilities.git.git_status module.

All git commands are mocked via subprocess — no real repository needed.
"""

from unittest import mock

import pytest

from siege_utilities.exceptions import GitError
from siege_utilities.git.git_status import (
    get_branch_info,
    get_file_status,
    get_log_summary,
    get_remote_info,
    get_repository_size,
    get_repository_status,
    get_stash_list,
    get_tag_list,
    run_git_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_run(stdout: str = "", returncode: int = 0, stderr: str = ""):
    """Build a mock subprocess.run return value."""
    m = mock.MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


# ---------------------------------------------------------------------------
# run_git_command
# ---------------------------------------------------------------------------

class TestRunGitCommand:

    @mock.patch("siege_utilities.git.git_status.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = _mock_run(stdout="main\n")
        result = run_git_command("branch", "--show-current")
        assert result == "main"

    @mock.patch("siege_utilities.git.git_status.subprocess.run")
    def test_failure_raises_git_error(self, mock_run):
        mock_run.side_effect = __import__("subprocess").CalledProcessError(
            1, "git", stderr="fatal: not a repo"
        )
        with pytest.raises(GitError, match="Git command failed"):
            run_git_command("status")

    @mock.patch("siege_utilities.git.git_status.subprocess.run")
    def test_failure_check_false_returns_empty(self, mock_run):
        mock_run.side_effect = __import__("subprocess").CalledProcessError(
            1, "git", stderr="error"
        )
        result = run_git_command("status", check=False)
        assert result == ""


# ---------------------------------------------------------------------------
# get_repository_status
# ---------------------------------------------------------------------------

class TestGetRepositoryStatus:

    def test_not_a_repo_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Not a git repository"):
            get_repository_status(str(tmp_path))

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd, tmp_path):
        (tmp_path / ".git").mkdir()

        def _side_effect(*args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "branch":
                return "main"
            if cmd == "status":
                return ""
            if cmd == "rev-parse":
                if "--abbrev-ref" in args:
                    return ""  # no upstream
                return "abc1234def"
            if cmd == "log":
                return "test"
            if cmd == "config":
                return "https://github.com/test/repo.git"
            return "0 0"

        mock_cmd.side_effect = _side_effect
        result = get_repository_status(str(tmp_path))
        assert isinstance(result, dict)
        assert result["current_branch"] == "main"
        assert "staged_files" in result
        assert "working_directory_clean" in result
        assert result["working_directory_clean"] is True


# ---------------------------------------------------------------------------
# get_branch_info
# ---------------------------------------------------------------------------

class TestGetBranchInfo:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd):
        mock_cmd.return_value = "main"
        result = get_branch_info()
        assert isinstance(result, dict)
        assert "current_branch" in result


# ---------------------------------------------------------------------------
# get_remote_info
# ---------------------------------------------------------------------------

class TestGetRemoteInfo:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd):
        mock_cmd.return_value = "origin"
        result = get_remote_info()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_stash_list
# ---------------------------------------------------------------------------

class TestGetStashList:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_empty_stash(self, mock_cmd):
        mock_cmd.return_value = ""
        result = get_stash_list()
        assert isinstance(result, list)
        assert len(result) == 0

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_with_stashes(self, mock_cmd):
        # Format matches --format=%gd|%cd|%s
        mock_cmd.return_value = "stash@{0}|2026-03-24|WIP on main\nstash@{1}|2026-03-23|WIP on dev"
        result = get_stash_list()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["ref"] == "stash@{0}"
        assert result[1]["message"] == "WIP on dev"


# ---------------------------------------------------------------------------
# get_tag_list
# ---------------------------------------------------------------------------

class TestGetTagList:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_empty(self, mock_cmd):
        mock_cmd.return_value = ""
        result = get_tag_list()
        assert isinstance(result, list)
        assert len(result) == 0

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_with_tags(self, mock_cmd):
        # Format matches --format=%(refname:short)|%(creatordate:short)|%(creator)
        mock_cmd.return_value = "v1.0.0|2026-01-01|Author A\nv2.0.0|2026-03-01|Author B"
        result = get_tag_list()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "v1.0.0"


# ---------------------------------------------------------------------------
# get_log_summary
# ---------------------------------------------------------------------------

class TestGetLogSummary:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd):
        mock_cmd.return_value = ""
        result = get_log_summary()
        assert isinstance(result, dict)
        assert "total_commits" in result
