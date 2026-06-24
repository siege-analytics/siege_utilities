"""Error-path coverage (SU-4b) for the populate_boundaries management command."""
import pytest
from django.core.management.base import CommandError
from siege_utilities.geo.django.management.commands.populate_boundaries import Command


def test_normalize_state_raises_command_error_on_invalid_state():
    with pytest.raises(CommandError) as exc_info:
        Command()._normalize_state("NOTASTATEZZ")
    assert "Invalid state identifier" in str(exc_info.value)
