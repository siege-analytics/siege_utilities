"""Regression tests for representative-point demographic assignment (#1562)."""

import itertools
import warnings

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
        result,
        pd.DataFrame({"GEOID": ["A", "B"], "TOTPOP": [400, 0], "VAP": [320, 0]}),
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

    with pytest.warns(UserWarning, match=r"1 census unit\(s\).*'residents': 300"):
        result = demographic_profile(
            plan, census, district_id_col="district", population_cols=["residents"]
        )

    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"district": ["A"], "residents": [100]})
    )


@pytest.mark.geo
def test_issue_probe_conserves_input_population():
    """#1562's exact probe: the straddling unit's interior point lies on the D1/D2 edge."""
    plan = gpd.GeoDataFrame(
        {"GEOID": ["D1", "D2"]},
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs=5070,
    )
    census = gpd.GeoDataFrame(
        {"TOTPOP": [100, 200, 300]},
        geometry=[box(1, 1, 2, 2), box(11, 1, 12, 2), box(9, 1, 11, 2)],
        crs=5070,
    )
    point = census.geometry.iloc[2].representative_point()
    # The interior point sits exactly on the shared edge, within neither district.
    assert point.wkt == "POINT (10 1.5)"
    assert not point.within(plan.geometry.iloc[0])
    assert not point.within(plan.geometry.iloc[1])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = demographic_profile(plan, census)

    # Conserved, counted once, and assigned to the first matching plan row.
    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"GEOID": ["D1", "D2"], "TOTPOP": [400, 200]})
    )


def _issue_probe(plan_order=("D1", "D2"), unit_order=(0, 1, 2)):
    boxes = {"D1": box(0, 0, 10, 10), "D2": box(10, 0, 20, 10)}
    plan = gpd.GeoDataFrame(
        {"GEOID": list(plan_order)}, geometry=[boxes[d] for d in plan_order], crs=5070,
    )
    units = [(100, box(1, 1, 2, 2)), (200, box(11, 1, 12, 2)), (300, box(9, 1, 11, 2))]
    census = gpd.GeoDataFrame(
        {"TOTPOP": [units[i][0] for i in unit_order]},
        geometry=[units[i][1] for i in unit_order],
        crs=5070,
    )
    return plan, census


@pytest.mark.geo
def test_edge_unit_follows_plan_row_order():
    """Tie-break rule: the whole edge unit goes to the first matching plan row."""
    plan, census = _issue_probe(plan_order=("D2", "D1"))

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = demographic_profile(plan, census)

    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"GEOID": ["D2", "D1"], "TOTPOP": [500, 100]})
    )


@pytest.mark.geo
@pytest.mark.parametrize(
    "unit_order", list(itertools.permutations(range(3))), ids=lambda order: "".join(map(str, order)),
)
def test_result_is_stable_under_census_unit_order(unit_order):
    plan, census = _issue_probe(unit_order=unit_order)

    result = demographic_profile(plan, census)

    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"GEOID": ["D1", "D2"], "TOTPOP": [400, 200]})
    )


@pytest.mark.geo
def test_null_id_plan_row_does_not_capture_a_shared_edge_unit():
    """A null-ID row listed first must not win the tie-break and lose the unit."""
    plan = gpd.GeoDataFrame(
        {"GEOID": [None, "D2"]},
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs=5070,
    )
    census = gpd.GeoDataFrame(
        {"TOTPOP": [300]}, geometry=[box(9, 1, 11, 2)], crs=5070,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = demographic_profile(plan, census)

    pd.testing.assert_frame_equal(result, pd.DataFrame({"GEOID": ["D2"], "TOTPOP": [300]}))


@pytest.mark.geo
def test_unit_matching_only_a_null_id_row_is_reported_as_excluded():
    plan = gpd.GeoDataFrame(
        {"GEOID": [None, "D2"]},
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs=5070,
    )
    census = gpd.GeoDataFrame(
        {"TOTPOP": [100, 200]}, geometry=[box(1, 1, 2, 2), box(11, 1, 12, 2)], crs=5070,
    )

    with pytest.warns(UserWarning, match=r"1 census unit\(s\).*'TOTPOP': 100"):
        result = demographic_profile(plan, census)

    pd.testing.assert_frame_equal(result, pd.DataFrame({"GEOID": ["D2"], "TOTPOP": [200]}))


@pytest.mark.geo
def test_districts_without_units_appear_with_zeros():
    plan = gpd.GeoDataFrame(
        {"GEOID": ["D1", "D2", "D3"]},
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10), box(20, 0, 30, 10)],
        crs=5070,
    )
    census = gpd.GeoDataFrame(
        {"TOTPOP": [100, 200], "VAP": [70, 150]},
        geometry=[box(1, 1, 2, 2), box(21, 1, 22, 2)],
        crs=5070,
    )

    result = demographic_profile(plan, census)

    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame({"GEOID": ["D1", "D2", "D3"], "TOTPOP": [100, 0, 200], "VAP": [70, 0, 150]}),
    )


@pytest.mark.geo
def test_census_layer_carrying_its_own_district_id_column():
    """Census tracts usually carry GEOID; it must not collide with the plan's GEOID."""
    plan = gpd.GeoDataFrame(
        {"GEOID": ["D1", "D2"]},
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs=5070,
    )
    census = gpd.GeoDataFrame(
        {"GEOID": ["48001000100", "48001000200"], "TOTPOP": [100, 200]},
        geometry=[box(1, 1, 2, 2), box(11, 1, 12, 2)],
        crs=5070,
    )

    result = demographic_profile(plan, census)

    pd.testing.assert_frame_equal(
        result, pd.DataFrame({"GEOID": ["D1", "D2"], "TOTPOP": [100, 200]})
    )
