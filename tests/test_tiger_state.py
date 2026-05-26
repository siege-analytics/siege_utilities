"""Tests for siege_utilities.geo.census.tiger_state."""

from __future__ import annotations

from unittest.mock import MagicMock

from siege_utilities.geo.census.tiger_state import (
    check_for_updates,
    get_last_fetched_vintage,
    set_last_fetched_vintage,
)


class TestStateFileIO:

    def test_get_returns_none_when_missing(self, tmp_path):
        assert get_last_fetched_vintage(tmp_path / "missing.year") is None

    def test_roundtrip(self, tmp_path):
        f = tmp_path / "sub" / "tiger.year"
        set_last_fetched_vintage(f, 2024)
        assert f.exists()
        assert get_last_fetched_vintage(f) == 2024

    def test_get_returns_none_on_unparseable(self, tmp_path):
        f = tmp_path / "bad.year"
        f.write_text("not-a-year\n")
        assert get_last_fetched_vintage(f) is None


class TestCheckForUpdates:

    def _provider(self, latest):
        p = MagicMock()
        p.latest_vintage.return_value = latest
        return p

    def test_no_state_file_signals_update(self, tmp_path):
        has, latest = check_for_updates(
            tmp_path / "missing", provider=self._provider(2025)
        )
        assert has is True and latest == 2025

    def test_state_equal_to_latest_no_update(self, tmp_path):
        f = tmp_path / "tiger.year"
        set_last_fetched_vintage(f, 2025)
        has, latest = check_for_updates(f, provider=self._provider(2025))
        assert has is False and latest == 2025

    def test_state_behind_signals_update(self, tmp_path):
        f = tmp_path / "tiger.year"
        set_last_fetched_vintage(f, 2024)
        has, latest = check_for_updates(f, provider=self._provider(2025))
        assert has is True and latest == 2025

    def test_discovery_failure_returns_no_update(self, tmp_path):
        f = tmp_path / "tiger.year"
        set_last_fetched_vintage(f, 2024)
        has, latest = check_for_updates(f, provider=self._provider(None))
        assert has is False and latest is None
