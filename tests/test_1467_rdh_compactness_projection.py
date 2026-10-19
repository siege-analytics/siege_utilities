"""Regression tests for RDH compactness geometry and projection (#1467)."""

import math

import geopandas as gpd
import pandas as pd
import pytest
from geopandas.testing import assert_geodataframe_equal
from shapely.geometry import Point, Polygon

from siege_utilities.geo.providers.redistricting_data_hub import (
    compare_plans,
    compute_compactness,
    polsby_popper,
    reock,
    schwartzberg,
)


METRICS = [
    ("polsby_popper", "compactness_mean_pp", polsby_popper),
    ("reock", "compactness_mean_reock", reock),
    ("schwartzberg", "compactness_mean_schwartzberg", schwartzberg),
]


def _circle_plan(longitude, latitude):
    """Make a 50 km geodesic circle, then store it in longitude/latitude."""
    local_crs = (
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} "
        "+datum=WGS84 +units=m"
    )
    return gpd.GeoDataFrame(
        {"GEOID": [f"{longitude},{latitude}"], "TOTPOP": [100_000]},
        geometry=[Point(0, 0).buffer(50_000, quad_segs=256)],
        crs=local_crs,
    ).to_crs("EPSG:4326")


@pytest.fixture(params=[(-122, 47), (-150, 61)], ids=["47N", "61N"])
def geodesic_plan(request):
    return _circle_plan(*request.param)


def test_reock_planar_circle_is_one():
    score = reock(Point(0, 0).buffer(1000, quad_segs=256))
    assert score >= 0.99
    assert score == pytest.approx(1.0, abs=1e-3)


def test_reock_equilateral_triangle():
    triangle = Polygon([(0, 0), (2, 0), (1, math.sqrt(3))])
    assert reock(triangle) == pytest.approx(3 * math.sqrt(3) / (4 * math.pi))


@pytest.mark.parametrize("metric,summary_metric,score_function", METRICS)
def test_compute_compactness_geodesic_circle(
    geodesic_plan, metric, summary_metric, score_function,
):
    score = compute_compactness(geodesic_plan).iloc[0][metric]
    assert score >= 0.99
    assert score == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize("metric,summary_metric,score_function", METRICS)
def test_compare_plans_geodesic_circle(
    geodesic_plan, metric, summary_metric, score_function,
):
    scores = compute_compactness(geodesic_plan)
    comparison = compare_plans(geodesic_plan, geodesic_plan)
    for plan in ("plan_a", "plan_b"):
        score = comparison[plan][summary_metric]
        assert score >= 0.99
        # Plan summaries retain their existing four-decimal rounding.
        assert score == round(scores[metric].mean(), 4)
    assert comparison["compactness_delta"] == 0.0


@pytest.mark.parametrize("metric,summary_metric,score_function", METRICS)
@pytest.mark.parametrize("source_crs", ["EPSG:4326", "ESRI:54009"])
def test_scalar_metrics_reproject_known_crs(
    geodesic_plan, metric, summary_metric, score_function, source_crs,
):
    plan = geodesic_plan.to_crs(source_crs)
    score = score_function(plan.geometry.iloc[0], source_crs=plan.crs)
    assert score == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize(
    "source_crs", ["EPSG:4326", "EPSG:4269", "EPSG:3857", "ESRI:54009"],
)
def test_each_district_uses_its_own_projection(source_crs):
    geographic = gpd.GeoDataFrame(
        pd.concat([_circle_plan(-122, 47), _circle_plan(-150, 61)], ignore_index=True),
        crs="EPSG:4326",
    ).rename_geometry("boundary").rename(columns={"GEOID": "district"})
    plan = geographic.to_crs(source_crs)
    original = plan.copy(deep=True)

    scores = compute_compactness(plan, district_id_col="district", geometry_col="boundary")
    comparison = compare_plans(plan, geographic, district_id_col="district")

    assert list(scores["district_id"]) == list(plan["district"])
    for metric, summary_metric, _ in METRICS:
        assert (scores[metric] >= 0.99).all()
        for label in ("plan_a", "plan_b"):
            assert comparison[label][summary_metric] == round(scores[metric].mean(), 4)
    assert comparison["compactness_delta"] == 0.0
    assert_geodataframe_equal(plan, original)


def test_missing_and_empty_geometries_keep_nan_scores(geodesic_plan):
    plan = gpd.GeoDataFrame(
        {"GEOID": ["circle", "missing", "empty"], "TOTPOP": [100_000, 0, 0]},
        geometry=[geodesic_plan.geometry.iloc[0], None, Polygon()],
        crs=geodesic_plan.crs,
    )
    scores = compute_compactness(plan)
    assert scores.iloc[1:].drop(columns="district_id").isna().all().all()
    comparison = compare_plans(plan, plan)
    for metric, summary_metric, _ in METRICS:
        assert comparison["plan_a"][summary_metric] == round(scores[metric].mean(), 4)


def test_planar_inputs_without_crs_keep_plan_comparison_contract():
    circle = Point(0, 0).buffer(1000, quad_segs=256)
    triangle = Polygon([(0, 0), (2, 0), (1, math.sqrt(3))])
    # Plan comparison permits frames without a district identifier column.
    plan_a = gpd.GeoDataFrame({"TOTPOP": [100_000]}, geometry=[circle])
    plan_b = gpd.GeoDataFrame({"TOTPOP": [100_000]}, geometry=[triangle])
    comparison = compare_plans(plan_a, plan_b)
    for _, summary_metric, score_function in METRICS:
        assert comparison["plan_a"][summary_metric] == round(score_function(circle), 4)
        assert comparison["plan_b"][summary_metric] == round(score_function(triangle), 4)
    expected_delta = round(polsby_popper(circle), 4) - round(polsby_popper(triangle), 4)
    assert comparison["compactness_delta"] == round(expected_delta, 4)
