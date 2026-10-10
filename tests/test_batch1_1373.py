"""Issue #1373 batch-1 regressions, checked against origin/develop."""

from importlib import import_module
from unittest.mock import Mock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box
from shapely.errors import GEOSException
from geopandas.testing import assert_geodataframe_equal


def test_to_geodataframe_decodes_hex_wkb_and_wkt():
    engines = import_module("siege_utilities.engines.dataframe_engine")
    eng = engines.DuckDBEngine()
    point = Point(1, 2)
    frame = eng.query(
        f"SELECT '{point.wkb_hex}'::VARCHAR AS geometry "
        "UNION ALL SELECT 'POINT (3 4)' UNION ALL SELECT NULL",
    )
    result = eng.to_geodataframe(frame, crs=3857)
    assert result.geometry.iloc[0].equals(point)
    assert result.geometry.iloc[1].equals(Point(3, 4))
    assert result.geometry.iloc[2] is None
    assert result.crs.to_epsg() == 3857
    assert frame.geometry.iloc[0] == point.wkb_hex
    # The same scalar decoder must retain WKT error reporting for corrupt text.
    with pytest.raises(GEOSException, match="ParseException"):
        eng.to_geodataframe(pd.DataFrame({"geometry": ["not a geometry"]}))
    with pytest.raises(GEOSException, match="ParseException"):
        eng.to_geodataframe(pd.DataFrame({"geometry": ["0101"]}))


@pytest.mark.parametrize("attr,geom", [('a"b', "geometry"), ("value", 'g"eom'), (None, 'g"eom')])
def test_from_geodataframe_quotes_identifiers(attr, geom):
    engines = import_module("siege_utilities.engines.dataframe_engine")
    eng = engines.DuckDBEngine()
    source = gpd.GeoDataFrame(
        {attr: [7, 8]} if attr else {}, geometry=[Point(1, 2), None], crs=3857,
    )
    if geom != "geometry":
        source = source.rename_geometry(geom)
    stored = eng.from_geodataframe(source, geometry_col=geom)
    assert list(stored.columns) == list(source.columns)
    result = eng.to_geodataframe(stored, geometry_col=geom, crs=3857)
    assert result.geometry.iloc[0].equals(Point(1, 2))
    assert result.geometry.iloc[1] is None
    if attr:
        assert result[attr].tolist() == [7, 8]


def select_backend(monkeypatch, areal, backend):
    # Force public dispatch but execute the actual installed backend.
    monkeypatch.setattr(areal, "_TOBLER_AVAILABLE", backend == "tobler")
    monkeypatch.setattr(areal, "_DUCKDB_AVAILABLE", backend == "duckdb")


@pytest.mark.parametrize("allocate_total", [True, False])
@pytest.mark.parametrize("backend", ["tobler", "duckdb"])
def test_extensive_nan_propagates_per_variable_across_backends(monkeypatch, allocate_total, backend):
    areal = import_module("siege_utilities.geo.interpolation.areal")
    source = gpd.GeoDataFrame(
        {"pop": [100.0, np.nan, 40.0], "other": [np.nan, 20.0, 30.0],
         "clean": [100.0, 20.0, 40.0], "rate": [0.2, np.nan, 0.0]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(3, 0, 4, 1)], crs=3857,
        index=[5, 8, 13],
    )
    target = gpd.GeoDataFrame(
        geometry=[box(0, 0, 2, 1), box(3, 0, 4, 1), box(5, 0, 6, 1), box(2, 0, 3, 1)],
        crs=3857, index=[20, 10, 40, 30],
    )
    outputs = {}
    for engine in [backend, "shapely"]:
        select_backend(monkeypatch, areal, engine)
        result = areal.interpolate_areal(
            source, target, extensive_variables=["pop", "other", "clean"],
            intensive_variables=["rate"], allocate_total=allocate_total,
        )
        assert result.backend == engine
        outputs[engine] = result.data
    for engine, result in outputs.items():
        np.testing.assert_allclose(result["pop"], [np.nan, 40, 0, 0], err_msg=engine)
        np.testing.assert_allclose(result["other"], [np.nan, 30, 0, 0], err_msg=engine)
        np.testing.assert_allclose(result["clean"], [120, 40, 0, 0], err_msg=engine)
        np.testing.assert_allclose(result["rate"], [0.2, 0, np.nan, np.nan], atol=1e-7)
        assert pd.api.types.is_float_dtype(result["pop"])
    assert source["pop"].isna().tolist() == [False, True, False]


