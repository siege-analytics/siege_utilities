"""Composition regressions for the second review of PR #1818."""

import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point

from siege_utilities.geo.spatial_transformations import DuckDBConnector


@pytest.fixture
def places():
    duckdb = pytest.importorskip("duckdb")
    connector = DuckDBConnector.__new__(DuckDBConnector)
    connector.connection = duckdb.connect()
    frame = gpd.GeoDataFrame(
        {"id": [7], "_siege_crs": ["caller attribute"]},
        geometry=[Point(1000000, 2000000)], crs=3857,
    )
    connector.upload_spatial_data(frame, "places")
    connector.connection.execute("CREATE TABLE labels AS SELECT 7 AS id, 'seven' AS label")
    connector.connection.execute("CREATE VIEW place_view AS SELECT * FROM places")
    try:
        yield connector, frame
    finally:
        connector.close()


@pytest.mark.parametrize("query", [
    "SELECT p.* FROM places p",
    "SELECT * FROM place_view",
    "SELECT p.*, l.label FROM places p JOIN labels l USING(id)",
    "SELECT p.*, l.label FROM places p JOIN labels l ON p.id=l.id",
    'SELECT p.* FROM "memory"."main"."places" AS p',
    "WITH places AS (SELECT * FROM main.places) SELECT p.* FROM places p",
    "SELECT * FROM place_view WHERE false",
])
def test_r2_2_rows_columns_and_crs_survive_composition(places, query):
    connector, frame = places
    driver_rows = connector.connection.execute(query).df()
    result = connector.execute_spatial_query(query)
    expected_columns = [c for c in driver_rows.columns if c != "geometry_wkt"] + ["geometry"]
    assert result.columns.tolist() == expected_columns
    assert result.id.tolist() == driver_rows.id.tolist()
    assert result._siege_crs.tolist() == driver_rows._siege_crs.tolist()
    assert result.geometry.to_wkt().tolist() == driver_rows.geometry_wkt.tolist()
    if "label" in result:
        assert result.label.tolist() == ["seven"]
    assert result.crs == frame.crs


@pytest.mark.parametrize("gap", [" ", "\n\t", "/* note */", "-- note\n", "/* outer /* inner */ end */"])
@pytest.mark.parametrize("boundary", range(10))
def test_r2_3_cte_and_target_token_boundaries_preserve_crs(places, gap, boundary):
    connector, frame = places
    gaps = [" "] * 10
    gaps[boundary] = gap
    query = (
        "WITH src AS" + gaps[0] + "(" + gaps[1] + "WITH inner_src AS (" + gaps[2]
        + "SELECT * FROM places" + gaps[3] + ")" + gaps[4]
        + "SELECT * FROM inner_src)" + gaps[5] + "INSERT" + gaps[6] + "INTO" + gaps[7]
        + '"main"' + gaps[8] + "." + gaps[9]
        + '"places" SELECT * FROM src RETURNING *'
    )
    result = connector.execute_spatial_query(query)
    assert result.id.tolist() == [7]
    assert result._siege_crs.tolist() == ["caller attribute"]
    assert result.geometry.iloc[0].equals_exact(frame.geometry.iloc[0], 0)
    assert connector.connection.execute("SELECT id FROM places").fetchall() == [(7,), (7,)]
    assert result.crs == frame.crs


def test_upload_metadata_does_not_require_module_global_driver(places, monkeypatch):
    import siege_utilities.geo.spatial_transformations as module

    connector, frame = places
    monkeypatch.delattr(module, "duckdb", raising=False)
    connector.upload_spatial_data(frame, "other_places")
    result = connector.download_spatial_data("other_places")
    assert result.id.tolist() == [7]
    assert result.crs == frame.crs
