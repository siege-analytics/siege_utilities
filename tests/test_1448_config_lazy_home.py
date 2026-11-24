"""Regression coverage for config imports without a resolvable home (#1448)."""

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "posix", reason="Requires POSIX passwd lookup")


def _run_without_home(monkeypatch, source):
    monkeypatch.delenv("HOME", raising=False)
    # Discard the suite's directory overrides to exercise real defaults.
    for name in list(os.environ):
        if name.startswith("SIEGE_") or name in {
            "SIEGE", "GEOCODE", "MASAI", "SPARK_CACHE", "CENSUS_DATA",
            "NCES_DATA", "SAMPLE_DATA",
        }:
            monkeypatch.delenv(name)
    script = """
import pwd
from unittest.mock import patch

with patch.object(pwd, "getpwuid", side_effect=KeyError("unmapped uid")):
""" + textwrap.indent(textwrap.dedent(source), "    ")
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("statement", [
    "from siege_utilities.config import DEFAULT_TIMEOUT; assert DEFAULT_TIMEOUT == 30",
    "import siege_utilities.geo.census.api",
    "import siege_utilities.geo.spatial_data",
    "import siege_utilities.geo.census_files.pl_downloader",
    "import siege_utilities.config.paths",
])
def test_import_without_home_or_passwd_entry(monkeypatch, statement):
    _run_without_home(monkeypatch, statement)


def test_cache_override_without_home(monkeypatch):
    _run_without_home(monkeypatch, """
        import os
        from pathlib import Path

        os.environ["SIEGE_CACHE"] = "/data/cache"
        from siege_utilities.config import SIEGE_CACHE_DIR
        assert SIEGE_CACHE_DIR == Path("/data/cache")
    """)


@pytest.mark.parametrize("auto_init", ["false", "true"])
def test_imports_do_not_resolve_home(monkeypatch, auto_init):
    _run_without_home(monkeypatch, f"""
        import os
        from pathlib import Path

        os.environ["SIEGE_AUTO_INIT_DIRS"] = {auto_init!r}
        with patch.object(Path, "home", side_effect=AssertionError("eager home lookup")):
            from siege_utilities.config import DEFAULT_TIMEOUT
            import siege_utilities.config.paths as paths
            assert DEFAULT_TIMEOUT == 30
            assert "SIEGE_CACHE_DIR" in dir(paths)
            assert "SIEGE_CACHE_DIR" not in vars(paths)
    """)


@pytest.mark.parametrize("module", ["constants", "paths"])
@pytest.mark.parametrize("allow_unsafe", [False, True])
def test_overrides_skip_home_and_parent_defaults(monkeypatch, module, allow_unsafe):
    _run_without_home(monkeypatch, f"""
        import importlib
        import os
        from pathlib import Path
        import tempfile

        root = Path(tempfile.gettempdir()) / f"siege_utilities-{{os.getuid()}}"
        target = root / "override"
        if {allow_unsafe!r}:
            os.environ["SIEGE_ALLOW_UNSAFE_PATHS"] = "1"
            target = Path("/data/override")
        module = importlib.import_module("siege_utilities.config.{module}")
        overrides = {{
            "SIEGE_UTILITIES_HOME": "SIEGE_UTILITIES",
            "SIEGE_CACHE_DIR": "SIEGE_CACHE",
            "SIEGE_OUTPUT_DIR": "SIEGE_OUTPUT",
        }}
        if {module!r} == "paths":
            overrides.update({{
                "SIEGE_UTILITIES_TEST": "SIEGE_UTILITIES_TEST",
                "SIEGE_ANALYTICS_ROOT": "SIEGE",
                "GEOCODING_PROJECT": "GEOCODE", "MASAI_PROJECT": "MASAI",
                "SPARK_CACHE_DIR": "SPARK_CACHE", "TEMP_DIR": "SIEGE_TEMP",
                "REPORTS_OUTPUT_DIR": "SIEGE_REPORTS",
                "CHARTS_OUTPUT_DIR": "SIEGE_CHARTS", "MAPS_OUTPUT_DIR": "SIEGE_MAPS",
                "DATA_DIR": "SIEGE_DATA", "CENSUS_DATA_DIR": "CENSUS_DATA",
                "NCES_DATA_DIR": "NCES_DATA", "SAMPLE_DATA_DIR": "SAMPLE_DATA",
                "CONFIG_DIR": "SIEGE_CONFIG", "USER_CONFIG_FILE": "SIEGE_USER_CONFIG",
                "LOG_DIR": "SIEGE_LOG_DIR", "BACKUP_DIR": "SIEGE_BACKUP",
            }})
        with patch.object(Path, "home", side_effect=AssertionError("unused default")):
            for name, env_name in overrides.items():
                importlib.reload(module)
                os.environ[env_name] = str(target)
                expected = target.resolve() if {module!r} == "paths" else target
                assert getattr(module, name) == expected, name
                del os.environ[env_name]
    """)


