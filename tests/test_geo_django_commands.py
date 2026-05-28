"""Error-path tests for siege_utilities.geo.django.management.commands (SU-4b).

Covers: classify_urbanicity, populate_boundaries, populate_crosswalks,
populate_demographics, populate_nces, populate_pl_demographics,
stage_boundaries_s3. All require Django to be configured.
"""

import pytest

try:
    from django.conf import settings as _ds
    _DJANGO_CONFIGURED = _ds.configured
except Exception:
    _DJANGO_CONFIGURED = False

pytestmark = pytest.mark.skipif(
    not _DJANGO_CONFIGURED, reason="Django not configured"
)


class TestPopulateBoundariesErrors:
    """Error paths for populate_boundaries command."""

    def test_invalid_state_raises(self):
        """Invalid state identifier must raise CommandError."""
        from django.core.management.base import CommandError
        from siege_utilities.geo.django.management.commands.populate_boundaries import (
            Command,
        )
        cmd = Command()
        with pytest.raises(CommandError):
            cmd._normalize_state("ZZ_INVALID_STATE")


class TestClassifyUrbanicityErrors:
    """Error paths for classify_urbanicity command."""

    def test_invalid_state_raises(self):
        from django.core.management.base import CommandError
        from siege_utilities.geo.django.management.commands.classify_urbanicity import (
            Command,
        )
        cmd = Command()
        with pytest.raises(CommandError):
            cmd._normalize_state("ZZ_INVALID_STATE")


class TestPopulateCrosswalksErrors:
    """Error paths for populate_crosswalks command."""

    def test_invalid_state_raises(self):
        from django.core.management.base import CommandError
        from siege_utilities.geo.django.management.commands.populate_crosswalks import (
            Command,
        )
        cmd = Command()
        with pytest.raises(CommandError):
            cmd._normalize_state("ZZ_INVALID_STATE")


class TestPopulateDemographicsErrors:
    """Error paths for populate_demographics command."""

    def test_invalid_state_raises(self):
        from django.core.management.base import CommandError
        from siege_utilities.geo.django.management.commands.populate_demographics import (
            Command,
        )
        cmd = Command()
        with pytest.raises(CommandError):
            cmd._normalize_state("ZZ_INVALID_STATE")


class TestPopulateNcesErrors:
    """Error paths for populate_nces command."""

    def test_command_class_exists(self):
        from siege_utilities.geo.django.management.commands.populate_nces import (
            Command,
        )
        assert Command is not None


class TestPopulatePLDemographicsErrors:
    """Error paths for populate_pl_demographics command."""

    def test_command_class_exists(self):
        from siege_utilities.geo.django.management.commands.populate_pl_demographics import (
            Command,
        )
        assert Command is not None


class TestStageBoundariesS3Errors:
    """Error paths for stage_boundaries_s3 command."""

    def test_command_class_exists(self):
        from siege_utilities.geo.django.management.commands.stage_boundaries_s3 import (
            Command,
        )
        assert Command is not None
