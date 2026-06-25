"""Error-path coverage (SU-4b) for the populate_nces management command."""
import pytest
from django.core.management.base import CommandError
from siege_utilities.geo.django.management.commands.populate_nces import Command


def test_handle_rejects_unknown_action():
    with pytest.raises(CommandError) as exc_info:
        Command().handle(
            year=2020, action="bogus_action_zzz", state=None,
            update=False, batch_size=500, cache_dir=None,
        )
    assert "Unknown action" in str(exc_info.value)
