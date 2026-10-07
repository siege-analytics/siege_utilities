"""Boundary-normalization failure must be loud, not silent.

Consensus finding C3 (#1351): when `apply_crosswalk` failed,
`_normalize_boundaries_multi_year` logged a warning and returned the
original-vintage frame. The caller then merges to wide format and
attaches target-year geometry, so the silent fallback placed
source-vintage values on target-vintage boundaries with no failure
signal. The fix raises instead. These tests pin both the failure path
(raises) and the success path (uses the crosswalk result).
"""
import pandas as pd
import pytest

from siege_utilities.geo.timeseries import longitudinal_data as mod


def _yearly():
    # 2015 -> 2010 boundary vintage; target 2020 -> 2020 vintage, so the
    # crosswalk branch fires for 2015.
    df2015 = pd.DataFrame({"GEOID": ["48001", "48003"], "B01001_001E": [10, 20]})
    df2020 = pd.DataFrame({"GEOID": ["48001", "48003"], "B01001_001E": [11, 21]})
    return {2015: df2015, 2020: df2020}


def test_normalization_failure_raises_not_silent_fallback(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("crosswalk file unreachable")

    monkeypatch.setattr(
        "siege_utilities.geo.crosswalk.crosswalk_processor.apply_crosswalk", boom
    )
    with pytest.raises(ValueError, match="Failed to normalize 2015 data"):
        mod._normalize_boundaries_multi_year(
            yearly_data=_yearly(),
            target_year=2020,
            geography_level="county",
            state_fips="48",
        )


def test_normalization_success_uses_crosswalk_result(monkeypatch):
    marker = pd.DataFrame({"GEOID": ["48001"], "B01001_001E": [99]})

    def ok(*args, **kwargs):
        return marker

    monkeypatch.setattr(
        "siege_utilities.geo.crosswalk.crosswalk_processor.apply_crosswalk", ok
    )
    out = mod._normalize_boundaries_multi_year(
        yearly_data=_yearly(),
        target_year=2020,
        geography_level="county",
        state_fips="48",
    )
    # target year passes through unchanged; source year is the crosswalk result
    assert out[2020].equals(_yearly()[2020])
    assert out[2015].equals(marker)
