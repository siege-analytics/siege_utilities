"""Contract for get_repository_status staged/unstaged porcelain counting.

Regression for the defect where run_git_command().strip() removed the leading
space of the first `git status --porcelain` line, shifting its two status
columns so a worktree-only change (" M file") was miscounted as staged. The
repo is built under tmp_path; the Siege Utilities repo is never touched.
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
def mixed_status_repo(tmp_path):
    """Repo whose FIRST porcelain line is worktree-only (' M alpha.txt').

    Layout after setup: one worktree-only modification, one staged add, one
    untracked file. A remote is configured so the status call does not trip
    the separate no-remote defect (tracked in the get_repository_status remote
    fix); this test isolates the staged/unstaged column counting.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "remote", "add", "origin", str(tmp_path / "remote.git"))
    (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    _git(repo, "add", "alpha.txt")
    _git(repo, "commit", "-m", "init")
    # Worktree-only modification -> first porcelain line is " M alpha.txt".
    (repo / "alpha.txt").write_text("alpha\nmore\n", encoding="utf-8")
    # Staged add.
    (repo / "staged_new.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged_new.txt")
    # Untracked.
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    return repo


def test_staged_unstaged_untracked_counted_exactly(mixed_status_repo):
    status = get_repository_status(str(mixed_status_repo))
    # The worktree-only first line must count as unstaged, not staged.
    assert status["staged_files"] == 1
    assert status["unstaged_files"] == 1
    assert status["untracked_files"] == 1
    assert status["total_changes"] == 3
    assert status["working_directory_clean"] is False
