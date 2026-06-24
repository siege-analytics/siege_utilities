"""Error-path coverage (SU-4b) for the stage_boundaries_s3 management command."""
import pytest
from django.core.management.base import CommandError
import siege_utilities.geo.django.management.commands.stage_boundaries_s3 as stage


def test_handle_raises_when_boto3_missing(monkeypatch):
    # Force the dependency guard regardless of whether boto3 is installed.
    monkeypatch.setattr(stage, "boto3", None)
    with pytest.raises(CommandError) as exc_info:
        stage.Command().handle()
    assert "boto3 is required" in str(exc_info.value)
