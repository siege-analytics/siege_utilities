"""Boundary-normalization failure must be loud, not silent.

Consensus finding C3 (#1351): when `apply_crosswalk` failed,
`_normalize_boundaries_multi_year` logged a warning and returned the
original-vintage frame. The caller then merges to wide format and
attaches target-year geometry, so the silent fallback placed
source-vintage values on target-vintage boundaries with no failure
signal. The fix raises instead. These tests pin both the failure path
(raises) and the success path (uses the crosswalk result).
"""
import inspect
import types

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


def test_areal_fallback_imports_the_real_function_name():
    """F13 (name): the areal fallback imported a nonexistent areal_interpolate;
    the real name is interpolate_areal. Cheap inspection guard (writing-tests:6,
    import-name typo is inspection-detectable); the behavioral test below runs
    the real backend.
    """
    src = inspect.getsource(mod.LongitudinalAligner._apply_areal_interpolation)
    assert "interpolate_areal" in src and "import areal_interpolate" not in src
    from siege_utilities.geo.interpolation import areal
    assert hasattr(areal, "interpolate_areal") and not hasattr(areal, "areal_interpolate")


def test_areal_fallback_preserves_target_geoids_behaviorally(monkeypatch):
    """F13 (behavior): fixing the import reaches the real Tobler backend, which
    drops non-geometry target columns. The fallback must re-attach the target
    GEOID so align() does not report success with the identifiers lost.
    """
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("tobler")
    from shapely.geometry import box

    # Source polygon (pop 100) fully covering two equal target polygons.
    source = gpd.GeoDataFrame(
        {"GEOID": ["S1"]}, geometry=[box(0, 0, 2, 1)], crs="EPSG:3857"
    )
    target = gpd.GeoDataFrame(
        {"GEOID": ["T1", "T2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:3857",
    )

    def _boundaries(year, geographic_level, state_fips, **kw):
        return source.copy() if year == 2010 else target.copy()

    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.get_census_boundaries", _boundaries
    )

    aligner = mod.LongitudinalAligner(target_vintage=2020, geography="tract")
    df = pd.DataFrame({"GEOID": ["S1"], "population": [100]})
    out = aligner._apply_areal_interpolation(
        df, source_year=2010, target_year=2020,
        geography_level="tract", state_fips="06", geoid_column="GEOID",
    )

    assert list(out["GEOID"]) == ["T1", "T2"], "target GEOIDs were lost"
    assert abs(out["population"].sum() - 100) < 1e-6, "population not conserved"


def test_areal_fallback_handles_backend_that_retains_geoid(monkeypatch):
    """F13-P2 (Codex re-check): the Tobler backend drops the target GEOID, but
    the Shapely and DuckDB backends retain it. Re-keying by insert() collided
    (`cannot insert GEOID, already exists`) on those backends, so align()
    returned method="failed" with unchanged data. Keying by assignment must
    tolerate a backend that already carries the column.
    """
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box

    source = gpd.GeoDataFrame(
        {"GEOID": ["S1"]}, geometry=[box(0, 0, 2, 1)], crs="EPSG:3857"
    )
    target = gpd.GeoDataFrame(
        {"GEOID": ["T1", "T2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:3857",
    )

    def _boundaries(year, geographic_level, state_fips, **kw):
        return source.copy() if year == 2010 else target.copy()

    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.get_census_boundaries", _boundaries
    )

    # Simulate a GEOID-retaining backend (Shapely/DuckDB): the returned frame
    # already carries GEOID in target order plus the interpolated value.
    retained = gpd.GeoDataFrame(
        {"GEOID": ["T1", "T2"], "population": [50.0, 50.0]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:3857",
    )
    # Patched at the source module: _apply_areal_interpolation imports
    # interpolate_areal in-function (from ..interpolation.areal import ...).
    monkeypatch.setattr(
        "siege_utilities.geo.interpolation.areal.interpolate_areal",
        lambda **kw: types.SimpleNamespace(data=retained.copy()),
    )

    aligner = mod.LongitudinalAligner(target_vintage=2020, geography="tract")
    df = pd.DataFrame({"GEOID": ["S1"], "population": [100]})
    out = aligner._apply_areal_interpolation(
        df, source_year=2010, target_year=2020,
        geography_level="tract", state_fips="06", geoid_column="GEOID",
    )

    assert list(out["GEOID"]) == ["T1", "T2"], "target GEOIDs lost on retain backend"
    assert abs(out["population"].sum() - 100) < 1e-6, "population not conserved"
