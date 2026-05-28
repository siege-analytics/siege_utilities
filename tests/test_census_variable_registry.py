"""Error-path tests for siege_utilities.geo.census.variable_registry (SU-4b)."""

import warnings

import pytest

try:
    from siege_utilities.geo.census.variable_registry import (
        VARIABLE_GROUPS,
        VariableRegistry,
        _DeprecatedDict,
    )
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or variable_registry deps missing")


class TestDeprecatedDictErrors:
    """Error paths for _DeprecatedDict deprecation warnings."""

    def test_access_emits_deprecation_warning(self):
        """Accessing VARIABLE_GROUPS must emit DeprecationWarning."""
        _DeprecatedDict._warned = False
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = VARIABLE_GROUPS["total_population"]
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "deprecated" in str(deprecation_warnings[0].message).lower()


class TestVariableRegistryErrors:
    """Error paths for VariableRegistry."""

    def test_missing_variable_returns_unknown(self):
        """Missing variable description returns 'Unknown'."""
        reg = VariableRegistry()
        assert reg.get_description("FAKE_VAR_999") == "Unknown"

    def test_invalid_group_name_returns_as_variable(self):
        """Invalid group name treated as single variable code."""
        reg = VariableRegistry()
        result = reg.resolve_variables("NOT_A_GROUP_XYZ")
        assert result == ["NOT_A_GROUP_XYZ"]


class TestVariableRegistryHappyPath:
    """Sanity checks for VariableRegistry."""

    def test_resolve_known_group(self):
        """Known group name resolves to variable list."""
        reg = VariableRegistry()
        result = reg.resolve_variables("total_population")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_add_moe_variables(self):
        """MOE variables are added for estimate variables."""
        reg = VariableRegistry()
        result = reg.add_moe_variables(["B01001_001E"])
        assert "B01001_001M" in result
