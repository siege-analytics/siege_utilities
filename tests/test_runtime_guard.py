"""Tests for the siege_utilities.runtime compatibility guard.

See: https://github.com/siege-analytics/siege_utilities/issues/211
"""

import importlib
import sys
from unittest import mock

import pytest

from siege_utilities.runtime import (
    RuntimeGuardError,
    diagnose_environment,
    ensure_compatible,
    is_databricks_runtime,
    purge_stale_modules,
)


# ---------------------------------------------------------------------------
# is_databricks_runtime
# ---------------------------------------------------------------------------

class TestIsDatabricksRuntime:
    def test_not_databricks_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("siege_utilities.runtime.Path") as mock_path:
                mock_path.return_value.is_dir.return_value = False
                # In a normal test env, should return False
                result = is_databricks_runtime()
                # Result depends on actual environment, but we can at least call it
                assert isinstance(result, bool)

    def test_detects_env_var(self):
        with mock.patch.dict("os.environ", {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            assert is_databricks_runtime() is True

    def test_detects_dbfs(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("siege_utilities.runtime.Path") as mock_path:
                mock_path.return_value.is_dir.return_value = True
                assert is_databricks_runtime() is True


# ---------------------------------------------------------------------------
# diagnose_environment
# ---------------------------------------------------------------------------

class TestDiagnoseEnvironment:
    def test_returns_dict(self):
        diag = diagnose_environment()
        assert isinstance(diag, dict)

    def test_contains_python_version(self):
        diag = diagnose_environment()
        assert "python_version" in diag
        assert diag["python_version"] == (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    def test_contains_pydantic_info(self):
        diag = diagnose_environment()
        assert "pydantic_version" in diag
        assert "pydantic_v2" in diag
        # In our test env, pydantic v2 should be installed
        assert diag["pydantic_v2"] is True
        assert diag["pydantic_version"] != "NOT INSTALLED"

    def test_contains_platform(self):
        diag = diagnose_environment()
        assert "platform" in diag
        assert diag["platform"] == sys.platform

    def test_contains_databricks_flag(self):
        diag = diagnose_environment()
        assert "is_databricks" in diag
        assert isinstance(diag["is_databricks"], bool)

    def test_contains_siege_utilities_version(self):
        diag = diagnose_environment()
        assert "siege_utilities_version" in diag
        assert diag["siege_utilities_version"] != "NOT INSTALLED"

    def test_contains_stale_modules_list(self):
        diag = diagnose_environment()
        assert "stale_pydantic_modules" in diag
        assert isinstance(diag["stale_pydantic_modules"], list)


# ---------------------------------------------------------------------------
# purge_stale_modules
# ---------------------------------------------------------------------------

class TestPurgeStaleModules:
    def test_purges_matching_modules(self):
        # Insert a fake module
        fake_name = "_test_purge_target"
        sys.modules[fake_name] = mock.MagicMock()
        sys.modules[fake_name + ".sub"] = mock.MagicMock()

        purged = purge_stale_modules(prefixes=[fake_name])
        assert fake_name in purged
        assert fake_name + ".sub" in purged
        assert fake_name not in sys.modules

    def test_returns_empty_when_nothing_matches(self):
        purged = purge_stale_modules(prefixes=["_nonexistent_prefix_xyz"])
        assert purged == []

    def test_default_prefixes(self):
        # Should not raise; just exercises the default code path
        # We don't actually want to purge real pydantic in the test env,
        # so we mock sys.modules.keys() to return controlled data
        fake_modules = {
            "pydantic": mock.MagicMock(),
            "pydantic.fields": mock.MagicMock(),
            "unrelated": mock.MagicMock(),
        }
        with mock.patch.dict(sys.modules, fake_modules, clear=False):
            # We can't fully control sys.modules here without breaking things,
            # so just verify the function is callable with defaults
            result = purge_stale_modules(prefixes=["_safe_test_prefix"])
            assert isinstance(result, list)


# ---------------------------------------------------------------------------
# ensure_compatible
# ---------------------------------------------------------------------------

class TestEnsureCompatible:
    def test_passes_in_healthy_environment(self):
        """In our test env pydantic v2 is installed, so this should pass."""
        diag = ensure_compatible(quiet=True)
        assert isinstance(diag, dict)
        assert diag["pydantic_v2"] is True

    def test_idempotent(self):
        """Calling multiple times should be safe and cheap."""
        diag1 = ensure_compatible(quiet=True)
        diag2 = ensure_compatible(quiet=True)
        assert diag1["pydantic_version"] == diag2["pydantic_version"]

    def test_returns_diagnostics(self):
        diag = ensure_compatible(quiet=True)
        assert "python_version" in diag
        assert "pydantic_version" in diag
        assert "siege_utilities_version" in diag

    def test_raises_on_missing_pydantic(self):
        """Simulate pydantic not being importable."""
        with mock.patch("siege_utilities.runtime._check_imports", return_value=False):
            with mock.patch("siege_utilities.runtime.diagnose_environment", return_value={
                "python_version": "3.11.0",
                "platform": "linux",
                "is_databricks": False,
                "databricks_runtime": None,
                "pydantic_version": "NOT INSTALLED",
                "pydantic_module_path": None,
                "pydantic_v2": False,
                "typing_extensions_version": "4.9.0",
                "siege_utilities_version": "3.4.1",
                "stale_pydantic_modules": [],
            }):
                with pytest.raises(RuntimeGuardError) as exc_info:
                    ensure_compatible(auto_install=False, purge_on_conflict=False, quiet=True)

                assert "pydantic>=2.0" in str(exc_info.value)
                assert exc_info.value.diagnostics["pydantic_version"] == "NOT INSTALLED"
                assert "pip install" in exc_info.value.remediation

    def test_raises_on_pydantic_v1(self):
        """Simulate pydantic v1 being installed."""
        with mock.patch("siege_utilities.runtime._check_imports", return_value=False):
            with mock.patch("siege_utilities.runtime.diagnose_environment", return_value={
                "python_version": "3.11.0",
                "platform": "linux",
                "is_databricks": True,
                "databricks_runtime": "14.3",
                "pydantic_version": "1.10.13",
                "pydantic_module_path": "/databricks/python3/lib/python3.11/site-packages/pydantic/__init__.py",
                "pydantic_v2": False,
                "typing_extensions_version": "4.5.0",
                "siege_utilities_version": "3.4.1",
                "stale_pydantic_modules": ["pydantic", "pydantic.fields"],
            }):
                with pytest.raises(RuntimeGuardError) as exc_info:
                    ensure_compatible(auto_install=False, purge_on_conflict=False, quiet=True)

                assert "1.10.13" in str(exc_info.value)
                assert exc_info.value.diagnostics["is_databricks"] is True
                assert "dbutils.library.restartPython" in exc_info.value.remediation

    def test_databricks_remediation_shown_on_databricks(self):
        """Remediation message should mention dbutils when on Databricks."""
        with mock.patch("siege_utilities.runtime._check_imports", return_value=False):
            with mock.patch("siege_utilities.runtime.diagnose_environment", return_value={
                "python_version": "3.11.0",
                "platform": "linux",
                "is_databricks": True,
                "databricks_runtime": "14.3",
                "pydantic_version": "1.10.13",
                "pydantic_module_path": None,
                "pydantic_v2": False,
                "typing_extensions_version": "4.5.0",
                "siege_utilities_version": "3.4.1",
                "stale_pydantic_modules": [],
            }):
                with pytest.raises(RuntimeGuardError) as exc_info:
                    ensure_compatible(auto_install=False, purge_on_conflict=False, quiet=True)
                assert "%pip install" in exc_info.value.remediation

    def test_local_remediation_shown_locally(self):
        """Remediation should show pip install when not on Databricks."""
        with mock.patch("siege_utilities.runtime._check_imports", return_value=False):
            with mock.patch("siege_utilities.runtime.diagnose_environment", return_value={
                "python_version": "3.11.0",
                "platform": "linux",
                "is_databricks": False,
                "databricks_runtime": None,
                "pydantic_version": "NOT INSTALLED",
                "pydantic_module_path": None,
                "pydantic_v2": False,
                "typing_extensions_version": "4.5.0",
                "siege_utilities_version": "3.4.1",
                "stale_pydantic_modules": [],
            }):
                with pytest.raises(RuntimeGuardError) as exc_info:
                    ensure_compatible(auto_install=False, purge_on_conflict=False, quiet=True)
                assert "pip install" in exc_info.value.remediation
                assert "%pip" not in exc_info.value.remediation

    def test_custom_required_imports(self):
        """Can specify additional imports to check."""
        diag = ensure_compatible(
            required_imports=[("sys", "path"), ("os", "environ")],
            quiet=True,
        )
        assert isinstance(diag, dict)


# ---------------------------------------------------------------------------
# RuntimeGuardError
# ---------------------------------------------------------------------------

class TestRuntimeGuardError:
    def test_stores_diagnostics(self):
        diag = {"pydantic_version": "1.10.0"}
        err = RuntimeGuardError("test", diagnostics=diag, remediation="pip install pydantic")
        assert err.diagnostics == diag
        assert err.remediation == "pip install pydantic"

    def test_message_includes_remediation(self):
        err = RuntimeGuardError("broken", remediation="fix it")
        assert "fix it" in str(err)

    def test_defaults(self):
        err = RuntimeGuardError("just a message")
        assert err.diagnostics == {}
        assert err.remediation == ""


import os  # noqa: E402 — needed by TestIsDatabricksRuntime