@pytest.mark.parametrize("home_available", [False, True])
def test_default_paths_keep_existing_layout(monkeypatch, tmp_path, home_available):
    _run_without_home(monkeypatch, f"""
        import os
        from pathlib import Path
        import tempfile

        root = Path(tempfile.gettempdir()) / f"siege_utilities-{{os.getuid()}}"
        if {home_available!r}:
            root = Path({str(tmp_path)!r})
            os.environ["HOME"] = str(root)
        from siege_utilities.config import constants, paths
        expected = {{
            "SIEGE_UTILITIES_HOME": "siege_utilities",
            "SIEGE_UTILITIES_TEST": "siege_utilities_test",
            "SIEGE_ANALYTICS_ROOT": "siege_analytics",
            "GEOCODING_PROJECT": "siege_analytics/geocoding",
            "MASAI_PROJECT": "siege_analytics/masai",
            "SIEGE_CACHE_DIR": ".siege_cache", "SPARK_CACHE_DIR": ".spark_hdfs_cache",
            "TEMP_DIR": ".siege_temp", "DOWNLOAD_TEMP_DIR": ".siege_temp/downloads",
            "PROCESSING_TEMP_DIR": ".siege_temp/processing",
            "SIEGE_OUTPUT_DIR": "Downloads",
            "REPORTS_OUTPUT_DIR": "Downloads/siege_reports",
            "CHARTS_OUTPUT_DIR": "Downloads/siege_charts",
            "MAPS_OUTPUT_DIR": "Downloads/siege_maps",
            "DATA_DIR": "siege_utilities/data",
            "CENSUS_DATA_DIR": "siege_utilities/data/census",
            "NCES_DATA_DIR": "siege_utilities/data/nces",
            "SAMPLE_DATA_DIR": "siege_utilities/data/samples",
            "CONFIG_DIR": "siege_utilities/config", "USER_CONFIG_FILE": ".siege_config.yaml",
            "DATABASE_CONFIG_DIR": "siege_utilities/config/databases",
            "LOG_DIR": ".siege_logs", "ERROR_LOG_DIR": ".siege_logs/errors",
            "DEBUG_LOG_DIR": ".siege_logs/debug", "BACKUP_DIR": ".siege_backups",
            "CONFIG_BACKUP_DIR": ".siege_backups/config",
            "DATA_BACKUP_DIR": ".siege_backups/data",
        }}
        for name, suffix in expected.items():
            assert getattr(paths, name) == root / suffix, name
        for name in ("SIEGE_UTILITIES_HOME", "SIEGE_CACHE_DIR", "SIEGE_OUTPUT_DIR"):
            assert getattr(constants, name) == root / expected[name], name
        from siege_utilities.geo.census.catalog_cache import CatalogCache
        assert CatalogCache().cache_dir == root / ".siege_utilities/cache/census_catalog"
        from siege_utilities.geo.census_files.pl_downloader import DEFAULT_CACHE_DIR
        assert DEFAULT_CACHE_DIR == root / ".siege_utilities/cache/pl_files"
    """)


@pytest.mark.parametrize("error", ["RuntimeError", "KeyError"])
def test_download_default_handles_home_lookup_errors(monkeypatch, error):
    _run_without_home(monkeypatch, f"""
        import os
        from pathlib import Path
        import tempfile
        from siege_utilities.config import user_config

        expected = Path(tempfile.gettempdir()) / f"siege_utilities-{{os.getuid()}}"
        with patch.object(user_config, "_is_databricks_runtime", return_value=False):
            with patch.object(Path, "home", side_effect={error}("missing home")):
                assert user_config._default_download_directory() == expected / "Downloads/siege_utilities"
    """)


def test_env_path_guards_without_home(monkeypatch):
    _run_without_home(monkeypatch, """
        import os
        from pathlib import Path
        from siege_utilities.config.paths import _env_path

        fallback = Path("fallback")
        os.environ["SIEGE_CACHE"] = "/etc"
        assert _env_path("SIEGE_CACHE", lambda: fallback) == fallback
        os.environ["SIEGE_CACHE"] = "~/cache"
        assert _env_path("SIEGE_CACHE", lambda: fallback) == fallback
    """)


def test_paths_cache_at_first_access_and_reload(monkeypatch, tmp_path):
    _run_without_home(monkeypatch, f"""
        import importlib
        import os
        from pathlib import Path
        from siege_utilities.config import constants, paths

        root = Path({str(tmp_path)!r})
        os.environ["HOME"] = str(root)
        for module in (constants, paths):
            os.environ["SIEGE_CACHE"] = str(root / "first")
            first = module.SIEGE_CACHE_DIR
            os.environ["SIEGE_CACHE"] = str(root / "second")
            assert module.SIEGE_CACHE_DIR is first
            importlib.reload(module)
            assert module.SIEGE_CACHE_DIR == (root / "second").resolve()
    """)


def test_auto_initialization_waits_for_path_access(monkeypatch, tmp_path):
    _run_without_home(monkeypatch, f"""
        import os
        from pathlib import Path

        root = Path({str(tmp_path)!r})
        os.environ["HOME"] = str(root)
        os.environ["SIEGE_AUTO_INIT_DIRS"] = "true"
        from siege_utilities.config import paths
        assert not list(root.iterdir())
        assert paths.SIEGE_CACHE_DIR == root / ".siege_cache"
        assert paths.SIEGE_CACHE_DIR.is_dir()
        assert paths.CENSUS_DATA_DIR.is_dir()
        assert paths.DATA_BACKUP_DIR.is_dir()
    """)
