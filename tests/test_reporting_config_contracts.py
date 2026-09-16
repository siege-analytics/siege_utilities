"""Canonical root-import contracts for reporting config helpers."""

import sys
import types

import pytest

from siege_utilities import export_branding_config
from siege_utilities import export_chart_type_config
from siege_utilities import import_branding_config
from siege_utilities.reporting import ReportingConfigError


def install_fake_branding_module(monkeypatch, manager_cls):
    client_branding = types.ModuleType(
        "siege_utilities.reporting.client_branding"
    )
    client_branding.ClientBrandingManager = manager_cls
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.reporting.client_branding",
        client_branding,
    )


def test_branding_config_helpers_delegate_with_paths(monkeypatch, tmp_path):
    calls = []

    class FakeBrandingManager:
        def export_branding_config(self, client_name, export_path):
            calls.append(("export", client_name, export_path))

        def import_branding_config(self, import_path, client_name):
            calls.append(("import", import_path, client_name))

    install_fake_branding_module(monkeypatch, FakeBrandingManager)

    export_path = tmp_path / "branding.json"
    import_path = tmp_path / "incoming.json"

    export_branding_config("Acme", str(export_path))
    import_branding_config(str(import_path), "Acme Imported")

    assert calls == [
        ("export", "Acme", export_path),
        ("import", import_path, "Acme Imported"),
    ]


def install_fake_chart_types_module(monkeypatch, registry_cls):
    chart_types = types.ModuleType("siege_utilities.reporting.chart_types")
    chart_types.ChartTypeRegistry = registry_cls
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.reporting.chart_types",
        chart_types,
    )


def test_export_chart_type_config_delegates_and_returns_true(
    monkeypatch,
    tmp_path,
):
    calls = []

    class FakeChartTypeRegistry:
        def export_chart_type_config(self, chart_type_name, output_path):
            calls.append((chart_type_name, output_path))

    install_fake_chart_types_module(monkeypatch, FakeChartTypeRegistry)

    output_path = tmp_path / "bar-chart.json"

    assert export_chart_type_config("bar", str(output_path)) is True
    assert calls == [("bar", str(output_path))]


def test_config_helpers_wrap_expected_failures(monkeypatch, tmp_path):
    class FailingBrandingManager:
        def export_branding_config(self, client_name, export_path):
            raise ValueError("missing client")

        def import_branding_config(self, import_path, client_name):
            raise ValueError("bad import")

    class FailingChartTypeRegistry:
        def export_chart_type_config(self, chart_type_name, output_path):
            raise ValueError("unknown chart")

    install_fake_branding_module(monkeypatch, FailingBrandingManager)
    install_fake_chart_types_module(monkeypatch, FailingChartTypeRegistry)

    export_message = "failed to export branding"
    import_message = "failed to import branding"
    chart_message = "failed to export chart type"

    with pytest.raises(ReportingConfigError, match=export_message):
        export_branding_config("Missing", str(tmp_path / "branding.json"))
    with pytest.raises(ReportingConfigError, match=import_message):
        import_branding_config(str(tmp_path / "incoming.json"), "Broken")
    with pytest.raises(ReportingConfigError, match=chart_message):
        export_chart_type_config("broken", str(tmp_path / "chart.json"))
