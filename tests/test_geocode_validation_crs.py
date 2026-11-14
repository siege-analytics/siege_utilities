"""Regression coverage for CRS-aware pandas and Spark validation (#1459)."""

import logging
from unittest.mock import Mock

import pandas as pd
import pytest

from siege_utilities.geo.geocoding import (
    mark_valid_geocode_data_pandas,
    validate_geocode_data_pandas,
)


def test_conus_albers_keeps_southern_conus_points():
    pyproj = pytest.importorskip("pyproj")
    # Key West, Miami, Brownsville, Laredo: all inside EPSG:5070's area of use.
    lat = [24.5551, 25.7617, 25.9017, 27.5306]
    lon = [-81.7800, -80.1918, -97.4975, -99.4803]
    xs, ys = pyproj.Transformer.from_crs(4326, 5070, always_xy=True).transform(lon, lat)
    out = mark_valid_geocode_data_pandas(pd.DataFrame({"lat": ys, "lon": xs}), "lat", "lon", crs=5070)
    assert out["is_valid"].tolist() == [True] * 4


def test_nad83_keeps_pacific_territories():
    pytest.importorskip("pyproj")
    # Guam, American Samoa, Saipan (CNMI): TIGER ships these in EPSG:4269.
    df = pd.DataFrame({"lat": [13.44, -14.27, 15.18], "lon": [144.79, -170.70, 145.75]})
    out = mark_valid_geocode_data_pandas(df, "lat", "lon", crs=4269)
    assert out["is_valid"].tolist() == [True] * 3


def test_spark_validators_reject_null_island(real_spark_session):
    from siege_utilities.distributed.spark_utils import (
        mark_valid_geocode_data, validate_geocode_data,
    )
    df = real_spark_session.createDataFrame(
        [(0.0, 0.0), (40.7, -74.0), (0.0, 10.0)], ["lat", "lon"])
    assert validate_geocode_data(df, "lat", "lon").count() == 2
    marked = {(r.lat, r.lon): r.is_valid for r in mark_valid_geocode_data(df, "lat", "lon").collect()}
    assert marked == {(0.0, 0.0): False, (40.7, -74.0): True, (0.0, 10.0): True}


@pytest.fixture(params=["validate", "mark"])
def check_coordinates(request, monkeypatch, caplog):
    """Exercise each public API, including its copy and index contracts."""
    # The shared Django test settings disable existing package loggers.
    logger = logging.getLogger("siege_utilities.geo.geocoding")
    monkeypatch.setattr(logger, "disabled", False)
    caplog.set_level(logging.WARNING, logger="siege_utilities.geo.geocoding")

    def check(df, expected, crs=None):
        before = df.copy(deep=True)
        if request.param == "validate":
            result = validate_geocode_data_pandas(df, "lat", "lon", crs=crs)
            pd.testing.assert_frame_equal(
                result, df.loc[expected].reset_index(drop=True)
            )
        else:
            result = mark_valid_geocode_data_pandas(df, "lat", "lon", crs=crs)
            assert result["is_valid"].tolist() == expected
            assert pd.api.types.is_bool_dtype(result["is_valid"])
            pd.testing.assert_frame_equal(result.drop(columns="is_valid"), df)
        pd.testing.assert_frame_equal(df, before)
    return check


@pytest.mark.parametrize("crs_form", ["integer", "string", "object"])
def test_nad83_accepts_both_sides_of_antimeridian(check_coordinates, crs_form):
    pyproj = pytest.importorskip("pyproj")
    crs = {
        "integer": 4269, "string": "EPSG:4269", "object": pyproj.CRS(4269),
    }[crs_form]
    aou = pyproj.CRS(4269).area_of_use
    df = pd.DataFrame(
        {
            "lat": [39, 34, 61.2, 20, 18.2, 52, 52, aou.south, aou.north,
                    40, 90, 40, 40, 40, None, "bad"],
            "lon": [-77, -118, -149.9, -155, -66.5, 179, -179,
                    aou.west, aou.east,
                    0, -77, 181, -181, float("inf"), -77, -77],
        },
        index=range(100, 116),
    )

    check_coordinates(df, [True] * 11 + [False] * 5, crs=crs)


@pytest.mark.parametrize("epsg", [5070, 5069])
def test_albers_validators_keep_southern_conus_points(check_coordinates, epsg):
    pyproj = pytest.importorskip("pyproj")
    # Key West, Miami, Brownsville, South Padre, Laredo.
    lat = [24.5551, 25.7617, 25.9017, 26.1118, 27.5306]
    lon = [-81.7800, -80.1918, -97.4975, -97.1681, -99.4803]
    xs, ys = pyproj.Transformer.from_crs(4326, epsg, always_xy=True).transform(lon, lat)

    check_coordinates(pd.DataFrame({"lat": ys, "lon": xs}), [True] * 5, crs=epsg)


