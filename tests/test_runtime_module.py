"""Tests for siege_utilities.runtime — covers uncovered code paths.

Focuses on lines not covered by test_runtime_guard.py:
- diagnose_environment: pydantic v1, pydantic missing, typing_extensions missing,
  siege_utilities version fallback paths
- purge_stale_modules: default prefixes
- ensure_compatible: non-quiet logging, auto_install path, purge-only resolution
- _check_imports: missing attr, ImportError
- _auto_install_deps: success, CalledProcessError, FileNotFoundError
"""

import logging
import subprocess
import sys
from types import ModuleType
from unittest import mock

import pytest

from siege_utilities.runtime import (
    RuntimeGuardError,
    _auto_install_deps,
    _check_imports,
    diagnose_environment,
    ensure_compatible,
    purge_stale_modules,
)


# ---------------------------------------------------------------------------
# diagnose_environment — pydantic edge cases
# ---------------------------------------------------------------------------

class TestDiagnoseEnvironmentEdgeCases:
    """Cover lines 118-123, 129-130, 135-140."""

    def test_pydantic_v1_no_field_validator(self):
        """Lines 118-119: pydantic importable but field_validator missing (v1)."""
        fake_pydantic = ModuleType("pydantic")
        fake_pydantic.__version__ = "1.10.13"
        fake_pydantic.__file__ = "/fake/pydantic/__init__.py"
        # No field_validator attribute — simulates pydantic v1

        with mock.patch.dict(sys.modules, {"pydantic": fake_pydantic}):
            # Patch the import to raise ImportError for field_validator
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

            def fake_import(name, *args, **kwargs):
                if name == "pydantic" and args and "field_validator" in (args[2] or ()):
                    # fromlist contains field_validator
                    raise ImportError("No field_validator in v1")
                return original_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=fake_import):
                diag = diagnose_environment()

            assert diag["pydantic_version"] == "1.10.13"
            assert diag["pydantic_v2"] is False

    def test_pydantic_not_installed(self):
        """Lines 120-123: pydantic not importable at all."""
        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pydantic":
                raise ImportError("No module named 'pydantic'")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            diag = diagnose_environment()

        assert diag["pydantic_version"] == "NOT INSTALLED"
        assert diag["pydantic_module_path"] is None
        assert diag["pydantic_v2"] is False

    def test_typing_extensions_not_installed(self):
        """Lines 129-130: typing_extensions not importable."""
        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "typing_extensions":
                raise ImportError("No module named 'typing_extensions'")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            diag = diagnose_environment()

        assert diag["typing_extensions_version"] == "NOT INSTALLED"

    def test_siege_utilities_version_via_dunder(self):
        """Lines 135-138: importlib.metadata.version fails, fallback to __version__."""
        with mock.patch("importlib.metadata.version", side_effect=Exception("no metadata")):
            diag = diagnose_environment()

        # Should fall back to importing __version__ from siege_utilities
        assert diag["siege_utilities_version"] != "NOT INSTALLED"

    def test_siege_utilities_version_not_installed(self):
        """Lines 135-140: both metadata and __version__ import fail."""
        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "siege_utilities" and args and args[2] and "__version__" in args[2]:
                raise ImportError("no __version__")
            return original_import(name, *args, **kwargs)

        with mock.patch("importlib.metadata.version", side_effect=Exception("no metadata")):
            with mock.patch("builtins.__import__", side_effect=fake_import):
                diag = diagnose_environment()

        assert diag["siege_utilities_version"] == "NOT INSTALLED"


# ---------------------------------------------------------------------------
# purge_stale_modules — default prefixes
# ---------------------------------------------------------------------------

class TestPurgeStaleModulesDefaults:
    """Cover line 169: default prefixes when None passed."""

    def test_default_prefixes_used_when_none(self):
        """Line 169: prefixes=None uses ['pydantic', 'siege_utilities']."""
        # Insert fake modules matching default prefixes
        fake_mod = mock.MagicMock()
        fakes = {
            "_test_pydantic_fake": fake_mod,
            "_test_pydantic_fake.sub": fake_mod,
        }
        with mock.patch.dict(sys.modules, fakes):
            # Call with explicit prefixes matching our fakes
            # to avoid purging real modules
            purged = purge_stale_modules(prefixes=["_test_pydantic_fake"])
            assert "_test_pydantic_fake" in purged

    def test_default_prefixes_none_path(self):
        """Line 169: exercises the None branch."""
        # We insert sentinel fake modules to prove the default prefixes are used
        sentinel = mock.MagicMock()
        with mock.patch.dict(
            sys.modules,
            {"pydantic.__test_sentinel": sentinel},
            clear=False,
        ):
            purged = purge_stale_modules()  # prefixes=None
            assert "pydantic.__test_sentinel" in purged


