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


@pytest.mark.parametrize("view", [False, True])
def test_r2_2_unserializable_scan_retains_catalog_geometry_metadata(places, view):
    import pandas as pd

    connector, frame = places
    connector.connection.register("frame_labels", pd.DataFrame({"id": [7], "label": ["seven"]}))
    query = "SELECT p.*, l.label FROM places p JOIN frame_labels l USING(id)"
    if view:
        connector.connection.execute("CREATE VIEW frame_view AS " + query)
        query = "SELECT * FROM frame_view"
    result = connector.execute_spatial_query(query)
    assert result.id.tolist() == [7]
    assert result.label.tolist() == ["seven"]
    assert result.geometry.iloc[0].equals_exact(frame.geometry.iloc[0], 0)
    assert result.crs == frame.crs


def test_r2_2_attached_catalog_and_quoted_view_resolve_geometry_source(places):
    connector, frame = places
    connector.connection.execute("ATTACH ':memory:' AS other")
    connector.connection.execute("CREATE SCHEMA other.retained")
    connector.connection.execute("USE other.retained")
    connector.upload_spatial_data(frame, "places")
    connector.connection.execute('CREATE VIEW "place.view" AS SELECT * FROM places')
    connector.connection.execute("USE memory.main")
    result = connector.execute_spatial_query('SELECT p.* FROM other.retained."place.view" p')
    assert result.id.tolist() == [7]
    assert result.crs == frame.crs


def test_r2_2_prepared_read_keeps_rows_columns_and_crs(places):
    connector, frame = places
    connector.connection.execute("PREPARE read_places AS SELECT p.* FROM place_view p")
    result = connector.execute_spatial_query("EXECUTE read_places")
    assert result.id.tolist() == [7]
    assert result.columns.tolist() == frame.columns.tolist()
    assert result.crs == frame.crs


@pytest.mark.parametrize("helper", ["_duckdb_table_metadata", "_duckdb_select_metadata", "_duckdb_parsed_metadata"])
@pytest.mark.parametrize("error", [RuntimeError, KeyError])
@pytest.mark.parametrize("crs", [None, "EPSG:4326"])
def test_r2_2_discovery_errors_keep_driver_rows_and_warn(places, monkeypatch, caplog, helper, error, crs):
    import pandas as pd
    import siege_utilities.geo.spatial_transformations as module

    connector, _ = places
    connector.connection.register("frame_labels", pd.DataFrame({"id": [7], "label": ["seven"]}))
    query = "SELECT p.*, l.label FROM places p JOIN frame_labels l USING(id)"
    driver = connector.connection.execute(query).df()

    def fail(*args, **kwargs):
        raise error("discovery probe failure")

    monkeypatch.setattr(module, helper, fail, raising=False)
    with caplog.at_level("WARNING", logger=module.__name__):
        result = connector.execute_spatial_query(query, crs=crs)
    assert result.id.tolist() == driver.id.tolist()
    assert result.label.tolist() == driver.label.tolist()
    assert result._siege_crs.tolist() == driver._siege_crs.tolist()
    assert result.geometry.to_wkt().tolist() == driver.geometry_wkt.tolist()
    assert result.crs is None
    assert "discovery probe failure" in caplog.text
    assert any(record.levelname == "WARNING" for record in caplog.records)


@pytest.mark.parametrize("metadata, reason", [
    ('["EPSG:3857", "EPSG:4326"]', "conflicting source CRSs"),
    ('["EPSG:3857", null]', "known and unknown CRSs"),
    ('[null]', "unknown"),
    ('["invalid:crs"]', "Invalid"),
    ('not json', "Expecting value"),
])
def test_r2_2_unusable_metadata_keeps_rows_with_reason(places, caplog, metadata, reason):
    connector, _ = places
    connector.connection.execute("COMMENT ON TABLE places IS '\nsiege_utilities.crs.v1=" + metadata + "'")
    driver = connector.connection.execute("SELECT * FROM places").df()
    with caplog.at_level("WARNING"):
        result = connector.execute_spatial_query("SELECT * FROM places")
    assert result.id.tolist() == driver.id.tolist()
    assert result._siege_crs.tolist() == driver._siege_crs.tolist()
    assert result.geometry.to_wkt().tolist() == driver.geometry_wkt.tolist()
    assert result.crs is None
    assert reason in caplog.text


@pytest.mark.parametrize("other", ["same", "conflicting", "unknown", "external"])
def test_r2_2_all_geometry_sources_determine_crs(places, caplog, other):
    connector, frame = places
    if other == "external":
        connector.connection.register("other_places", frame.to_wkt().rename(columns={"geometry": "geometry_wkt"}))
    elif other == "unknown":
        connector.connection.execute("CREATE TABLE other_places AS SELECT * FROM places")
    else:
        connector.upload_spatial_data(frame if other == "same" else frame.to_crs(4326), "other_places")
    query = "SELECT * FROM places UNION ALL SELECT * FROM other_places"
    driver = connector.connection.execute(query).df()
    with caplog.at_level("WARNING"):
        result = connector.execute_spatial_query(query)
    assert result.id.tolist() == driver.id.tolist()
    assert result._siege_crs.tolist() == driver._siege_crs.tolist()
    assert result.geometry.to_wkt(rounding_precision=-1).tolist() == driver.geometry_wkt.tolist()
    if other == "same":
        assert result.crs == frame.crs
        assert not caplog.records
    else:
        assert result.crs is None
        assert ("conflicting" if other == "conflicting" else "unknown") in caplog.text


def test_r2_2_discovery_failure_keeps_returning_rows_and_write(places, monkeypatch, caplog):
    import siege_utilities.geo.spatial_transformations as module

    connector, frame = places

    def fail(*args, **kwargs):
        raise RuntimeError("target metadata unavailable")

    monkeypatch.setattr(module, "_duckdb_table_metadata", fail)
    with caplog.at_level("WARNING"):
        result = connector.execute_spatial_query("INSERT INTO places SELECT * FROM places RETURNING *")
    assert result.id.tolist() == frame.id.tolist()
    assert result.geometry.to_wkt().tolist() == frame.geometry.to_wkt().tolist()
    assert result.crs is None
    assert connector.connection.execute("SELECT id FROM places").fetchall() == [(7,), (7,)]
    assert "target metadata unavailable" in caplog.text
