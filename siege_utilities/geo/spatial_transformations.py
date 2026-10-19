"""
Spatial data transformation utilities for siege_utilities.
Provides format conversion and transformation capabilities using the core geospatial stack.
DuckDB support is included but optional for enhanced performance on large datasets.
"""

import logging
from pathlib import Path

try:
    import geopandas as gpd
    from shapely.errors import ShapelyError as _ShapelyError
    _GEOPANDAS_AVAILABLE = True
except ImportError:
    gpd = None
    _ShapelyError = ValueError
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

        Row-returning statements, including CTEs and DML with RETURNING,
        produce a GeoDataFrame (without active geometry for tabular results).
        Other statements return an affected-row count, or -1 if unavailable.

        Args:
            query: SQL query string
            crs: Output CRS. Defaults to
                :func:`~siege_utilities.geo.crs.get_default_crs`.
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

        cursor = None
        try:
            cursor = self.connection.cursor()
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
                        result = result.set_crs(epsg=srid)
                    result = reproject_if_needed(result, crs)
            else:
                result = cursor.rowcount
            self.connection.commit()
            log.info("Successfully executed PostGIS query")
            return result
        except (_Psycopg2Error, _ShapelyError, OSError, ValueError, TypeError, AttributeError) as e:
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


def _duckdb_result_frame(df, *, source_crs=None, crs=None):
    """Decode stored WKT and CRS without guessing missing source metadata."""
    from pyproj import CRS

    source = CRS.from_user_input(source_crs) if source_crs is not None else None
    if '_siege_crs' in df.columns:
        metadata = df.pop('_siege_crs')
        known = {CRS.from_user_input(value) for value in metadata.dropna().unique()}
        if len(known) > 1 or (source is not None and any(value != source for value in known)):
            raise ValueError("Result contains conflicting source CRSs")
        if source is None and known:
            if metadata.isna().any():
                raise ValueError("Result mixes known and unknown CRSs; provide source_crs")
            source = next(iter(known))
    if 'geometry_wkt' in df.columns:
        df['geometry'] = gpd.GeoSeries.from_wkt(df.pop('geometry_wkt'), index=df.index)
    if 'geometry' not in df.columns:
        return gpd.GeoDataFrame(df)
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=source)
    if crs is not None:
        if source is None:
            raise ValueError("Source CRS is unknown; provide source_crs before reprojecting")
        return gdf.to_crs(crs)
    return gdf


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
                with full CRS WKT in the reserved _siege_crs column.
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
            if '_siege_crs' in gdf.columns or 'geometry_wkt' in gdf.columns:
                raise ValueError("_siege_crs and geometry_wkt are reserved storage columns")
            # WKT alone has no CRS. Keep full CRS WKT alongside each geometry
            # so SELECT/CTE/RETURNING results retain it across connections.
            df = gdf.to_wkt(rounding_precision=-1).rename(columns={gdf.geometry.name: 'geometry_wkt'})
            df['geometry_wkt'] = df['geometry_wkt'].astype('string')
            df['_siege_crs'] = gdf.crs.to_wkt() if gdf.crs is not None else None
            df['_siege_crs'] = df['_siege_crs'].astype('string')
            self.connection.register("siege_upload_df", df)
            try:
                self.connection.execute("BEGIN TRANSACTION")
                try:
                    if if_exists == 'replace':
                        self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                    if if_exists == 'append':
                        self.connection.execute(
                            f"CREATE TABLE IF NOT EXISTS {table_name} AS "
                            "SELECT * FROM siege_upload_df WHERE FALSE"
                        )
                        # Legacy tables lack metadata. Preserve their unknown
                        # CRS instead of assigning the incoming data's CRS.
                        self.connection.execute(
                            f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS _siege_crs VARCHAR"
                        )
                        from pyproj import CRS

                        stored = self.connection.execute(
                            f"SELECT DISTINCT _siege_crs FROM {table_name} "
                            "WHERE _siege_crs IS NOT NULL"
                        ).fetchall()
                        if any(CRS.from_user_input(value) != gdf.crs for (value,) in stored):
                            raise ValueError("Cannot append data with a different source CRS")
                        self.connection.execute(
                            f"INSERT INTO {table_name} BY NAME SELECT * FROM siege_upload_df"
                        )
                    else:
                        self.connection.execute(
                            f"CREATE TABLE {table_name} AS SELECT * FROM siege_upload_df"
                        )
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

        except (_DuckDBError, OSError, ValueError, TypeError, AttributeError) as e:
            raise RuntimeError(f"Failed to upload to DuckDB: {e}") from e

    def download_spatial_data(self, table_name: str, *, crs: str | None = None, **kwargs) -> GeoDataFrame:
        """
        Download spatial data from DuckDB.

        Args:
            table_name: Source table name
            crs: Optional output CRS. Omit to preserve the source CRS.
            **kwargs: Additional parameters. Reads accept source_crs for
                legacy tables, empty results, or projections without _siege_crs.

        Returns:
            GeoDataFrame retaining the stored source CRS. Legacy WKT tables
            and queries omitting _siege_crs have unknown CRS unless source_crs
            is supplied. Empty results also require source_crs. Pass crs to
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

            gdf = _duckdb_result_frame(df, source_crs=kwargs.get('source_crs'), crs=crs)
            log.info(f"Successfully downloaded from DuckDB: {table_name}")
            return gdf

        except (_DuckDBError, _ShapelyError, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
            raise SpatialQueryError(f"DuckDB download failed for {table_name}: {e}") from e
    
    def execute_spatial_query(self, query: str, *, crs: str | None = None, **kwargs) -> Union[GeoDataFrame, int]:
        """
        Execute a spatial SQL query.

        Row-returning statements, including CTEs and DML with RETURNING,
        produce a GeoDataFrame (without active geometry for tabular results).
        Other statements return an affected-row count, or -1 if unavailable.

        Args:
            query: SQL query string
            crs: Optional output CRS. Omit to preserve the source CRS.
            **kwargs: Additional parameters. Reads accept source_crs for
                legacy tables, empty results, or projections without _siege_crs.

        Returns:
            GeoDataFrame for row-returning queries, int rowcount for others.

        Raises:
            SpatialQueryError: If the connection is unavailable or the
                query fails. The original exception is chained as
                ``__cause__``.
        """
        if not self.connection:
            self.connect()

        try:
            from siege_utilities.engines.dataframe_engine import DuckDBEngine

            # DuckDB describes affected-row Counts as result columns too.
            # Reuse its parser-based classifier to distinguish those from rows.
            engine = DuckDBEngine()
            engine._conn = self.connection
            statements = self.connection.extract_statements(query)
            for statement in statements[:-1]:
                self.connection.execute(statement)
            statement = statements[-1] if statements else None
            returns_rows = statement is not None and engine._statement_returns_rows(statement)
            result = self.connection.execute(statement if statement is not None else query)
            if returns_rows:
                gdf = _duckdb_result_frame(
                    result.df(), source_crs=kwargs.get('source_crs'), crs=crs,
                )
                log.info("Successfully executed DuckDB query")
                return gdf

            try:
                row = result.fetchone()
                rowcount = row[0] if row is not None else -1
            except (_DuckDBError, TypeError):
                rowcount = -1
            log.info("Successfully executed DuckDB query")
            return rowcount

        except (_DuckDBError, _ShapelyError, OSError, ValueError, TypeError, AttributeError, ImportError) as e:
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
            ``crs`` (output CRS, applies to row-returning queries) and
            ``source_crs`` for missing metadata. Include ``_siege_crs``
            in spatial query projections to retain uploaded CRS metadata;
            otherwise supply ``source_crs``. Omit ``crs`` to keep the source.

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
