"""Tests for siege_utilities.git.git_status module.

All git commands are mocked via run_git_command -- no real repository needed.
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
)
from siege_utilities.git._utils import run_git_command


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

    @mock.patch("siege_utilities.git._utils.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = _mock_run(stdout="main\n")
        result = run_git_command("branch", "--show-current")
        assert result == "main"

    @mock.patch("siege_utilities.git._utils.subprocess.run")
    def test_failure_raises_git_error(self, mock_run):
        mock_run.side_effect = __import__("subprocess").CalledProcessError(
            1, "git", stderr="fatal: not a repo"
        )
        with pytest.raises(GitError, match="Git command failed"):
            run_git_command("status")

    @mock.patch("siege_utilities.git._utils.subprocess.run")
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

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_commit_info_failure_raises_git_error(self, mock_cmd, tmp_path):
        (tmp_path / ".git").mkdir()

        def _side_effect(*args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "branch":
                return "main"
            if cmd == "status":
                return ""
            # Fail on rev-parse (commit info)
            raise GitError("rev-parse failed")

        mock_cmd.side_effect = _side_effect
        with pytest.raises(GitError, match="Could not retrieve last commit info"):
            get_repository_status(str(tmp_path))

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_remote_info_failure_raises_git_error(self, mock_cmd, tmp_path):
        (tmp_path / ".git").mkdir()

        def _side_effect(*args, **kwargs):
            cmd = args[0] if args else ""
            if cmd == "branch":
                return "main"
            if cmd == "status":
                return ""
            if cmd == "rev-parse":
                if "--abbrev-ref" in args:
                    raise GitError("no upstream")
                return "abc1234def"
            if cmd == "log":
                return "test"
            if cmd == "config":
                raise GitError("config failed")
            return ""

        mock_cmd.side_effect = _side_effect
        with pytest.raises(GitError, match="Could not retrieve remote info"):
            get_repository_status(str(tmp_path))


# ---------------------------------------------------------------------------
# get_branch_info
# ---------------------------------------------------------------------------

class TestGetBranchInfo:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd):
        call_count = [0]

        def _side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # branch --list: one branch with no upstream/tracking
                return "main||"
            if call_count[0] == 2:
                # log for "main" branch commit
                return "abc1234def5678|2026-05-29|Test Author|Initial commit"
            if call_count[0] == 3:
                # branch -r (remote branches)
                return ""
            # branch --show-current
            return "main"

        mock_cmd.side_effect = _side_effect
        result = get_branch_info()
        assert isinstance(result, dict)
        assert "current_branch" in result
        assert result["current_branch"] == "main"
        assert len(result["local_branches"]) == 1
        assert result["local_branches"][0]["name"] == "main"

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_branch_commit_failure_raises_git_error(self, mock_cmd):
        call_count = [0]

        def _side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: branch --list
                return "main||"
            # Second call: log for branch commit -- fail
            raise GitError("log failed")

        mock_cmd.side_effect = _side_effect
        with pytest.raises(GitError, match="Could not retrieve commit info for branch main"):
            get_branch_info()


# ---------------------------------------------------------------------------
# get_remote_info
# ---------------------------------------------------------------------------

class TestGetRemoteInfo:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd):
        mock_cmd.return_value = "origin"
        result = get_remote_info()
        assert isinstance(result, dict)

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_remote_url_failure_raises_git_error(self, mock_cmd):
        call_count = [0]

        def _side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "origin"  # remote list
            raise GitError("config failed")

        mock_cmd.side_effect = _side_effect
        with pytest.raises(GitError, match="Could not retrieve URL for remote origin"):
            get_remote_info()


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

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_failure_raises_git_error(self, mock_cmd):
        mock_cmd.side_effect = GitError("stash failed")
        with pytest.raises(GitError, match="Could not retrieve stash list"):
            get_stash_list()


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

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_failure_raises_git_error(self, mock_cmd):
        mock_cmd.side_effect = GitError("tag failed")
        with pytest.raises(GitError, match="Could not retrieve tag list"):
            get_tag_list()


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

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_failure_raises_git_error(self, mock_cmd):
        mock_cmd.side_effect = GitError("log failed")
        with pytest.raises(GitError, match="Could not retrieve commit log"):
            get_log_summary()


# ---------------------------------------------------------------------------
# get_file_status
# ---------------------------------------------------------------------------

class TestGetFileStatus:

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_returns_dict(self, mock_cmd):
        mock_cmd.return_value = ""
        result = get_file_status()
        assert isinstance(result, dict)
        assert "staged" in result

    @mock.patch("siege_utilities.git.git_status.run_git_command")
    def test_failure_raises_git_error(self, mock_cmd):
        mock_cmd.side_effect = GitError("status failed")
        with pytest.raises(GitError, match="Could not retrieve file status"):
            get_file_status()


# ---------------------------------------------------------------------------
# get_repository_size
# ---------------------------------------------------------------------------

class TestGetRepositorySize:

    @mock.patch("siege_utilities.git.git_status.Path.resolve")
    def test_failure_raises_git_error(self, mock_resolve, tmp_path):
        """OSError during size calculation raises GitError."""
        mock_path = mock.MagicMock()
        mock_resolve.return_value = mock_path
        git_dir = mock.MagicMock()
        mock_path.__truediv__ = mock.MagicMock(return_value=git_dir)
        git_dir.rglob.side_effect = OSError("Permission denied")

        with pytest.raises(GitError, match="Could not calculate repository size"):
            get_repository_size("/fake/path")