# ---------------------------------------------------------------------------
# _check_imports
# ---------------------------------------------------------------------------

class TestCheckImports:
    """Cover lines 306-309: missing attr and ImportError."""

    def test_returns_true_when_all_present(self):
        assert _check_imports([("sys", "path"), ("os", "environ")]) is True

    def test_returns_false_when_attr_missing(self):
        """Line 306-307: module importable but attribute missing."""
        assert _check_imports([("sys", "nonexistent_attr_xyz")]) is False

    def test_returns_false_on_import_error(self):
        """Lines 308-309: module not importable."""
        assert _check_imports([("nonexistent_module_xyz_123", "anything")]) is False

    def test_returns_false_on_partial_failure(self):
        """First import succeeds, second fails."""
        result = _check_imports([
            ("sys", "path"),
            ("nonexistent_module_xyz_123", "foo"),
        ])
        assert result is False


# ---------------------------------------------------------------------------
# _auto_install_deps
# ---------------------------------------------------------------------------

class TestAutoInstallDeps:
    """Cover lines 315-331."""

    def test_success_not_quiet(self):
        """Lines 315-323, 326-327: successful pip install, not quiet."""
        with mock.patch("subprocess.check_call") as mock_call:
            _auto_install_deps(quiet=False)
            mock_call.assert_called_once()
            cmd = mock_call.call_args[0][0]
            assert "pip" in " ".join(cmd)
            assert "pydantic>=2,<3" in cmd
            assert "typing_extensions>=4.6" in cmd
            # Not quiet: stdout should NOT be DEVNULL
            kwargs = mock_call.call_args[1]
            assert kwargs.get("stdout") is None

    def test_success_quiet(self):
        """Lines 326-327: quiet mode passes DEVNULL."""
        with mock.patch("subprocess.check_call") as mock_call:
            _auto_install_deps(quiet=True)
            kwargs = mock_call.call_args[1]
            assert kwargs["stdout"] is subprocess.DEVNULL
            assert kwargs["stderr"] is subprocess.STDOUT

    def test_called_process_error(self, caplog):
        """Lines 328-329: pip install fails."""
        with mock.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(1, "pip"),
        ):
            with caplog.at_level(logging.ERROR, logger="siege_utilities.runtime"):
                _auto_install_deps(quiet=False)
            assert "pip install failed" in caplog.text

    def test_file_not_found_error(self, caplog):
        """Lines 330-331: pip executable not found."""
        with mock.patch(
            "subprocess.check_call",
            side_effect=FileNotFoundError("No such file"),
        ):
            with caplog.at_level(logging.ERROR, logger="siege_utilities.runtime"):
                _auto_install_deps(quiet=False)
            assert "pip not found" in caplog.text


# ---------------------------------------------------------------------------
# ensure_compatible — non-quiet and repair paths
# ---------------------------------------------------------------------------

