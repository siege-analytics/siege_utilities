"""Error-path coverage (SU-4b) for siege_utilities.git.branch_analyzer.

Forces:
- the ValueError raised by analyze_branch_status on a non-git directory
- the ``except (GitError, RuntimeError)`` degradation paths in
  analyze_branch_status and get_file_changes, induced with a real git repo
  that has no ``main`` branch (so ``main...HEAD`` comparisons fail).
"""

import shutil
import subprocess

import pytest

from siege_utilities.git.branch_analyzer import (
    analyze_branch_status,
    get_file_changes,
)

_GIT = shutil.which("git")
requires_git = pytest.mark.skipif(
    _GIT is None,
    reason="git executable not on PATH; install git to run these tests",
)


def _run(args, cwd):
    subprocess.run(
        [_GIT, *args], cwd=cwd, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=30,  # writing-code:15 — bound the git subprocess
    )


@pytest.fixture
def repo_without_main(tmp_path):
    """A real git repo with one commit on a branch that is NOT ``main``."""
    _run(["init", "-b", "work"], tmp_path)
    _run(["config", "user.email", "t@example.test"], tmp_path)
    _run(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "f.txt").write_text("hello")
    _run(["add", "f.txt"], tmp_path)
    _run(["commit", "-m", "init"], tmp_path)
    return tmp_path


def test_analyze_branch_status_rejects_non_git_dir(tmp_path):
    target = tmp_path / "not_a_repo"
    target.mkdir()
    with pytest.raises(ValueError) as exc_info:
        analyze_branch_status(str(target))
    assert "Not a git repository" in str(exc_info.value)


@requires_git
def test_analyze_branch_status_degrades_when_main_missing(repo_without_main):
    # main...HEAD fails -> the except (GitError, RuntimeError) handler runs
    # and ahead/behind fall back to "0".
    status = analyze_branch_status(str(repo_without_main))
    assert status["ahead"] == "0"
    assert status["behind"] == "0"
    assert status["branch"] == "work"


@requires_git
def test_get_file_changes_degrades_when_main_missing(repo_without_main):
    # diff main...HEAD fails -> the except handler returns empty buckets
    # rather than propagating the GitError.
    changes = get_file_changes(str(repo_without_main))
    assert changes == {"added": [], "modified": [], "deleted": []}
