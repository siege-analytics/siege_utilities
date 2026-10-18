"""Regression tests for representative-point demographic assignment (#1562)."""

import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")

from geopandas.testing import assert_geodataframe_equal
from shapely.geometry import Polygon, box

from siege_utilities.geo.providers.redistricting_data_hub import demographic_profile


@pytest.mark.geo
@pytest.mark.parametrize("census_crs", ["EPSG:3857", "EPSG:4326"])
@pytest.mark.parametrize("concave", [False, True], ids=["rectangle", "concave"])
def test_straddling_unit_assigned_once_to_interior_point_district(census_crs, concave):
    plan = gpd.GeoDataFrame(
        {"GEOID": ["A", "B"]},
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs="EPSG:3857",
    )
    straddling = (
        Polygon([(8, 1), (18, 1), (18, 2), (9, 2), (9, 9), (8, 9)])
        if concave else box(8, 1, 11, 3)
    )
    assert straddling.intersects(plan.geometry.iloc[0])
    assert straddling.intersects(plan.geometry.iloc[1])
    assert straddling.representative_point().within(plan.geometry.iloc[0])
    if concave:
        assert not straddling.centroid.within(straddling)
        assert straddling.centroid.within(plan.geometry.iloc[1])

    census = gpd.GeoDataFrame(
        {"TOTPOP": [100, 300], "VAP": [80, 240]},
        geometry=[box(1, 1, 2, 2), straddling],
        crs=plan.crs,
    ).to_crs(census_crs)
    original_census = census.copy()

    result = demographic_profile(plan, census)

    assert result.loc[result["GEOID"] == "A", "TOTPOP"].item() == 400
    assert result.loc[result["GEOID"] == "B", "TOTPOP"].sum() == 0
    assert result["TOTPOP"].sum() == census["TOTPOP"].sum()
    assert result["VAP"].sum() == census["VAP"].sum()
    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"GEOID": ["A"], "TOTPOP": [400], "VAP": [320]})
    )
    assert_geodataframe_equal(census, original_census)


@pytest.mark.geo
def test_units_with_interior_points_outside_plan_are_excluded():
    plan = gpd.GeoDataFrame(
        {"district": ["A"]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3857",
    )
    census = gpd.GeoDataFrame(
        {"residents": [100, 300]},
        geometry=[box(1, 1, 2, 2), box(9, 1, 14, 3)],
        crs=plan.crs,
    )
    outside = census.geometry.iloc[1]
    assert outside.intersects(plan.geometry.iloc[0])
    assert not outside.representative_point().within(plan.geometry.iloc[0])

    result = demographic_profile(
        plan, census, district_id_col="district", population_cols=["residents"]
    )

    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"district": ["A"], "residents": [100]})
    )
