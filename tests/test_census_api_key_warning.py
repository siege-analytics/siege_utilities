"""Tests for Census API key missing warning (#820)."""

import logging
from unittest.mock import patch

import pytest

from siege_utilities.geo.census.api import CensusAPI


@pytest.fixture
def _no_census_key(monkeypatch, tmp_path):
    """Ensure no Census API key is available from any source."""
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    return tmp_path


class TestCensusAPIKeyWarning:
    """Verify that CensusAPI warns when no API key is configured."""

    def test_warning_logged_when_api_key_missing(self, _no_census_key, caplog):
        """CensusAPI.__init__ logs a warning when _resolve_api_key returns None."""
        cache_dir = _no_census_key
        with patch.object(CensusAPI, "_resolve_api_key", return_value=None):
            with caplog.at_level(logging.WARNING, logger="siege_utilities.geo.census.api"):
                CensusAPI(cache_dir=cache_dir)

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("No Census API key configured" in msg for msg in warning_messages), (
            f"Expected warning about missing Census API key, got: {warning_messages}"
        )
        # Verify the warning contains actionable remediation info
        full_warning = next(m for m in warning_messages if "No Census API key configured" in m)
        assert "CENSUS_API_KEY" in full_warning
        assert "rate limit" in full_warning.lower()

    def test_no_warning_when_api_key_present(self, _no_census_key, caplog):
        """CensusAPI.__init__ does NOT warn when an API key is provided."""
        cache_dir = _no_census_key
        with patch.object(CensusAPI, "_resolve_api_key", return_value="test-key-123"):
            with caplog.at_level(logging.WARNING, logger="siege_utilities.geo.census.api"):
                CensusAPI(cache_dir=cache_dir)

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert not any("No Census API key configured" in msg for msg in warning_messages), (
            f"Warning should not appear when API key is present, got: {warning_messages}"
        )
