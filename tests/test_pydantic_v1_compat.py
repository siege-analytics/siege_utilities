"""
Tests for pydantic v1 / no-pydantic-v2 compatibility (su#160).

Verifies that siege_utilities can be imported and core functions work
when pydantic v2 is not available (e.g., Databricks runtimes with
pydantic v1 pre-installed).

When pydantic v2 IS available, the tests verify that the full config
system loads correctly (no regression).
"""

import pytest
import sys


def _pydantic_major_version():
    """Return the major version of pydantic, or 0 if not installed."""
    try:
        import pydantic
        return int(pydantic.VERSION.split(".")[0])
    except ImportError:
        return 0


_HAS_PYDANTIC_V2 = _pydantic_major_version() >= 2


class TestPackageImport:
    """Top-level import must succeed regardless of pydantic version."""

    def test_import_siege_utilities(self):
        import siege_utilities
        assert hasattr(siege_utilities, "__version__")

    def test_version_is_string(self):
        import siege_utilities
        assert isinstance(siege_utilities.__version__, str)


class TestCoreModulesAvailable:
    """Core modules that do NOT depend on pydantic must always work."""

    def test_core_logging(self):
        from siege_utilities.core.logging import get_logger, log_info, log_warning
        assert callable(get_logger)
        assert callable(log_info)

    def test_core_string_utils(self):
        from siege_utilities import remove_wrapping_quotes_and_trim
        assert callable(remove_wrapping_quotes_and_trim)

    def test_file_operations(self):
        from siege_utilities import file_exists, touch_file, count_lines
        assert callable(file_exists)
        assert callable(touch_file)
        assert callable(count_lines)

    def test_conf_settings(self):
        from siege_utilities.conf import settings
        assert settings is not None

    def test_config_constants(self):
        from siege_utilities.config.census_constants import GEOGRAPHIC_LEVELS
        assert isinstance(GEOGRAPHIC_LEVELS, dict)


class TestPydanticV2ConfigSystem:
    """When pydantic v2 is present, the full config system must load."""

    @pytest.mark.skipif(not _HAS_PYDANTIC_V2, reason="pydantic v2 not available")
    def test_user_config_loads(self):
        from siege_utilities import get_user_config
        assert callable(get_user_config)

    @pytest.mark.skipif(not _HAS_PYDANTIC_V2, reason="pydantic v2 not available")
    def test_enhanced_config_loads(self):
        from siege_utilities import load_user_profile, SiegeConfig
        assert callable(load_user_profile)
        assert SiegeConfig is not None

    @pytest.mark.skipif(not _HAS_PYDANTIC_V2, reason="pydantic v2 not available")
    def test_profile_manager_loads(self):
        from siege_utilities import get_default_profile_location
        assert callable(get_default_profile_location)


class TestPydanticV1Fallback:
    """When pydantic v2 is NOT present, config wrappers degrade gracefully."""

    @pytest.mark.skipif(_HAS_PYDANTIC_V2, reason="pydantic v2 is available")
    def test_get_user_config_raises_helpful_error(self):
        from siege_utilities import get_user_config
        with pytest.raises(ImportError, match="pydantic"):
            get_user_config()

    @pytest.mark.skipif(_HAS_PYDANTIC_V2, reason="pydantic v2 is available")
    def test_load_user_profile_raises_helpful_error(self):
        from siege_utilities import load_user_profile
        with pytest.raises(ImportError, match="pydantic"):
            load_user_profile("test")

    @pytest.mark.skipif(_HAS_PYDANTIC_V2, reason="pydantic v2 is available")
    def test_profile_manager_raises_helpful_error(self):
        from siege_utilities import get_default_profile_location
        with pytest.raises(ImportError, match="pydantic"):
            get_default_profile_location()

    @pytest.mark.skipif(_HAS_PYDANTIC_V2, reason="pydantic v2 is available")
    def test_user_config_singleton_is_none(self):
        from siege_utilities import user_config
        assert user_config is None


class TestPackageIntrospection:
    """Package introspection functions must work regardless of pydantic."""

    def test_check_dependencies(self):
        from siege_utilities import check_dependencies
        deps = check_dependencies()
        assert isinstance(deps, dict)

    def test_get_package_info(self):
        from siege_utilities import get_package_info
        info = get_package_info()
        assert isinstance(info, dict)
        assert "total_functions" in info
