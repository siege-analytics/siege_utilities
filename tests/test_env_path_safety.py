"""Tests for the _env_path safety guard in siege_utilities.config.paths.

PR follow-up: env-var-controlled paths must be ${HOME}-relative by
default to prevent ``SIEGE_OUTPUT=/etc`` from flowing into the
package's I/O layer.
"""

from __future__ import annotations

from pathlib import Path


class TestEnvPathSafety:

    def test_missing_env_returns_default(self, monkeypatch):
        from siege_utilities.config.paths import _env_path
        monkeypatch.delenv("SIEGE_TEST_VAR", raising=False)
        default = Path.home() / "x"
        assert _env_path("SIEGE_TEST_VAR", default) == default

    def test_home_relative_env_accepted(self, monkeypatch, tmp_path):
        from siege_utilities.config.paths import _env_path
        # tmp_path is not under HOME in all environments, but pytest's
        # tmp_path is under tmpdir. For this test, point at a real
        # HOME-relative location.
        target = Path.home() / "_pytest_env_path_target"
        try:
            monkeypatch.setenv("SIEGE_TEST_VAR", str(target))
            result = _env_path("SIEGE_TEST_VAR", Path.home() / "fallback")
            assert result == target.resolve()
        finally:
            pass  # nothing to clean — target was never created

    def test_outside_home_rejected_by_default(self, monkeypatch, caplog):
        from siege_utilities.config.paths import _env_path
        monkeypatch.delenv("SIEGE_ALLOW_UNSAFE_PATHS", raising=False)
        monkeypatch.setenv("SIEGE_TEST_VAR", "/etc")
        default = Path.home() / "fallback"
        result = _env_path("SIEGE_TEST_VAR", default)
        assert result == default

    def test_outside_home_accepted_with_opt_in(self, monkeypatch):
        from siege_utilities.config.paths import _env_path
        monkeypatch.setenv("SIEGE_ALLOW_UNSAFE_PATHS", "1")
        monkeypatch.setenv("SIEGE_TEST_VAR", "/tmp/_pytest_unsafe_target")
        default = Path.home() / "fallback"
        result = _env_path("SIEGE_TEST_VAR", default)
        assert result == Path("/tmp/_pytest_unsafe_target").resolve()

    def test_tilde_expansion(self, monkeypatch):
        from siege_utilities.config.paths import _env_path
        monkeypatch.setenv("SIEGE_TEST_VAR", "~/_pytest_tilde")
        result = _env_path("SIEGE_TEST_VAR", Path.home() / "fallback")
        assert result == (Path.home() / "_pytest_tilde").resolve()
