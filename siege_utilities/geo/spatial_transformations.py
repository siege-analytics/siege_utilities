"""
Spatial data transformation utilities for siege_utilities.
Provides format conversion and transformation capabilities using the core geospatial stack.
DuckDB support is included but optional for enhanced performance on large datasets.
"""

import json
import logging
import re
from pathlib import Path

try:
    import geopandas as gpd
    from pyproj.exceptions import CRSError as _CRSError
    from shapely.errors import ShapelyError as _ShapelyError
    _GEOPANDAS_AVAILABLE = True
except ImportError:
    gpd = None
    _ShapelyError = ValueError
    _CRSError = ValueError
    _GEOPANDAS_AVAILABLE = False
from typing import Optional, Union

# Import existing library functions
from ..config.user_config import get_user_config
from ..conf import settings

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]
GeoDataFrame = gpd.GeoDataFrame if _GEOPANDAS_AVAILABLE else None


class SpatialQueryError(RuntimeError):
    """Raised when a spatial SQL query fails.

    Use the ``__cause__`` attribute (set via ``raise ... from e``) to
    inspect the underlying database exception.
    """


_SQL_TOKEN = re.compile(
    r"(?P<space>\s+|--[^\n]*(?:\n|$))|(?P<comment>/\*)|"
    r"(?P<string>[eE]'(?:[^'\\]|\\.|'')*'|'(?:[^']|'')*')|"
    r'(?P<identifier>"(?:[^"]|"")*")|'
    r"(?P<dollar>\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$)|"
    r"(?P<word>[A-Za-z_\u0080-\uffff][A-Za-z_0-9$\u0080-\uffff]*)|(?P<symbol>.)",
    re.DOTALL,
)


def _sql_tokens(query):
    """Yield actual lexemes, excluding whitespace and nested SQL comments."""
    offset = 0
    while offset < len(query):
        match = _SQL_TOKEN.match(query, offset)
        kind, value = match.lastgroup, match.group()
        offset = match.end()
        if kind == 'comment':
            depth = 1
            while depth and offset < len(query):
                delimiter = re.search(r'/\*|\*/', query[offset:])
                if delimiter is None:
                    offset = len(query)
                    break
                depth += 1 if delimiter.group() == '/*' else -1
                offset += delimiter.end()
        elif kind == 'dollar':
            end = query.find(value, offset)
            offset = len(query) if end < 0 else end + len(value)
            yield 'string', query[match.start():offset]
        elif kind != 'space':
            yield kind, value


def _postgis_has_dml(query):
    """Flag write keywords at any depth outside literals."""
    keywords = {'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE', 'DROP', 'ALTER',
                'TRUNCATE', 'COPY', 'CALL', 'DO', 'GRANT', 'REVOKE'}
    return any(kind == 'word' and value.upper() in keywords
               for kind, value in _sql_tokens(query))

# Try to import DuckDB (optional)
try:
    import duckdb
    DUCKDB_AVAILABLE = True
    _DuckDBError = duckdb.Error
    log.info("DuckDB available for enhanced spatial operations")
except ImportError:
    DUCKDB_AVAILABLE = False
    _DuckDBError = Exception
    log.info("DuckDB not available - using standard geospatial stack")

# Conditional import for psycopg2 error base class (optional dependency)
try:
    from psycopg2 import Error as _Psycopg2Error
except ImportError:
    _Psycopg2Error = Exception


