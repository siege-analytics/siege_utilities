"""Live PostGIS authority and transaction regressions for PR #1818."""

import os
from uuid import uuid4

import pytest
from pyproj import CRS
from shapely.geometry import Point

from siege_utilities.geo.spatial_transformations import PostGISConnector, SpatialQueryError

pytestmark = pytest.mark.postgis


@pytest.fixture
def postgis_pair():
    """Use only the disposable database named by the test run."""
    psycopg2 = pytest.importorskip("psycopg2")
    dsn = os.environ.get("SIEGE_TEST_POSTGIS_DSN") or os.environ.get("SIEGE_UTILITIES_TEST_PG_DSN")
    if not dsn:
        pytest.skip("Set SIEGE_TEST_POSTGIS_DSN to a disposable PostGIS database")
    observer = psycopg2.connect(dsn)
    observer.autocommit = True
    connector = PostGISConnector.__new__(PostGISConnector)
    connector.connection = psycopg2.connect(dsn)
    schema = "review_1818_" + uuid4().hex
    with observer.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{schema}"')
        cursor.execute(f'CREATE TABLE "{schema}".places (id INTEGER, geometry geometry)')
    try:
        yield connector, observer, f'"{schema}".places'
    finally:
        connector.close()
        with observer.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA "{schema}" CASCADE')
        observer.close()



def test_b1_postgis_resolves_esri_authority(postgis_pair):
    connector, observer, _ = postgis_pair
    with observer.cursor() as cursor:
        cursor.execute(
            "INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext) "
            "VALUES (102003, 'ESRI', 102003, %s) ON CONFLICT (srid) DO NOTHING",
            [CRS("ESRI:102003").to_wkt()],
        )
    result = connector.execute_spatial_query(
        "SELECT ST_SetSRID(ST_Point(1000000,2000000),102003) AS geometry",
        crs="ESRI:102003",
    )
    assert result.crs == CRS("ESRI:102003")
    assert result.geometry.iloc[0].equals_exact(Point(1000000, 2000000), 0)



def test_b1_postgis_wraps_crs_errors(postgis_pair):
    connector, _, _ = postgis_pair
    with pytest.raises(SpatialQueryError) as raised:
        connector.execute_spatial_query(
            "SELECT ST_SetSRID(ST_Point(0,0),4326) AS geometry", crs="invalid:crs",
        )
    from pyproj.exceptions import CRSError

    assert isinstance(raised.value.__cause__, CRSError)
    assert connector.connection.get_transaction_status() == 0



def test_b3_select_does_not_commit_caller_pending_write(postgis_pair):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    before = connector.connection.get_transaction_status()
    result = connector.execute_spatial_query(f"SELECT * FROM {table}")
    after = connector.connection.get_transaction_status()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        visible_before_rollback = cursor.fetchone()[0]
    connector.connection.rollback()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        visible_after_rollback = cursor.fetchone()[0]
    assert result.id.tolist() == [99]
    assert (visible_before_rollback, visible_after_rollback) == (0, 0)
    assert before == after



def test_b3_returning_commits_only_after_crs_validation(postgis_pair):
    connector, observer, table = postgis_pair
    with pytest.raises(SpatialQueryError):
        connector.execute_spatial_query(
            f"INSERT INTO {table} VALUES (1, ST_SetSRID(ST_Point(1,2),4326)) RETURNING *",
            crs="invalid:crs",
        )
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        assert cursor.fetchone() == (0,)
    result = connector.execute_spatial_query(
        f"INSERT INTO {table} VALUES (2, ST_SetSRID(ST_Point(1,2),4326)) RETURNING *",
        crs="EPSG:4326",
    )
    assert result.id.tolist() == [2]
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(2,)]

