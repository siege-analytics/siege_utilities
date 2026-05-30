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
    
    def convert_format(self, gdf: GeoDataFrame, output_format: str, **kwargs) -> bool:
        """
        Convert GeoDataFrame to different format.
        
        Args:
            gdf: Input GeoDataFrame
            output_format: Desired output format
            **kwargs: Additional format-specific parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if output_format == 'shp':
                return self._convert_to_shapefile(gdf, **kwargs)
            elif output_format == 'geojson':
                return self._convert_to_geojson(gdf, **kwargs)
            elif output_format == 'gpkg':
                return self._convert_to_geopackage(gdf, **kwargs)
            elif output_format == 'kml':
                return self._convert_to_kml(gdf, **kwargs)
            elif output_format == 'gml':
                return self._convert_to_gml(gdf, **kwargs)
            elif output_format == 'wkt':
                return self._convert_to_wkt(gdf, **kwargs)
            elif output_format == 'wkb':
                return self._convert_to_wkb(gdf, **kwargs)
            elif output_format == 'postgis':
                return self._convert_to_postgis(gdf, **kwargs)
            elif output_format == 'duckdb':
                if DUCKDB_AVAILABLE:
                    return self._convert_to_duckdb(gdf, **kwargs)
                else:
                    log.error("DuckDB not available. Install with: pip install duckdb")
                    return False
            else:
                log.error(f"Unsupported output format: {output_format}")
                return False
                
        except (OSError, ValueError, TypeError, AttributeError, KeyError, ImportError) as e:
            log.error(f"Format conversion failed: {e}")
            return False
    
    def _convert_to_shapefile(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to ESRI Shapefile format."""
        try:
            output_path = kwargs.get('output_path', 'output.shp')
            gdf.to_file(output_path, driver='ESRI Shapefile')
            log.info(f"Successfully converted to Shapefile: {output_path}")
            return True
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            log.error(f"Failed to convert to Shapefile: {e}")
            return False
    
    def _convert_to_geojson(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to GeoJSON format."""
        try:
            output_path = kwargs.get('output_path', 'output.geojson')
            gdf.to_file(output_path, driver='GeoJSON')
            log.info(f"Successfully converted to GeoJSON: {output_path}")
            return True
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            log.error(f"Failed to convert to GeoJSON: {e}")
            return False
    
    def _convert_to_geopackage(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to GeoPackage format."""
        try:
            output_path = kwargs.get('output_path', 'output.gpkg')
            gdf.to_file(output_path, driver='GPKG')
            log.info(f"Successfully converted to GeoPackage: {output_path}")
            return True
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            log.error(f"Failed to convert to GeoPackage: {e}")
            return False
    
    def _convert_to_kml(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to KML format."""
        try:
            output_path = kwargs.get('output_path', 'output.kml')
            gdf.to_file(output_path, driver='KML')
            log.info(f"Successfully converted to KML: {output_path}")
            return True
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            log.error(f"Failed to convert to KML: {e}")
            return False
    
    def _convert_to_gml(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to GML format."""
        try:
            output_path = kwargs.get('output_path', 'output.gml')
            gdf.to_file(output_path, driver='GML')
            log.info(f"Successfully converted to GML: {output_path}")
            return True
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            log.error(f"Failed to convert to GML: {e}")
            return False
    
    def _convert_to_wkt(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to WKT (Well-Known Text) format."""
        try:
            output_path = kwargs.get('output_path', 'output.wkt')
            
            # Convert geometries to WKT strings
            wkt_data = gdf.copy()
            wkt_data['geometry'] = wkt_data.geometry.astype(str)
            
            # Save as CSV with WKT geometries
            wkt_data.to_csv(output_path, index=False)
            log.info(f"Successfully converted to WKT: {output_path}")
            return True
        except (OSError, ValueError, TypeError, AttributeError) as e:
            log.error(f"Failed to convert to WKT: {e}")
            return False
    
    def _convert_to_wkb(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to WKB (Well-Known Binary) format."""
        try:
            output_path = kwargs.get('output_path', 'output.wkb')
            
            # Convert geometries to WKB bytes
            wkb_data = gdf.copy()
            wkb_data['geometry'] = wkb_data.geometry.apply(lambda geom: geom.wkb)
            
            # Save as pickle (WKB is binary data)
            wkb_data.to_pickle(output_path)
            log.info(f"Successfully converted to WKB: {output_path}")
            return True
        except (OSError, ValueError, TypeError, AttributeError) as e:
            log.error(f"Failed to convert to WKB: {e}")
            return False
    
    def _convert_to_postgis(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to PostGIS format (upload to PostgreSQL database)."""
        try:
            # This would require psycopg2 and database connection
            # For now, just save as SQL file that can be imported
            output_path = kwargs.get('output_path', 'output.sql')
            
            # Generate SQL INSERT statements. WKT comes from shapely
            # which can't normally produce single quotes, but the file
            # is written for human inspection / re-import — escape
            # defensively so a hand-edited row can't break out of the
            # literal.
            from siege_utilities.core.sql_safety import escape_sql_string_literal as escape_string_literal
            # Vectorised: pull the geometry column into a Series of WKT
            # strings in one pass and join with newlines. The previous
            # row-at-a-time iterrows produced O(N) Python-level
            # attribute lookups; on a 100K-row state file that was
            # measurably slower than the IO it bookended.
            wkt_series = gdf.geometry.apply(lambda g: escape_string_literal(g.wkt))
            sql_lines = (
                "INSERT INTO spatial_table (geom) VALUES (ST_GeomFromText('"
                + wkt_series
                + "'));"
            )

            with open(output_path, 'w') as f:
                f.write('\n'.join(sql_lines))
            
            log.info(f"Successfully generated PostGIS SQL: {output_path}")
            return True
        except (OSError, ValueError, TypeError, AttributeError, ImportError) as e:
            log.error(f"Failed to convert to PostGIS: {e}")
            return False
    
    def _convert_to_duckdb(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to DuckDB format and save to database."""
        if not DUCKDB_AVAILABLE:
            log.error("DuckDB not available")
            return False
            
        try:
            # Get database parameters from user config or kwargs.
            db_path = kwargs.get('db_path')
            if db_path is None and self.user_config is not None:
                try:
                    db_path = self.user_config.get_database_connection('duckdb')
                except (AttributeError, ValueError, KeyError, TypeError) as e:
                    log.warning(f"user_config.get_database_connection('duckdb') failed: {e}")
            db_path = db_path or ':memory:'
            table_name = kwargs.get('table_name', 'spatial_data')

            # DuckDB doesn't permit parameter-bound identifiers, so the
            # table name has to be validated up front.
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
            return True

        except (_DuckDBError, OSError, ValueError, TypeError, AttributeError, KeyError) as e:
            log.error(f"Failed to convert to DuckDB: {e}")
            return False


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

    def upload_spatial_data(self, gdf: GeoDataFrame, table_name: str, **kwargs) -> bool:
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

        Returns:
            True if successful, False otherwise.

        Note:
            Requires ``geoalchemy2`` (declared in the ``geo`` optional
            extra). If missing, the import error is logged and the
            upload returns False with a clear remediation hint.
        """
        if not self.connection_string:
            log.error("No PostGIS connection_string available")
            return False

        if_exists = kwargs.get('if_exists', 'replace')
        schema = kwargs.get('schema', 'public')

        # Validate identifiers before they reach SQL. to_postgis itself
        # uses parameterized SQL but defense-in-depth keeps the validation
        # consistent with download_spatial_data + the prior implementation.
        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        validate_identifier(schema, label="schema name", allow_dotted=False)
        validate_identifier(table_name, label="table name", allow_dotted=False)

        try:
            import geoalchemy2  # noqa: F401  -- presence-check; to_postgis needs it
        except ImportError:
            log.error(
                "geoalchemy2 not available -- upload_spatial_data requires it "
                "for full-column writes. Install with: pip install 'siege_utilities[geo]'"
            )
            return False

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
            return True

        except (_Psycopg2Error, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
            log.error(f"Failed to upload to PostGIS: {e}")
            return False
    
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
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = duckdb.connect(self.db_path)
            log.info("Successfully connected to DuckDB")
            return True
        except (_DuckDBError, OSError) as e:
            log.error(f"Failed to connect to DuckDB: {e}")
            return False

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

    def upload_spatial_data(self, gdf: GeoDataFrame, table_name: str, **kwargs) -> bool:
        """
        Upload spatial data to DuckDB.
        
        Args:
            gdf: GeoDataFrame to upload
            table_name: Target table name
            **kwargs: Additional parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connection:
            if not self.connect():
                return False
        
        from siege_utilities.core.sql_safety import validate_sql_identifier
        validate_sql_identifier(table_name, "table name")

        try:
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: geom.wkt)
            df = df.drop(columns=['geometry'])

            if_exists = kwargs.get('if_exists', 'replace')
            if if_exists == 'replace':
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")

            # table_name validated above; pin the DataFrame under an
            # explicit name rather than relying on duckdb's replacement
            # scan picking it up from the caller frame.
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
            return True

        except (_DuckDBError, OSError, ValueError, TypeError, AttributeError) as e:
            log.error(f"Failed to upload to DuckDB: {e}")
            return False
    
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
            if not self.connect():
                raise SpatialQueryError("No DuckDB connection available")

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

            # Create GeoDataFrame — default to WGS84 since WKT lacks SRID
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

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
            if not self.connect():
                raise SpatialQueryError("No DuckDB connection available")

        try:
            if query.strip().upper().startswith('SELECT'):
                df = self.connection.execute(query).df()

                if 'geometry_wkt' in df.columns:
                    from shapely import wkt
                    df['geometry'] = df['geometry_wkt'].apply(wkt.loads)
                    df = df.drop(columns=['geometry_wkt'])

                # Default to WGS84 since WKT lacks SRID metadata
                gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

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
def convert_spatial_format(gdf: GeoDataFrame, output_format: str, **kwargs) -> bool:
    """Convert spatial data to different format."""
    transformer = SpatialDataTransformer()
    return transformer.convert_format(gdf, output_format, **kwargs)


def upload_to_postgis(gdf: GeoDataFrame, table_name: str, connection_string: Optional[str] = None, **kwargs) -> bool:
    """Upload spatial data to PostGIS."""
    with PostGISConnector(connection_string) as connector:
        return connector.upload_spatial_data(gdf, table_name, **kwargs)


def download_from_postgis(table_name: str, connection_string: Optional[str] = None, **kwargs) -> GeoDataFrame:
    """Download spatial data from PostGIS.

    Raises:
        SpatialQueryError: If the connection is unavailable or the
            query fails.
    """
    with PostGISConnector(connection_string) as connector:
        return connector.download_spatial_data(table_name, **kwargs)


def execute_postgis_query(query: str, connection_string: Optional[str] = None, **kwargs) -> Union[GeoDataFrame, int]:
    """Execute a spatial SQL query on PostGIS.

    Raises:
        SpatialQueryError: If the connection is unavailable or the
            query fails.
    """
    with PostGISConnector(connection_string) as connector:
        return connector.execute_spatial_query(query, **kwargs)


def upload_to_duckdb(gdf: GeoDataFrame, table_name: str, db_path: Optional[str] = None, **kwargs) -> bool:
    """Upload spatial data to DuckDB (optional).

    Raises:
        ImportError: If DuckDB is not installed.
    """
    if not DUCKDB_AVAILABLE:
        raise ImportError("DuckDB not available. Install with: pip install duckdb")

    with DuckDBConnector(db_path) as connector:
        return connector.upload_spatial_data(gdf, table_name, **kwargs)


def download_from_duckdb(table_name: str, db_path: Optional[str] = None, **kwargs) -> GeoDataFrame:
    """Download spatial data from DuckDB (optional).

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