class SpatialDataTransformer:
    """Transform spatial data between different formats and coordinate systems."""
    
    def __init__(self):
        """Initialize the spatial data transformer."""
        self.user_config = get_user_config()


        # Supported output formats (using core geospatial stack + optional DuckDB)
        self.supported_formats = {
            'output': ['shp', 'geojson', 'gpkg', 'kml', 'gml', 'wkt', 'wkb', 'postgis']
        }
        
        # Add DuckDB if available
        if DUCKDB_AVAILABLE:
            self.supported_formats['output'].append('duckdb')
    
    def convert_format(self, gdf: GeoDataFrame, output_format: str, **kwargs) -> None:
        """
        Convert GeoDataFrame to different format.

        Args:
            gdf: Input GeoDataFrame
            output_format: Desired output format
            **kwargs: Additional format-specific parameters

        Raises:
            ValueError: If output_format is unsupported
            ImportError: If required dependency is not available
            OSError: If file write fails
        """
        if output_format == 'shp':
            self._convert_to_shapefile(gdf, **kwargs)
        elif output_format == 'geojson':
            self._convert_to_geojson(gdf, **kwargs)
        elif output_format == 'gpkg':
            self._convert_to_geopackage(gdf, **kwargs)
        elif output_format == 'kml':
            self._convert_to_kml(gdf, **kwargs)
        elif output_format == 'gml':
            self._convert_to_gml(gdf, **kwargs)
        elif output_format == 'wkt':
            self._convert_to_wkt(gdf, **kwargs)
        elif output_format == 'wkb':
            self._convert_to_wkb(gdf, **kwargs)
        elif output_format == 'postgis':
            self._convert_to_postgis(gdf, **kwargs)
        elif output_format == 'duckdb':
            if not DUCKDB_AVAILABLE:
                raise ImportError("DuckDB not available. Install with: pip install duckdb")
            self._convert_to_duckdb(gdf, **kwargs)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _convert_to_shapefile(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to ESRI Shapefile format."""
        output_path = kwargs.get('output_path', 'output.shp')
        from siege_utilities.files.operations import atomic_write_shapefile
        atomic_write_shapefile(gdf, output_path)
        log.info(f"Successfully converted to Shapefile: {output_path}")

    def _convert_to_geojson(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to GeoJSON format."""
        output_path = kwargs.get('output_path', 'output.geojson')
        from siege_utilities.files.operations import atomic_write_path
        with atomic_write_path(output_path) as tmp:
            gdf.to_file(str(tmp), driver='GeoJSON')
        log.info(f"Successfully converted to GeoJSON: {output_path}")

    def _convert_to_geopackage(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to GeoPackage format."""
        output_path = kwargs.get('output_path', 'output.gpkg')
        from siege_utilities.files.operations import atomic_write_path
        with atomic_write_path(output_path) as tmp:
            gdf.to_file(str(tmp), driver='GPKG')
        log.info(f"Successfully converted to GeoPackage: {output_path}")

    def _convert_to_kml(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to KML format."""
        output_path = kwargs.get('output_path', 'output.kml')
        from siege_utilities.files.operations import atomic_write_path
        with atomic_write_path(output_path) as tmp:
            gdf.to_file(str(tmp), driver='KML')
        log.info(f"Successfully converted to KML: {output_path}")

    def _convert_to_gml(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to GML format."""
        output_path = kwargs.get('output_path', 'output.gml')
        from siege_utilities.files.operations import atomic_write_path
        with atomic_write_path(output_path) as tmp:
            gdf.to_file(str(tmp), driver='GML')
        log.info(f"Successfully converted to GML: {output_path}")

    def _convert_to_wkt(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to WKT (Well-Known Text) format."""
        output_path = kwargs.get('output_path', 'output.wkt')
        from siege_utilities.files.operations import atomic_write_path
        wkt_data = gdf.copy()
        wkt_data['geometry'] = wkt_data.geometry.astype(str)
        with atomic_write_path(output_path) as tmp:
            wkt_data.to_csv(str(tmp), index=False)
        log.info(f"Successfully converted to WKT: {output_path}")

    def _convert_to_wkb(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to WKB (Well-Known Binary) format."""
        output_path = kwargs.get('output_path', 'output.wkb')
        from siege_utilities.files.operations import atomic_write_path
        wkb_data = gdf.copy()
        wkb_data['geometry'] = wkb_data.geometry.apply(lambda geom: geom.wkb)
        with atomic_write_path(output_path) as tmp:
            wkb_data.to_pickle(str(tmp))
        log.info(f"Successfully converted to WKB: {output_path}")
    
    def _convert_to_postgis(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to PostGIS format (generate SQL file)."""
        output_path = kwargs.get('output_path', 'output.sql')

        from siege_utilities.core.sql_safety import escape_sql_string_literal as escape_string_literal
        wkt_series = gdf.geometry.apply(lambda g: escape_string_literal(g.wkt))
        sql_lines = (
            "INSERT INTO spatial_table (geom) VALUES (ST_GeomFromText('"
            + wkt_series
            + "'));"
        )

        from siege_utilities.files.operations import atomic_write_path
        with atomic_write_path(output_path) as tmp:
            tmp.write_text('\n'.join(sql_lines), encoding='utf-8')

        log.info(f"Successfully generated PostGIS SQL: {output_path}")

    def _convert_to_duckdb(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to DuckDB format and save to database."""
        db_path = kwargs.get('db_path')
        if db_path is None and self.user_config is not None:
            try:
                db_path = self.user_config.get_database_connection('duckdb')
            except (AttributeError, ValueError, KeyError, TypeError) as e:
                log.warning(f"user_config.get_database_connection('duckdb') failed: {e}")
        db_path = db_path or ':memory:'
        table_name = kwargs.get('table_name', 'spatial_data')

        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        validate_identifier(table_name, label="table name", allow_dotted=False)

        with duckdb.connect(db_path) as con:
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: geom.wkt)
            df = df.drop(columns=['geometry'])
            con.register("siege_upload_df", df)
            try:
                con.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} "
                    f"AS SELECT * FROM siege_upload_df"
                )
            finally:
                try:
                    con.unregister("siege_upload_df")
                except (_DuckDBError, RuntimeError) as cleanup_exc:
                    log.warning(
                        "Failed to unregister siege_upload_df: %s",
                        cleanup_exc,
                    )

        log.info(f"Successfully uploaded to DuckDB table: {table_name}")


class PostGISConnector:
    """Handles PostGIS database connections and operations."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize PostGIS connector.

        Args:
            connection_string: PostgreSQL connection string. When omitted,
                we look up the configured ``postgresql`` connection from
                the user-config. Missing settings raise ValueError; config
                errors propagate and connection failures raise ConnectionError.
        """
        self.user_config = get_user_config()

        if connection_string is None and self.user_config is not None:
            try:
                connection_string = self.user_config.get_database_connection('postgresql')
            except (AttributeError, ValueError, KeyError, TypeError) as e:
                raise ValueError("Could not load configured PostgreSQL connection") from e
        self.connection_string = connection_string

        self.psycopg2 = None
        self.connection = None
        if self.connection_string is None:
            raise ValueError("PostGISConnector: no connection_string and none configured")

        try:
            import psycopg2
            self.psycopg2 = psycopg2
            self.connection = psycopg2.connect(self.connection_string)
            self._opened_connection = True
            log.info("Successfully connected to PostGIS")
        except ImportError:
            raise ImportError("psycopg2 not available. Install with: pip install psycopg2-binary")
        except (_Psycopg2Error, OSError) as e:
            raise ConnectionError("Failed to connect to PostGIS") from e

    def close(self):
        """Close the database connection."""
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception as exc:
                log.warning("Failed to close PostGIS connection: %s", exc)
            self.connection = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def upload_spatial_data(self, gdf: GeoDataFrame, table_name: str, **kwargs) -> None:
        """
        Upload spatial data to PostGIS with all columns preserved.

        Uses geopandas.GeoDataFrame.to_postgis under the hood, which
        handles full-column writes (geometry + every attribute column) via
        SQLAlchemy + GeoAlchemy2. This is the canonical geopandas idiom
        for PostGIS upload.

        Pre-#516 behavior (replaced): the old implementation manually
        built `INSERT INTO {table} (geom) VALUES (...)` statements,
        dropping all tabular columns from the GeoDataFrame. Any caller
        passing attribute data got an empty-attribute table silently.

        Args:
            gdf: GeoDataFrame to upload (all columns including geometry).
            table_name: Target table name.
            **kwargs: Additional parameters:
                if_exists: How to handle existing table -- ``'fail'``
                    (default), ``'replace'``, or ``'append'``. Failed
                    replacements roll back the original table.
                schema: PostgreSQL schema name (default ``'public'``).

        Raises:
            RuntimeError: If no connection string is configured
            ImportError: If geoalchemy2 is not available
            SpatialQueryError: If the upload fails
        """
        if not self.connection_string:
            raise RuntimeError("No PostGIS connection_string available")

        if_exists = kwargs.get('if_exists', 'fail')
        schema = kwargs.get('schema', 'public')

        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        validate_identifier(schema, label="schema name", allow_dotted=False)
        validate_identifier(table_name, label="table name", allow_dotted=False)

        try:
            import geoalchemy2  # noqa: F401  -- presence-check; to_postgis needs it
        except ImportError as e:
            raise ImportError(
                "geoalchemy2 not available -- upload_spatial_data requires it "
                "for full-column writes. Install with: pip install 'siege_utilities[geo]'"
            ) from e

        try:
            from sqlalchemy import create_engine
            engine = create_engine(self.connection_string)
            try:
                # Keep DROP, CREATE and inserts in one transaction.
                with engine.begin() as connection:
                    gdf.to_postgis(
                        name=table_name,
                        con=connection,
                        schema=schema,
                        if_exists=if_exists,
                    )
            finally:
                engine.dispose()
            log.info(
                f"Successfully uploaded to PostGIS table: {schema}.{table_name} "
                f"({len(gdf)} rows, {len(gdf.columns)} columns)"
            )

        except Exception as e:
            # to_postgis surfaces failures as SQLAlchemy / psycopg2 / value
            # errors depending on the cause; wrap them all in the documented
            # SpatialQueryError (preserving the cause). The engine is already
            # disposed in the finally above.
            raise SpatialQueryError(f"Failed to upload to PostGIS: {e}") from e
    
    def download_spatial_data(self, table_name: str, *, crs: str | None = None, **kwargs) -> GeoDataFrame:
        """
        Download spatial data from PostGIS.

        Args:
            table_name: Source table name
            crs: Optional output CRS. Omit to preserve the native SRID when
                available; otherwise use the configured default CRS.
            **kwargs: Additional parameters. Accepts ``geom_col``
                (default ``'geom'``) to specify the geometry column name.

        Returns:
            GeoDataFrame with spatial data.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails.
        """
        from siege_utilities.geo.crs import reproject_if_needed

        if not self.connection:
            raise SpatialQueryError("No PostGIS connection available")

        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        from psycopg2 import sql as _pg_sql
        # `allow_dotted=True` because the line below explicitly handles
        # schema-qualified names by splitting on '.'.
        validate_identifier(table_name, label="table name", allow_dotted=True)
        try:
            geom_col = kwargs.get('geom_col', 'geom')
            query = _pg_sql.SQL("SELECT * FROM {}").format(
                _pg_sql.Identifier(*table_name.split("."))
            )
            gdf = gpd.read_postgis(
                query.as_string(self.connection),
                self.connection,
                geom_col=geom_col,
            )
            log.info(f"Successfully downloaded from PostGIS: {table_name}")
            return reproject_if_needed(gdf, crs) if crs is not None else gdf

        except (_Psycopg2Error, _CRSError, OSError, ValueError, TypeError, AttributeError, KeyError) as e:
            raise SpatialQueryError(f"PostGIS download failed for {table_name}: {e}") from e
    
    def execute_spatial_query(self, query: str, *, crs: str | None = None, **kwargs) -> Union[GeoDataFrame, int]:
        """
        Execute a spatial SQL query.

        Row-returning statements, including CTEs and DML with RETURNING,
        produce a GeoDataFrame (without active geometry for tabular results).
        Other statements return an affected-row count, or -1 if unavailable.

        When this connector opened the connection and no caller transaction is
        active, every statement commits after decoding succeeds and rolls back
        on error. In a caller transaction, read-only statements never commit;
        statements containing write tokens commit, while volatile-function SELECT
        calls without write tokens leave the transaction open. Savepoints isolate
        failures without rolling back the caller's transaction.

        Args:
            query: SQL query string
            crs: Optional output CRS. Omit to preserve the native SRID when
                available; otherwise use the configured default CRS.
            **kwargs: Additional parameters

        Returns:
            GeoDataFrame for row-returning queries, int rowcount for others.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails. The original exception is chained as
                ``__cause__``.
        """
        from siege_utilities.geo.crs import reproject_if_needed

        if not self.connection:
            raise SpatialQueryError("No PostGIS connection available")

        from psycopg2.extensions import TRANSACTION_STATUS_INTRANS

        cursor = None
        caller_transaction = self.connection.get_transaction_status() == TRANSACTION_STATUS_INTRANS
        owns_transaction = self._opened_connection and not caller_transaction
        savepoint = False
        try:
            cursor = self.connection.cursor()
            if caller_transaction:
                cursor.execute("SAVEPOINT siege_spatial_query")
                savepoint = True
            cursor.execute(query)
            if cursor.description is not None:
                result = gpd.GeoDataFrame(
                    cursor.fetchall(), columns=[column[0] for column in cursor.description],
                )
                geom_col = kwargs.get('geom_col', 'geometry')
                if geom_col in result.columns:
                    from shapely import get_srid

                    # Decode fetched rows without replaying INSERT ... RETURNING.
                    wkb = result[geom_col].map(
                        lambda value: bytes(value) if isinstance(value, memoryview) else value
                    )
                    geometry = gpd.GeoSeries.from_wkb(wkb)
                    non_null = geometry.dropna()
                    srid = int(get_srid(non_null.iloc[0])) if len(non_null) else 0
                    result = result.set_geometry(geometry.rename(geom_col))
                    if srid:
                        with self.connection.cursor() as crs_cursor:
                            crs_cursor.execute(
                                "SELECT auth_name, auth_srid FROM spatial_ref_sys WHERE srid = %s",
                                (srid,),
                            )
                            authority = crs_cursor.fetchone()
                        # Match read_postgis's EPSG fallback for an absent row.
                        source_crs = f"{authority[0]}:{authority[1]}" if authority else f"EPSG:{srid}"
                        result = result.set_crs(source_crs)
                    elif crs is None:
                        log.warning(
                            "PostGIS geometries lack SRID metadata; assuming the default CRS. "
                            "Pass crs= to specify a target CRS."
                        )
                    if crs is not None or not srid:
                        result = reproject_if_needed(result, crs)
            else:
                result = cursor.rowcount
            if savepoint:
                cursor.execute("RELEASE SAVEPOINT siege_spatial_query")
                savepoint = False
            if owns_transaction:
                # SELECT can invoke volatile functions that write data.
                self.connection.commit()
            elif not query.strip().upper().startswith('SELECT') and _postgis_has_dml(query):
                # Preserve develop's commit behavior for caller-owned writes.
                # A SELECT-prefixed statement (including FOR UPDATE / FOR SHARE and
                # volatile-function SELECT) is never committed here, matching develop's
                # read_postgis path, so the caller keeps its transaction and row locks.
                self.connection.commit()
            log.info("Successfully executed PostGIS query")
            return result
        except (_Psycopg2Error, _ShapelyError, _CRSError, OSError, ValueError, TypeError, AttributeError) as e:
            log.error(f"Failed to execute PostGIS query: {e}")
            if self.connection:
                try:
                    if savepoint:
                        cursor.execute("ROLLBACK TO SAVEPOINT siege_spatial_query")
                        cursor.execute("RELEASE SAVEPOINT siege_spatial_query")
                    elif owns_transaction:
                        self.connection.rollback()
                except (_Psycopg2Error, OSError) as rb_exc:
                    log.warning("Failed to rollback PostGIS transaction: %s", rb_exc)
            raise SpatialQueryError(f"PostGIS query failed: {e}") from e
        finally:
            if cursor is not None:
                cursor.close()
    
    def _create_spatial_table(self, table_name: str, gdf: GeoDataFrame):
        """DEPRECATED. Kept only for backward compatibility with callers
        that referenced this private helper directly (pre-#516).

        The new upload_spatial_data uses gdf.to_postgis which creates the
        table with the full column set automatically. This helper, if
        called directly, still creates only (id, geom) -- which is the
        same broken behavior #516 fixed. Do not call this directly; use
        upload_spatial_data.

        Will be removed in a future major version.
        """
        from siege_utilities.core.sql_safety import validate_sql_identifier
        validate_sql_identifier(table_name, "table_name")

        cursor = self.connection.cursor()
        try:
            geom_types = gdf.geometry.geom_type.unique()
            if len(geom_types) == 1:
                pg_geom_type = geom_types[0].upper()
            else:
                pg_geom_type = "GEOMETRY"

            srid = None
            if gdf.crs is not None:
                try:
                    srid = gdf.crs.to_epsg()
                except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
                    log.warning(
                        "Could not derive EPSG code from CRS %r, "
                        "falling back to STORAGE_CRS (%s): %s",
                        gdf.crs, settings.STORAGE_CRS, exc,
                    )
                    srid = None
            srid = srid or settings.STORAGE_CRS
            if not isinstance(srid, int):
                raise TypeError(f"SRID must be an integer, got {type(srid)}")

            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                geom GEOMETRY({pg_geom_type}, {srid})
            );
            """

            cursor.execute(create_sql)
            self.connection.commit()
        finally:
            cursor.close()


_DUCKDB_CRS_COMMENT = '\nsiege_utilities.crs.v1='


def _duckdb_table_metadata(connection, table_name):
    """Read table comments without using any caller column names."""
    # Uploads can be exercised with a supplied connection and no installed
    # optional driver. Identifier parsing must not use a module-global driver.
    parts = []
    for kind, value in _sql_tokens(table_name):
        if kind in {'identifier', 'word'}:
            parts.append(value[1:-1].replace('""', '"') if kind == 'identifier' else value)
        elif value != '.':
            break
    table = parts[-1]
    schema = parts[-2] if len(parts) > 1 else None
    database = parts[-3] if len(parts) > 2 else None
    row = connection.execute(
        "SELECT comment FROM duckdb_tables() "
        "WHERE lower(table_name) = lower(?) "
        "AND lower(schema_name) = lower(coalesce(?, current_schema())) "
        "AND (lower(database_name) = lower(coalesce(?, current_database())) "
        "OR (? IS NULL AND temporary)) ORDER BY temporary DESC LIMIT 1",
        [table, schema, database, database],
    ).fetchone()
    comment = row[0] if row else None
    if comment and _DUCKDB_CRS_COMMENT in comment:
        return comment, json.loads(comment.rsplit(_DUCKDB_CRS_COMMENT, 1)[1])
    return comment, None


def _duckdb_result_frame(df, *, source_crs=None, crs=None, stored_crs=()):
    """Decode stored WKT and table CRS without consuming caller attributes."""
    from pyproj import CRS

    if 'geometry_wkt' not in df.columns and 'geometry' not in df.columns:
        return gpd.GeoDataFrame(df)
    source = CRS.from_user_input(source_crs) if source_crs is not None else None
    known = {CRS.from_user_input(value) for value in stored_crs if value is not None}
    if len(known) > 1 or (source is not None and any(value != source for value in known)):
        raise ValueError("Result contains conflicting source CRSs")
    if source is None and known:
        if None in stored_crs:
            raise ValueError("Result mixes known and unknown CRSs; provide source_crs")
        source = next(iter(known))
    if 'geometry_wkt' in df.columns:
        df['geometry'] = gpd.GeoSeries.from_wkt(df.pop('geometry_wkt'), index=df.index)
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=source)
    if crs is not None:
        if source is None:
            raise ValueError("Source CRS is unknown; provide source_crs before reprojecting")
        return gdf.to_crs(crs)
    return gdf


def _duckdb_query_frame(df, crs=None):
    """Decode arbitrary SQL results using develop's assumed WKT CRS."""
    from siege_utilities.geo.crs import reproject_if_needed

    if 'geometry_wkt' not in df.columns and 'geometry' not in df.columns:
        return gpd.GeoDataFrame(df)
    if 'geometry_wkt' in df.columns:
        df['geometry'] = gpd.GeoSeries.from_wkt(df.pop('geometry_wkt'), index=df.index)
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
    if crs is None:
        log.warning(
            "DuckDB WKT geometries lack SRID metadata; assuming EPSG:4326. "
            "Pass crs= to reproject to a target CRS."
        )
    return reproject_if_needed(gdf, crs)


class DuckDBConnector:
    """Handles DuckDB database connections and operations (optional)."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DuckDB connector.
        
        Args:
            db_path: Path to DuckDB database file (optional, uses user config if not provided)
        """
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB not available. Install with: pip install duckdb")
        
        self.user_config = get_user_config()

        if db_path is None and self.user_config is not None:
            try:
                db_path = self.user_config.get_database_connection('duckdb')
            except (AttributeError, ValueError, KeyError, TypeError) as e:
                log.warning(f"user_config.get_database_connection('duckdb') failed: {e}")
                db_path = None
        self.db_path = db_path or ':memory:'
        self.connection = None
    
    def connect(self) -> None:
        """Establish database connection.

        Raises:
            RuntimeError: If connection fails
        """
        try:
            self.connection = duckdb.connect(self.db_path)
            log.info("Successfully connected to DuckDB")
        except Exception as e:
            # Any failure opening the connection is a connection failure; wrap
            # it (preserving the cause) so callers see one typed error.
            raise RuntimeError(f"Failed to connect to DuckDB: {e}") from e

    def close(self):
        """Close the database connection."""
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception as exc:
                log.warning("Failed to close DuckDB connection: %s", exc)
            self.connection = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def upload_spatial_data(self, gdf: GeoDataFrame, table_name: str, **kwargs) -> None:
        """
        Upload spatial data to DuckDB in one transaction.

        Args:
            gdf: GeoDataFrame to upload. Geometry is stored as geometry_wkt
                with full CRS WKT in the table comment, including for empty tables.
            table_name: Target table name
            **kwargs: if_exists is 'fail' (default), 'replace', or 'append'.
                Append matches columns by name and rejects conflicting CRSs.
                Legacy rows retain unknown CRS when metadata is first added.

        Raises:
            RuntimeError: If connection or upload fails
        """
        if not self.connection:
            self.connect()

        from siege_utilities.core.sql_safety import validate_sql_identifier
        validate_sql_identifier(table_name, "table name")

        try:
            if_exists = kwargs.get('if_exists', 'fail')
            if if_exists not in {'fail', 'replace', 'append'}:
                raise ValueError("if_exists must be 'fail', 'replace', or 'append'")
            if 'geometry_wkt' in gdf.columns:
                raise ValueError("geometry_wkt is a reserved storage column")
            df = gdf.to_wkt(rounding_precision=-1).rename(columns={gdf.geometry.name: 'geometry_wkt'})
            df['geometry_wkt'] = df['geometry_wkt'].astype('string')
            incoming_crs = gdf.crs.to_wkt() if gdf.crs is not None else None
            self.connection.register("siege_upload_df", df)
            try:
                self.connection.execute("BEGIN TRANSACTION")
                try:
                    if if_exists == 'replace':
                        self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                    comment, stored = _duckdb_table_metadata(self.connection, table_name)
                    metadata = [incoming_crs]
                    if if_exists == 'append':
                        self.connection.execute(
                            f"CREATE TABLE IF NOT EXISTS {table_name} AS "
                            "SELECT * FROM siege_upload_df WHERE FALSE"
                        )
                        if stored is None:
                            has_rows = self.connection.execute(
                                f"SELECT EXISTS (SELECT 1 FROM {table_name})"
                            ).fetchone()[0]
                            stored = [None] if has_rows else []
                        from pyproj import CRS

                        if any(value is not None and CRS.from_user_input(value) != gdf.crs
                               for value in (stored or [])):
                            raise ValueError("Cannot append data with a different source CRS")
                        metadata = list(dict.fromkeys((stored or []) + [incoming_crs]))
                        self.connection.execute(
                            f"INSERT INTO {table_name} BY NAME SELECT * FROM siege_upload_df"
                        )
                    else:
                        self.connection.execute(
                            f"CREATE TABLE {table_name} AS SELECT * FROM siege_upload_df"
                        )
                    from siege_utilities.core.sql_safety import escape_sql_string_literal

                    prior_comment = (comment or '').split(_DUCKDB_CRS_COMMENT, 1)[0]
                    comment = prior_comment + _DUCKDB_CRS_COMMENT + json.dumps(metadata)
                    literal = escape_sql_string_literal(comment)
                    self.connection.execute(f"COMMENT ON TABLE {table_name} IS '{literal}'")
                    self.connection.execute("COMMIT")
                except Exception:
                    # Roll back every failure after BEGIN, including conversion
                    # and schema errors. A rollback failure retains the upload
                    # failure as its exception context.
                    self.connection.execute("ROLLBACK")
                    raise
            finally:
                try:
                    self.connection.unregister("siege_upload_df")
                except (_DuckDBError, RuntimeError) as cleanup_exc:
                    log.warning("Failed to unregister siege_upload_df: %s", cleanup_exc)

            log.info(f"Successfully uploaded to DuckDB: {table_name}")

        except (_DuckDBError, _CRSError, OSError, ValueError, TypeError, AttributeError) as e:
            raise RuntimeError(f"Failed to upload to DuckDB: {e}") from e

    def download_spatial_data(self, table_name: str, *, crs: str | None = None, **kwargs) -> GeoDataFrame:
        """
        Download spatial data from DuckDB.

        Args:
            table_name: Source table name
            crs: Optional output CRS. Omit to preserve the source CRS.
            **kwargs: Additional parameters. Reads accept source_crs for
                legacy tables without source table metadata.

        Returns:
            GeoDataFrame retaining the stored source CRS. Legacy WKT tables
            without table metadata have unknown CRS unless
            source_crs is supplied. Empty tables retain their CRS. Pass crs to
            reproject from the known source to a different target.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails.
        """
        if not self.connection:
            self.connect()

        from siege_utilities.core.sql_safety import (
            validate_sql_identifier,
            validate_sql_fragment,
        )
        validate_sql_identifier(table_name, "table name")

        try:
            query = f"SELECT * FROM {table_name}"
            where_clause = kwargs.get('where_clause')
            if where_clause:
                validate_sql_fragment(where_clause, "where_clause")
                query += f" WHERE {where_clause}"

            # Execute query
            df = self.connection.execute(query).df()

            _, stored = _duckdb_table_metadata(self.connection, table_name)
            gdf = _duckdb_result_frame(
                df, source_crs=kwargs.get('source_crs'), crs=crs, stored_crs=stored or [],
            )
            log.info(f"Successfully downloaded from DuckDB: {table_name}")
            return gdf

        except (_DuckDBError, _ShapelyError, _CRSError, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
            raise SpatialQueryError(f"DuckDB download failed for {table_name}: {e}") from e
    
    def execute_spatial_query(self, query: str, *, crs: str | None = None, **kwargs) -> Union[GeoDataFrame, int]:
        """
        Execute a spatial SQL query.

        Row-returning statements, including CTEs and DML with RETURNING,
        produce a GeoDataFrame (without active geometry for tabular results).
        Other statements return an affected-row count, or -1 if unavailable.
        Mutating calls own a transaction through result validation. They require
        a connection without an active transaction; nested transactions are
        unsupported by DuckDB. SELECT calls do not finalize transactions.
        WKT results assume EPSG:4326, matching develop. Pass crs to reproject.
        Use download_spatial_data to attach a named table's stored CRS.

        Args:
            query: SQL query string
            crs: Output CRS. WKT results start with an EPSG:4326 label.
            **kwargs: Additional parameters.

        Returns:
            GeoDataFrame for row-returning queries, int rowcount for others.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails. The original exception is chained as
                ``__cause__``.
        """
        if not self.connection:
            self.connect()

        transaction_started = False
        try:
            import duckdb
            from siege_utilities.engines.dataframe_engine import DuckDBEngine

            # Result shape and transaction ownership are separate decisions.
            engine = DuckDBEngine()
            engine._conn = self.connection
            statements = self.connection.extract_statements(query)
            if any(statement.type != duckdb.StatementType.SELECT for statement in statements):
                # Two autocommit reads have distinct transaction IDs. Refuse
                # caller-owned transactions before BEGIN can abort one.
                first_id = self.connection.execute("SELECT current_transaction_id()").fetchone()[0]
                second_id = self.connection.execute("SELECT current_transaction_id()").fetchone()[0]
                if first_id == second_id:
                    raise ValueError("Mutating queries require a connection without an active transaction")
                self.connection.execute("BEGIN TRANSACTION")
                transaction_started = True
            for statement in statements[:-1]:
                self.connection.execute(statement)
            statement = statements[-1] if statements else None
            returns_rows = statement is not None and engine._statement_returns_rows(statement)
            result = self.connection.execute(statement if statement is not None else query)
            if returns_rows:
                result = _duckdb_query_frame(result.df(), crs=crs)
            else:
                try:
                    row = result.fetchone()
                    result = row[0] if row is not None else -1
                except (_DuckDBError, TypeError):
                    result = -1
            if transaction_started:
                self.connection.execute("COMMIT")
                transaction_started = False
            log.info("Successfully executed DuckDB query")
            return result

        except Exception as e:
            # Every failure before commit must undo owned writes, including
            # errors raised by result conversion or metadata validation.
            if transaction_started:
                try:
                    self.connection.execute("ROLLBACK")
                except _DuckDBError as rollback_error:
                    e.add_note(f"DuckDB rollback also failed: {rollback_error}")
            log.error(f"Failed to execute DuckDB query: {e}")
            raise SpatialQueryError(f"DuckDB query failed: {e}") from e


# Convenience functions
def convert_spatial_format(gdf: GeoDataFrame, output_format: str, **kwargs) -> None:
    """Convert spatial data to different format.

    Args:
        gdf: Input GeoDataFrame.
        output_format: Target format (``'shp'``, ``'geojson'``, ``'gpkg'``,
            ``'kml'``, ``'gml'``, ``'wkt'``, ``'wkb'``, ``'postgis'``,
            ``'duckdb'``).
        **kwargs: Format-specific parameters:
            output_path (str): Output file path (default varies by format).
            db_path (str): DuckDB database path (``'duckdb'`` format only).
            table_name (str): DuckDB table name (``'duckdb'`` format only,
                default ``'spatial_data'``).

    Raises:
        ValueError: If *output_format* is unsupported.
        ImportError: If a required dependency is not available.
    """
    transformer = SpatialDataTransformer()
    transformer.convert_format(gdf, output_format, **kwargs)


def upload_to_postgis(gdf: GeoDataFrame, table_name: str, connection_string: Optional[str] = None, **kwargs) -> None:
    """Upload spatial data to PostGIS.

    Args:
        gdf: GeoDataFrame to upload.
        table_name: Target table name.
        connection_string: PostgreSQL connection string (uses user config
            when omitted).
        **kwargs: Forwarded to
            :meth:`PostGISConnector.upload_spatial_data`. Accepts
            ``if_exists`` (``'fail'``, ``'replace'``, ``'append'``;
            default ``'fail'``) and ``schema`` (default ``'public'``).

    Raises:
        RuntimeError: If no connection string is configured.
        ImportError: If geoalchemy2 is not available.
        SpatialQueryError: If the upload fails.
    """
    with PostGISConnector(connection_string) as connector:
        connector.upload_spatial_data(gdf, table_name, **kwargs)


def download_from_postgis(table_name: str, connection_string: Optional[str] = None, **kwargs) -> GeoDataFrame:
    """Download spatial data from PostGIS.

    Args:
        table_name: Source table name (may be schema-qualified, e.g.
            ``'public.my_table'``).
        connection_string: PostgreSQL connection string (uses user config
            when omitted).
        **kwargs: Forwarded to
            :meth:`PostGISConnector.download_spatial_data`. Accepts
            ``geom_col`` (default ``'geom'``) and ``crs`` (output CRS).

    Returns:
        GeoDataFrame with spatial data.

    Raises:
        SpatialQueryError: If the connection is unavailable or the
            query fails.
    """
    with PostGISConnector(connection_string) as connector:
        return connector.download_spatial_data(table_name, **kwargs)


def execute_postgis_query(query: str, connection_string: Optional[str] = None, **kwargs) -> Union[GeoDataFrame, int]:
    """Execute a spatial SQL query on PostGIS.

    Args:
        query: SQL query string.
        connection_string: PostgreSQL connection string (uses user config
            when omitted).
        **kwargs: Forwarded to
            :meth:`PostGISConnector.execute_spatial_query`. Accepts
            ``geom_col`` (default ``'geometry'``) and ``crs`` (output CRS,
            applies to row-returning queries).

    Returns:
        GeoDataFrame for row-returning queries, int rowcount for others.

    Raises:
        SpatialQueryError: If the connection is unavailable or the
            query fails.
    """
    with PostGISConnector(connection_string) as connector:
        return connector.execute_spatial_query(query, **kwargs)


def upload_to_duckdb(gdf: GeoDataFrame, table_name: str, db_path: Optional[str] = None, **kwargs) -> None:
    """Upload spatial data to DuckDB (optional).

    Args:
        gdf: GeoDataFrame to upload.
        table_name: Target table name.
        db_path: Path to DuckDB database file (uses user config or
            in-memory when omitted).
        **kwargs: Forwarded to
            :meth:`DuckDBConnector.upload_spatial_data`. Accepts
            ``if_exists`` (``'fail'`` by default; ``'replace'`` or ``'append'``).

    Raises:
        ImportError: If DuckDB is not installed.
        RuntimeError: If upload fails.
    """
    if not DUCKDB_AVAILABLE:
        raise ImportError("DuckDB not available. Install with: pip install duckdb")

    with DuckDBConnector(db_path) as connector:
        connector.upload_spatial_data(gdf, table_name, **kwargs)


def download_from_duckdb(table_name: str, db_path: Optional[str] = None, **kwargs) -> GeoDataFrame:
    """Download spatial data from DuckDB (optional).

    Args:
        table_name: Source table name.
        db_path: Path to DuckDB database file (uses user config or
            in-memory when omitted).
        **kwargs: Forwarded to
            :meth:`DuckDBConnector.download_spatial_data`. Accepts
            ``where_clause`` (optional SQL WHERE fragment) and ``crs``
            (output CRS). ``source_crs`` supplies missing source metadata
            for legacy tables or empty results. Without ``crs``, the
            source CRS is preserved.

    Returns:
        GeoDataFrame with spatial data.

    Raises:
        SpatialQueryError: If the connection is unavailable or the
            query fails.
        ImportError: If DuckDB is not installed.
    """
    if not DUCKDB_AVAILABLE:
        raise ImportError("DuckDB not available. Install with: pip install duckdb")

    with DuckDBConnector(db_path) as connector:
        return connector.download_spatial_data(table_name, **kwargs)


def execute_duckdb_query(query: str, db_path: Optional[str] = None, **kwargs) -> Union[GeoDataFrame, int]:
    """Execute a spatial SQL query on DuckDB (optional).

    Args:
        query: SQL query string.
        db_path: Path to DuckDB database file (uses user config or
            in-memory when omitted).
        **kwargs: Forwarded to
            :meth:`DuckDBConnector.execute_spatial_query`. Accepts
            ``crs`` (output CRS, applies to row-returning queries). WKT
            results assume EPSG:4326. Use download_from_duckdb for stored
            table CRS metadata.

    Returns:
        GeoDataFrame for row-returning queries, int rowcount for others.

    Raises:
        SpatialQueryError: If the connection is unavailable or the
            query fails.
        ImportError: If DuckDB is not installed.
    """
    if not DUCKDB_AVAILABLE:
        raise ImportError("DuckDB not available. Install with: pip install duckdb")

    with DuckDBConnector(db_path) as connector:
        return connector.execute_spatial_query(query, **kwargs)


__all__ = [
    'SpatialQueryError',
    'SpatialDataTransformer',
    'PostGISConnector',
    'DuckDBConnector',
    'convert_spatial_format',
    'upload_to_postgis',
    'download_from_postgis',
    'execute_postgis_query',
    'upload_to_duckdb',
    'download_from_duckdb',
    'execute_duckdb_query',
    'DUCKDB_AVAILABLE'
]
