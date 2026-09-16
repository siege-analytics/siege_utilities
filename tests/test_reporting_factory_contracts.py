"""Canonical root-import contracts for reporting factory helpers."""

import sys
import types

from siege_utilities import create_powerpoint_generator
from siege_utilities import create_report_generator
from siege_utilities import get_report_output_directory


def test_get_report_output_directory_uses_profile_downloads(
    monkeypatch,
    tmp_path,
):
    from siege_utilities.config import enhanced_config

    calls = []

    def fake_get_download_directory(username):
        calls.append(username)
        return tmp_path / "downloads"

    monkeypatch.setenv("SIEGE_USERNAME", "report-user")
    monkeypatch.setattr(
        enhanced_config,
        "get_download_directory",
        fake_get_download_directory,
    )

    assert get_report_output_directory("client-a") == (
        tmp_path / "downloads" / "client-a" / "reports"
    )
    assert get_report_output_directory() == tmp_path / "downloads" / "reports"
    assert calls == ["report-user", "report-user"]


def test_create_report_generator_uses_profile_report_directory(
    monkeypatch,
    tmp_path,
):
    from siege_utilities import reporting

    report_generator = types.ModuleType(
        "siege_utilities.reporting.report_generator"
    )
    created = []

    class FakeReportGenerator:
        def __init__(self, client_name, output_dir):
            created.append((client_name, output_dir))

    report_generator.ReportGenerator = FakeReportGenerator
    monkeypatch.setattr(
        reporting,
        "get_report_output_directory",
        lambda client_code=None: tmp_path / client_code / "reports",
    )
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.reporting.report_generator",
        report_generator,
    )

    result = create_report_generator("Acme", "acme")

    assert isinstance(result, FakeReportGenerator)
    assert created == [("Acme", tmp_path / "acme" / "reports")]


def test_create_powerpoint_generator_uses_profile_presentation_directory(
    monkeypatch,
    tmp_path,
):
    enhanced_config = types.ModuleType(
        "siege_utilities.config.enhanced_config"
    )
    powerpoint_generator = types.ModuleType(
        "siege_utilities.reporting.powerpoint_generator"
    )
    calls = []
    created = []

    def fake_get_download_directory(username):
        calls.append(username)
        return tmp_path / "downloads"

    class FakePowerPointGenerator:
        def __init__(self, client_name, output_dir):
            created.append((client_name, output_dir))

    enhanced_config.get_download_directory = fake_get_download_directory
    powerpoint_generator.PowerPointGenerator = FakePowerPointGenerator
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.config.enhanced_config",
        enhanced_config,
    )
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.reporting.powerpoint_generator",
        powerpoint_generator,
    )
    monkeypatch.setenv("SIEGE_USERNAME", "deck-user")

    result = create_powerpoint_generator("Acme", "acme")

    assert isinstance(result, FakePowerPointGenerator)
    assert calls == ["deck-user"]
    assert created == [
        ("Acme", tmp_path / "downloads" / "acme" / "presentations")
    ]
