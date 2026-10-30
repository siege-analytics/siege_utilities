"""Regression: an unrelated state's invalid span must not poison a query.

Adopted from lean-field's cross-state thread-triage fixture. A
foreign-state assignment with an inverted span must be filtered out by the
state scope before span validation, so it cannot abort a valid query for the
requested state on the provider, overlay-fetch, or place_history paths.
"""
from datetime import date

from siege_utilities.geo.overlays.redistricting import (
    DictRedistrictingDataProvider,
    DistrictAssignment,
    RedistrictingOverlay,
)
from siege_utilities.geo.overlay_registry import OverlayRegistry
from siege_utilities.geo.place_history import DictCrosswalkProvider, place_history


def setup_rows():
    valid = DistrictAssignment(
        plan_id="tx-valid", state="TX", from_date=date(2020, 1, 1), to_date=None
    )
    invalid_other_state = DistrictAssignment(
        plan_id="ca-invalid", state="CA",
        from_date=date(2023, 6, 2), to_date=date(2023, 6, 1),
    )
    provider = DictRedistrictingDataProvider()
    provider.add(valid)
    provider.add(invalid_other_state)
    return provider, valid, invalid_other_state


def test_other_state_invalid_span_does_not_abort_provider():
    # The TX abbreviation is accepted on both versions, isolating validation
    # order from the independently fixed FIPS-to-abbreviation bug on develop.
    p, valid, invalid = setup_rows()
    assert p.get_district_assignments("48201", 2023, 2023, "TX") == [valid]
    assert p._assignments == [valid, invalid]


def test_other_state_invalid_span_does_not_abort_overlay():
    p, valid, invalid = setup_rows()
    assert RedistrictingOverlay(p).fetch("48201", 2023, 2023, "TX").assignments == [valid]
    assert p._assignments == [valid, invalid]


def test_other_state_invalid_span_does_not_remove_place_history_overlay():
    p, valid, invalid = setup_rows()
    registry = OverlayRegistry()
    registry.register_instance("redistricting", RedistrictingOverlay(p))
    result = place_history(
        "48201", 2023, 2023, state_fips="TX", overlays=["redistricting"],
        provider=DictCrosswalkProvider(), overlay_registry=registry,
    )
    assert result.errors == []
    assert result.overlays["redistricting"].assignments == [valid]
    assert p._assignments == [valid, invalid]
