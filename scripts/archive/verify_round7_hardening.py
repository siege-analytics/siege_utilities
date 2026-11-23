"""Assert round-7 surfaces, then all prior public hardening controls.

Run from /tmp with PYTHONPATH pointing at the checkout. Census HTTP is mocked.
Use --spark-boundary-only when JVM socket binding is forbidden by the sandbox.
"""

import gc
from importlib import import_module
from unittest.mock import Mock, patch
import weakref

import pandas as pd
from shapely import from_wkb

from verify_round6_hardening import main as prior_controls


def main(*, spark_boundary_only=False):
    engines = import_module("siege_utilities.engines.dataframe_engine")
    census = import_module("siege_utilities.geo.census.catalog_populator")
    import duckdb

    for setup, sql, remaining in [
        ("", "INSERT INTO items VALUES (1)", [1]),
        ("INSERT INTO items VALUES (0);", "UPDATE items SET i=i+1", [1]),
        ("INSERT INTO items VALUES (1);", "DELETE FROM items", []),
    ]:
        eng = engines.DuckDBEngine()
        result = eng.query(
            f"CREATE TABLE items(i INT); {setup} {sql} "
            "RETURNING i, ST_Point(i,i) AS geometry, 1 AS x, 2 AS x"
        )
        assert isinstance(result, pd.DataFrame)
        assert result[["i", "x", "x_1"]].iloc[0].tolist() == [1, 1, 2]
        for _ in range(2):
            assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 1)"
            assert from_wkb(bytes(eng.to_pandas(result).geometry.iloc[0])).wkt == "POINT (1 1)"
        assert eng.query("SELECT i FROM items").i.tolist() == remaining
        print(f"{sql.split()[0]} RETURNING: POINT (1 1), x=1, x_1=2; exactly once, remaining={remaining}")

    eng = engines.DuckDBEngine()
    indexed = eng.index_points(
        eng.query("SELECT 41 AS lat, -87 AS lon, ST_Point(-87,41) AS geometry"),
        "lat", "lon", grid="s2", level=12,
    )
    out = eng.to_geodataframe(indexed)
    assert out.geometry.iloc[0].wkt == "POINT (-87 41)" and out.s2_index.iloc[0]
    print(f"index_points(query): {out.geometry.iloc[0].wkt}, s2_index={out.s2_index.iloc[0]}")

    refs = []

    def get_result():
        local = engines.DuckDBEngine()
        refs.append(weakref.ref(local))
        return local.query("SELECT ST_Point(1,2) AS geometry")

    result = get_result()
    gc.collect()
    assert refs[0]() is None
    assert engines.DuckDBEngine().to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"
    print("dead-engine result: POINT (1 2), engine collected=True")
    eng.query("CREATE TABLE points AS SELECT 7 AS i, ST_Point(1,2) AS geometry")
    saved = eng.query("SELECT * FROM points")
    assert eng.query("DELETE FROM points").to_dict("list") == {"Count": [1]}
    out = eng.to_geodataframe(saved)
    assert out.i.tolist() == [7] and out.geometry.iloc[0].wkt == "POINT (1 2)"
    assert eng.query("SELECT count(*) AS n FROM points").n.iloc[0] == 0
    print("snapshot after DELETE: i=7, POINT (1 2); source rows=0")

    for sql, expected in [
        ("SELECT ST_Point(1,2) AS geometry UNION ALL SELECT NULL::GEOMETRY", ["POINT (1 2)", None]),
        ("SELECT NULL::GEOMETRY AS geometry", [None]),
        ("SELECT NULL::GEOMETRY AS geometry WHERE FALSE", []),
        ("DELETE FROM points WHERE FALSE RETURNING ST_Point(i,i) AS geometry", []),
    ]:
        result = eng.query(sql)
        assert isinstance(result, pd.DataFrame) and result.columns.tolist() == ["geometry"]
        out = eng.to_geodataframe(result)
        actual = [g.wkt if g is not None else None for g in out.geometry]
        assert actual == expected
        print(f"geometry schema {sql}: {actual}, columns={list(out.columns)}")

    restricted = engines.DuckDBEngine(config={"enable_external_access": False})
    try:
        restricted.query("SELECT ST_Point(1,2) AS geometry")
    except duckdb.PermissionException:
        assert restricted.query("SELECT 42 AS answer").answer.iloc[0] == 42
        print("failed spatial load: PermissionException; subsequent SELECT 42=42")
    else:
        raise AssertionError("spatial load unexpectedly permitted")

    # Tokenization must not mistake literal/comment/identifier text for RETURNING.
    eng.query('CREATE TABLE words("returning" VARCHAR)')
    for sql in [
        'INSERT INTO words VALUES (\'é🍊 RETURNING\') /* RETURNING */',
        'UPDATE words SET "returning" = \'RETURNING\'',
        'DELETE FROM words WHERE "returning" = \'RETURNING\'',
    ]:
        assert eng.query(sql).to_dict("list") == {"Count": [1]}
    returned = eng.query("INSERT INTO words VALUES ('é🍊') RETURNING ST_Point(1,2) AS geometry")
    assert eng.to_geodataframe(returned).geometry.iloc[0].wkt == "POINT (1 2)"
    print("RETURNING tokenizer: quoted names, literals, comments, UTF-8; Count preserved; geometry decoded")

    for base in ["https://proxy/data/2023/gw", "https://proxy/data/2023/acs/acs5"]:
        requested = []
        response = Mock()
        response.json.return_value = {"variables": {}, "groups": []}
        with patch.object(census.requests, "get", side_effect=lambda url, **kwargs: requested.append(url) or response):
            census.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
        assert requested == [f"{base}/data/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]]
        print(f"census ACCEPT {base}: {requested}")

    prior_controls(spark_boundary_only=spark_boundary_only)
    print("ROUND-7 SELF-REGRESSION GATE: PASS")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spark-boundary-only", action="store_true")
    main(spark_boundary_only=parser.parse_args().spark_boundary_only)
