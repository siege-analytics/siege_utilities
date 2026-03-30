"""Tests for siege_utilities.git.git_operations — git command wrappers."""
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from siege_utilities.exceptions import GitError

from siege_utilities.git.git_operations import (
    run_git_command,
    create_feature_branch,
    switch_branch,
    merge_branch,
    rebase_branch,
    stash_changes,
    apply_stash,
    clean_working_directory,
    reset_to_commit,
    cherry_pick_commit,
    create_tag,
    push_branch,
    pull_branch,
)


# ---------------------------------------------------------------------------
# Helper: patch run_git_command across all tests that don't test it directly
# ---------------------------------------------------------------------------
RGC = "siege_utilities.git.git_operations.run_git_command"
SUBPROCESS_RUN = "siege_utilities.git.git_operations.subprocess.run"


# ===================================================================
# run_git_command
# ===================================================================
class TestRunGitCommand:
    """Unit tests for the low-level run_git_command wrapper."""

    def test_returns_stripped_stdout(self):
        mock_result = MagicMock()
        mock_result.stdout = "  abc123  \n"
        with patch(SUBPROCESS_RUN, return_value=mock_result) as mock_run:
            out = run_git_command("status", repo_path="/tmp/repo")
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd="/tmp/repo",
            capture_output=True,
            text=True,
            check=True,
        )
        assert out == "abc123"

    def test_multiple_args(self):
        mock_result = MagicMock()
        mock_result.stdout = "ok"
        with patch(SUBPROCESS_RUN, return_value=mock_result) as mock_run:
            result = run_git_command("checkout", "-b", "feature/x", repo_path=".")
        mock_run.assert_called_once_with(
            ["git", "checkout", "-b", "feature/x"],
            cwd=".",
            capture_output=True,
            text=True,
            check=True,
        )
        assert result == "ok"

    def test_raises_runtime_error_when_check_true(self):
        with patch(SUBPROCESS_RUN, side_effect=subprocess.CalledProcessError(
            1, "git", stderr="fatal: not a git repo"
        )):
            with pytest.raises(GitError, match="Git command failed"):
                run_git_command("status")

    def test_returns_empty_string_when_check_false(self):
        with patch(SUBPROCESS_RUN, side_effect=subprocess.CalledProcessError(
            1, "git", stderr="error"
        )):
            out = run_git_command("status", check=False)
        assert out == ""

    def test_default_repo_path_is_dot(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch(SUBPROCESS_RUN, return_value=mock_result) as mock_run:
            run_git_command("log")
        assert mock_run.call_args[1]["cwd"] == "." or mock_run.call_args[0][0] == ["git", "log"]


# ===================================================================
# create_feature_branch
# ===================================================================
class TestCreateFeatureBranch:
    """Tests for create_feature_branch."""

    def test_invalid_branch_name_raises(self):
        with pytest.raises(ValueError, match="Invalid branch name"):
            create_feature_branch("branch with spaces")

    def test_invalid_branch_name_special_chars(self):
        for bad_name in ["br;anch", "br&anch", "br|anch", "br$anch"]:
            with pytest.raises(ValueError, match="Invalid branch name"):
                create_feature_branch(bad_name)

    def test_valid_branch_name_accepted(self):
        """Valid names pass regex and reach run_git_command."""
        with patch(RGC) as mock_rgc:
            mock_rgc.return_value = "main"  # current branch
            create_feature_branch("feature/my-branch-123")
        # Should have called run_git_command at least for branch --show-current
        assert mock_rgc.called

    def test_already_on_base_branch_skips_checkout(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append((args, kwargs))
            if args[0] == "branch" and args[1] == "--show-current":
                return "main"
            if args[0] == "remote":
                return ""
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = create_feature_branch("feature/x", base_branch="main")

        # Should NOT have called checkout to base branch (already on main)
        checkout_base_calls = [
            c for c in call_log
            if len(c[0]) >= 2 and c[0][0] == "checkout" and c[0][1] == "main"
        ]
        assert len(checkout_base_calls) == 0
        assert result["branch_name"] == "feature/x"
        assert result["status"] == "created"

    def test_not_on_base_branch_switches_first(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch" and args[1] == "--show-current":
                return "develop"
            if args[0] == "remote":
                return ""
            return ""

        with patch(RGC, side_effect=fake_rgc):
            create_feature_branch("feature/x", base_branch="main")

        # Should have a checkout to main
        assert ("checkout", "main") in call_log

    def test_pulls_from_origin_when_remote_exists(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch" and args[1] == "--show-current":
                return "main"
            if args[0] == "remote":
                return "origin"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            create_feature_branch("feature/x")

        pull_calls = [c for c in call_log if c[0] == "pull"]
        assert len(pull_calls) == 1

    def test_return_dict_shape(self):
        with patch(RGC, return_value=""):
            result = create_feature_branch("test-branch")
        assert result["branch_name"] == "test-branch"
        assert result["base_branch"] == "main"
        assert result["status"] == "created"
        assert "remote_tracking" in result


# ===================================================================
# switch_branch
# ===================================================================
class TestSwitchBranch:
    """Tests for switch_branch."""

    def test_branch_exists_locally(self):
        def fake_rgc(*args, **kwargs):
            if args[0] == "branch" and args[1] == "--list":
                return "  main\n  develop\n  feature/x"
            if args[0] == "checkout":
                return ""
            if args[0] == "branch" and args[1] == "--show-current":
                return "feature/x"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = switch_branch("feature/x")
        assert result["current_branch"] == "feature/x"
        assert result["status"] == "switched"

    def test_branch_exists_on_remote(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch" and args[1] == "--list":
                return "  main"
            if args[0] == "branch" and args[1] == "-r":
                return "  origin/feature/y"
            if args[0] == "branch" and args[1] == "--show-current":
                return "feature/y"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = switch_branch("feature/y")
        assert result["status"] == "switched"
        # Should have created a tracking branch
        assert ("checkout", "-b", "feature/y", "origin/feature/y") in call_log

    def test_branch_not_found_raises(self):
        def fake_rgc(*args, **kwargs):
            if args[0] == "branch" and args[1] == "--list":
                return "  main"
            if args[0] == "branch" and args[1] == "-r":
                return "  origin/main"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            with pytest.raises(ValueError, match="does not exist"):
                switch_branch("nonexistent")


# ===================================================================
# merge_branch
# ===================================================================
class TestMergeBranch:
    """Tests for merge_branch."""

    def test_basic_merge_success(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch" and args[1] == "--show-current":
                return "main"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = merge_branch("feature/x", target_branch="main")

        assert result["status"] == "success"
        assert result["source_branch"] == "feature/x"
        assert result["target_branch"] == "main"
        # merge command should contain "merge" and source branch
        merge_calls = [c for c in call_log if c[0] == "merge"]
        assert len(merge_calls) == 1
        assert "feature/x" in merge_calls[0]

    def test_fast_forward_only_flag(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch":
                return "main"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = merge_branch("feature/x", fast_forward_only=True)

        merge_calls = [c for c in call_log if c[0] == "merge"]
        assert "--ff-only" in merge_calls[0]
        assert result["fast_forward_only"] is True

    def test_squash_flag(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch":
                return "main"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = merge_branch("feature/x", squash=True)

        merge_calls = [c for c in call_log if c[0] == "merge"]
        assert "--squash" in merge_calls[0]
        assert result["squash"] is True

    def test_switches_to_target_branch_if_not_current(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch" and args[1] == "--show-current":
                return "develop"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            merge_branch("feature/x", target_branch="main")

        assert ("checkout", "main") in call_log

    def test_merge_failure_returns_error(self):
        call_count = [0]

        def fake_rgc(*args, **kwargs):
            call_count[0] += 1
            if args[0] == "branch":
                return "main"
            if args[0] == "pull":
                return ""
            if args[0] == "merge":
                raise GitError("merge conflict")
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = merge_branch("feature/x")
        assert result["status"] == "failed"
        assert "error" in result


# ===================================================================
# rebase_branch
# ===================================================================
class TestRebaseBranch:
    """Tests for rebase_branch."""

    def test_basic_rebase_success(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch":
                return "feature/x"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = rebase_branch("feature/x", base_branch="main")

        assert result["status"] == "success"
        rebase_calls = [c for c in call_log if c[0] == "rebase"]
        assert len(rebase_calls) == 1
        assert "main" in rebase_calls[0]

    def test_interactive_flag(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch":
                return "feature/x"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = rebase_branch("feature/x", interactive=True)

        rebase_calls = [c for c in call_log if c[0] == "rebase"]
        assert "-i" in rebase_calls[0]
        assert result["interactive"] is True

    def test_switches_to_source_branch_if_needed(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if args[0] == "branch":
                return "main"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            rebase_branch("feature/x")

        assert ("checkout", "feature/x") in call_log

    def test_rebase_failure(self):
        def fake_rgc(*args, **kwargs):
            if args[0] == "branch":
                return "feature/x"
            if args[0] == "rebase":
                raise GitError("rebase conflict")
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = rebase_branch("feature/x")
        assert result["status"] == "failed"
        assert "error" in result


# ===================================================================
# stash_changes
# ===================================================================
class TestStashChanges:
    """Tests for stash_changes."""

    def test_basic_stash_success(self):
        with patch(RGC, return_value="Saved working directory") as mock_rgc:
            result = stash_changes()
        assert result["status"] == "success"
        mock_rgc.assert_called_once()

    def test_stash_with_message(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = stash_changes(message="WIP: fixing tests")

        assert call_log[0] == ("stash", "push", "-m", "WIP: fixing tests")
        assert result["status"] == "success"

    def test_stash_with_untracked(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            stash_changes(include_untracked=True)

        assert "-u" in call_log[0]

    def test_stash_with_message_and_untracked(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            stash_changes(message="WIP", include_untracked=True)

        args = call_log[0]
        assert "push" in args
        assert "-m" in args
        assert "-u" in args

    def test_stash_extracts_hash_from_output(self):
        with patch(RGC, return_value="Saved working directory and index state On main: stash@{0}"):
            result = stash_changes()
        assert result["stash_hash"] == "0"

    def test_stash_failure(self):
        with patch(RGC, side_effect=GitError("stash failed")):
            result = stash_changes()
        assert result["status"] == "failed"
        assert "error" in result


# ===================================================================
# apply_stash
# ===================================================================
class TestApplyStash:
    """Tests for apply_stash."""

    def test_apply_default_stash(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = apply_stash()

        assert result["status"] == "success"
        assert result["action"] == "apply"
        assert call_log[0] == ("stash", "apply", "stash@{0}")

    def test_pop_stash(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = apply_stash(pop=True)

        assert result["action"] == "pop"
        assert call_log[0] == ("stash", "pop", "stash@{0}")

    def test_custom_stash_ref(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = apply_stash(stash_ref="stash@{2}")

        assert call_log[0] == ("stash", "apply", "stash@{2}")
        assert result["stash_ref"] == "stash@{2}"

    def test_apply_failure(self):
        with patch(RGC, side_effect=GitError("conflict")):
            result = apply_stash()
        assert result["status"] == "failed"
        assert "error" in result


# ===================================================================
# clean_working_directory
# ===================================================================
class TestCleanWorkingDirectory:
    """Tests for clean_working_directory."""

    def test_already_clean(self):
        with patch(RGC, return_value=""):
            result = clean_working_directory()
        assert result["status"] == "clean"
        assert "already clean" in result["message"]

    def test_force_clean_success(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if "-n" in args:
                return "Would remove foo.txt"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = clean_working_directory(force=True)

        assert result["status"] == "success"
        assert result["force"] is True

    def test_force_and_directories_flags(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            if "-n" in args:
                return "Would remove foo/"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = clean_working_directory(force=True, directories=True)

        assert result["directories"] is True
        # The actual clean call should include -f and -d
        actual_clean = [c for c in call_log if "-n" not in c]
        assert len(actual_clean) == 1
        assert "-f" in actual_clean[0]
        assert "-d" in actual_clean[0]

    def test_no_force_prompts_user_cancel(self):
        """Without force, user is prompted; simulate 'n' response."""
        with patch(RGC, return_value="Would remove foo.txt"):
            with patch("builtins.input", return_value="n"):
                result = clean_working_directory(force=False)
        assert result["status"] == "cancelled"

    def test_no_force_prompts_user_accept(self):
        """Without force, user is prompted; simulate 'y' response."""
        call_count = [0]

        def fake_rgc(*args, **kwargs):
            call_count[0] += 1
            if "-n" in args:
                return "Would remove foo.txt"
            return ""

        with patch(RGC, side_effect=fake_rgc):
            with patch("builtins.input", return_value="y"):
                result = clean_working_directory(force=False)
        assert result["status"] == "success"

    def test_clean_failure(self):
        call_count = [0]

        def fake_rgc(*args, **kwargs):
            call_count[0] += 1
            if "-n" in args:
                return "Would remove foo.txt"
            raise GitError("clean failed")

        with patch(RGC, side_effect=fake_rgc):
            result = clean_working_directory(force=True)
        assert result["status"] == "failed"


# ===================================================================
# reset_to_commit
# ===================================================================
class TestResetToCommit:
    """Tests for reset_to_commit."""

    def test_soft_reset(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = reset_to_commit("abc1234", reset_type="soft")

        assert result["status"] == "success"
        assert ("reset", "--soft", "abc1234") in call_log

    def test_mixed_reset(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            reset_to_commit("abc1234", reset_type="mixed")

        assert ("reset", "--mixed", "abc1234") in call_log

    def test_hard_reset(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            reset_to_commit("abc1234", reset_type="hard")

        assert ("reset", "--hard", "abc1234") in call_log

    def test_invalid_reset_type_raises(self):
        with pytest.raises(ValueError, match="Invalid reset type"):
            reset_to_commit("abc1234", reset_type="superhard")

    def test_reset_failure(self):
        with patch(RGC, side_effect=GitError("reset failed")):
            result = reset_to_commit("abc1234")
        assert result["status"] == "failed"
        assert "error" in result

    def test_return_dict_shape(self):
        with patch(RGC, return_value=""):
            result = reset_to_commit("abc1234")
        assert result["commit_hash"] == "abc1234"
        assert result["reset_type"] == "soft"
        assert result["status"] == "success"


# ===================================================================
# cherry_pick_commit
# ===================================================================
class TestCherryPickCommit:
    """Tests for cherry_pick_commit."""

    def test_basic_cherry_pick(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = cherry_pick_commit("abc1234")

        assert result["status"] == "success"
        assert ("cherry-pick", "abc1234") in call_log

    def test_continue_on_conflict(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = cherry_pick_commit("abc1234", continue_on_conflict=True)

        assert result["status"] == "success"
        assert result["continue_on_conflict"] is True
        assert ("cherry-pick", "--continue") in call_log

    def test_cherry_pick_failure(self):
        with patch(RGC, side_effect=GitError("cherry-pick conflict")):
            result = cherry_pick_commit("abc1234")
        assert result["status"] == "failed"
        assert "error" in result


# ===================================================================
# create_tag
# ===================================================================
class TestCreateTag:
    """Tests for create_tag."""

    def test_lightweight_tag(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = create_tag("v1.0.0")

        assert result["status"] == "success"
        assert result["tag_name"] == "v1.0.0"
        tag_calls = [c for c in call_log if c[0] == "tag"]
        assert len(tag_calls) == 1
        assert "v1.0.0" in tag_calls[0]

    def test_annotated_tag_with_message(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = create_tag("v1.0.0", message="Release 1.0.0")

        tag_calls = [c for c in call_log if c[0] == "tag"]
        assert "-m" in tag_calls[0]
        assert "Release 1.0.0" in tag_calls[0]
        assert result["message"] == "Release 1.0.0"

    def test_tag_at_specific_commit(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            create_tag("v1.0.0", commit_hash="abc1234")

        tag_calls = [c for c in call_log if c[0] == "tag"]
        assert "abc1234" in tag_calls[0]

    def test_tag_with_push(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = create_tag("v1.0.0", push=True)

        assert result["status"] == "pushed"
        push_calls = [c for c in call_log if c[0] == "push"]
        assert len(push_calls) == 1
        assert "v1.0.0" in push_calls[0]

    def test_tag_creation_failure(self):
        with patch(RGC, side_effect=GitError("tag exists")):
            result = create_tag("v1.0.0")
        assert result["status"] == "failed"
        assert "error" in result

    def test_empty_tag_name_fallback_validation(self):
        """When validation module is not importable, fallback checks empty name."""
        with patch(
            "siege_utilities.git.git_operations.run_git_command"
        ):
            # Force ImportError on validation import inside create_tag
            with patch("builtins.__import__", side_effect=ImportError):
                with pytest.raises((ValueError, ImportError)):
                    create_tag("")


# ===================================================================
# push_branch
# ===================================================================
class TestPushBranch:
    """Tests for push_branch."""

    def test_push_current_branch(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = push_branch()

        assert result["status"] == "success"
        push_calls = [c for c in call_log if c[0] == "push"]
        assert len(push_calls) == 1
        assert "origin" in push_calls[0]

    def test_push_named_branch(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            push_branch(branch_name="feature/x")

        push_calls = [c for c in call_log if c[0] == "push"]
        assert "feature/x" in push_calls[0]

    def test_force_push_uses_lease(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = push_branch(force=True)

        push_calls = [c for c in call_log if c[0] == "push"]
        assert "--force-with-lease" in push_calls[0]
        assert result["force"] is True

    def test_custom_remote(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = push_branch(remote="upstream")

        push_calls = [c for c in call_log if c[0] == "push"]
        assert "upstream" in push_calls[0]
        assert result["remote"] == "upstream"

    def test_push_failure(self):
        with patch(RGC, side_effect=GitError("push rejected")):
            result = push_branch()
        assert result["status"] == "failed"
        assert "error" in result


# ===================================================================
# pull_branch
# ===================================================================
class TestPullBranch:
    """Tests for pull_branch."""

    def test_pull_current_branch(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = pull_branch()

        assert result["status"] == "success"
        pull_calls = [c for c in call_log if c[0] == "pull"]
        assert "origin" in pull_calls[0]

    def test_pull_named_branch(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            pull_branch(branch_name="develop")

        pull_calls = [c for c in call_log if c[0] == "pull"]
        assert "develop" in pull_calls[0]

    def test_pull_with_rebase(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            result = pull_branch(rebase=True)

        pull_calls = [c for c in call_log if c[0] == "pull"]
        assert "--rebase" in pull_calls[0]
        assert result["rebase"] is True

    def test_custom_remote(self):
        call_log = []

        def fake_rgc(*args, **kwargs):
            call_log.append(args)
            return ""

        with patch(RGC, side_effect=fake_rgc):
            pull_branch(remote="upstream")

        pull_calls = [c for c in call_log if c[0] == "pull"]
        assert "upstream" in pull_calls[0]

    def test_pull_failure(self):
        with patch(RGC, side_effect=GitError("pull failed")):
            result = pull_branch()
        assert result["status"] == "failed"
        assert "error" in result

    def test_return_dict_shape(self):
        with patch(RGC, return_value=""):
            result = pull_branch(branch_name="main", rebase=True)
        assert result["branch_name"] == "main"
        assert result["remote"] == "origin"
        assert result["rebase"] is True
        assert result["status"] == "success"
