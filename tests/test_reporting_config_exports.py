"""Tests for reporting top-level config export/import functions (ELE-2420).

Applies PU3 from docs/TEST_UPGRADES.md — every raise path has a negative test.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from siege_utilities.reporting import (
    ReportingConfigError,
    export_branding_config,
    import_branding_config,
    export_chart_type_config,
)


class TestExportBrandingConfig:
    def test_raises_on_os_error(self, tmp_path, monkeypatch):
        """OSError from the branding manager surfaces as ReportingConfigError."""
        class _Boom:
            def export_branding_config(self, *a, **kw):
                raise OSError("disk full")

        with patch("siege_utilities.reporting.client_branding.ClientBrandingManager", return_value=_Boom()):
            with pytest.raises(ReportingConfigError, match="failed to export"):
                export_branding_config("acme", str(tmp_path / "out.yaml"))

    def test_raises_on_unknown_client(self, tmp_path):
        """ValueError from the manager (unknown client) surfaces as ReportingConfigError."""
        class _Boom:
            def export_branding_config(self, *a, **kw):
                raise ValueError("unknown client")

        with patch("siege_utilities.reporting.client_branding.ClientBrandingManager", return_value=_Boom()):
            with pytest.raises(ReportingConfigError, match="acme"):
                export_branding_config("acme", str(tmp_path / "out.yaml"))

    def test_success_returns_true(self, tmp_path):
        class _OK:
            def export_branding_config(self, *a, **kw):
                return True

        with patch("siege_utilities.reporting.client_branding.ClientBrandingManager", return_value=_OK()):
            assert export_branding_config("acme", str(tmp_path / "out.yaml")) is True


class TestImportBrandingConfig:
    def test_raises_on_missing_file(self, tmp_path):
        class _Boom:
            def import_branding_config(self, *a, **kw):
                raise OSError("no such file")

        with patch("siege_utilities.reporting.client_branding.ClientBrandingManager", return_value=_Boom()):
            with pytest.raises(ReportingConfigError):
                import_branding_config(str(tmp_path / "missing.yaml"))

    def test_raises_on_parse_error(self, tmp_path):
        class _Boom:
            def import_branding_config(self, *a, **kw):
                raise ValueError("bad yaml")

        with patch("siege_utilities.reporting.client_branding.ClientBrandingManager", return_value=_Boom()):
            with pytest.raises(ReportingConfigError):
                import_branding_config(str(tmp_path / "out.yaml"))

    def test_success_passes_client_name(self, tmp_path):
        captured = {}

        class _OK:
            def import_branding_config(self, path, client_name):
                captured["path"] = path
                captured["client_name"] = client_name
                return True

        with patch("siege_utilities.reporting.client_branding.ClientBrandingManager", return_value=_OK()):
            assert import_branding_config(str(tmp_path / "x.yaml"), client_name="acme") is True
        assert captured["client_name"] == "acme"


class TestExportChartTypeConfig:
    @pytest.fixture(autouse=True)
    def _require_matplotlib(self):
        pytest.importorskip("matplotlib")

    def test_raises_on_unknown_chart_type(self, tmp_path):
        class _Boom:
            def export_chart_type_config(self, *a, **kw):
                raise KeyError("unknown chart type")

        with patch("siege_utilities.reporting.chart_types.ChartTypeRegistry", return_value=_Boom()):
            with pytest.raises(ReportingConfigError, match="mystery_chart"):
                export_chart_type_config("mystery_chart", str(tmp_path / "out.json"))

    def test_success_returns_true(self, tmp_path):
        class _OK:
            def export_chart_type_config(self, *a, **kw):
                return None  # implementation returns None; wrapper returns True

        with patch("siege_utilities.reporting.chart_types.ChartTypeRegistry", return_value=_OK()):
            assert export_chart_type_config("bar", str(tmp_path / "out.json")) is True


class TestReportingConfigError:
    def test_is_runtime_error(self):
        assert issubclass(ReportingConfigError, RuntimeError)

    def test_preserves_cause(self):
        """raise ... from e should populate __cause__ for traceback chain."""
        original = OSError("underlying")
        wrapped = ReportingConfigError("wrapped")
        try:
            raise wrapped from original
        except ReportingConfigError as e:
            assert e.__cause__ is original
