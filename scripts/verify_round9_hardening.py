"""Check round-9 findings and rerun the full confirmed-good gate.

Run from /tmp with PYTHONPATH pointing to the checkout. HTTP is mocked.
Use --spark-boundary-only when JVM socket binding is forbidden.
"""

from importlib import import_module
from unittest.mock import Mock, patch

import pandas as pd

from verify_round8_hardening import main as prior_controls


def round9_findings():
    engines = import_module("siege_utilities.engines.dataframe_engine")
    census = import_module("siege_utilities.geo.census.catalog_populator")
    for collation in ["nocase", "noaccent", "noaccent.nocase"]:
        eng = engines.DuckDBEngine()
        eng.query(f"SET default_collation='{collation}'")
        eng.query("CREATE TABLE items(i INT)")
        for first, second in [("é", "É"), ("e", "é")]:
            for count_name, row_name in [(first, second), (second, first)]:
                eng.query(f'PREPARE "{count_name}" AS INSERT INTO items VALUES (7)')
                eng.query(f'PREPARE "{row_name}" AS SELECT ST_Point(1,2) AS geometry')
                count = eng.query(f'EXECUTE "{count_name}"').to_dict("list")
                point = eng.to_geodataframe(eng.query(f'EXECUTE "{row_name}"')).geometry.iloc[0].wkt
                assert count == {"Count": [1]} and point == "POINT (1 2)"
                print(f"{collation}: Count name={count_name!r} {count}; geometry name={row_name!r} {point}")
        assert eng.query("SELECT i FROM items").i.tolist() == [7] * 4

    eng = engines.DuckDBEngine()
    for char in ["\u0085", "\u1680", "\u2028", "\u2029"]:
        name = char + "p"
        eng.query(f'PREPARE "{name}" AS SELECT ST_Point(1,2) AS geometry')
        for spelling in [f'"{name}"', name]:
            point = eng.to_geodataframe(eng.query(f"EXECUTE {spelling}")).geometry.iloc[0].wkt
            assert point == "POINT (1 2)"
            print(f"identifier {ascii(spelling)}: {point}")

    for host in ["api.census.gov", "%61pi.census.gov", "api.census.gov."]:
        for path in ["/%64ata/2023/cbp", "/data/%32%30%32%33/cbp"]:
            base = f"https://{host}{path}"
            with patch.object(census.requests, "get", side_effect=AssertionError("unexpected HTTP")) as request:
                try:
                    census.CensusCatalogPopulator(base_url=base)
                except ValueError as exc:
                    assert "full dataset path" in str(exc)
                    print(f"census REJECT {base}: ValueError (full dataset path), no HTTP")
                else:
                    raise AssertionError(f"Accepted dataset endpoint {base}")
                request.assert_not_called()


def normalization_and_grammar_controls():
    """Include previously green controls without claiming each was a regression."""
    census = import_module("siege_utilities.geo.census.catalog_populator")
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    for base, expected in [
        ("https://api.census.gov/%64ata", "https://api.census.gov/data"),
        ("https://api.census.gov//%64ata//data/", "https://api.census.gov/data"),
        ("https://proxy/%64ata/%32%30%32%33/census", "https://proxy/data/2023/census/data"),
        ("https://proxy/%7e%61%2D%5F%2e", "https://proxy/~a-_./data"),
        ("https://api.census.gov/data%2f2023/cbp", "https://api.census.gov/data%2f2023/cbp/data"),
        ("https://api.census.gov/%64ata%2F2023/cbp", "https://api.census.gov/data%2F2023/cbp/data"),
        ("https://proxy/%252f/%3F/%23/%25/%c3%a9/%zz", "https://proxy/%252f/%3F/%23/%25/%c3%a9/%zz/data"),
    ]:
        with patch.object(census.requests, "get", return_value=response) as request:
            census.CensusCatalogPopulator(base_url=base).populate("acs5", 2023)
        assert [call.args[0] for call in request.call_args_list] == [
            f"{expected}/2023/acs/acs5/{leaf}.json" for leaf in ["variables", "groups"]
        ]
        print(f"census ACCEPT {base} -> {expected}: fetch paths verified")

    engines = import_module("siege_utilities.engines.dataframe_engine")
    eng = engines.DuckDBEngine()
    for name in ['semi; colon', 'quote"--/*\t name', "_p$9", "😀p"]:
        quoted = '"' + name.replace('"', '""') + '"'
        eng.query(f"pRePaRe {quoted} AS sElEcT ST_Point($1,2) AS geometry")
        spellings = [quoted, name] if name in ["_p$9", "😀p"] else [quoted]
        for spelling in spellings:
            result = eng.query(f" \t eXeCuTe /* outer /* nested */ comment */ {spelling}/* after */(1)--end\n;")
            assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"
        print(f"prepared grammar {ascii(name)}: POINT (1 2)")
    eng.query("PREPARE normalized_space AS SELECT ST_Point(1,2) AS geometry")
    for separator in [" ", "\t", "\r", "\n", "\f", "\u00a0", "\u2003", "\ufeff"]:
        result = eng.query(f"EXECUTE{separator}normalized_space{separator};")
        assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"
    print("DuckDB ASCII and normalized Unicode separators: POINT (1 2)")
    for sql in [
        "cReAtE TABLE words AS sElEcT 'RETURNING' AS word",
        "iNsErT INTO words VALUES ('RETURNING')",
        "wItH q AS (SELECT 1) SELECT * FROM q",
        "eXpLaIn SELECT * FROM words", "pRaGmA version", "sEt threads=1", "cAlL pragma_version()",
    ]:
        result = eng.query(sql)
        assert isinstance(result, pd.DataFrame)
        if sql.startswith("iNsErT"):
            assert result.to_dict("list") == {"Count": [1]}
    print("mixed-case CTAS/CTE/EXPLAIN/PRAGMA/SET/CALL and literal RETURNING: PASS")
    import duckdb
    for sql, error in [("EXECUTE /", duckdb.ParserException), ("EXECUTE missing", duckdb.BinderException)]:
        try:
            eng.query(sql)
        except error as exc:
            print(f"{sql}: clear {type(exc).__name__}")
        else:
            raise AssertionError(f"Accepted invalid EXECUTE: {sql}")


def main(*, spark_boundary_only=False):
    round9_findings()
    normalization_and_grammar_controls()
    prior_controls(spark_boundary_only=spark_boundary_only)
    print("ROUND-9 FULL SELF-REGRESSION GATE: PASS")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spark-boundary-only", action="store_true")
    main(spark_boundary_only=parser.parse_args().spark_boundary_only)
