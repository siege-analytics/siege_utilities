"""Recorder regressions for #1543: no git subprocesses or worktree mutations.

Copy this file unchanged into a v4.0.0 checkout to reproduce the failures.
"""

import pytest

from siege_utilities.git import git_operations as operations
from siege_utilities.git import git_workflow as workflow
from siege_utilities.git.validation import (
    GitSecurityError,
    validate_branch_name,
    validate_remote_name,
)


class GitRecorder:
    """Model exact local/remote refs, including the old substring trap."""

    def __init__(self):
        self.calls = []
        self.refs = {"refs/heads/feature/x", "refs/heads/release/1.2"}

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        if args == ("branch", "--show-current"):
            return "develop"
        if args == ("branch", "--list"):
            return "\n".join(ref.removeprefix("refs/heads/") for ref in self.refs
                             if ref.startswith("refs/heads/"))
        if args == ("branch", "-r"):
            return "\n".join(ref.removeprefix("refs/remotes/") for ref in self.refs
                             if ref.startswith("refs/remotes/"))
        if args[:2] == ("rev-parse", "--verify"):
            return "a" * 40 if args[-1] in self.refs else ""
        if args == ("remote",):
            return "origin"
        return ""


@pytest.fixture
def recorder(monkeypatch):
    recorded = GitRecorder()
    monkeypatch.setattr(operations, "run_git_command", recorded)
    monkeypatch.setattr(workflow, "run_git_command", recorded)
    monkeypatch.setattr(workflow, "_update_version_files", lambda *args: None)

    def unexpected_subprocess(*args, **kwargs):
        pytest.fail("Recorder tests must never execute a subprocess")

    monkeypatch.setattr(operations.subprocess, "run", unexpected_subprocess)
    return recorded


@pytest.mark.parametrize("validator", [validate_remote_name, validate_branch_name])
def test_validators_reject_options_aliases_and_bare_paths(validator, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "LICENSE").write_text("local file")
    for name in ("--mirror", "--force", "-f", "--all", "--prune", "--delete",
                 "HEAD", "@", "README.md", "docs", "LICENSE"):
        with pytest.raises((GitSecurityError, ValueError)):
            validator(name)


@pytest.mark.parametrize("function", [operations.push_branch, operations.pull_branch])
@pytest.mark.parametrize("remote", ["--mirror", "--force", "-f", "--all", "--prune", "--delete"])
def test_remote_options_rejected_before_any_git(function, remote, recorder):
    with pytest.raises(GitSecurityError):
        function(remote=remote)
    assert recorder.calls == []


REF_ARGUMENTS = [
    (operations.push_branch, {}, "branch_name"),
    (operations.pull_branch, {}, "branch_name"),
    (operations.create_feature_branch, {}, "branch_name"),
    (operations.create_feature_branch, {"branch_name": "feature/x"}, "base_branch"),
    (operations.switch_branch, {}, "branch_name"),
    (operations.merge_branch, {}, "source_branch"),
    (operations.merge_branch, {"source_branch": "feature/x"}, "target_branch"),
    (operations.rebase_branch, {}, "source_branch"),
    (operations.rebase_branch, {"source_branch": "feature/x"}, "base_branch"),
    (workflow.start_feature_workflow, {"feature_name": "x"}, "base_branch"),
    (workflow.complete_feature_workflow, {}, "feature_branch"),
    (workflow.complete_feature_workflow, {"feature_branch": "feature/x"}, "target_branch"),
    (workflow.hotfix_workflow, {"hotfix_name": "x"}, "base_branch"),
    (workflow.release_workflow, {"version": "1.2.3"}, "base_branch"),
]


@pytest.mark.parametrize("function,kwargs,argument", REF_ARGUMENTS)
def test_every_ref_rejected_before_any_git(function, kwargs, argument, recorder, tmp_path):
    # The directory is in repo_path, deliberately outside the test's cwd.
    (tmp_path / "docs").mkdir()
    for value in ("HEAD", "@", "README.md", "docs", "-f", "--force", "."):
        recorder.calls.clear()
        with pytest.raises((GitSecurityError, ValueError)):
            function(**kwargs, **{argument: value}, repo_path=str(tmp_path))
        assert recorder.calls == []


