"""Assert round-8 regressions and the complete confirmed-good public surface.

Run from /tmp with PYTHONPATH pointing at the checkout. HTTP is mocked.
Use --spark-boundary-only when JVM socket binding is forbidden.
"""

from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pandas as pd
from shapely import from_wkb
from shapely.geometry import Point

from verify_round7_hardening import main as prior_controls


def round8_findings():
    engines = import_module("siege_utilities.engines.dataframe_engine")
    census = import_module("siege_utilities.geo.census.catalog_populator")
    eng = engines.DuckDBEngine()
    eng.query("CREATE TABLE items(i INT)")
    result = eng.query("PREPARE p AS INSERT INTO items VALUES (1) RETURNING i")
    assert isinstance(result, pd.DataFrame) and result.to_dict("list") == {"Success": []}
    assert eng.query("SELECT count(*) AS n FROM items").n.iloc[0] == 0
    print("PREPARE RETURNING: DataFrame {'Success': []}; mutation not executed")
    assert eng.query("EXECUTE p").i.tolist() == [1]
    assert eng.query("SELECT i FROM items").i.tolist() == [1]
    for count_name, row_name in [("é", "É"), ("É", "é")]:
        eng.query(f'PREPARE "{count_name}" AS INSERT INTO items VALUES (2)')
        eng.query(f'PREPARE "{row_name}" AS SELECT ST_Point(1,2) AS geometry')
        count = eng.query(f'EXECUTE "{count_name}"').to_dict("list")
        point = eng.to_geodataframe(eng.query(f'EXECUTE "{row_name}"')).geometry.iloc[0].wkt
        assert count == {"Count": [1]} and point == "POINT (1 2)"
        print(f'EXECUTE "{count_name}": {count}; EXECUTE "{row_name}": {point}')
    eng.query("PREPARE commented AS INSERT INTO items VALUES (3) RETURNING ST_Point(i,i) AS geometry")
    for sql in ["EXECUTE commented--comment", "EXECUTE commented/* trailing */"]:
        point = eng.to_geodataframe(eng.query(sql)).geometry.iloc[0].wkt
        assert point == "POINT (3 3)"
        print(f"{sql}: {point}")
    assert eng.query("SELECT i FROM items ORDER BY i").i.tolist() == [1, 2, 2, 3, 3]
    for base in ["https://%61pi.census.gov/data/2023/cbp", "https://api.census.gov./data/2023/cbp"]:
        try:
            census.CensusCatalogPopulator(base_url=base)
        except ValueError as exc:
            assert "full dataset path" in str(exc)
            print(f"census REJECT {base}: ValueError (full dataset path)")
        else:
            raise AssertionError(f"Accepted dataset endpoint {base}")


