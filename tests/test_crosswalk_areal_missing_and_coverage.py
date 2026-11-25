"""Missing contributors and <col>_coverage across crosswalk and areal paths.

#1945: for extensive totals, a target with any missing contributor is missing
(NaN), on the crosswalk path and on the areal-interpolation path alike.

#1779: the <col>_coverage columns a crosswalk step adds are carried through a
chained alignment as coverage. They are not transformed as counts by the next
crosswalk step, not split by area in the areal fallback, and a caller column
with a coverage name is refused instead of overwritten.

Geography: 2000 tracts A, B, C (side by side, equal area); 2010 tracts X = A
and Y = B + C; 2020 tracts P = X and Q1, Q2 = the two halves of Y.
"""
import numpy as np
import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
box = pytest.importorskip("shapely.geometry").box

from siege_utilities.geo import spatial_data  # noqa: E402
from siege_utilities.geo.crosswalk import crosswalk_processor  # noqa: E402
from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor  # noqa: E402
from siege_utilities.geo.interpolation.areal import interpolate_areal  # noqa: E402
from siege_utilities.geo.timeseries.longitudinal_data import LongitudinalAligner  # noqa: E402

K = 1000.0
CRS = "EPSG:5070"
BOUNDS = {
    2000: (["A", "B", "C"], [box(0, 0, K, K), box(K, 0, 2 * K, K), box(2 * K, 0, 3 * K, K)]),
    2010: (["X", "Y"], [box(0, 0, K, K), box(K, 0, 3 * K, K)]),
    2020: (["P", "Q1", "Q2"], [box(0, 0, K, K), box(K, 0, 2 * K, K), box(2 * K, 0, 3 * K, K)]),
}
STEP1 = pd.DataFrame({"source_geoid": ["A", "B", "C"], "target_geoid": ["X", "Y", "Y"],
                      "area_weight": [1.0, 1.0, 1.0]})
STEP2 = pd.DataFrame({"source_geoid": ["X", "Y", "Y"], "target_geoid": ["P", "Q1", "Q2"],
                      "area_weight": [1.0, 0.5, 0.5]})

FULL = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [10.0, 5.0, 7.0]})
PARTIAL = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [10.0, 5.0, np.nan]})


def _boundaries(year, geographic_level="tract", state_fips=None, **_):
    geoids, geoms = BOUNDS[year]
    return gpd.GeoDataFrame({"GEOID": geoids}, geometry=geoms, crs=CRS)


def _crosswalks(both_steps):
    def get_crosswalk(source_year, target_year, geography_level="tract", state_fips=None):
        if (source_year, target_year) == (2000, 2010):
            return STEP1.copy()
        if both_steps and (source_year, target_year) == (2010, 2020):
            return STEP2.copy()
        raise ValueError(f"no crosswalk {source_year}->{target_year}")
    return get_crosswalk


def _align(monkeypatch, data, both_steps):
    monkeypatch.setattr(crosswalk_processor, "get_crosswalk", _crosswalks(both_steps))
    monkeypatch.setattr(spatial_data, "get_census_boundaries", _boundaries)
    result = LongitudinalAligner(target_vintage=2020).align(data, source_vintage=2000)
    return result, result.data.set_index("GEOID")


# --- chained crosswalk steps ---------------------------------------------------

def test_chained_crosswalk_carries_coverage_and_propagates_a_missing_value(monkeypatch):
    result, out = _align(monkeypatch, PARTIAL, both_steps=True)
    assert result.method == "crosswalk"
    assert sorted(out.columns) == ["pop", "pop_coverage"]
    assert out.loc["P", "pop"] == 10.0
    assert out.loc["P", "pop_coverage"] == pytest.approx(1.0)
    # Y was missing after step 1 (C has no value), so both halves are missing,
    # and half of their original contribution weight had data.
    assert out.loc[["Q1", "Q2"], "pop"].isna().all()
    assert out.loc["Q1", "pop_coverage"] == pytest.approx(0.5)
    assert out.loc["Q2", "pop_coverage"] == pytest.approx(0.5)


def test_chained_crosswalk_with_complete_data_reports_full_coverage(monkeypatch):
    _, out = _align(monkeypatch, FULL, both_steps=True)
    assert sorted(out.columns) == ["pop", "pop_coverage"]
    assert out["pop"].to_dict() == {"P": 10.0, "Q1": 6.0, "Q2": 6.0}
    assert (out["pop_coverage"] == 1.0).all()


# --- crosswalk step followed by the areal fallback ----------------------------

def test_areal_fallback_averages_carried_coverage_instead_of_splitting_it(monkeypatch):
    result, out = _align(monkeypatch, FULL, both_steps=False)
    assert result.method == "areal"
    assert sorted(out.columns) == ["pop", "pop_coverage"]
    assert out.loc["P", "pop"] == pytest.approx(10.0)
    assert out.loc["Q1", "pop"] == pytest.approx(6.0)
    assert out.loc["Q2", "pop"] == pytest.approx(6.0)
    assert out["pop_coverage"].to_numpy() == pytest.approx([1.0, 1.0, 1.0])


def test_areal_fallback_propagates_a_missing_value_and_keeps_its_coverage(monkeypatch):
    _, out = _align(monkeypatch, PARTIAL, both_steps=False)
    assert out.loc["P", "pop"] == pytest.approx(10.0)
    assert out.loc[["Q1", "Q2"], "pop"].isna().all()
    assert out.loc["P", "pop_coverage"] == pytest.approx(1.0)
    assert out.loc["Q1", "pop_coverage"] == pytest.approx(0.5)
    assert out.loc["Q2", "pop_coverage"] == pytest.approx(0.5)


def test_align_refuses_a_caller_column_named_like_a_coverage_output(monkeypatch):
    data = FULL.assign(pop_coverage=[1000.0, 400.0, 80.0])
    monkeypatch.setattr(crosswalk_processor, "get_crosswalk", _crosswalks(True))
    monkeypatch.setattr(spatial_data, "get_census_boundaries", _boundaries)
    with pytest.raises(ValueError, match="pop_coverage"):
        LongitudinalAligner(target_vintage=2020).align(data, source_vintage=2000)


# --- #1945: both paths agree ---------------------------------------------------

def test_crosswalk_and_areal_paths_agree_on_a_missing_contributor():
    # Same geography and data on both paths: B and C merge into Y, C missing.
    crosswalk = CrosswalkProcessor(STEP1, 2000, 2010, "tract").transform(PARTIAL)
    crosswalk = crosswalk.set_index("GEOID")["pop"]

    source = _boundaries(2000).merge(PARTIAL, on="GEOID")
    target = _boundaries(2010)
    areal = interpolate_areal(source, target, extensive_variables=["pop"]).data
    areal = pd.Series(areal["pop"].to_numpy(), index=target["GEOID"])

    assert crosswalk.loc["X"] == pytest.approx(10.0)
    assert areal.loc["X"] == pytest.approx(10.0)
    assert pd.isna(crosswalk.loc["Y"])
    assert pd.isna(areal.loc["Y"])
