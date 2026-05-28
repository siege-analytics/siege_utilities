"""Error-path tests for siege_utilities.files.remote (SU-4b)."""

import pytest

from siege_utilities.files.remote import (
    _check_requests_dependency,
    generate_local_path_from_url,
)


class TestCheckRequestsDependencyErrors:
    """Error paths for _check_requests_dependency."""

    def test_raises_when_requests_missing(self, monkeypatch):
        """Must raise ImportError when requests is unavailable."""
        import siege_utilities.files.remote as mod

        monkeypatch.setattr(mod, "REQUESTS_AVAILABLE", False)
        with pytest.raises(ImportError, match="requests library is required"):
            _check_requests_dependency()


class TestGenerateLocalPathErrors:
    """Error paths for generate_local_path_from_url."""

    def test_empty_filename_returns_false(self):
        """URL with no filename segment returns False."""
        result = generate_local_path_from_url("https://example.com/", "/tmp")
        assert result is False

    def test_valid_url_generates_path(self, tmp_path):
        """Valid URL with filename produces correct path."""
        result = generate_local_path_from_url(
            "https://example.com/data/file.zip", str(tmp_path)
        )
        assert result is not False
        assert "file.zip" in str(result)
