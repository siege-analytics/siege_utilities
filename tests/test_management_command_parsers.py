"""Guard management command credentials without using a database or network."""

import argparse
import importlib
import re
from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("django", reason="Install siege_utilities[geodjango] to test command parsers")
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError

try:
    from django.contrib.gis import gdal  # noqa: F401
except (ImproperlyConfigured, OSError) as exc:
    pytest.skip(
        f"Install GDAL and configure GDAL_LIBRARY_PATH to test command parsers: {exc}",
        allow_module_level=True,
    )

from siege_utilities.geo.django.management.commands import stage_boundaries_s3 as stage


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).resolve().parents[1]
_COMMAND_MODULES = tuple(
    ".".join(path.relative_to(_ROOT).with_suffix("").parts)
    for path in sorted((_ROOT / "siege_utilities").glob("**/management/commands/*.py"))
    if not path.name.startswith("_")
)
if not _COMMAND_MODULES:
    raise RuntimeError("No management commands found for the credential-default guard")

_SENSITIVE_DEST = re.compile(
    r"(?:^|_)(?:(?:password|token|api_key)$|secret\w*|aws_(?:secret|access|session))",
    re.IGNORECASE,
)


@pytest.mark.parametrize("module_name", _COMMAND_MODULES)
def test_management_command_sensitive_defaults_are_none(module_name):
    command = importlib.import_module(module_name).Command()
    parsers = [command.create_parser("manage.py", module_name.rsplit(".", 1)[-1])]
    violations = []
    while parsers:
        for action in parsers.pop()._actions:
            if isinstance(action, argparse._SubParsersAction):
                parsers.extend(action.choices.values())
            if action.option_strings and _SENSITIVE_DEST.search(action.dest):
                if action.default is not None:
                    # Report only the option name, never a credential default.
                    violations.append(action.dest)
    assert not violations, f"{module_name}: non-None sensitive defaults: {violations}"


@pytest.mark.parametrize(
    "flag,environment_variable",
    [("--secret-key", "AWS_SECRET_ACCESS_KEY"), ("--access-key", "AWS_ACCESS_KEY_ID")],
)
@pytest.mark.parametrize("form", ["separate", "equals"])
def test_removed_credential_flags_reject_without_echoing(flag, environment_variable, form):
    sentinel = "removed-credential-sentinel-1578"
    flags = [flag, sentinel] if form == "separate" else [f"{flag}={sentinel}"]
    parser = stage.Command().create_parser("manage.py", "stage_boundaries_s3")

    with pytest.raises(CommandError) as error:
        parser.parse_args(["--year", "2020", "--type", "county", *flags])

    message = str(error.value)
    assert sentinel not in message
    assert message == (
        f"Error: argument {flag}: {flag} was removed; "
        f"set {environment_variable} or use a boto3 profile"
    )


@pytest.mark.parametrize(
    "flag,environment_variable",
    [("--secret-key", "AWS_SECRET_ACCESS_KEY"), ("--access-key", "AWS_ACCESS_KEY_ID")],
)
@pytest.mark.parametrize("form", ["separate", "equals"])
def test_removed_credential_cli_exits_two_without_traceback(
    capsys, flag, environment_variable, form,
):
    sentinel = "removed-credential-sentinel-1578"
    flags = [flag, sentinel] if form == "separate" else [f"{flag}={sentinel}"]

    with pytest.raises(SystemExit) as error:
        stage.Command().run_from_argv([
            "manage.py", "stage_boundaries_s3", "--year", "2020", "--type", "county", *flags,
        ])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert sentinel not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err
    assert f"error: argument {flag}: {flag} was removed" in captured.err
    assert f"set {environment_variable} or use a boto3 profile" in captured.err


@pytest.mark.parametrize("flag", ["--se", "--s", "--secret_key"])
def test_malformed_credential_cli_redacts_equals_value(capsys, flag):
    sentinel = "removed-credential-sentinel-1578"

    with pytest.raises(SystemExit) as error:
        stage.Command().run_from_argv([
            "manage.py", "stage_boundaries_s3", "--year", "2020", "--type", "county",
            f"{flag}={sentinel}",
        ])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert f"{flag}=<redacted>" in captured.err
    assert sentinel not in captured.out + captured.err


@pytest.mark.parametrize(
    "option,environment_variable",
    [("secret_key", "AWS_SECRET_ACCESS_KEY"), ("access_key", "AWS_ACCESS_KEY_ID")],
)
@pytest.mark.parametrize("value", ["removed-credential-sentinel-1578", ""])
def test_call_command_rejects_removed_credentials(
    monkeypatch, capsys, option, environment_variable, value,
):
    sdk = Mock()
    export = Mock()
    monkeypatch.setattr(stage, "boto3", sdk)
    monkeypatch.setattr(stage, "gpd", Mock())
    monkeypatch.setattr(stage.Command, "_export_type", export)

    with pytest.raises(CommandError) as error:
        call_command(
            "stage_boundaries_s3", year=2020, type="county", dry_run=True, **{option: value},
        )

    assert str(error.value) == (
        f"--{option.replace('_', '-')} was removed; "
        f"set {environment_variable} or use a boto3 profile"
    )
    captured = capsys.readouterr()
    if value:
        assert value not in str(error.value) + captured.out + captured.err
    sdk.client.assert_not_called()
    export.assert_not_called()


def test_removed_credential_flags_are_hidden_from_help():
    help_text = stage.Command().create_parser("manage.py", "stage_boundaries_s3").format_help()
    assert "--secret-key" not in help_text
    assert "--access-key" not in help_text
