"""Tests for ELE-2437: data/ split by nature + deprecation shims."""
from __future__ import annotations

import importlib
import sys
import warnings


def _reimport(module_name: str):
    """Force a fresh import so the module-level DeprecationWarning fires."""
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


class TestNewPackageLayout:
    """Files moved to new homes per the D2 decision."""

    def test_engines_package_exists(self):
        import siege_utilities.engines.dataframe_engine as mod
        assert hasattr(mod, "Engine")
        assert hasattr(mod, "DataFrameEngine")
        assert hasattr(mod, "get_engine")

    def test_statistics_subpackage_exists(self):
        import siege_utilities.data.statistics.cross_tabulation as ct
        import siege_utilities.data.statistics.moe_propagation as mp
        assert hasattr(ct, "contingency_table")
        assert hasattr(mp, "moe_sum")

    def test_reference_package_exists(self):
        import siege_utilities.reference.naics_soc_crosswalk as nc
        import siege_utilities.reference.sample_data as sd
        # Both modules import without error; that's enough here
        assert nc is not None
        assert sd is not None


class TestDeprecationShims:
    """Old paths still work but emit DeprecationWarning."""

    def test_data_dataframe_engine_shim(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = _reimport("siege_utilities.data.dataframe_engine")
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert hasattr(mod, "get_engine")

    def test_data_cross_tabulation_shim(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = _reimport("siege_utilities.data.cross_tabulation")
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert hasattr(mod, "contingency_table")

    def test_data_moe_propagation_shim(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = _reimport("siege_utilities.data.moe_propagation")
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert hasattr(mod, "moe_sum")

    def test_data_sample_data_shim(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = _reimport("siege_utilities.data.sample_data")
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        # sample_data exports load_sample_data among others
        assert hasattr(mod, "load_sample_data")

    def test_data_naics_soc_crosswalk_shim(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = _reimport("siege_utilities.data.naics_soc_crosswalk")
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)


class TestDataPackageFacade:
    """Top-level data.__init__ re-exports preserve public API."""

    def test_data_reexports_engine(self):
        from siege_utilities.data import Engine, DataFrameEngine, get_engine
        assert Engine is not None
        assert DataFrameEngine is not None
        assert callable(get_engine)

    def test_data_reexports_sample_data(self):
        from siege_utilities.data import load_sample_data, list_available_datasets
        assert callable(load_sample_data)
        assert callable(list_available_datasets)
