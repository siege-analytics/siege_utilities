"""Error-path coverage (SU-4b) for the populate_crosswalks management command."""
import pytest
from django.core.management.base import CommandError
from siege_utilities.geo.django.management.commands.populate_crosswalks import Command


def test_normalize_state_raises_command_error_on_invalid_state():
    with pytest.raises(CommandError) as exc_info:
        Command()._normalize_state("NOTASTATEZZ")
    assert "Invalid state identifier" in str(exc_info.value)


def test_handle_rejects_source_year_after_target_year():
    with pytest.raises(CommandError) as exc_info:
        Command().handle(
            source_year=2020, target_year=2010, type="tract",
            state=None, weight_type="population", update=False, batch_size=1000,
        )
    assert "Source year must be earlier than target year" in str(exc_info.value)
