"""
Spatial data transformation utilities for siege_utilities.
Provides format conversion and transformation capabilities using the core geospatial stack.
DuckDB support is included but optional for enhanced performance on large datasets.
"""

import logging
from pathlib import Path

try:
    import geopandas as gpd
    _GEOPANDAS_AVAILABLE = True
except ImportError:
    gpd = None
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
        try:
            self.user_config = get_user_config()
        except (ImportError, OSError, ValueError, KeyError, AttributeError) as e:
            log.warning(f"Failed to load user config: {e}")
            # Use None (not {}) so callers branching on `is None` work
            # uniformly across SpatialDataTransformer / PostGISConnector
            # / DuckDBConnector. {} would silently AttributeError on
            # .get_database_connection() in the converters.
            self.user_config = None


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
        gdf.to_file(output_path, driver='ESRI Shapefile')
        log.info(f"Successfully converted to Shapefile: {output_path}")

    def _convert_to_geojson(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to GeoJSON format."""
        output_path = kwargs.get('output_path', 'output.geojson')
        gdf.to_file(output_path, driver='GeoJSON')
        log.info(f"Successfully converted to GeoJSON: {output_path}")

    def _convert_to_geopackage(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to GeoPackage format."""
        output_path = kwargs.get('output_path', 'output.gpkg')
        gdf.to_file(output_path, driver='GPKG')
        log.info(f"Successfully converted to GeoPackage: {output_path}")

    def _convert_to_kml(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to KML format."""
        output_path = kwargs.get('output_path', 'output.kml')
        gdf.to_file(output_path, driver='KML')
        log.info(f"Successfully converted to KML: {output_path}")

    def _convert_to_gml(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to GML format."""
        output_path = kwargs.get('output_path', 'output.gml')
        gdf.to_file(output_path, driver='GML')
        log.info(f"Successfully converted to GML: {output_path}")

    def _convert_to_wkt(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to WKT (Well-Known Text) format."""
        output_path = kwargs.get('output_path', 'output.wkt')
        wkt_data = gdf.copy()
        wkt_data['geometry'] = wkt_data.geometry.astype(str)
        wkt_data.to_csv(output_path, index=False)
        log.info(f"Successfully converted to WKT: {output_path}")

    def _convert_to_wkb(self, gdf: GeoDataFrame, **kwargs) -> None:
        """Convert to WKB (Well-Known Binary) format."""
        output_path = kwargs.get('output_path', 'output.wkb')
        wkb_data = gdf.copy()
        wkb_data['geometry'] = wkb_data.geometry.apply(lambda geom: geom.wkb)
        wkb_data.to_pickle(output_path)
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

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_lines))

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
                the user-config; if that's unavailable too, the connector
                stays uninitialized (``self.connection is None``).
        """
        try:
            self.user_config = get_user_config()
        except (ImportError, OSError, ValueError, KeyError, AttributeError) as e:
            log.warning(f"Failed to load user config: {e}")
            self.user_config = None

        if connection_string is None and self.user_config is not None:
            try:
                connection_string = self.user_config.get_database_connection('postgresql')
            except (AttributeError, ValueError, KeyError, TypeError) as e:
                log.warning(f"user_config.get_database_connection('postgresql') failed: {e}")
                connection_string = None
        self.connection_string = connection_string

        self.psycopg2 = None
        self.connection = None
        if self.connection_string is None:
            log.error("PostGISConnector: no connection_string and none configured")
            return

        try:
            import psycopg2
            self.psycopg2 = psycopg2
            self.connection = psycopg2.connect(self.connection_string)
            log.info("Successfully connected to PostGIS")
        except ImportError:
            log.error("psycopg2 not available. Install with: pip install psycopg2-binary")
        except (_Psycopg2Error, OSError) as e:
            log.error(f"Failed to connect to PostGIS: {e}")

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
                if_exists: How to handle existing table -- ``'fail'``,
                    ``'replace'`` (default), or ``'append'``.
                schema: PostgreSQL schema name (default ``'public'``).

        Raises:
            RuntimeError: If no connection string is configured
            ImportError: If geoalchemy2 is not available
            SpatialQueryError: If the upload fails
        """
        if not self.connection_string:
            raise RuntimeError("No PostGIS connection_string available")

        if_exists = kwargs.get('if_exists', 'replace')
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
                gdf.to_postgis(
                    name=table_name,
                    con=engine,
                    schema=schema,
                    if_exists=if_exists,
                )
            finally:
                engine.dispose()
            log.info(
                f"Successfully uploaded to PostGIS table: {schema}.{table_name} "
                f"({len(gdf)} rows, {len(gdf.columns)} columns)"
            )

        except (_Psycopg2Error, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
            raise SpatialQueryError(f"Failed to upload to PostGIS: {e}") from e
    
    def download_spatial_data(self, table_name: str, *, crs: str | None = None, **kwargs) -> GeoDataFrame:
        """
        Download spatial data from PostGIS.

        Args:
            table_name: Source table name
            crs: Output CRS. Defaults to
                :func:`~siege_utilities.geo.crs.get_default_crs`.
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
            return reproject_if_needed(gdf, crs)

        except (_Psycopg2Error, OSError, ValueError, TypeError, AttributeError, KeyError) as e:
            raise SpatialQueryError(f"PostGIS download failed for {table_name}: {e}") from e
    
    def execute_spatial_query(self, query: str, *, crs: str | None = None, **kwargs) -> Union[GeoDataFrame, int]:
        """
        Execute a spatial SQL query.

        For SELECT queries the result is a :class:`GeoDataFrame`.
        For non-SELECT queries (INSERT, UPDATE, DELETE, DDL) the result
        is the ``cursor.rowcount`` integer (``-1`` when the row count
        is not determinable, e.g. DDL).

        Args:
            query: SQL query string
            crs: Output CRS. Defaults to
                :func:`~siege_utilities.geo.crs.get_default_crs`.
            **kwargs: Additional parameters

        Returns:
            GeoDataFrame for SELECT queries, int rowcount for others.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails. The original exception is chained as
                ``__cause__``.
        """
        from siege_utilities.geo.crs import reproject_if_needed

        if not self.connection:
            raise SpatialQueryError("No PostGIS connection available")

        if query.strip().upper().startswith('SELECT'):
            try:
                geom_col = kwargs.get('geom_col', 'geometry')
                # gpd.read_postgis decodes WKB and reads SRID from the
                # geometry column. The previous manual-fetch path
                # returned raw bytes in the geometry column, which
                # silently produced a non-geo frame.
                gdf = gpd.read_postgis(query, self.connection, geom_col=geom_col)
                log.info("Successfully executed PostGIS query")
                return reproject_if_needed(gdf, crs)
            except (_Psycopg2Error, OSError, ValueError, TypeError, AttributeError) as e:
                # read_postgis raises sqlalchemy / pandas / geopandas
                # exceptions depending on the failure mode; catch broadly
                # and roll back so the psycopg2 connection is not left in
                # an aborted-transaction state for subsequent calls.
                log.error(f"Failed to execute PostGIS query: {e}")
                if self.connection:
                    try:
                        self.connection.rollback()
                    except (_Psycopg2Error, OSError) as rb_exc:
                        log.warning("Failed to rollback PostGIS transaction: %s", rb_exc)
                raise SpatialQueryError(f"PostGIS query failed: {e}") from e

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            rowcount = cursor.rowcount
            log.info("Successfully executed PostGIS query")
            return rowcount
        except (_Psycopg2Error, OSError, ValueError, TypeError, AttributeError) as e:
            log.error(f"Failed to execute PostGIS query: {e}")
            if self.connection:
                try:
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
        
        try:
            self.user_config = get_user_config()
        except (ImportError, OSError, ValueError, KeyError, AttributeError) as e:
            log.warning(f"Failed to load user config: {e}")
            self.user_config = None

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
        except (_DuckDBError, OSError) as e:
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
        Upload spatial data to DuckDB.

        Args:
            gdf: GeoDataFrame to upload
            table_name: Target table name
            **kwargs: Additional parameters

        Raises:
            RuntimeError: If connection or upload fails
        """
        if not self.connection:
            self.connect()

        from siege_utilities.core.sql_safety import validate_sql_identifier
        validate_sql_identifier(table_name, "table name")

        try:
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: geom.wkt)
            df = df.drop(columns=['geometry'])

            if_exists = kwargs.get('if_exists', 'replace')
            if if_exists == 'replace':
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")

            self.connection.register("siege_upload_df", df)
            try:
                self.connection.execute(
                    f"CREATE TABLE {table_name} AS SELECT * FROM siege_upload_df"
                )
            finally:
                try:
                    self.connection.unregister("siege_upload_df")
                except (_DuckDBError, RuntimeError) as cleanup_exc:
                    log.warning(
                        "Failed to unregister siege_upload_df: %s",
                        cleanup_exc,
                    )

            log.info(f"Successfully uploaded to DuckDB: {table_name}")

        except (_DuckDBError, OSError, ValueError, TypeError, AttributeError) as e:
            raise RuntimeError(f"Failed to upload to DuckDB: {e}") from e
    
    def download_spatial_data(self, table_name: str, *, crs: str | None = None, **kwargs) -> GeoDataFrame:
        """
        Download spatial data from DuckDB.

        Args:
            table_name: Source table name
            crs: Output CRS. Defaults to
                :func:`~siege_utilities.geo.crs.get_default_crs`.
            **kwargs: Additional parameters

        Returns:
            GeoDataFrame with spatial data.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails.
        """
        from siege_utilities.geo.crs import reproject_if_needed

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

            # Convert WKT back to geometries
            if 'geometry_wkt' in df.columns:
                from shapely import wkt
                df['geometry'] = df['geometry_wkt'].apply(wkt.loads)
                df = df.drop(columns=['geometry_wkt'])

            # WKT does not carry SRID metadata.  Assume WGS84 as the
            # storage CRS, then reproject to the caller's target CRS if
            # one was specified.  If the data was actually stored in a
            # different CRS the coordinates will be wrong — there is no
            # way to recover the SRID from bare WKT.
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
            if crs is None:
                log.warning(
                    "DuckDB WKT geometries lack SRID metadata; assuming "
                    "EPSG:4326.  Pass crs= to reproject to a target CRS."
                )

            log.info(f"Successfully downloaded from DuckDB: {table_name}")
            return reproject_if_needed(gdf, crs)

        except (_DuckDBError, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
            raise SpatialQueryError(f"DuckDB download failed for {table_name}: {e}") from e
    
    def execute_spatial_query(self, query: str, *, crs: str | None = None, **kwargs) -> Union[GeoDataFrame, int]:
        """
        Execute a spatial SQL query.

        For SELECT queries the result is a :class:`GeoDataFrame`.
        For non-SELECT queries (INSERT, UPDATE, DELETE, DDL) the result
        is the ``cursor.rowcount`` integer (``-1`` when the row count
        is not determinable, e.g. DDL).

        Args:
            query: SQL query string
            crs: Output CRS. Defaults to
                :func:`~siege_utilities.geo.crs.get_default_crs`.
            **kwargs: Additional parameters

        Returns:
            GeoDataFrame for SELECT queries, int rowcount for others.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails. The original exception is chained as
                ``__cause__``.
        """
        from siege_utilities.geo.crs import reproject_if_needed

        if not self.connection:
            self.connect()

        try:
            if query.strip().upper().startswith('SELECT'):
                df = self.connection.execute(query).df()

                if 'geometry_wkt' in df.columns:
                    from shapely import wkt
                    df['geometry'] = df['geometry_wkt'].apply(wkt.loads)
                    df = df.drop(columns=['geometry_wkt'])

                gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                if crs is None:
                    log.warning(
                        "DuckDB WKT geometries lack SRID metadata; assuming "
                        "EPSG:4326.  Pass crs= to reproject to a target CRS."
                    )

                log.info("Successfully executed DuckDB query")
                return reproject_if_needed(gdf, crs)

            result = self.connection.execute(query)
            try:
                row = result.fetchone()
                rowcount = row[0] if row is not None else -1
            except (_DuckDBError, TypeError):
                rowcount = -1
            log.info("Successfully executed DuckDB query")
            return rowcount

        except (_DuckDBError, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
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
            default ``'replace'``) and ``schema`` (default ``'public'``).

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
            applies to SELECT queries only).

    Returns:
        GeoDataFrame for SELECT queries, int rowcount for others.

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
            ``if_exists`` (``'replace'`` by default).

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
            (output CRS).

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
            ``crs`` (output CRS, applies to SELECT queries only).

    Returns:
        GeoDataFrame for SELECT queries, int rowcount for others.

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