def test_nad83_validators_keep_pacific_territories(check_coordinates):
    pytest.importorskip("pyproj")
    df = pd.DataFrame(
        {"lat": [13.44, -14.27, 15.18], "lon": [144.79, -170.70, 145.75]}
    )

    check_coordinates(df, [True] * 3, crs=4269)


@pytest.mark.parametrize(
    "epsg,latitudes,longitudes",
    [
        (5070, [39, 34], [-77, -118]),
        (3857, [39, 34], [-77, -118]),
        (2263, [40.7, 40.8], [-74, -73.9]),  # US survey feet, not metres.
    ],
)
def test_projected_crs_uses_own_units(
    check_coordinates, epsg, latitudes, longitudes,
):
    pyproj = pytest.importorskip("pyproj")
    transformer = pyproj.Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = transformer.transform(longitudes, latitudes, errcheck=True)
    df = pd.DataFrame(
        {
            "lat": [*ys, 1e9, None, float("inf")],
            "lon": [*xs, 1e9, xs[0], xs[0]],
        }
    )

    check_coordinates(df, [True, True, False, False, False], crs=epsg)


@pytest.mark.parametrize("crs", [None, 4326, 4269])
def test_geographic_null_island_rejected_but_single_zero_valid(
    check_coordinates, crs,
):
    if crs is not None:
        pytest.importorskip("pyproj")
    df = pd.DataFrame(
        {
            "lat": [0.0, -0.0, "0", 0, 10, 1e-12, 0],
            "lon": [0.0, 0.0, "0", 10, 0, 0, 1e-12],
        }
    )

    check_coordinates(
        df, [False, False, False, True, True, True, True], crs=crs,
    )


@pytest.mark.parametrize("crs", [None, 4326, 4269])
def test_geographic_world_bounds_preserved_except_null_island(check_coordinates, crs):
    if crs is not None:
        pytest.importorskip("pyproj")
    df = pd.DataFrame(
        {
            "lat": [-90, 90, 0, 0, "39", 91, -91, 0, 0, None, "bad", 0],
            "lon": [0, 0, -180, 180, "-77", 0, 0, 181, -181, 10, 10, 0],
        }
    )

    check_coordinates(df, [True] * 5 + [False] * 7, crs=crs)


def test_projected_origin_is_not_a_geographic_sentinel(check_coordinates):
    pytest.importorskip("pyproj")
    df = pd.DataFrame({"lat": [0, 4_721_671.57], "lon": [0, -8_571_600.79]})

    check_coordinates(df, [True, True], crs=3857)


@pytest.mark.parametrize("failure", ["constructor", "transform", "nonfinite"])
def test_projected_transform_failure_keeps_finite_coordinates(
    check_coordinates, monkeypatch, caplog, failure,
):
    pyproj = pytest.importorskip("pyproj")
    transformer = Mock()
    if failure == "nonfinite":
        transformer.transform_bounds.return_value = (
            float("inf"), float("nan"), float("inf"), float("nan"),
        )
    else:
        transformer.transform_bounds.side_effect = pyproj.exceptions.ProjError(
            "transform unavailable"
        )
    factory = Mock(return_value=transformer)
    if failure == "constructor":
        factory.side_effect = pyproj.exceptions.ProjError(
            "transform unavailable"
        )
    monkeypatch.setattr(pyproj.Transformer, "from_crs", factory)
    df = pd.DataFrame(
        {
            "lat": [1_937_334.61, 0, None, "bad", float("inf"), 1, 1],
            "lon": [1_619_396.69, 0, 1, 1, 1, float("-inf"), float("nan")],
        }
    )

    check_coordinates(
        df, [True, True, False, False, False, False, False], crs=5070,
    )
    assert "skipping bounds validation" in caplog.text


def test_projected_crs_without_area_of_use_keeps_finite_coordinates(
    check_coordinates, caplog,
):
    pyproj = pytest.importorskip("pyproj")
    crs = pyproj.CRS("+proj=utm +zone=15 +datum=WGS84 +units=m +type=crs")
    assert crs.area_of_use is None
    df = pd.DataFrame(
        {"lat": [4_500_000, 0, None], "lon": [500_000, 0, 500_000]}
    )

    check_coordinates(df, [True, True, False], crs=crs)
    assert "skipping bounds validation" in caplog.text
