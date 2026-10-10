"""Run batch-1 fixes 1-8 and the confirmed-good hardening gate from /tmp.

Set PYTHONPATH to the checkout. Use --spark-boundary-only if the sandbox
forbids JVM socket binding; that mode does not verify a live Spark session.
"""

from importlib import import_module, metadata
from unittest.mock import Mock, patch

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, box

from verify_round9_hardening import main as prior_controls


def batch1_examples():
    engines = import_module("siege_utilities.engines.dataframe_engine")
    areal = import_module("siege_utilities.geo.interpolation.areal")
    census = import_module("siege_utilities.geo.census.catalog_populator")
    for module in [engines, areal, census]:
        print(f"Imported {module.__name__}: {module.__file__}")
    print("Libraries:", {name: metadata.version(name) for name in ["duckdb", "tobler", "shapely"]})

    eng = engines.DuckDBEngine()
    point = Point(1, 2)
    hex_frame = eng.query(f"SELECT '{point.wkb_hex}'::VARCHAR AS geometry")
    decoded = eng.to_geodataframe(hex_frame)
    assert decoded.geometry.iloc[0].equals(point)
    print(f"1: VARCHAR hex WKB {point.wkb_hex} -> {decoded.geometry.iloc[0].wkt}")
    for geom, attrs in [("geometry", {'a"b': [7]}), ('g"eom', {'a"b': [7]}), ('g"eom', {})]:
        source = gpd.GeoDataFrame(attrs, geometry=[point], crs=3857)
        if geom != "geometry":
            source = source.rename_geometry(geom)
        result = eng.to_geodataframe(eng.from_geodataframe(source, geom), geom, crs=3857)
        assert result.geometry.iloc[0].equals(point)
        assert result.columns.tolist() == source.columns.tolist()
        print(f"2: round-trip columns={result.columns.tolist()}, geometry={result.geometry.iloc[0].wkt}")

    source = gpd.GeoDataFrame(
        {"pop": [100.0, np.nan], "rate": [0.0, 0.0]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs=3857,
    )
    target = gpd.GeoDataFrame(geometry=[box(0, 0, 2, 1), box(9, 9, 10, 10)], crs=3857)
    for backend in ["tobler", "duckdb", "shapely"]:
        with patch.object(areal, "_TOBLER_AVAILABLE", backend == "tobler"), \
             patch.object(areal, "_DUCKDB_AVAILABLE", backend == "duckdb"):
            result = areal.interpolate_areal(
                source, target, extensive_variables=["pop"], intensive_variables=["rate"],
            )
        assert result.backend == backend
        np.testing.assert_allclose(result.data["pop"], [np.nan, 0])
        np.testing.assert_allclose(result.data["rate"], [0, np.nan])
        assert pd.api.types.is_float_dtype(result.data["pop"])
        print(f"3/4 {backend}: extensive [100, NaN] -> {result.data['pop'].tolist()}; "
              f"intensive [covered zero, disjoint] -> {result.data['rate'].tolist()}")

    for fix, base in [
        (5, "https://api.census.gov/data/timeseries/govs/schfin"),
        (6, "https://api.census.gov../data/2023/acs/acs5"),
        (6, "https://api.census.gov../data/timeseries/govs/schfin"),
    ]:
        with patch.object(census.requests, "get", side_effect=AssertionError("unexpected HTTP")) as request:
            try:
                census.CensusCatalogPopulator(base_url=base)
            except ValueError as exc:
                assert "full dataset path" in str(exc)
                print(f"{fix}: REJECT {base}: {exc}")
            else:
                raise AssertionError(f"Accepted dataset path: {base}")
            request.assert_not_called()

    for base, root in [
        ("https://api.census.gov", "https://api.census.gov/data"),
        ("https://api.census.gov/data", "https://api.census.gov/data"),
        ("https://api.census.gov/data/", "https://api.census.gov/data"),
        ("https://api.census.gov//data//data/", "https://api.census.gov/data"),
        ("https://proxy/data/census", "https://proxy/data/census/data"),
        ("https://proxy/data/2023/census", "https://proxy/data/2023/census/data"),
        ("https://proxy/2023/gw", "https://proxy/2023/gw/data"),
        ("https://proxy../data/timeseries/govs/schfin", "https://proxy../data/timeseries/govs/schfin/data"),
        ("https://api.census.gov/data%2f2023/cbp", "https://api.census.gov/data%2f2023/cbp/data"),
        ("https://api.census.gov/%64ata%2F2023/cbp", "https://api.census.gov/data%2F2023/cbp/data"),
    ]:
        response = Mock()
        response.json.return_value = {"variables": {}, "groups": []}
        with patch.object(census.requests, "get", return_value=response) as request:
            census.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
        assert [call.args[0] for call in request.call_args_list] == [
            f"{root}/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]
        ]
        print(f"5/6/7 control: {base} -> {root}; fetch URLs verified")


def empty_input_examples():
    areal = import_module("siege_utilities.geo.interpolation.areal")
    source = gpd.GeoDataFrame(
        {"pop": [10.0], "rate": [0.0]}, geometry=[box(0, 0, 1, 1)], crs=3857,
    )
    target = gpd.GeoDataFrame(
        {"target_id": ["covered", "disjoint", "touch"]},
        geometry=[box(0, 0, 1, 1), box(9, 0, 10, 1), box(1, 0, 2, 1)],
        crs=3857, index=[20, 10, 30],
    )
    kwargs = dict(extensive_variables=["pop"], intensive_variables=["rate"], crs=3857)
    for backend in ["tobler", "duckdb", "shapely"]:
        with patch.object(areal, "_TOBLER_AVAILABLE", backend == "tobler"), \
             patch.object(areal, "_DUCKDB_AVAILABLE", backend == "duckdb"):
            populated = areal.interpolate_areal(source, target, **kwargs)
            with patch.object(areal, f"_interpolate_{backend}",
                              side_effect=AssertionError("unexpected empty-frame dispatch")) as dispatch:
                for src, tgt in [(source.iloc[:0], target), (source, target.iloc[1:])]:
                    result = areal.interpolate_areal(src, tgt, **kwargs)
                    assert result.backend == backend
                    assert result.data.columns.tolist() == populated.data.columns.tolist() == [
                        "target_id", "geometry", "pop", "rate",
                    ]
                    assert result.data.index.equals(tgt.index)
                    assert result.data.target_id.tolist() == tgt.target_id.tolist()
                    assert result.data.crs == tgt.crs
                    assert (result.data["pop"] == 0.0).all()
                    assert result.data["rate"].isna().all()
                    print(f"8 {backend}: source={len(src)}, targets={len(tgt)}, "
                          f"columns={result.data.columns.tolist()}, pop=0, rate=NaN; no dispatch")
                try:
                    areal.interpolate_areal(source, target.iloc[:0], **kwargs)
                except ValueError as exc:
                    assert str(exc) == "target GeoDataFrame is empty; provide at least one target polygon"
                    print(f"8 {backend}: empty target still raises {exc}")
                else:
                    raise AssertionError("empty target accepted")
                dispatch.assert_not_called()


def main(*, spark_boundary_only=False):
    batch1_examples()
    empty_input_examples()
    prior_controls(spark_boundary_only=spark_boundary_only)
    print("BATCH-1 FIXES 1-8 + CONFIRMED-GOOD GATE: PASS")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spark-boundary-only", action="store_true")
    main(spark_boundary_only=parser.parse_args().spark_boundary_only)
