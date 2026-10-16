"""Guard management command credentials without using a database or network."""

import argparse
import importlib
import re
from pathlib import Path

import pytest

pytest.importorskip("django", reason="Install siege_utilities[geodjango] to test command parsers")
from django.core.exceptions import ImproperlyConfigured
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

_SENSITIVE_DEST = re.compile(r"key|secret|token|password|endpoint", re.IGNORECASE)


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
    assert message == f"{flag} was removed; set {environment_variable} or use a boto3 profile"


def test_removed_credential_flags_are_hidden_from_help():
    help_text = stage.Command().create_parser("manage.py", "stage_boundaries_s3").format_help()
    assert "--secret-key" not in help_text
    assert "--access-key" not in help_text
