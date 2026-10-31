"""Independent real-driver lexical boundaries for FINAL R6; own DB only.

Adopted from the R-1818-2 review harness. The only adaptation is the pg_pair
fixture skipping when SIEGE_TEST_POSTGIS_DSN is unset, so the PostGIS cases run
in CI (which provides a cluster) and skip on a workstation without one; no
assertion changed. The DuckDB boundary behavior is also covered without a
cluster by test_1818_r2_duckdb_and_lexer.py.
"""
import os
from uuid import uuid4

import duckdb
import pytest
from siege_utilities.geo import spatial_transformations as module

@pytest.fixture
def pg_pair():
    dsn = os.environ.get('SIEGE_TEST_POSTGIS_DSN')
    if not dsn:
        pytest.skip('SIEGE_TEST_POSTGIS_DSN not set; real-PostGIS boundary cases need a live cluster')
    import psycopg2
    observer=psycopg2.connect(dsn);observer.autocommit=True
    client=module.PostGISConnector(dsn)
    table='review_lex_'+uuid4().hex
    with observer.cursor() as cursor:cursor.execute(f'CREATE TABLE {table}(id INT, geometry geometry)')
    try:yield client,observer,table
    finally:
        client.close()
        with observer.cursor() as cursor:cursor.execute(f'DROP TABLE {table}')
        observer.close()

@pytest.mark.parametrize('backend',['duckdb','postgis'])
@pytest.mark.parametrize('newline',['\n','\r\n','\r'],ids=['LF','CRLF','CR'])
def test_embedded_commit_in_comment_terminated_batch_is_rejected(backend,newline,pg_pair):
    if backend=='postgis':
        client,observer,table=pg_pair
        query=f"INSERT INTO {table} VALUES(8,ST_SetSRID(ST_Point(1,2),4326)); -- review{newline}COMMIT;{newline}SELECT 'not WKB'::text AS geometry"
    else:
        client=module.DuckDBConnector.__new__(module.DuckDBConnector);client.connection=duckdb.connect(':memory:')
        client.connection.execute('CREATE TABLE places(id INT,geometry_wkt VARCHAR)')
        query=f"INSERT INTO places VALUES(8,'POINT (1 2)'); -- review{newline}COMMIT;{newline}SELECT 'not geometry' AS geometry_wkt"
    try:
        with pytest.raises(module.SpatialQueryError) as caught:client.execute_spatial_query(query)
        if backend=='postgis':
            with observer.cursor() as cursor:cursor.execute(f'SELECT id FROM {table}');rows=cursor.fetchall()
        else:rows=client.connection.execute('SELECT id FROM places').fetchall()
        assert rows==[],f'Guard bypass; committed rows after failed API call: {rows}; {caught.value}'
        assert 'multi-statement batch' in str(caught.value)
    finally:
        if backend=='duckdb':client.close()

@pytest.mark.parametrize('tag',['review','é','分析'])
def test_valid_dollar_quote_with_control_text_is_not_rejected(pg_pair,tag):
    client,observer,_=pg_pair
    query=f'SELECT ST_SetSRID(ST_Point(1,2),4326) AS geometry, ${tag}$; COMMIT; ${tag}$ AS label'
    # Real driver control verifies that each exact SQL form is valid, not a
    # fabricated lexical edge that PostgreSQL rejects itself.
    with observer.cursor() as cursor:
        cursor.execute(query)
        assert cursor.fetchone()[1]=='; COMMIT; '
    result=client.execute_spatial_query(query)
    assert result.label.tolist()==['; COMMIT; ']
    assert result.crs.to_epsg()==4326

@pytest.mark.parametrize('autocommit',[False,True])
@pytest.mark.parametrize('caller',[False,True])
@pytest.mark.parametrize('failure',['bad_wkb','runtime_decoder'])
def test_real_postgis_error_ownership(pg_pair,autocommit,caller,failure,monkeypatch):
    client,observer,table=pg_pair
    conn=client.connection;conn.autocommit=autocommit
    if caller:
        with conn.cursor() as cursor:
            cursor.execute('BEGIN')
            cursor.execute(f'INSERT INTO {table} VALUES(99,ST_SetSRID(ST_Point(1,2),4326))')
    if failure=='runtime_decoder':
        def fail(*args,**kwargs):raise RuntimeError('independent decoder failure')
        monkeypatch.setattr(module.gpd,'GeoDataFrame',fail)
        geom='geometry'
    else:geom="'not WKB'::text AS geometry"
    with pytest.raises(module.SpatialQueryError):
        client.execute_spatial_query(f'INSERT INTO {table} VALUES(8,ST_SetSRID(ST_Point(1,2),4326)) RETURNING id,{geom}',crs='EPSG:4326')
    assert conn.get_transaction_status()==(2 if caller else 0)
    with observer.cursor() as cursor:cursor.execute(f'SELECT id FROM {table}');assert cursor.fetchall()==[]
    if caller:
        with conn.cursor() as cursor:cursor.execute(f'SELECT id FROM {table}');assert cursor.fetchall()==[(99,)]
        conn.rollback() if not autocommit else conn.cursor().execute('ROLLBACK')

@pytest.mark.parametrize('autocommit',[False,True])
def test_real_postgis_owned_success_is_durable(pg_pair,autocommit):
    client,observer,table=pg_pair;client.connection.autocommit=autocommit
    result=client.execute_spatial_query(f'INSERT INTO {table} VALUES(8,ST_SetSRID(ST_Point(1,2),4326)) RETURNING *')
    assert result.id.tolist()==[8]
    assert client.connection.get_transaction_status()==0
    with observer.cursor() as cursor:cursor.execute(f'SELECT id FROM {table}');assert cursor.fetchall()==[(8,)]

@pytest.mark.parametrize('finalizer',['COMMIT','ROLLBACK'])
def test_real_duckdb_caller_query_joins(finalizer):
    client=module.DuckDBConnector.__new__(module.DuckDBConnector);client.connection=duckdb.connect(':memory:')
    conn=client.connection
    try:
        conn.execute('CREATE TABLE pending(id INT)');conn.execute('BEGIN');conn.execute('INSERT INTO pending VALUES(99)')
        assert client.execute_spatial_query('INSERT INTO pending VALUES(8) RETURNING *').id.tolist()==[8]
        conn.execute(finalizer)
        assert conn.execute('SELECT id FROM pending ORDER BY id').fetchall()==([(8,),(99,)] if finalizer=='COMMIT' else [])
    finally:client.close()
