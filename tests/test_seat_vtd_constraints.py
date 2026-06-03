"""Tests for #977: Seat and VTD model constraint enforcement.

Seat constraint (DB-level CheckConstraint) is verified structurally.
VTD clean() validation is tested via direct model method invocation.
"""

import pytest

try:
    from django.core.exceptions import ValidationError

    from siege_utilities.geo.django.models.temporal_political import Seat
    from siege_utilities.geo.django.models.political import VTD

    HAS_DJANGO_GIS = True
except (ImportError, RuntimeError, Exception):
    HAS_DJANGO_GIS = False
    Seat = None
    VTD = None

pytestmark = pytest.mark.skipif(
    not HAS_DJANGO_GIS, reason="Django GIS (GDAL) not available"
)


class TestSeatConstraintStructure:
    """Verify the CheckConstraint exists on the Seat model Meta."""

    def test_constraint_exists(self):
        constraint_names = [c.name for c in Seat._meta.constraints]
        assert "seat_state_required_unless_president" in constraint_names

    def test_constraint_condition_covers_president(self):
        constraint = next(
            c for c in Seat._meta.constraints
            if c.name == "seat_state_required_unless_president"
        )
        assert constraint is not None


class TestVTDCrossStateValidation:
    """VTD.clean() must reject cross-state congressional_district links."""

    def _make_vtd(self, state_fips, cd_state_fips=None):
        """Create a VTD instance with a mock congressional district."""
        vtd = VTD(
            geoid=f"{state_fips}037001",
            state_fips=state_fips,
            county_fips="037",
            vtd_code="001",
            vintage_year=2020,
        )
        if cd_state_fips is not None:

            class FakeCD:
                def __init__(self, sf):
                    self.state_fips = sf

            vtd.congressional_district_id = 999
            vtd._congressional_district_cache = FakeCD(cd_state_fips)
            # Django caches FK objects on the descriptor; simulate by
            # patching the attribute the clean() method reads.
            vtd.congressional_district = FakeCD(cd_state_fips)
        return vtd

    def test_same_state_passes(self):
        vtd = self._make_vtd("06", "06")
        vtd.clean()

    def test_cross_state_raises(self):
        vtd = self._make_vtd("06", "48")
        with pytest.raises(ValidationError) as exc_info:
            vtd.clean()
        assert "congressional_district" in exc_info.value.message_dict

    def test_no_cd_assigned_passes(self):
        vtd = self._make_vtd("06", cd_state_fips=None)
        vtd.clean()