@pytest.mark.parametrize("namespace", ["refs/heads/", "refs/remotes/origin/"])
def test_switch_requires_exact_ref_not_substring(namespace, recorder):
    recorder.refs = {namespace + "docs-update"}
    with pytest.raises(ValueError, match="does not exist"):
        operations.switch_branch("docs")
    assert recorder.calls == [
        ("rev-parse", "--verify", "refs/heads/docs"),
        ("rev-parse", "--verify", "refs/remotes/origin/docs"),
    ]


# Options inserted by these helpers, never accepted as caller-supplied refs.
LIBRARY_OPTIONS = {
    "branch": {"--show-current", "-d", "--"},
    "rev-parse": {"--verify"},
    "switch": {"--", "-c", "--track", "--no-guess"},
    "push": {"--", "-u", "--force-with-lease", "--delete"},
    "pull": {"--", "--rebase"},
    "merge": {"--", "--squash", "--ff-only"},
    "rebase": {"--", "-i"},
    "commit": {"-m"},
    "stash": {"--"},
    "reset": {"--soft", "--"},
    "cherry-pick": {"--"},
    "tag": {"-m", "--"},
}


SAFE_CALLS = [
    (operations.push_branch, {"branch_name": "feature/x", "force": True}),
    (operations.pull_branch, {"branch_name": "release/1.2", "rebase": True}),
    (operations.create_feature_branch, {"branch_name": "release/1.2"}),
    (operations.switch_branch, {"branch_name": "feature/x"}),
    (operations.merge_branch, {"source_branch": "feature/x", "fast_forward_only": True}),
    (operations.rebase_branch, {"source_branch": "feature/x", "interactive": True}),
    (workflow.start_feature_workflow, {"feature_name": "x", "base_branch": "release/1.2"}),
    (workflow.complete_feature_workflow, {"feature_branch": "feature/x"}),
    (workflow.hotfix_workflow, {"hotfix_name": "x", "base_branch": "release/1.2"}),
    (workflow.release_workflow, {"version": "1.2.3", "base_branch": "release/1.2"}),
    (operations.apply_stash, {}),
    (operations.reset_to_commit, {"commit_hash": "abc1234"}),
    (operations.cherry_pick_commit, {"commit_hash": "abc1234"}),
    (operations.create_tag, {"tag_name": "v1.2.3", "push": True}),
]


@pytest.mark.parametrize("function,kwargs", SAFE_CALLS)
def test_legitimate_names_use_unambiguous_argv(function, kwargs, recorder):
    for branch in ("feature/x", "release/1.2", "hotfix-3", "main", "develop"):
        assert validate_branch_name(branch) == branch
    result = function(**kwargs)
    assert result["status"] in {"success", "created", "switched", "pushed"}
    assert recorder.calls
    for argv in recorder.calls:
        command = argv[0]
        assert command != "checkout", argv
        for argument in argv[1:]:
            if argument.startswith("-"):
                assert argument in LIBRARY_OPTIONS.get(command, set()), argv
        if command in {"switch", "push", "pull", "merge", "rebase", "stash",
                       "reset", "cherry-pick", "tag"} or argv[:2] == ("branch", "-d"):
            assert "--" in argv, argv
        if command in {"push", "pull"}:
            separator = argv.index("--")
            assert argv[separator + 1] == "origin"
            assert all(ref.startswith("refs/") for ref in argv[separator + 2:]), argv


def test_remote_tracking_uses_exact_ref_and_switch(recorder):
    recorder.refs = {"refs/remotes/origin/feature/x"}
    operations.switch_branch("feature/x")
    assert recorder.calls[:3] == [
        ("rev-parse", "--verify", "refs/heads/feature/x"),
        ("rev-parse", "--verify", "refs/remotes/origin/feature/x"),
        ("switch", "--track", "-c", "feature/x", "--", "refs/remotes/origin/feature/x"),
    ]


def test_empty_branch_name_keeps_current_branch_push_and_pull(monkeypatch):
    """An empty branch_name keeps the historical "current branch" behaviour:
    push/pull run with just the "--" boundary and the remote, no refs/heads ref.
    """
    calls = []
    monkeypatch.setattr(operations, "run_git_command", lambda *a, **k: calls.append(a) or "")
    operations.push_branch(branch_name="")
    operations.pull_branch(branch_name="")
    assert calls == [("push", "--", "origin"), ("pull", "--", "origin")]
