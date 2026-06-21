"""Tests for VARIABLE_GROUPS deprecation warning."""

import warnings



def _reset_warned():
    from siege_utilities.geo.census.variable_registry import _DeprecatedDict
    _DeprecatedDict._warned = False


class TestVariableGroupsDeprecation:
    def test_access_emits_deprecation_warning(self):
        _reset_warned()
        from siege_utilities.geo.census.variable_registry import VARIABLE_GROUPS
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = VARIABLE_GROUPS["total_population"]
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "CensusCatalog" in str(w[0].message)

    def test_warns_only_once(self):
        _reset_warned()
        from siege_utilities.geo.census.variable_registry import VARIABLE_GROUPS
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = VARIABLE_GROUPS["total_population"]
            _ = VARIABLE_GROUPS["demographics_basic"]
            assert len(w) == 1

    def test_data_still_accessible(self):
        _reset_warned()
        from siege_utilities.geo.census.variable_registry import VARIABLE_GROUPS
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert "B01001_001E" in VARIABLE_GROUPS["total_population"]

    def test_iteration_emits_warning(self):
        _reset_warned()
        from siege_utilities.geo.census.variable_registry import VARIABLE_GROUPS
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            keys = list(VARIABLE_GROUPS.keys())
            assert len(w) == 1
            assert len(keys) > 0

    def test_get_emits_warning(self):
        _reset_warned()
        from siege_utilities.geo.census.variable_registry import VARIABLE_GROUPS
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = VARIABLE_GROUPS.get("total_population")
            assert len(w) == 1
            assert result is not None

    def test_registry_init_does_not_warn(self):
        _reset_warned()
        from siege_utilities.geo.census.variable_registry import VariableRegistry
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            reg = VariableRegistry()
            _ = reg.resolve_variables("total_population")
            assert len(w) == 0
