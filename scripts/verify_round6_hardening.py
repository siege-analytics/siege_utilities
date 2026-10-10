"""Print and assert the round-6 public self-regression gate.

Run from /tmp with PYTHONPATH pointing at the checkout and PYSPARK_PYTHON
pointing at the interpreter. Census and Snowflake network boundaries are
mocked; DuckDB, tobler, Shapely, and Spark execute locally.
Use --spark-boundary-only when the sandbox forbids JVM socket binding; that
mode exercises the real SparkEngine conversions with a stubbed session.
"""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, patch

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, box


def main(*, spark_boundary_only=False):
    engines = import_module("siege_utilities.engines.dataframe_engine")
    cp = import_module("siege_utilities.geo.crosswalk.crosswalk_processor")
    census = import_module("siege_utilities.geo.census.catalog_populator")
    areal = import_module("siege_utilities.geo.interpolation.areal")
    longitudinal = import_module("siege_utilities.geo.timeseries.longitudinal_data")

    for config in [{}, {"enable_external_access": False}]:
        eng = engines.DuckDBEngine(config=config)
        actual = eng.query("SELECT 42 AS answer").to_dict("list")
        assert actual == {"answer": [42]}
        print(f"SELECT config={config}: {actual}")
    eng = engines.DuckDBEngine()
    print("DDL:", eng.query("CREATE TABLE items(x INT)").to_dict("list"))
    for sql, count in [
        ("INSERT INTO items VALUES (1), (2)", 2),
        ("UPDATE items SET x = 3 WHERE x = 1", 1),
        ("DELETE FROM items WHERE x > 0", 2),
    ]:
        actual = eng.query(sql).to_dict("list")
        assert actual == {"Count": [count]}
        print(f"{sql.split()[0]}: {actual}")

    for sql, active, expected in [
        ("ST_Point(1,2) AS geometry, 1 AS x, 2 AS x", "geometry", {"geometry": "POINT (1 2)", "x": 1, "x_1": 2}),
        ("ST_Point(1,2) AS x, ST_Point(3,4) AS x", "x", {"x": "POINT (1 2)", "x_1": "POINT (3 4)"}),
        ("ST_Point(1,2) AS x, 7 AS x", "x", {"x": "POINT (1 2)", "x_1": 7}),
        ("7 AS x, ST_Point(1,2) AS x", "x_1", {"x": 7, "x_1": "POINT (1 2)"}),
    ]:
        result = eng.query(f"SELECT {sql}")
        frame = eng.to_geodataframe(result, geometry_col=active)
        actual = {}
        for name, value in expected.items():
            actual[name] = (
                eng.to_geodataframe(result, geometry_col=name).geometry.iloc[0].wkt
                if isinstance(value, str) else int(frame[name].iloc[0])
            )
        assert actual == expected
        print(f"SELECT {sql}: {actual}")
    result = eng.query("SELECT ST_Point(1,2) AS geometry")
    assert eng.to_geodataframe(result).geometry.iloc[0].equals(Point(1, 2))
    native = bytes(eng.to_pandas(result).geometry.iloc[0])
    import duckdb
    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        assert native == conn.execute("SELECT ST_Point(1,2)").fetchone()[0]
    print("query -> to_geodataframe: POINT (1 2)")
    print(f"query -> to_pandas: native geometry preserved, hex={native.hex()}")
    registered = pd.DataFrame({"id": [7, 9], "value": [0.2, 0.4]})
    pd.testing.assert_frame_equal(eng.query("SELECT * FROM registered", table="registered", df=registered), registered)
    assert eng.to_pandas(registered) is registered
    print("registered DataFrame + to_pandas identity: PASS")
    empty = eng.to_geodataframe(eng.query("SELECT 1 AS x, ST_Point(1,2) AS x WHERE FALSE"), geometry_col="x_1")
    assert empty.empty and list(empty.columns) == ["x", "x_1"]
    print(f"empty geometry result: rows={len(empty)}, columns={list(empty.columns)}, active={empty.geometry.name}")

    data = pd.DataFrame({"GEOID": ["S1", "S2"], "rate": [0.1, 0.9]})
    xwalk = pd.DataFrame({"source_geoid": ["S1", "S2"], "target_geoid": ["T1", "T1"], "area_weight": [1.0, 0.0], "overlap_area": [1.0, 0.0]})
    transformed = cp.CrosswalkProcessor(xwalk, 2010, 2020, "tract").transform(data, intensive_variables=["rate"])
    with patch.object(cp, "get_crosswalk", return_value=xwalk):
        applied = cp.apply_crosswalk(data, intensive_variables=["rate"])
        aligner = longitudinal.LongitudinalAligner(target_vintage=2020)
        with patch.object(aligner, "_apply_areal_interpolation", side_effect=AssertionError("unexpected fallback")) as fallback:
            aligned = aligner.align(data, source_vintage=2010, intensive_columns=["rate"])
            fallback.assert_not_called()
    for label, frame in [("transform", transformed), ("apply_crosswalk", applied), ("align", aligned.data)]:
        rate = float(frame.set_index("GEOID").loc["T1", "rate"])
        assert np.isclose(rate, 0.1)
        print(f"zero-overlap {label}: T1.rate={rate}")
    assert aligned.method == "crosswalk" and not aligned.warnings
    print("zero-overlap align: method=crosswalk, areal calls=0, warnings=[]")

    requested = []
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    for base, expected_root in [
        ("https://api.census.gov", "https://api.census.gov/data"),
        ("https://api.census.gov/data", "https://api.census.gov/data"),
        ("https://api.census.gov/data/", "https://api.census.gov/data"),
        ("https://api.census.gov//data//data/", "https://api.census.gov/data"),
        ("https://api.census.gov//data/", "https://api.census.gov/data"),
        ("https://proxy/data/census", "https://proxy/data/census/data"),
        ("https://proxy/data/2023/census", "https://proxy/data/2023/census/data"),
        ("https://proxy/2023/gw", "https://proxy/2023/gw/data"),
    ]:
        with patch.object(census.requests, "get", side_effect=lambda url, **kwargs: requested.append(url) or response):
            census.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
        expected = [f"{expected_root}/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]]
        assert requested[-2:] == expected
        print(f"census ACCEPT {base}: {requested[-2:]}")
    for path in ["data/2023/cbp", "data/2023/acs/acs5", "data/2023/custom/a/b", "data/2023"]:
        base = f"https://api.census.gov/{path}"
        try:
            census.CensusCatalogPopulator(base_url=base)
        except ValueError as exc:
            assert "full dataset path" in str(exc)
            print(f"census REJECT {base}: ValueError (full dataset path)")
        else:
            raise AssertionError(f"Accepted dataset endpoint {base}")

    source = gpd.GeoDataFrame(data, geometry=[box(0, 0, 1, 1), box(0, 1, 1, 10)], crs=3857)
    for height, expected in [(2, 0.5), (10, 0.82)]:
        target = gpd.GeoDataFrame({"GEOID": ["T1"]}, geometry=[box(0, 0, 1, height)], crs=3857)
        weights = xwalk.drop(columns="overlap_area").assign(source_area=[1.0, 9.0], area_weight=[1.0, (height - 1) / 9])
        actual = float(cp.CrosswalkProcessor(weights, 2010, 2020, "tract").transform(data, intensive_variables=["rate"]).rate.iloc[0])
        from tobler.area_weighted import area_interpolate
        reference = float(area_interpolate(source, target, intensive_variables=["rate"]).rate.iloc[0])
        assert np.isclose(actual, expected) and np.isclose(reference, expected)
        print(f"intensive parity: crosswalk={actual:.2f}, real tobler={reference:.2f}")
    try:
        cp.CrosswalkProcessor(xwalk.drop(columns="overlap_area").assign(area_weight=[1.0, 1.0]), 2010, 2020, "tract").transform(data, intensive_variables=["rate"])
    except ValueError as exc:
        assert "area-weight intensive" in str(exc)
        print("distinct-source merge without absolute area: ValueError (area-weight intensive)")
    else:
        raise AssertionError("Ambiguous merge accepted")

    nan_data = data.assign(rate=[0.2, np.nan])
    source = gpd.GeoDataFrame(nan_data, geometry=[box(0, 0, 1, 1), box(0, 1, 1, 2)], crs=3857)
    target = gpd.GeoDataFrame({"GEOID": ["T1"]}, geometry=[box(0, 0, 1, 2)], crs=3857)
    spatial_data = import_module("siege_utilities.geo.spatial_data")
    with patch.object(cp, "get_crosswalk", return_value=xwalk.drop(columns="overlap_area").assign(area_weight=[1.0, 1.0])):
        with patch.object(spatial_data, "get_census_boundaries", side_effect=lambda year, **kwargs: source.drop(columns="rate") if year == 2010 else target):
            aligned = longitudinal.LongitudinalAligner().align(nan_data, source_vintage=2010, intensive_columns=["rate"])
    assert aligned.method == "areal" and np.isclose(aligned.data.rate.iloc[0], 0.2)
    print(f"align NaN fallback: rate={aligned.data.rate.iloc[0]}, method={aligned.method}")

    source = gpd.GeoDataFrame({"rate": [np.nan, 0.8]}, geometry=[box(0, 0, 1, 1), box(10, 10, 11, 11)], crs=3857)
    target = gpd.GeoDataFrame({"id": [1, 2]}, geometry=source.geometry, crs=3857)
    for backend in ["tobler", "duckdb", "shapely"]:
        with patch.object(areal, "_select_backend", return_value=backend):
            result = areal.interpolate_areal(source, target, intensive_variables=["rate"])
        assert np.isnan(result.data.rate.iloc[0]) and np.isclose(result.data.rate.iloc[1], 0.8)
        print(f"per-target NaN {backend}: {result.data.rate.tolist()}")
    with patch.object(areal, "_TOBLER_AVAILABLE", False):
        try:
            areal.interpolate_areal(source, target.iloc[:0], intensive_variables=["rate"])
        except ValueError as exc:
            assert "target GeoDataFrame is empty" in str(exc)
            print(f"empty-target DuckDB/areal: ValueError: {exc}")
        else:
            raise AssertionError("Empty target not rejected")

    snowflake = import_module("siege_utilities.analytics.snowflake_connector")
    connector = snowflake.SnowflakeConnector(account="test", user="test")
    connector.connection = object()
    for method in ["upload_dataframe", "get_table_info", "list_tables"]:
        connector.cursor = Mock()
        connector.cursor.fetchall.return_value = []
        connector.cursor.fetchone.side_effect = [(1,), (100, 1)]
        with patch.object(snowflake, "write_pandas", return_value=(True, 1, 1, None)):
            if method == "upload_dataframe":
                connector.upload_dataframe(pd.DataFrame({"x": [1]}), "MixedTable", database="MixedDb", schema="MixedSchema", auto_create_table=False)
            elif method == "get_table_info":
                connector.get_table_info("MixedTable", database="MixedDb", schema="MixedSchema")
            else:
                connector.list_tables(database="MixedDb", schema="MixedSchema")
        sql = [call.args[0] for call in connector.cursor.execute.call_args_list[:2]]
        assert sql == ['USE DATABASE "MixedDb"', 'USE SCHEMA "MixedSchema"']
        print(f"Snowflake {method} SQL capture: {sql}")

    original = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[Point(100000, 200000), None], crs=3857)
    restored = eng.to_geodataframe(eng.from_geodataframe(original), crs="EPSG:3857")
    assert restored.geometry.iloc[0].equals(original.geometry.iloc[0]) and restored.geometry.iloc[1] is None
    print(f"DuckDB from_geodataframe round-trip: {restored.geometry.iloc[0].wkt}, null preserved, EPSG:{restored.crs.to_epsg()}")
    if spark_boundary_only:
        def create_frame(pdf):
            assert pdf.geometry.tolist() == ["POINT (100000 200000)", None]
            return SimpleNamespace(toPandas=lambda: pdf.copy())
        spark = SimpleNamespace(createDataFrame=create_frame, stop=lambda: None)
        mode = "session-boundary stub"
    else:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.master("local[1]").appName("round6-gate").config("spark.ui.enabled", "false").getOrCreate()
        spark.sparkContext.setLogLevel("ERROR")
        mode = "real session"
    try:
        spark_engine = engines.SparkEngine(spark=spark)
        sdf = spark_engine.from_geodataframe(original)
        restored = spark_engine.to_geodataframe(sdf, crs="EPSG:3857")
        assert restored.geometry.iloc[0].equals(original.geometry.iloc[0]) and restored.geometry.iloc[1] is None
        assert restored.crs.to_epsg() == 3857
        print(f"Spark ({mode}) assign-not-reproject round-trip: {restored.geometry.iloc[0].wkt}, null preserved, EPSG:{restored.crs.to_epsg()}")
    finally:
        spark.stop()
    print("SELF-REGRESSION GATE: PASS")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spark-boundary-only", action="store_true")
    main(spark_boundary_only=parser.parse_args().spark_boundary_only)
