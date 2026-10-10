"""Contract for get_file_status porcelain first-line classification.

Regression for the defect where run_git_command().strip() removed the leading
space of the first `git status --porcelain` line, shifting get_file_status's
status=line[:2]/filepath=line[3:] slices so a worktree-only first change was
misclassified as staged with a corrupted path. The repo is built under
tmp_path; the Siege Utilities repo is never touched.
"""

import subprocess

import pytest

from siege_utilities.git.git_status import get_file_status


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
    """Repo whose FIRST porcelain line is worktree-only (' M alpha.txt')."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    _git(repo, "add", "alpha.txt")
    _git(repo, "commit", "-m", "init")
    # Worktree-only modification -> first porcelain line " M alpha.txt".
    (repo / "alpha.txt").write_text("alpha\nmore\n", encoding="utf-8")
    # Staged add.
    (repo / "staged_new.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged_new.txt")
    # Untracked.
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    return repo


def test_first_line_worktree_change_classified_unstaged(mixed_status_repo):
    files = get_file_status(str(mixed_status_repo))
    # The worktree-only first line is unstaged, not staged, and its path
    # is intact (not shifted by one).
    assert "alpha.txt" in files["unstaged"]
    assert "alpha.txt" not in files["staged"]
    assert "staged_new.txt" in files["staged"]
    assert "untracked.txt" in files["untracked"]
