"""Round-9 regressions; every parametrized case must fail on a29d8198."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def engine():
    pytest.importorskip("duckdb")
    return import_module("siege_utilities.engines.dataframe_engine").DuckDBEngine()


@pytest.mark.parametrize("collation", ["nocase", "noaccent", "noaccent.nocase"])
def test_prepared_lookup_is_independent_of_session_collation(collation):
    eng = engine()
    eng.query(f"SET default_collation='{collation}'")
    eng.query("CREATE TABLE items(i INT)")
    # noaccent alone distinguishes é/É, but merges e/é. Check both pairs,
    # both Count/geometry roles, and ASCII aliases under every collation.
    for first, second in [("é", "É"), ("e", "é")]:
        for count_name, row_name in [(first, second), (second, first)]:
            eng.query(f'PREPARE "{count_name}" AS INSERT INTO items VALUES (7)')
            eng.query(f'PREPARE "{row_name}" AS SELECT ST_Point(1,2) AS geometry')
            for _ in range(2):
                assert eng.query(f'EXECUTE "{count_name}"').to_dict("list") == {"Count": [1]}
                result = eng.query(f'EXECUTE "{row_name}"')
                assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 2)"
            eng.query(f'PREPARE "{count_name}P" AS INSERT INTO items VALUES (8)')
            eng.query(f'PREPARE "{row_name}P" AS SELECT ST_Point(3,4) AS geometry')
            assert eng.query(f'EXECUTE "{count_name}p"').to_dict("list") == {"Count": [1]}
            result = eng.query(f'EXECUTE "{row_name}p"')
            assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (3 4)"
    assert eng.query("SELECT i FROM items ORDER BY i").i.tolist() == [7] * 8 + [8] * 4


@pytest.mark.parametrize("char", ["\u0085", "\u1680", "\u2028", "\u2029"],
                         ids=["U0085", "U1680", "U2028", "U2029"])
@pytest.mark.parametrize("template", ["{}p", "p{}q", "p{}"], ids=["leading", "middle", "trailing"])
def test_unicode_identifier_characters_are_not_whitespace(char, template):
    eng = engine()
    eng.query("CREATE TABLE items(i INT)")
    name = template.format(char)
    for spelling in [f'"{name}"', name]:
        eng.query(f'PREPARE "{name}" AS INSERT INTO items VALUES (1) RETURNING ST_Point(i,i) AS geometry')
        result = eng.query(f"eXeCuTe /* before */ {spelling}--after\n;")
        assert eng.to_geodataframe(result).geometry.iloc[0].wkt == "POINT (1 1)"
        eng.query(f'PREPARE "{name}" AS INSERT INTO items VALUES (2)')
        assert eng.query(f"EXECUTE {spelling}/* after */;").to_dict("list") == {"Count": [1]}
    assert eng.query("SELECT i FROM items ORDER BY i").i.tolist() == [1, 1, 2, 2]


@pytest.mark.parametrize("query", ["EXECUTE /", "EXECUTE"])
def test_unextractable_prepared_name_raises_clear_error(query):
    import duckdb

    eng = engine()
    # Public malformed SQL is rejected by DuckDB before this helper. Exercise
    # its defensive path with inconsistent statement metadata explicitly.
    statement = SimpleNamespace(type=duckdb.StatementType.EXECUTE, query=query)
    with pytest.raises(ValueError, match="Cannot extract prepared statement name from EXECUTE"):
        eng._statement_returns_rows(statement)


@pytest.mark.parametrize("host", ["api.census.gov", "%61pi.census.gov", "api.census.gov."])
@pytest.mark.parametrize("path", ["/%64ata/2023/cbp", "/data/%32%30%32%33/cbp"])
def test_encoded_census_dataset_paths_reject_before_http(monkeypatch, host, path):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)
    with pytest.raises(ValueError, match="full dataset path"):
        census.CensusCatalogPopulator(base_url=f"https://{host}{path}")
    request.assert_not_called()


@pytest.mark.parametrize("path", ["/%64ata", "//data//%64ata/"])
def test_encoded_census_roots_deduplicate_before_fetch(monkeypatch, path):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    request = Mock(return_value=response)
    monkeypatch.setattr(census.requests, "get", request)
    census.CensusCatalogPopulator(base_url=f"https://api.census.gov{path}").populate("acs5", 2023)
    assert [call.args[0] for call in request.call_args_list] == [
        f"https://api.census.gov/data/2023/acs/acs5/{leaf}.json"
        for leaf in ["variables", "groups"]
    ]