def additional_prior_controls():
    """Previously green controls; no red-on-revert claim for these assertions."""
    engines = import_module("siege_utilities.engines.dataframe_engine")
    census = import_module("siege_utilities.geo.census.catalog_populator")
    eng = engines.DuckDBEngine()
    eng.query("CREATE TABLE stored AS SELECT ST_Point(1,2) AS g")
    for label, sql in [
        ("stored", "SELECT g AS geometry FROM stored"),
        ("function", "SELECT ST_Centroid(ST_Buffer(g,1)) AS geometry FROM stored"),
        ("CTE", "WITH q AS (SELECT g FROM stored) SELECT g AS geometry FROM q"),
        ("subquery", "SELECT g AS geometry FROM (SELECT * FROM stored) q"),
        ("arbitrary position", "SELECT 7 AS a, g AS geometry, 8 AS b FROM stored"),
    ]:
        result = eng.query(sql)
        assert eng.to_geodataframe(result).geometry.iloc[0].equals_exact(Point(1, 2), 1e-10)
        assert from_wkb(bytes(result.geometry.iloc[0])).equals_exact(Point(1, 2), 1e-10)
        print(f"geometry detection {label}: POINT (1 2), standard WKB")
    hexadecimal = Point(1, 2).wkb_hex
    result = eng.query(f"SELECT '{hexadecimal}' AS geometry")
    assert result.geometry.iloc[0] == hexadecimal
    assert eng.to_pandas(result) is result
    print("VARCHAR WKB-hex: preserved verbatim, no double conversion")
    result = eng.query("SELECT i, ST_Point(i,i) AS geometry FROM range(100000) q(i)")
    assert isinstance(result, pd.DataFrame) and len(result) == 100000
    assert result.i.tolist() == list(range(100000))
    assert from_wkb(bytes(result.geometry.iloc[-1])).wkt == "POINT (99999 99999)"
    print("100000 rows: eager DataFrame, complete sequence, last geometry POINT (99999 99999)")

    for label, mutation in [
        ("CTE", "WITH q AS (SELECT 1 AS i) INSERT INTO mutations SELECT * FROM q RETURNING i, ST_Point(i,i) AS geometry"),
        ("MERGE", "MERGE INTO mutations t USING (SELECT 1 AS i) s ON t.i=s.i WHEN MATCHED THEN UPDATE SET i=t.i+1 WHEN NOT MATCHED THEN INSERT VALUES (s.i) RETURNING i, ST_Point(i,i) AS geometry"),
    ]:
        # DuckDB 1.4.4 does not support PREPARE ... AS MERGE.
        for prepared in ([False] if label == "MERGE" else [False, True]):
            local = engines.DuckDBEngine()
            if prepared:
                mutation_sql = f"PREPARE p AS {mutation}; EXECUTE p"
            else:
                mutation_sql = mutation
            result = local.query(f"CREATE TABLE mutations(i INT); {mutation_sql}")
            assert result.i.tolist() == [1]
            assert local.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 1)"
            assert local.to_pandas(result) is result
            assert local.query("SELECT i FROM mutations").i.tolist() == [1]
            print(f"{label} RETURNING {'prepared' if prepared else 'direct'} batch: POINT (1 1), exactly once")

    points = eng.query("SELECT i AS id, i AS value, 'all' AS category, ST_Point(i,i) AS geometry FROM range(2) t(i)")
    polygons = eng.query("SELECT 'zone' AS zone, ST_GeomFromText('POLYGON((-1 -1,3 -1,3 3,-1 3,-1 -1))') AS geometry")
    assert eng.spatial_join(points, polygons).zone.tolist() == ["zone", "zone"]
    assert eng.buffer(points, 0.1).geometry.geom_type.tolist() == ["Polygon", "Polygon"]
    assert eng.distance(points, Point(0, 0)).iloc[0] == 0
    assert eng.dissolve(points, by="category").geometry.iloc[0].geom_type == "MultiPoint"
    assert eng.groupby_agg(points, ["category"], {"value": "sum"}).value.tolist() == [1]
    assert eng.assign_boundaries(points, polygons).zone.tolist() == ["zone", "zone"]
    assert eng.nearest(points, polygons)["distance"].tolist() == [0.0, 0.0]
    filtered = eng.filter(points, points.id == 1)
    assert eng.to_geodataframe(filtered).geometry.iloc[0].wkt == "POINT (1 1)"
    joined = eng.join(points, pd.DataFrame({"id": [1], "label": ["kept"]}), on="id")
    assert eng.to_geodataframe(joined).geometry.iloc[0].wkt == "POINT (1 1)"
    assert joined.label.tolist() == ["kept"]
    print("query-frame consumers: spatial_join/buffer/distance/dissolve/aggregation/assign_boundaries/nearest/filter/join PASS")

    with TemporaryDirectory() as temp:
        path = Path(temp) / "collision.geojson"
        path.write_text('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"geom":123},"geometry":{"type":"Point","coordinates":[1,2]}}]}')
        result = eng.read_spatial(str(path))
        assert result.geom.iloc[0] == 123 and result.geometry.iloc[0].wkt == "POINT (1 2)"
    print("read_spatial collision: geom=123, active geometry POINT (1 2)")

    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    for host in ["https://api.census.gov", "https://%61pi.census.gov", "https://api.census.gov."]:
        for path in ["", "/data", "/data/", "//data//data/"]:
            requested = []
            with patch.object(census.requests, "get", side_effect=lambda url, **kwargs: requested.append(url) or response):
                census.CensusCatalogPopulator(base_url=host + path).populate("acs5", 2023)
            assert requested == [f"{host}/data/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]]
        print(f"census ACCEPT {host}: root, /data, /data/, //data//data/ -> single /data")
    for base in [
        "HTTP://API.CENSUS.GOV/data/2023/cbp",
        "https://api.census.gov:443/data/2023/cbp",
        "https://user:pw@api.census.gov/data/2023/cbp",
        "https://api.census.gov/data/2023/cbp?key=value#fragment",
    ]:
        try:
            census.CensusCatalogPopulator(base_url=base)
        except ValueError as exc:
            assert "full dataset path" in str(exc)
            print(f"census REJECT {base}: ValueError (full dataset path)")
        else:
            raise AssertionError(f"Accepted dataset endpoint {base}")
    for base in ["https://api.census.gov.proxy/data/2023/cbp", "https://proxy/data/2023/cbp", "https://proxy/any/path"]:
        requested = []
        with patch.object(census.requests, "get", side_effect=lambda url, **kwargs: requested.append(url) or response):
            census.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
        assert requested == [f"{base}/data/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]]
        print(f"census ACCEPT proxy {base}: prefix preserved")

    for sql in [
        "SELECT 42", "SHOW TABLES", "DESCRIBE stored",
        "WITH x AS (SELECT 1) SELECT * FROM x", "PREPARE scalar AS SELECT 1", "EXECUTE scalar",
        "BEGIN", "COMMIT", "SET threads=1", "PRAGMA disable_profiling",
        "PRAGMA version", "CALL pragma_version()", "EXPLAIN SELECT * FROM stored", "DEALLOCATE scalar",
    ]:
        assert isinstance(eng.query(sql), pd.DataFrame), sql
    print("row/status DataFrame contract: SELECT/SHOW/DESCRIBE/CTE/PREPARE/EXECUTE/transaction/SET/PRAGMA/CALL/EXPLAIN/DEALLOCATE PASS")
    # Both documented conversion boundaries deliberately leave nested geometry
    # and POINT_2D unchanged; only a column typed exactly GEOMETRY becomes WKB.
    for result in [
        eng.query("SELECT ST_Point(1,2) AS geometry, [ST_Point(1,2)] AS nested, ST_Point2D(1,2) AS point2d"),
        eng.to_pandas(eng._connection.sql("SELECT ST_Point(1,2) AS geometry, [ST_Point(1,2)] AS nested, ST_Point2D(1,2) AS point2d")),
    ]:
        assert from_wkb(bytes(result.geometry.iloc[0])).wkt == "POINT (1 2)"
        assert result.point2d.iloc[0] == {"x": 1.0, "y": 2.0}
        assert bytes(result.nested.iloc[0][0]) != bytes(result.geometry.iloc[0])
    print("WKB claim: query and to_pandas(relation) convert GEOMETRY columns; nested GEOMETRY[] and POINT_2D unchanged")


def main(*, spark_boundary_only=False):
    round8_findings()
    additional_prior_controls()
    prior_controls(spark_boundary_only=spark_boundary_only)
    print("ROUND-8 FULL SELF-REGRESSION GATE: PASS")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spark-boundary-only", action="store_true")
    main(spark_boundary_only=parser.parse_args().spark_boundary_only)
