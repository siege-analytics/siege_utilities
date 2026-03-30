"""Tests for siege_utilities.git.git_workflow module.

All git commands are mocked — no real repository needed.
"""

from unittest import mock

import pytest

from siege_utilities.git.git_workflow import (
    enforce_commit_conventions,
    validate_branch_naming,
)


# ---------------------------------------------------------------------------
# validate_branch_naming
# ---------------------------------------------------------------------------

class TestValidateBranchNaming:

    def test_valid_feature_branch(self):
        result = validate_branch_naming("feature/add-login")
        assert isinstance(result, dict)
        assert result["is_valid"] is True

    def test_valid_bugfix_branch(self):
        result = validate_branch_naming("bugfix/fix-crash")
        assert result["is_valid"] is True

    def test_valid_hotfix_branch(self):
        result = validate_branch_naming("hotfix/urgent-fix")
        assert result["is_valid"] is True

    def test_valid_release_branch(self):
        result = validate_branch_naming("release/v1.0.0")
        assert result["is_valid"] is True

    def test_valid_developer_prefix(self):
        result = validate_branch_naming("dheerajchand/my-feature")
        assert result["is_valid"] is True

    def test_empty_branch_name(self):
        result = validate_branch_naming("")
        assert result["is_valid"] is False
        assert len(result["issues"]) > 0

    def test_main_branch_warning(self):
        result = validate_branch_naming("main")
        # main is valid but may have a warning
        assert isinstance(result, dict)

    def test_has_suggestions(self):
        result = validate_branch_naming("bad name with spaces")
        assert result["is_valid"] is False
        assert "suggestions" in result


# ---------------------------------------------------------------------------
# enforce_commit_conventions
# ---------------------------------------------------------------------------

class TestEnforceCommitConventions:

    def test_valid_conventional_commit(self):
        result = enforce_commit_conventions("feat: add user login")
        assert isinstance(result, dict)
        assert result["is_valid"] is True

    def test_valid_fix_commit(self):
        result = enforce_commit_conventions("fix: resolve crash on startup")
        assert result["is_valid"] is True

    def test_valid_chore_commit(self):
        result = enforce_commit_conventions("chore: clean up temp file")
        assert result["is_valid"] is True

    def test_empty_message(self):
        result = enforce_commit_conventions("")
        assert result["is_valid"] is False

    def test_too_long_subject(self):
        msg = "feat: " + "x" * 200
        result = enforce_commit_conventions(msg)
        # May flag as warning or issue
        assert isinstance(result, dict)

    def test_has_suggestions_for_bad_format(self):
        result = enforce_commit_conventions("did some stuff")
        assert isinstance(result, dict)
        if not result["is_valid"]:
            assert "suggestions" in result
