"""A servable chain: the caller's own 2000 to 2010 crosswalk table through
CrosswalkProcessor.transform, then normalize_to_year from 2010 to 2020.

The Census client publishes only 2010 to 2020, so the first step cannot be a
normalize_to_year call. Only the 2010 to 2020 lookup is patched here.
"""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from siege_utilities.geo.crosswalk import crosswalk_processor
from siege_utilities.geo.crosswalk.crosswalk_processor import (
    CrosswalkProcessor,
    normalize_to_year,
)

OWN_2000_2010 = {"source_geoid": ["A", "B", "C"], "target_geoid": ["X", "Y", "Y"],
                 "area_weight": [1.0, 1.0, 1.0]}
CENSUS_2010_2020 = {"source_geoid": ["X", "Y", "Y"], "target_geoid": ["P", "Q1", "Q2"],
                    "area_weight": [1.0, 0.5, 0.5]}


def _get_crosswalk(source_year, target_year, geography_level="tract", state_fips=None):
    if (source_year, target_year) == (2010, 2020):
        return pd.DataFrame(CENSUS_2010_2020)
    raise ValueError(f"Crosswalk not supported for {source_year}->{target_year}.")


def _chain(data, **kwargs):
    step1 = CrosswalkProcessor(pd.DataFrame(OWN_2000_2010), 2000, 2010, "tract").transform(data)
    with patch.object(crosswalk_processor, "get_crosswalk", side_effect=_get_crosswalk):
        return normalize_to_year(step1, data_year=2010, target_year=2020, **kwargs)


def test_own_table_then_normalize_to_year_carries_coverage():
    data = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [10.0, 5.0, np.nan]})
    out = _chain(data, carried_coverage=["pop_coverage"]).set_index("GEOID")
    assert sorted(out.columns) == ["pop", "pop_coverage"]
    assert out.loc["P", "pop"] == pytest.approx(10.0)
    assert out.loc[["Q1", "Q2"], "pop"].isna().all()
    assert out["pop_coverage"].to_dict() == pytest.approx({"P": 1.0, "Q1": 0.5, "Q2": 0.5})


def test_own_table_then_normalize_to_year_without_carried_coverage_names_the_remedy():
    data = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [10.0, 5.0, 7.0]})
    with pytest.raises(ValueError, match="carried_coverage"):
        _chain(data)


def test_normalize_to_year_2000_to_2010_is_not_served_by_the_census_client():
    data = pd.DataFrame({"GEOID": ["A"], "pop": [1.0]})
    with pytest.raises(ValueError, match="2000->2010"):
        normalize_to_year(data, data_year=2000, target_year=2010)
