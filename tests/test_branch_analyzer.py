"""Error-path tests for siege_utilities.git.branch_analyzer (SU-4b)."""

import pytest

from siege_utilities.git.branch_analyzer import analyze_branch_status


class TestAnalyzeBranchStatusErrors:
    """Error paths for analyze_branch_status."""

    def test_not_a_git_repo_raises(self, tmp_path):
        """Non-git directory must raise ValueError."""
        with pytest.raises(ValueError, match="Not a git repository"):
            analyze_branch_status(str(tmp_path))

    def test_nonexistent_path_raises(self, tmp_path):
        """Nonexistent path must raise ValueError."""
        bogus = tmp_path / "does_not_exist"
        with pytest.raises(ValueError, match="Not a git repository"):
            analyze_branch_status(str(bogus))