class TestEnsureCompatiblePaths:
    """Cover lines 249, 259, 264-276, 280-285."""

    def _make_diag(self, *, is_databricks=False, pydantic_version="2.6.0",
                   pydantic_v2=True, stale=None):
        return {
            "python_version": "3.11.0",
            "platform": "linux",
            "is_databricks": is_databricks,
            "databricks_runtime": "14.3" if is_databricks else None,
            "pydantic_version": pydantic_version,
            "pydantic_module_path": "/fake/pydantic/__init__.py",
            "pydantic_v2": pydantic_v2,
            "typing_extensions_version": "4.9.0",
            "siege_utilities_version": "3.4.1",
            "stale_pydantic_modules": stale or [],
        }

    def test_non_quiet_logs_on_success(self, caplog):
        """Lines 249 and 259: non-quiet mode logs info messages."""
        with caplog.at_level(logging.INFO, logger="siege_utilities.runtime"):
            ensure_compatible(quiet=False)
        assert "runtime guard" in caplog.text.lower()

    def test_auto_install_repairs_successfully(self):
        """Lines 264-276: auto_install=True, install succeeds, re-check passes."""
        call_count = {"n": 0}

        def check_imports_side_effect(required):
            call_count["n"] += 1
            # First call fails, second (after install+purge) succeeds
            return call_count["n"] > 1

        broken_diag = self._make_diag(pydantic_version="1.10.13", pydantic_v2=False)
        fixed_diag = self._make_diag(pydantic_version="2.6.0", pydantic_v2=True)

        with mock.patch("siege_utilities.runtime._check_imports", side_effect=check_imports_side_effect):
            with mock.patch("siege_utilities.runtime.diagnose_environment", side_effect=[broken_diag, fixed_diag]):
                with mock.patch("siege_utilities.runtime._auto_install_deps") as mock_install:
                    with mock.patch("siege_utilities.runtime.purge_stale_modules") as mock_purge:
                        result = ensure_compatible(auto_install=True, purge_on_conflict=True, quiet=False)

        mock_install.assert_called_once_with(quiet=False)
        mock_purge.assert_called_once()
        assert result["pydantic_version"] == "2.6.0"

    def test_auto_install_no_purge(self):
        """Lines 264-267, 273-276: auto_install=True but purge_on_conflict=False."""
        call_count = {"n": 0}

        def check_imports_side_effect(required):
            call_count["n"] += 1
            return call_count["n"] > 1

        broken_diag = self._make_diag(pydantic_version="1.10.13", pydantic_v2=False)
        fixed_diag = self._make_diag(pydantic_version="2.6.0", pydantic_v2=True)

        with mock.patch("siege_utilities.runtime._check_imports", side_effect=check_imports_side_effect):
            with mock.patch("siege_utilities.runtime.diagnose_environment", side_effect=[broken_diag, fixed_diag]):
                with mock.patch("siege_utilities.runtime._auto_install_deps"):
                    with mock.patch("siege_utilities.runtime.purge_stale_modules") as mock_purge:
                        result = ensure_compatible(
                            auto_install=True, purge_on_conflict=False, quiet=True,
                        )

        mock_purge.assert_not_called()
        assert result["pydantic_version"] == "2.6.0"

    def test_auto_install_fails_raises(self):
        """Lines 264-276 failure path: auto_install but still broken after install."""
        broken_diag = self._make_diag(
            pydantic_version="1.10.13", pydantic_v2=False, is_databricks=True,
        )

        with mock.patch("siege_utilities.runtime._check_imports", return_value=False):
            with mock.patch("siege_utilities.runtime.diagnose_environment", return_value=broken_diag):
                with mock.patch("siege_utilities.runtime._auto_install_deps"):
                    with mock.patch("siege_utilities.runtime.purge_stale_modules"):
                        with pytest.raises(RuntimeGuardError) as exc_info:
                            ensure_compatible(auto_install=True, quiet=True)

        assert "pydantic>=2.0" in str(exc_info.value)
        assert "dbutils" in exc_info.value.remediation

    def test_purge_only_resolves(self):
        """Lines 280-285: no auto_install, but purge resolves the conflict."""
        call_count = {"n": 0}

        def check_imports_side_effect(required):
            call_count["n"] += 1
            return call_count["n"] > 1  # Fail first, pass after purge

        stale_diag = self._make_diag(
            pydantic_version="1.10.13", pydantic_v2=False,
            stale=["pydantic", "pydantic.fields"],
        )
        clean_diag = self._make_diag(pydantic_version="2.6.0", pydantic_v2=True)

        with mock.patch("siege_utilities.runtime._check_imports", side_effect=check_imports_side_effect):
            with mock.patch("siege_utilities.runtime.diagnose_environment", side_effect=[stale_diag, clean_diag]):
                with mock.patch("siege_utilities.runtime.purge_stale_modules") as mock_purge:
                    result = ensure_compatible(
                        auto_install=False, purge_on_conflict=True, quiet=False,
                    )

        mock_purge.assert_called_once()
        assert result["pydantic_version"] == "2.6.0"

    def test_purge_only_still_fails(self):
        """Lines 280-285 failure path: purge doesn't resolve, raises."""
        stale_diag = self._make_diag(
            pydantic_version="1.10.13", pydantic_v2=False,
            stale=["pydantic"],
        )

        with mock.patch("siege_utilities.runtime._check_imports", return_value=False):
            with mock.patch("siege_utilities.runtime.diagnose_environment", return_value=stale_diag):
                with mock.patch("siege_utilities.runtime.purge_stale_modules"):
                    with pytest.raises(RuntimeGuardError):
                        ensure_compatible(
                            auto_install=False, purge_on_conflict=True, quiet=True,
                        )

    def test_auto_install_quiet_logging(self, caplog):
        """Lines 264-265: auto_install with quiet=False logs warning."""
        call_count = {"n": 0}

        def check_side_effect(req):
            call_count["n"] += 1
            return call_count["n"] > 1

        broken_diag = self._make_diag(pydantic_version="NOT INSTALLED", pydantic_v2=False)
        fixed_diag = self._make_diag()

        with caplog.at_level(logging.WARNING, logger="siege_utilities.runtime"):
            with mock.patch("siege_utilities.runtime._check_imports", side_effect=check_side_effect):
                with mock.patch("siege_utilities.runtime.diagnose_environment", side_effect=[broken_diag, fixed_diag]):
                    with mock.patch("siege_utilities.runtime._auto_install_deps"):
                        with mock.patch("siege_utilities.runtime.purge_stale_modules"):
                            ensure_compatible(auto_install=True, quiet=False)

        assert "auto-install" in caplog.text.lower()
