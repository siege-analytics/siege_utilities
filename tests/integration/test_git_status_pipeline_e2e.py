"""End-to-end git-status pipeline over a real repository.

Builds a throwaway git repository with a deliberately mixed working tree (one
worktree-only modification as the FIRST porcelain line, one staged add, one
untracked file) on a feature branch two commits ahead of main, then runs the
public git helpers against it and cross-checks that they agree.

This exercises, end to end and together, the fixes shipped in this sweep:
- get_repository_status staged/unstaged porcelain counting (#1316/#1317)
- get_file_status staged/unstaged classification (#1315/#1323)
- analyze_branch_status / generate_branch_report ahead-count + status header
  (#1304)

The Siege Utilities repo is never touched; everything happens under tmp_path.
"""

import subprocess

import pytest

from siege_utilities import get_repository_status
from siege_utilities import analyze_branch_status
from siege_utilities import generate_branch_report
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
def repo_with_mixed_status(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    # A remote (no upstream tracking) so status does not trip the no-remote
    # path; isolates this E2E to the staged/unstaged counting behaviour.
    _git(repo, "remote", "add", "origin", str(tmp_path / "remote.git"))

    (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    _git(repo, "add", "alpha.txt")
    _git(repo, "commit", "-m", "feat: add alpha")
    (repo / "readme.md").write_text("readme\n", encoding="utf-8")
    _git(repo, "add", "readme.md")
    _git(repo, "commit", "-m", "docs: add readme")

    # Feature branch two commits ahead of main.
    _git(repo, "checkout", "-b", "feature/demo")
    (repo / "beta.txt").write_text("beta\n", encoding="utf-8")
    _git(repo, "add", "beta.txt")
    _git(repo, "commit", "-m", "fix: correct beta")
    (repo / "gamma.txt").write_text("gamma\n", encoding="utf-8")
    _git(repo, "add", "gamma.txt")
    _git(repo, "commit", "-m", "refactor: clean gamma")

    # Mixed working tree. The modified-but-unstaged alpha.txt sorts first in
    # porcelain output (" M alpha.txt"), which is exactly the line the strip
    # bug used to miscount.
    (repo / "alpha.txt").write_text("alpha\nmore\n", encoding="utf-8")
    (repo / "staged_new.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged_new.txt")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    return repo


@pytest.mark.e2e
class TestGitStatusPipelineE2E:
    def test_repository_and_file_status_agree_on_mixed_tree(
        self, repo_with_mixed_status
    ):
        repo = str(repo_with_mixed_status)

        status = get_repository_status(repo)
        # Porcelain counting: the worktree-only first line is unstaged, not
        # staged; the staged add and untracked file are counted once each.
        assert status["current_branch"] == "feature/demo"
        assert status["staged_files"] == 1
        assert status["unstaged_files"] == 1
        assert status["untracked_files"] == 1
        assert status["total_changes"] == 3
        assert status["working_directory_clean"] is False

        files = get_file_status(repo)
        assert "alpha.txt" in files["unstaged"]
        assert "alpha.txt" not in files["staged"]
        assert "staged_new.txt" in files["staged"]
        assert "untracked.txt" in files["untracked"]

        # The two public views of the same tree agree on the counts.
        assert len(files["staged"]) == status["staged_files"]
        assert len(files["unstaged"]) == status["unstaged_files"]
        assert len(files["untracked"]) == status["untracked_files"]

    def test_branch_analyzers_report_in_development(
        self, repo_with_mixed_status
    ):
        repo = str(repo_with_mixed_status)

        branch_status = analyze_branch_status(repo)
        assert branch_status["branch"] == "feature/demo"
        assert branch_status["ahead"] == "2"
        assert branch_status["behind"] == "0"
        assert branch_status["last_commit_msg"] == "refactor: clean gamma"

        report = generate_branch_report(repo_path=repo)
        assert "**Status**: **IN DEVELOPMENT**" in report
        assert "**Status**: **READY FOR MERGE**" not in report
        assert "**Ahead of main**: 2 commits" in report