@pytest.mark.parametrize("backend", ["tobler", "duckdb", "shapely"])
@pytest.mark.parametrize("no_intersections", [False, True])
def test_intensive_no_coverage_is_nan_but_covered_zero_stays_zero(monkeypatch, backend, no_intersections):
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, backend)
    source = gpd.GeoDataFrame(
        {"rate": [0.0, -1.0, 1.0], "pop": [10.0, 10.0, 10.0]},
        geometry=[box(0, 0, 1, 1), box(2, 0, 3, 1), box(3, 0, 4, 1)], crs=3857,
    )
    target = gpd.GeoDataFrame(
        geometry=[box(0, 0, 1, 1), box(2, 0, 4, 1), box(9, 0, 10, 1), box(4, 0, 5, 1)],
        crs=3857, index=[30, 20, 10, 0],
    )
    if no_intersections:
        target = target.iloc[2:]
    result = areal.interpolate_areal(
        source, target, extensive_variables=["pop"], intensive_variables=["rate"],
    )
    expected = [np.nan, np.nan] if no_intersections else [0.0, 0.0, np.nan, np.nan]
    np.testing.assert_allclose(result.data["rate"], expected)
    np.testing.assert_allclose(result.data["pop"], [0, 0] if no_intersections else [10, 20, 0, 0])


@pytest.mark.parametrize("path", ["/data/timeseries/govs/schfin", "/data/timeseries", "//data//data/timeseries/govs/schfin"])
def test_census_rejects_yearless_dataset_before_http(monkeypatch, path):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)
    with pytest.raises(ValueError, match="full dataset path"):
        census.CensusCatalogPopulator(base_url=f"https://api.census.gov{path}")
    request.assert_not_called()


@pytest.mark.parametrize("host", ["api.census.gov..", "api.census.gov...", "%61pi.census.gov.."])
def test_census_normalizes_all_trailing_host_dots(monkeypatch, host):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)
    with pytest.raises(ValueError, match="full dataset path"):
        census.CensusCatalogPopulator(base_url=f"https://{host}/data/2023/acs/acs5")
    request.assert_not_called()


@pytest.mark.parametrize("backend", ["tobler", "duckdb", "shapely"])
@pytest.mark.parametrize("empty_source", [False, True])
def test_empty_target_still_raises_control(monkeypatch, backend, empty_source):
    """Existing guard: intentionally green on origin/develop as well."""
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, backend)
    source = gpd.GeoDataFrame({"pop": [1.0]}, geometry=[box(0, 0, 1, 1)], crs=3857)
    target = source.iloc[:0].copy()
    if empty_source:
        source = source.iloc[:0]
    dispatch = Mock(side_effect=AssertionError("empty target must fail before dispatch"))
    monkeypatch.setattr(areal, f"_interpolate_{backend}", dispatch)
    with pytest.raises(ValueError, match="^target GeoDataFrame is empty; provide at least one target polygon$"):
        areal.interpolate_areal(source, target, extensive_variables=["pop"])
    dispatch.assert_not_called()


