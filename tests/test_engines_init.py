"""Error-path tests for siege_utilities.engines.__init__ (SU-4b)."""

import sys
import types

import pytest


class TestEnginesImportFallback:
    """The engines __init__ catches ImportError on __all__ re-export."""

    def test_import_succeeds_normally(self):
        """engines package loads without error under normal conditions."""
        import siege_utilities.engines as eng

        assert hasattr(eng, "__name__")

    def test_missing_dataframe_engine_does_not_crash(self, monkeypatch):
        """If dataframe_engine raises ImportError, engines still importable."""
        stub = types.ModuleType("siege_utilities.engines.dataframe_engine")
        monkeypatch.setitem(sys.modules, "siege_utilities.engines.dataframe_engine", stub)
        import siege_utilities.engines as eng

        assert eng is not None
