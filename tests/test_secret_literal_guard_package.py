"""Scan the published package in the required test matrix (#1578)."""

from pathlib import Path

import pytest

from scripts.check_secret_literals import main


pytestmark = pytest.mark.unit
_PACKAGE = Path(__file__).resolve().parents[1] / "siege_utilities"


def test_published_package_has_no_credential_literals(capsys):
    result = main([str(_PACKAGE)])
    captured = capsys.readouterr()
    assert result == 0, captured.out + captured.err