@pytest.mark.parametrize("backend", ["tobler", "duckdb", "shapely"])
@pytest.mark.parametrize("kind", ["extensive", "intensive", "both"])
def test_empty_source_preserves_nonempty_schema_without_dispatch(monkeypatch, backend, kind):
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, backend)
    source = gpd.GeoDataFrame(
        {"pop": [10.0, 20.0], "missing_rate": [np.nan, 2.0], "rate": [0.0, 1.0]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs=3857,
    )
    target = gpd.GeoDataFrame(
        {"target_id": ["a", "b"], "label": pd.Categorical(["first", "second"])},
        geometry=[box(0, 0, 2, 1), box(9, 0, 10, 1)], crs=3857, index=[20, 10],
    )
    original_target = target.copy()
    original_source = source.copy()
    ext_vars = ["pop"] if kind != "intensive" else []
    int_vars = ["missing_rate", "rate"] if kind != "extensive" else []
    kwargs = dict(extensive_variables=ext_vars, intensive_variables=int_vars, crs=3857)
    dispatch = Mock(wraps=getattr(areal, f"_interpolate_{backend}"))
    monkeypatch.setattr(areal, f"_interpolate_{backend}", dispatch)

    empty = areal.interpolate_areal(source.iloc[:0], target, **kwargs)
    dispatch.assert_not_called()
    assert empty.backend == backend
    assert (empty.n_source, empty.n_target) == (0, 2)
    assert empty.source_crs == empty.target_crs == "EPSG:3857"
    assert empty.warnings == []
    for var in ext_vars:
        np.testing.assert_array_equal(empty.data[var], [0.0, 0.0])
    for var in int_vars:
        assert empty.data[var].isna().all()
    for var in ext_vars + int_vars:
        assert pd.api.types.is_float_dtype(empty.data[var])
    populated = areal.interpolate_areal(source, target, **kwargs)
    assert dispatch.called
    expected = target.columns.tolist() + ext_vars + int_vars
    assert empty.data.columns.tolist() == populated.data.columns.tolist() == expected
    assert empty.data.dtypes.equals(populated.data.dtypes)
    assert_geodataframe_equal(empty.data[target.columns], target)
    assert_geodataframe_equal(populated.data[target.columns], target)
    assert pd.concat([populated.data, empty.data]).columns.tolist() == expected
    assert_geodataframe_equal(source, original_source)
    assert_geodataframe_equal(target, original_target)


@pytest.mark.parametrize("backend", ["tobler", "duckdb", "shapely"])
@pytest.mark.parametrize("touch_only", [False, True])
def test_no_positive_overlap_skips_backend(monkeypatch, backend, touch_only):
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, backend)
    source = gpd.GeoDataFrame(
        {"pop": [np.nan], "rate": [0.0]}, geometry=[box(0, 0, 1, 1)], crs=3857,
    )
    target = gpd.GeoDataFrame(
        {"target_id": ["a"]},
        geometry=[box(1, 0, 2, 1) if touch_only else box(9, 0, 10, 1)], crs=3857,
    )
    dispatch = Mock(wraps=getattr(areal, f"_interpolate_{backend}"))
    monkeypatch.setattr(areal, f"_interpolate_{backend}", dispatch)
    result = areal.interpolate_areal(
        source, target, extensive_variables=["pop"], intensive_variables=["rate"], crs=3857,
    )
    dispatch.assert_not_called()
    # A missing value in a non-contributing source does not propagate NaN mass.
    assert result.data["pop"].tolist() == [0.0]
    assert result.data["rate"].isna().all()
    assert result.data.columns.tolist() == ["target_id", "geometry", "pop", "rate"]
    assert_geodataframe_equal(result.data[target.columns], target)


@pytest.mark.parametrize("backend", ["tobler", "duckdb", "shapely"])
def test_valid_intensive_subset_without_overlap_skips_backend(monkeypatch, backend):
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, backend)
    source = gpd.GeoDataFrame(
        {"rate": [np.nan, 0.0]},
        geometry=[box(0, 0, 1, 1), box(9, 0, 10, 1)], crs=3857,
    )
    target = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs=3857)
    dispatch = Mock(wraps=getattr(areal, f"_interpolate_{backend}"))
    monkeypatch.setattr(areal, f"_interpolate_{backend}", dispatch)
    result = areal.interpolate_intensive(source, target, ["rate"], crs=3857)
    dispatch.assert_not_called()
    assert result.data["rate"].isna().all()
    assert result.data.columns.tolist() == ["geometry", "rate"]


def test_duckdb_empty_geometry_frame_returns_cleanly(monkeypatch):
    """Real DuckDB regression: empty WKB conversion retains geometry dtype."""
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, "duckdb")
    source = gpd.GeoDataFrame({"pop": pd.Series(dtype=float)}, geometry=[], crs=3857)
    target = gpd.GeoDataFrame({"target_id": ["a"]}, geometry=[box(0, 0, 1, 1)], crs=3857)
    result = areal.interpolate_extensive(source, target, ["pop"], crs=4326)
    assert result.data["pop"].tolist() == [0.0]
    assert result.data.columns.tolist() == ["target_id", "geometry", "pop"]
    assert_geodataframe_equal(result.data[target.columns], target.to_crs(4326))


@pytest.mark.parametrize("backend", ["tobler", "duckdb", "shapely"])
def test_backend_failure_still_propagates_control(monkeypatch, backend):
    """No-overlap handling must not turn backend failures into clean results."""
    areal = import_module("siege_utilities.geo.interpolation.areal")
    select_backend(monkeypatch, areal, backend)
    source = gpd.GeoDataFrame({"pop": [1.0]}, geometry=[box(0, 0, 1, 1)], crs=3857)
    dispatch = Mock(side_effect=RuntimeError("backend failure"))
    monkeypatch.setattr(areal, f"_interpolate_{backend}", dispatch)
    with pytest.raises(RuntimeError, match="^backend failure$"):
        areal.interpolate_extensive(source, source, ["pop"])
    dispatch.assert_called_once()


