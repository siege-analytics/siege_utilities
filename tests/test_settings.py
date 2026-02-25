"""
Tests for siege_utilities.conf settings layer.

Covers:
- Default resolution
- Env var override + type coercion
- YAML file loading + directory walking
- override() context manager (single + nested)
- Unknown setting → AttributeError
- Django integration (mocked)
- Priority ordering
- Thread safety
- Singleton reset for test isolation
"""

import os
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from siege_utilities.conf import Settings, settings
from siege_utilities.conf.defaults import DEFAULTS


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset the Settings singleton between every test."""
    Settings._reset()
    yield
    Settings._reset()


# ── 1. Default resolution ──────────────────────────────────────


class TestDefaults:
    def test_storage_crs_default(self):
        s = Settings()
        assert s.STORAGE_CRS == 4269

    def test_projection_crs_default(self):
        s = Settings()
        assert s.PROJECTION_CRS == 2163

    def test_web_crs_default(self):
        s = Settings()
        assert s.WEB_CRS == 4326

    def test_distance_units_default(self):
        s = Settings()
        assert s.DISTANCE_UNITS == "miles"

    def test_census_timeout_default(self):
        s = Settings()
        assert s.CENSUS_TIMEOUT == 45

    def test_spatial_backend_default(self):
        s = Settings()
        assert s.SPATIAL_BACKEND == "geopandas"

    def test_tabular_engine_default(self):
        s = Settings()
        assert s.TABULAR_ENGINE == "pandas"

    def test_all_defaults_accessible(self):
        """Every key in DEFAULTS should be accessible."""
        s = Settings()
        for key in DEFAULTS:
            assert getattr(s, key) == DEFAULTS[key]


# ── 2. Environment variable override ───────────────────────────


class TestEnvVarOverride:
    def test_int_from_env(self):
        with patch.dict(os.environ, {"SIEGE_STORAGE_CRS": "4326"}):
            s = Settings()
            assert s.STORAGE_CRS == 4326

    def test_string_from_env(self):
        with patch.dict(os.environ, {"SIEGE_DISTANCE_UNITS": "km"}):
            s = Settings()
            assert s.DISTANCE_UNITS == "km"

    def test_env_beats_default(self):
        with patch.dict(os.environ, {"SIEGE_PROJECTION_CRS": "5070"}):
            s = Settings()
            assert s.PROJECTION_CRS == 5070


# ── 3. Type coercion ───────────────────────────────────────────


class TestCoercion:
    def test_coerce_int(self):
        s = Settings()
        result = s._coerce("STORAGE_CRS", "4326")
        assert result == 4326
        assert isinstance(result, int)

    def test_coerce_string(self):
        s = Settings()
        result = s._coerce("DISTANCE_UNITS", "km")
        assert result == "km"
        assert isinstance(result, str)

    def test_coerce_unknown_key_returns_string(self):
        """If key not in DEFAULTS, coerce returns the raw string."""
        s = Settings()
        result = s._coerce("UNKNOWN_SETTING", "hello")
        assert result == "hello"


# ── 4. YAML file loading ───────────────────────────────────────


class TestYAMLLoading:
    def test_yaml_file_loaded(self, tmp_path):
        yaml_file = tmp_path / "siege_utilities.yaml"
        yaml_file.write_text("STORAGE_CRS: 4326\nDISTANCE_UNITS: km\n")

        with patch("siege_utilities.conf.Path.cwd", return_value=tmp_path):
            s = Settings()
            assert s.STORAGE_CRS == 4326
            assert s.DISTANCE_UNITS == "km"

    def test_yaml_walks_up(self, tmp_path):
        """YAML should be found by walking up from CWD."""
        yaml_file = tmp_path / "siege_utilities.yaml"
        yaml_file.write_text("PROJECTION_CRS: 5070\n")

        child = tmp_path / "a" / "b" / "c"
        child.mkdir(parents=True)

        with patch("siege_utilities.conf.Path.cwd", return_value=child):
            s = Settings()
            assert s.PROJECTION_CRS == 5070

    def test_no_yaml_falls_through(self, tmp_path):
        """When no YAML file exists, defaults are used."""
        with patch("siege_utilities.conf.Path.cwd", return_value=tmp_path):
            s = Settings()
            assert s.STORAGE_CRS == 4269  # default

    def test_yaml_missing_pyyaml(self, tmp_path):
        """If pyyaml is missing, YAML loading is skipped gracefully."""
        yaml_file = tmp_path / "siege_utilities.yaml"
        yaml_file.write_text("STORAGE_CRS: 4326\n")

        with patch("siege_utilities.conf.Path.cwd", return_value=tmp_path):
            with patch.dict("sys.modules", {"yaml": None}):
                s = Settings()
                # yaml import fails, falls through to defaults
                assert s.STORAGE_CRS == 4269


# ── 5. override() context manager ──────────────────────────────


class TestOverride:
    def test_override_basic(self):
        s = Settings()
        assert s.STORAGE_CRS == 4269
        with s.override(STORAGE_CRS=4326):
            assert s.STORAGE_CRS == 4326
        assert s.STORAGE_CRS == 4269

    def test_override_nested(self):
        s = Settings()
        with s.override(STORAGE_CRS=4326):
            assert s.STORAGE_CRS == 4326
            with s.override(STORAGE_CRS=5070):
                assert s.STORAGE_CRS == 5070
            assert s.STORAGE_CRS == 4326
        assert s.STORAGE_CRS == 4269

    def test_override_multiple_keys(self):
        s = Settings()
        with s.override(STORAGE_CRS=4326, DISTANCE_UNITS="km"):
            assert s.STORAGE_CRS == 4326
            assert s.DISTANCE_UNITS == "km"
        assert s.STORAGE_CRS == 4269
        assert s.DISTANCE_UNITS == "miles"

    def test_override_yields_settings(self):
        s = Settings()
        with s.override(STORAGE_CRS=4326) as ctx:
            assert ctx is s


# ── 6. Unknown settings ────────────────────────────────────────


class TestUnknownSetting:
    def test_raises_attribute_error(self):
        s = Settings()
        with pytest.raises(AttributeError, match="siege_utilities has no setting"):
            _ = s.NONEXISTENT_SETTING

    def test_private_attrs_raise_normally(self):
        s = Settings()
        with pytest.raises(AttributeError):
            _ = s._some_private_thing


# ── 7. Django integration ──────────────────────────────────────


class TestDjangoIntegration:
    def test_django_settings_consulted(self):
        mock_django_settings = MagicMock()
        mock_django_settings.STORAGE_CRS = 9999

        mock_module = MagicMock()
        mock_module.settings = mock_django_settings

        with patch.dict("sys.modules", {"django": MagicMock(), "django.conf": mock_module}):
            s = Settings()
            assert s.STORAGE_CRS == 9999


# ── 8. Priority ordering ───────────────────────────────────────


class TestPriority:
    def test_env_beats_yaml(self, tmp_path):
        yaml_file = tmp_path / "siege_utilities.yaml"
        yaml_file.write_text("STORAGE_CRS: 5070\n")

        with patch("siege_utilities.conf.Path.cwd", return_value=tmp_path):
            with patch.dict(os.environ, {"SIEGE_STORAGE_CRS": "4326"}):
                s = Settings()
                assert s.STORAGE_CRS == 4326  # env wins

    def test_override_beats_env(self):
        with patch.dict(os.environ, {"SIEGE_STORAGE_CRS": "4326"}):
            s = Settings()
            assert s.STORAGE_CRS == 4326
            with s.override(STORAGE_CRS=9999):
                assert s.STORAGE_CRS == 9999

    def test_yaml_beats_defaults(self, tmp_path):
        yaml_file = tmp_path / "siege_utilities.yaml"
        yaml_file.write_text("STORAGE_CRS: 5070\n")

        with patch("siege_utilities.conf.Path.cwd", return_value=tmp_path):
            s = Settings()
            assert s.STORAGE_CRS == 5070  # yaml wins over default 4269


# ── 9. Thread safety ───────────────────────────────────────────


class TestThreadSafety:
    def test_singleton_across_threads(self):
        instances = []

        def get_instance():
            instances.append(Settings())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert all(inst is instances[0] for inst in instances)


# ── 10. Singleton reset ────────────────────────────────────────


class TestReset:
    def test_reset_clears_singleton(self):
        s1 = Settings()
        Settings._reset()
        s2 = Settings()
        assert s1 is not s2

    def test_reset_clears_yaml_cache(self, tmp_path):
        yaml_file = tmp_path / "siege_utilities.yaml"
        yaml_file.write_text("STORAGE_CRS: 5070\n")

        with patch("siege_utilities.conf.Path.cwd", return_value=tmp_path):
            s1 = Settings()
            assert s1.STORAGE_CRS == 5070

        Settings._reset()

        # After reset, no YAML in new cwd → falls back to default
        s2 = Settings()
        assert s2.STORAGE_CRS == 4269


# ── 11. Module-level settings instance ─────────────────────────


class TestModuleLevelInstance:
    def test_import_path(self):
        from siege_utilities.conf import settings as s
        assert isinstance(s, Settings)

    def test_top_level_import(self):
        from siege_utilities import settings as s
        assert isinstance(s, Settings)

    def test_config_reexport(self):
        from siege_utilities.config import settings as s
        assert isinstance(s, Settings)
