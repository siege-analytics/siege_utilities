"""Contract test for get_repository_status on a local-only repository.

Regression for the defect where get_repository_status raised GitError on a
valid git repo with no 'origin' remote (git config --get exits 1 on a missing
key). The repo is built under tmp_path; the Siege Utilities repo is untouched.
"""

import subprocess

import pytest

from siege_utilities import get_repository_status


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def no_remote_repo(tmp_path):
    """A valid repo on main, no remote, with a dirty working tree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    _git(repo, "add", "alpha.txt")
    _git(repo, "commit", "-m", "feat: add alpha")
    # Dirty tree: staged new file, unstaged modification, untracked file.
    (repo / "staged_new.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged_new.txt")
    (repo / "alpha.txt").write_text("alpha\nmore\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    return repo


def test_get_repository_status_handles_repo_without_remote(no_remote_repo):
    # Regression: this must not raise on a remote-less repo.
    status = get_repository_status(str(no_remote_repo))

    # Missing remote is normalized to None rather than crashing.
    assert status["remote"]["url"] is None
    assert status["remote"]["ahead"] == 0
    assert status["remote"]["behind"] == 0

    # Worktree state is still reported.
    assert status["current_branch"] == "main"
    assert status["is_detached"] is False
    assert status["untracked_files"] == 1
    assert status["working_directory_clean"] is False
    # total_changes is self-consistent with its components. (The exact
    # staged/unstaged split is not asserted here: run_git_command strips
    # porcelain output, which corrupts the first line's status columns -
    # tracked as a separate defect.)
    assert status["total_changes"] == (
        status["staged_files"]
        + status["unstaged_files"]
        + status["untracked_files"]
    )
    assert status["last_commit"]["message"] == "feat: add alpha"
