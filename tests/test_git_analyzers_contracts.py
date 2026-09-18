"""Root-import contracts for git branch/commit analyzers.

Each git-dependent test runs against a deterministic throwaway repository
created under tmp_path; the Siege Utilities repo is never touched.
"""

import subprocess

import pytest

from siege_utilities import analyze_branch_status
from siege_utilities import categorize_commits
from siege_utilities import get_branch_info
from siege_utilities import get_commit_history
from siege_utilities import get_file_changes
from siege_utilities import generate_branch_report
from siege_utilities import validate_branch_naming


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(cwd, filename, message):
    (cwd / filename).write_text(f"content of {filename}\n", encoding="utf-8")
    _git(cwd, "add", filename)
    _git(cwd, "commit", "-m", message)


@pytest.fixture
def demo_repo(tmp_path):
    """main (feat, docs) + feature/demo (fix, refactor) with a dirty tree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _commit(repo, "alpha.txt", "feat: add alpha")
    _commit(repo, "readme.md", "docs: write readme")
    _git(repo, "checkout", "-b", "feature/demo")
    _commit(repo, "beta.txt", "fix: correct beta")
    _commit(repo, "gamma.txt", "refactor: clean gamma")
    # Dirty working tree: one staged new file, one unstaged modification,
    # one untracked file.
    (repo / "staged_new.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged_new.txt")
    (repo / "alpha.txt").write_text(
        "content of alpha.txt\nmore\n", encoding="utf-8"
    )
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    return repo


def test_analyze_branch_status_reports_branch_and_ahead(demo_repo):
    status = analyze_branch_status(str(demo_repo))
    assert status["branch"] == "feature/demo"
    # feature/demo is 2 commits ahead of main, 0 behind.
    assert status["ahead"] == "2"
    assert status["behind"] == "0"
    assert status["last_commit_msg"] == "refactor: clean gamma"


def test_get_commit_history_returns_messages_most_recent_first(demo_repo):
    commits = get_commit_history(limit=10, repo_path=str(demo_repo))
    assert [c["message"] for c in commits] == [
        "refactor: clean gamma",
        "fix: correct beta",
        "docs: write readme",
        "feat: add alpha",
    ]
    # Each entry carries the documented fields.
    assert set(commits[0].keys()) >= {
        "hash",
        "hash_full",
        "date",
        "author",
        "message",
    }


def test_categorize_commits_buckets_by_prefix(demo_repo):
    commits = get_commit_history(limit=10, repo_path=str(demo_repo))
    cats = categorize_commits(commits)
    assert [c["message"] for c in cats["features"]] == ["feat: add alpha"]
    assert [c["message"] for c in cats["fixes"]] == ["fix: correct beta"]
    assert [c["message"] for c in cats["docs"]] == ["docs: write readme"]
    assert [c["message"] for c in cats["refactor"]] == [
        "refactor: clean gamma"
    ]
    assert cats["infrastructure"] == []
    assert cats["other"] == []


def test_get_file_changes_lists_files_added_vs_main(demo_repo):
    changes = get_file_changes(str(demo_repo))
    # Files introduced on feature/demo relative to main.
    assert sorted(changes["added"]) == ["beta.txt", "gamma.txt"]
    assert changes["modified"] == []
    assert changes["deleted"] == []


def test_get_branch_info_includes_local_branches(demo_repo):
    info = get_branch_info(str(demo_repo))
    names = {b["name"] for b in info["local_branches"]}
    assert {"main", "feature/demo"} <= names
    assert info["current_branch"] == "feature/demo"


def test_generate_branch_report_contains_branch_and_status(demo_repo):
    report = generate_branch_report(repo_path=str(demo_repo))
    assert "feature/demo" in report
    # 2 commits ahead => in-development status text.
    assert "IN DEVELOPMENT" in report
    assert "refactor: clean gamma" in report


def test_validate_branch_naming_accepts_and_rejects():
    ok = validate_branch_naming("feature/add-thing")
    assert ok["is_valid"] is True
    assert ok["matched_pattern"] == "feature"
    assert ok["issues"] == []

    bad = validate_branch_naming("Feature/Add_Thing")
    assert bad["is_valid"] is False
    assert any("uppercase" in issue.lower() for issue in bad["issues"])