@pytest.mark.parametrize("source_vintage", [2000, 2010])
@pytest.mark.parametrize("geoid_column", ["GEOID", "tract_id"])
def test_align_areal_carries_only_requested_variables(monkeypatch, source_vintage, geoid_column):
    """Boundary metadata must not become variables in a three-vintage chain."""
    areal = import_module("siege_utilities.geo.interpolation.areal")
    longitudinal = import_module("siege_utilities.geo.timeseries.longitudinal_data")
    crosswalk = import_module("siege_utilities.geo.crosswalk.crosswalk_processor")
    spatial = import_module("siege_utilities.geo.spatial_data")
    select_backend(monkeypatch, areal, "tobler")
    boundaries = {
        2000: gpd.GeoDataFrame(
            {"GEOID": ["S1", "S2"], "ALAND": [20, 20], "AWATER": [2, 2]},
            geometry=[box(0, 0, 2, 1), box(2, 0, 4, 1)], crs=3857,
        ),
        2010: gpd.GeoDataFrame(
            {"GEOID": ["M1"], "ALAND": [40], "AWATER": [4]},
            geometry=[box(0, 0, 4, 1)], crs=3857, index=[90],
        ),
        2020: gpd.GeoDataFrame(
            {
                "GEOID": ["T2", "T1"], "ALAND": [10, 30], "AWATER": [1, 3],
                # Same-named target attributes must yield to interpolated values.
                "pop": [-999, -999], "rate": [-999, -999],
            },
            geometry=[box(3, 0, 4, 1), box(0, 0, 3, 1)], crs=3857, index=[70, 10],
        ),
    }
    monkeypatch.setattr(
        spatial, "get_census_boundaries", lambda year, **kwargs: boundaries[year].copy(),
    )
    unavailable = Mock(side_effect=FileNotFoundError("crosswalk unavailable"))
    monkeypatch.setattr(crosswalk, "apply_crosswalk", unavailable)
    interpolations = []
    interpolate = areal.interpolate_areal

    def capture_interpolation(**kwargs):
        result = interpolate(**kwargs)
        interpolations.append(result)
        return result

    interpolation = Mock(side_effect=capture_interpolation)
    monkeypatch.setattr(areal, "interpolate_areal", interpolation)
    data = pd.DataFrame(
        {geoid_column: ["S1", "S2"], "pop": [100.0, 300.0], "rate": [0.2, 0.8]}
        if source_vintage == 2000 else
        {geoid_column: ["M1"], "pop": [400.0], "rate": [0.5]}
    )
    result = longitudinal.LongitudinalAligner(target_vintage=2020).align(
        data, source_vintage=source_vintage, geoid_column=geoid_column,
        intensive_columns=["rate"],
    )

    assert result.method == "areal", result.warnings
    steps = 2 if source_vintage == 2000 else 1
    assert unavailable.call_count == interpolation.call_count == steps
    assert len(result.warnings) == steps
    assert (result.rows_before, result.rows_after) == (len(data), 2)
    expected = pd.DataFrame(
        {"pop": [100.0, 300.0], "rate": [0.5, 0.5], geoid_column: ["T2", "T1"]},
        index=boundaries[2020].index,
    )
    pd.testing.assert_frame_equal(result.data, expected)
    # Projection preserves interpolated floats exactly, including dtype and order.
    pd.testing.assert_frame_equal(
        result.data[["pop", "rate"]],
        pd.DataFrame(interpolations[-1].data[["pop", "rate"]]), check_exact=True,
    )
    for call, interpolated in zip(interpolation.call_args_list, interpolations):
        assert interpolated.backend == "tobler"
        assert call.kwargs["extensive_variables"] == ["pop"]
        assert call.kwargs["intensive_variables"] == ["rate"]
        assert {"ALAND", "AWATER"} <= set(call.kwargs["source_gdf"].columns)
        assert not any(c.endswith(("_x", "_y")) for c in call.kwargs["source_gdf"].columns)
        # interpolate_areal's public boundary-metadata schema remains intact.
        pd.testing.assert_frame_equal(
            pd.DataFrame(interpolated.data[["ALAND", "AWATER"]]),
            pd.DataFrame(call.kwargs["target_gdf"][["ALAND", "AWATER"]]),
        )
