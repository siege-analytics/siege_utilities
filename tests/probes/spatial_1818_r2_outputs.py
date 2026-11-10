"""Capture base/head observations using only disposable local databases.

Run with Python followed by this file, the source checkout, and an output JSON
path. SIEGE_TEST_POSTGIS_DSN must identify a disposable PostGIS database.
"""

import json
import os
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, sys.argv[1])

import duckdb
import geopandas as gpd
import psycopg2
from shapely.geometry import Point

from siege_utilities.geo.spatial_transformations import DuckDBConnector, PostGISConnector


def capture(call):
    try:
        result = call()
        if isinstance(result, gpd.GeoDataFrame):
            geometry = result.geometry.name
            return {
                "columns": result.columns.tolist(),
                "rows": result.assign(**{geometry: result.geometry.to_wkt()}).to_dict("records"),
                "crs": result.crs.to_string() if result.crs else None,
            }
        return result
    except Exception as error:
        return {"error": type(error).__name__, "message": str(error)}


def duck_observations():
    queries = {
        "direct": "SELECT * FROM places",
        "alias": "SELECT p.* FROM places p",
        "qualified": 'SELECT p.* FROM "memory"."main"."places" p',
        "view": "SELECT * FROM place_view",
        "nested_view": "SELECT * FROM nested_view",
        "using": "SELECT p.*, l.label FROM places p JOIN labels l USING(id)",
        "on": "SELECT p.*, l.label FROM places p JOIN labels l ON p.id=l.id",
        "cte": "WITH src AS (SELECT * FROM places) SELECT * FROM src",
        "empty": "SELECT * FROM place_view WHERE false",
        "prepared_read": "EXECUTE read_places",
        "insert_returning": "INSERT INTO places SELECT * FROM places RETURNING *",
        "prepared_write": "EXECUTE write_places",
        "comment_cte": "WITH src AS (/* note */ SELECT * FROM places) "
                       "INSERT INTO places SELECT * FROM src RETURNING *",
        "update_returning": "UPDATE places SET id=8 RETURNING *",
        "delete_returning": "DELETE FROM places RETURNING *",
    }
    output = {}
    for srid in (4326, 3857):
        for name, query in queries.items():
            connector = DuckDBConnector.__new__(DuckDBConnector)
            connector.connection = duckdb.connect()
            try:
                point = Point(1, 2) if srid == 4326 else Point(1000000, 2000000)
                frame = gpd.GeoDataFrame({"id": [7]}, geometry=[point], crs=srid)
                connector.upload_spatial_data(frame, "places")
                for sql in [
                    "CREATE VIEW place_view AS SELECT * FROM places",
                    "CREATE VIEW nested_view AS SELECT p.* FROM place_view p",
                    "CREATE TABLE labels AS SELECT 7 AS id, 'seven' AS label",
                    "PREPARE read_places AS SELECT p.* FROM place_view p",
                    "PREPARE write_places AS INSERT INTO places SELECT * FROM places RETURNING *",
                ]:
                    connector.connection.execute(sql)
                output[f"duck_{srid}_{name}"] = {
                    "result": capture(lambda: connector.execute_spatial_query(query)),
                    "stored": connector.connection.execute("SELECT * FROM places ORDER BY id").fetchall(),
                }
            finally:
                connector.close()
    return output


def postgis_observations():
    dsn = os.environ["SIEGE_TEST_POSTGIS_DSN"]
    observer = psycopg2.connect(dsn)
    observer.autocommit = True
    schema = "r2_outputs_" + uuid4().hex
    table = f'"{schema}".places'
    output = {}
    with observer.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{schema}"')
        cursor.execute(f"CREATE TABLE {table}(id INT, geometry geometry(Point,4326))")
    try:
        operations = {
            "insert": f"INSERT INTO {table} VALUES (8,ST_SetSRID(ST_Point(3,4),4326)) RETURNING *",
            "delete": f"DELETE FROM {table} WHERE id=7 RETURNING *",
            "update": f"UPDATE {table} SET id=8 WHERE id=7 RETURNING *",
            "merge": f"MERGE INTO {table} p USING (VALUES(7)) src(id) ON p.id=src.id "
                     "WHEN MATCHED THEN UPDATE SET id=8 RETURNING p.*",
        }
        for name in [*operations, "b3_read", "caller_write", "bad_crs"]:
            with observer.cursor() as cursor:
                cursor.execute(f"TRUNCATE {table}")
                cursor.execute(f"INSERT INTO {table} VALUES (7,ST_SetSRID(ST_Point(1,2),4326))")
            connector = PostGISConnector.__new__(PostGISConnector)
            connector._opened_connection = True
            connector.connection = psycopg2.connect(dsn)
            try:
                if name in {"b3_read", "caller_write"}:
                    with connector.connection.cursor() as cursor:
                        cursor.execute(f"INSERT INTO {table} VALUES (99,ST_SetSRID(ST_Point(0,0),4326))")
                    query = f"SELECT * FROM {table} ORDER BY id" if name == "b3_read" else operations["insert"]
                else:
                    query = f"WITH changed AS ({operations.get(name, operations['insert'])}) SELECT * FROM changed"
                options = {"crs": "invalid:crs"} if name == "bad_crs" else {}
                result = capture(lambda: connector.execute_spatial_query(query, **options))
                with observer.cursor() as cursor:
                    cursor.execute(f"SELECT id FROM {table} ORDER BY id")
                    success = cursor.fetchall()
                connector.close()
                with observer.cursor() as cursor:
                    cursor.execute(f"SELECT id FROM {table} ORDER BY id")
                    closed = cursor.fetchall()
                output["postgis_" + name] = {
                    "result": result, "observer_after_success": success, "observer_after_close": closed,
                }
            finally:
                connector.close()
    finally:
        with observer.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA "{schema}" CASCADE')
        observer.close()
    return output


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(json.dumps(duck_observations() | postgis_observations(), indent=2, sort_keys=True))
