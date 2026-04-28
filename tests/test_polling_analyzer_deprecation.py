"""Tests for ELE-2439: PollingAnalyzer deprecation + analytics_reports promotion."""
from __future__ import annotations

import importlib
import sys
import warnings

import pytest


def _reimport(module_name: str):
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


class TestPollingAnalyzerDeprecation:
    @pytest.fixture(autouse=True)
    def _require_matplotlib(self):
        pytest.importorskip("matplotlib")

    def test_construction_emits_deprecation_warning(self):
        from siege_utilities.reporting.analytics.polling_analyzer import (
            PollingAnalyzer,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            PollingAnalyzer()

        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(deprecations) == 1
        msg = str(deprecations[0].message)
        assert "PollingAnalyzer is deprecated" in msg
        assert "siege_utilities.survey" in msg
        assert "siege_utilities.data.statistics" in msg


class TestAnalyticsReportsPromotion:
    @pytest.fixture(autouse=True)
    def _require_reportlab(self):
        pytest.importorskip("reportlab")

    def test_new_import_path_works(self):
        from siege_utilities.reporting.analytics_reports import (
            AnalyticsReportGenerator,
        )
        assert AnalyticsReportGenerator is not None

    def test_old_path_shim_fires_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = _reimport("siege_utilities.reporting.analytics.analytics_reports")

        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("analytics_reports has moved" in str(w.message) for w in deprecations)
        assert hasattr(mod, "AnalyticsReportGenerator")

    def test_top_level_lazy_export_still_works(self):
        import siege_utilities
        # Lazy attribute access at package top level
        assert hasattr(siege_utilities, "AnalyticsReportGenerator")
