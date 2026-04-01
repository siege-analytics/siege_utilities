"""
Engine-agnostic DataFrame operations.

Provides a thin abstraction so the same analytical operations can run on
DuckDB, Spark, or PostGIS instead of only pandas/GeoPandas.

Usage::

    from siege_utilities.data.dataframe_engine import get_engine, Engine

    engine = get_engine(Engine.PANDAS)
    df = engine.read_csv("data.csv")
    result = engine.groupby_agg(df, ["state"], {"pop": "sum"})
    pdf = engine.to_pandas(result)

Each back-end uses lazy imports so the module itself never requires DuckDB,
PySpark, or SQLAlchemy/psycopg2 to be installed.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Engine enum
# ---------------------------------------------------------------------------

class Engine(enum.Enum):
    """Supported DataFrame engine back-ends."""
    PANDAS = "pandas"
    DUCKDB = "duckdb"
    SPARK = "spark"
    POSTGIS = "postgis"


# Convenience string constants (for callers who prefer plain strings).
PANDAS = Engine.PANDAS.value
DUCKDB = Engine.DUCKDB.value
SPARK = Engine.SPARK.value
POSTGIS = Engine.POSTGIS.value


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------

class DataFrameEngine(ABC):
    """Abstract base class for engine-agnostic DataFrame operations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the canonical engine name."""

    # -- I/O ----------------------------------------------------------------

    @abstractmethod
    def read_csv(self, path: str, **kwargs: Any) -> Any:
        """Read a CSV file and return a DataFrame-like object."""

    @abstractmethod
    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        """Read a Parquet file and return a DataFrame-like object."""

    # -- SQL ----------------------------------------------------------------

    @abstractmethod
    def query(self, sql: str, **kwargs: Any) -> Any:
        """Execute *sql* and return a DataFrame-like object.

        Back-end specific keyword arguments (e.g. ``table`` for DuckDB,
        ``connection`` for PostGIS) are passed through via *kwargs*.
        """

    # -- Transforms ---------------------------------------------------------

    @abstractmethod
    def to_pandas(self, df: Any) -> Any:
        """Convert *df* to a pandas DataFrame."""

    @abstractmethod
    def groupby_agg(
        self,
        df: Any,
        group_cols: Sequence[str],
        agg_dict: Dict[str, str],
    ) -> Any:
        """Group *df* by *group_cols* and aggregate according to *agg_dict*.

        *agg_dict* maps column names to aggregation function names
        (``"sum"``, ``"mean"``, ``"count"``, ``"min"``, ``"max"``).
        """

    @abstractmethod
    def filter(self, df: Any, condition: Any) -> Any:
        """Return rows of *df* that satisfy *condition*.

        The type of *condition* is engine-specific (boolean Series for
        pandas, SQL expression string for DuckDB/Spark, etc.).
        """

    @abstractmethod
    def join(
        self,
        left: Any,
        right: Any,
        on: Union[str, List[str]],
        how: str = "inner",
    ) -> Any:
        """Join *left* and *right* on column(s) *on* using join type *how*."""

    # -- Spatial I/O -------------------------------------------------------

    @abstractmethod
    def read_spatial(self, path: str, *, crs: Optional[str] = None, **kwargs: Any) -> Any:
        """Read a spatial file (GeoJSON, Shapefile, GeoParquet, GPKG).

        Returns an engine-native spatial DataFrame.  *crs* defaults to
        ``EPSG:4326`` (via ``geo.crs.get_default_crs``).
        """

    # -- Spatial operations ------------------------------------------------

    @abstractmethod
    def spatial_join(
        self,
        left: Any,
        right: Any,
        how: str = "inner",
        predicate: str = "intersects",
        *,
        left_geom: str = "geometry",
        right_geom: str = "geometry",
    ) -> Any:
        """Spatial join using a geometric predicate.

        *predicate* is one of: intersects, contains, within, touches,
        crosses, overlaps.
        """

    @abstractmethod
    def buffer(
        self,
        df: Any,
        distance: float,
        geometry_col: str = "geometry",
        *,
        crs: Optional[str] = None,
    ) -> Any:
        """Buffer geometries by *distance* (in CRS units).

        Returns a new DataFrame with the geometry column replaced by
        buffered geometries.
        """

    @abstractmethod
    def distance(
        self,
        df: Any,
        other: Any,
        geometry_col: str = "geometry",
        other_geom: str = "geometry",
    ) -> Any:
        """Compute distances between geometries.

        *other* may be a DataFrame (row-aligned pairwise) or a single
        geometry (shapely object / WKT string).
        """

    @abstractmethod
    def to_geodataframe(
        self, df: Any, geometry_col: str = "geometry", *, crs: Optional[str] = None,
    ) -> Any:
        """Convert *df* to a GeoPandas ``GeoDataFrame``.

        Always returns a ``geopandas.GeoDataFrame`` regardless of engine.
        """

    # -- Spatial sugar (concrete defaults) ---------------------------------

    def point_in_polygon(
        self,
        points_df: Any,
        polygons_df: Any,
        *,
        points_geom: str = "geometry",
        polygons_geom: str = "geometry",
    ) -> Any:
        """Find which polygon each point falls within.

        Delegates to :meth:`spatial_join` with ``predicate='within'``.
        """
        return self.spatial_join(
            points_df, polygons_df,
            how="inner", predicate="within",
            left_geom=points_geom, right_geom=polygons_geom,
        )

    def dissolve(
        self,
        df: Any,
        by: Union[str, List[str]],
        geometry_col: str = "geometry",
        **agg_kwargs: Any,
    ) -> Any:
        """Dissolve/merge geometries grouped by *by* columns.

        Default converts to GeoDataFrame and uses ``gdf.dissolve()``.
        Engines may override for native performance.
        """
        gdf = self.to_geodataframe(df, geometry_col=geometry_col)
        return gdf.dissolve(by=by, **agg_kwargs).reset_index()

    # -- Spatial geometry loading (concrete defaults) ----------------------

    def load_polygons(
        self,
        path: str,
        *,
        geometry_col: str = "geometry",
        format: str = "auto",
        crs: Optional[str] = None,
    ) -> Any:
        """Load polygon geometries from any supported spatial format.

        Handles GeoJSON, Shapefile, GeoParquet, GPKG, WKT CSV.
        Returns engine-native DataFrame with a geometry column.
        Engines may override for native loaders (e.g., Sedona, DuckDB spatial).
        """
        return self.read_spatial(path, crs=crs)

    def load_points(
        self,
        df: Any,
        lat_col: str = "lat",
        lon_col: str = "lon",
        geometry_col: str = "geometry",
    ) -> Any:
        """Create point geometries from latitude/longitude columns.

        Adds a ``geometry`` column with WKT POINT strings (or native
        geometry objects, depending on engine).
        Engines may override for native point construction.
        """
        # Default: convert to GeoDataFrame with shapely Points
        import pandas as pd
        pdf = self.to_pandas(df) if not isinstance(df, pd.DataFrame) else df
        from shapely.geometry import Point

        pdf = pdf.copy()
        pdf[geometry_col] = [
            Point(lon, lat) if pd.notna(lon) and pd.notna(lat) else None
            for lat, lon in zip(pdf[lat_col], pdf[lon_col])
        ]
        return pdf

    def load_lines(
        self,
        path: str,
        *,
        geometry_col: str = "geometry",
        format: str = "auto",
        crs: Optional[str] = None,
    ) -> Any:
        """Load line/multiline geometries from any supported spatial format.

        Same interface as :meth:`load_polygons` — works for roads, rivers,
        transit routes, or any linear feature.
        """
        return self.read_spatial(path, crs=crs)

    # -- Spatial boundary operations (concrete defaults) -------------------

    def assign_boundaries(
        self,
        points: Any,
        polygons: Any,
        *,
        point_geom: str = "geometry",
        polygon_geom: str = "geometry",
        how: str = "left",
    ) -> Any:
        """Assign each point to its containing polygon(s).

        Core DSTK replacement: given addresses (points) and boundaries
        (polygons), determine which boundary contains each address.

        Default delegates to :meth:`spatial_join` with predicate='contains'
        (reversed: polygon contains point). Engines may override for
        broadcast optimization or native spatial indexing.
        """
        return self.spatial_join(
            points, polygons,
            how=how, predicate="within",
            left_geom=point_geom, right_geom=polygon_geom,
        )

    def intersect_boundaries(
        self,
        poly_a: Any,
        poly_b: Any,
        *,
        a_geom: str = "geometry",
        b_geom: str = "geometry",
    ) -> Any:
        """Find overlapping regions between two polygon boundary sets.

        Returns all pairs of polygons that intersect, with both sets of
        attributes. Useful for county-to-district apportionment or
        boundary change analysis.

        Default delegates to :meth:`spatial_join` with predicate='intersects'.
        Engines may override to compute intersection geometry and area.
        """
        return self.spatial_join(
            poly_a, poly_b,
            how="inner", predicate="intersects",
            left_geom=a_geom, right_geom=b_geom,
        )

    def apportion(
        self,
        source_polys: Any,
        target_polys: Any,
        weight_col: str,
        *,
        source_geom: str = "geometry",
        target_geom: str = "geometry",
    ) -> Any:
        """Apportion a value from source polygons to target polygons by overlap.

        Distributes ``weight_col`` from source to target proportional to
        the fraction of source area that overlaps each target. Example:
        apportion tract population to congressional districts.

        Default: intersect, compute area ratios via GeoPandas, aggregate.
        Engines may override for native area computation (Sedona ST_Area,
        PostGIS ST_Area, etc.).
        """
        import geopandas as gpd

        src = self.to_geodataframe(source_polys, source_geom)
        tgt = self.to_geodataframe(target_polys, target_geom)

        # Compute intersection
        overlay = gpd.overlay(src, tgt, how="intersection")

        # Area ratio: intersection_area / source_area
        overlay["_src_area"] = src.loc[overlay.index].geometry.area
        overlay["_isect_area"] = overlay.geometry.area
        overlay["_ratio"] = overlay["_isect_area"] / overlay["_src_area"].replace(0, float("nan"))
        overlay[f"apportioned_{weight_col}"] = overlay[weight_col] * overlay["_ratio"]

        # Aggregate by target
        tgt_id_cols = [c for c in tgt.columns if c != target_geom]
        return overlay.groupby(tgt_id_cols).agg(
            {f"apportioned_{weight_col}": "sum"}
        ).reset_index()

    def nearest(
        self,
        points: Any,
        targets: Any,
        *,
        k: int = 1,
        max_distance: Optional[float] = None,
        point_geom: str = "geometry",
        target_geom: str = "geometry",
    ) -> Any:
        """Find the k nearest targets for each point.

        Default: brute-force via GeoPandas sjoin_nearest.
        Engines should override for native spatial indexing (Sedona KNN,
        PostGIS ST_DWithin + ORDER BY distance, DuckDB spatial).
        """
        import geopandas as gpd

        pts = self.to_geodataframe(points, point_geom)
        tgts = self.to_geodataframe(targets, target_geom)

        return gpd.sjoin_nearest(
            pts, tgts,
            how="left",
            max_distance=max_distance,
            distance_col="distance",
        )

    def multi_assign(
        self,
        points: Any,
        boundary_layers: Dict[str, Any],
        *,
        point_geom: str = "geometry",
    ) -> Any:
        """Assign points to multiple boundary layers simultaneously.

        Calls :meth:`assign_boundaries` for each layer and joins results.

        Parameters
        ----------
        points : DataFrame
            Point DataFrame.
        boundary_layers : dict
            ``{layer_name: polygon_DataFrame}``. Each polygon DataFrame
            must have a geometry column and identifying columns.

        Returns
        -------
        DataFrame
            Points enriched with ``{layer_name}_geoid`` and
            ``{layer_name}_name`` from each boundary layer.
        """
        result = points
        for layer_name, polygons in boundary_layers.items():
            assigned = self.assign_boundaries(
                result, polygons,
                point_geom=point_geom, polygon_geom="geometry",
                how="left",
            )
            result = assigned
        return result


# ---------------------------------------------------------------------------
# Pandas engine (always available)
# ---------------------------------------------------------------------------

class PandasEngine(DataFrameEngine):
    """Engine backed by pandas (and optionally GeoPandas)."""

    @property
    def name(self) -> str:
        return PANDAS

    # -- I/O ----------------------------------------------------------------

    def read_csv(self, path: str, **kwargs: Any) -> Any:
        import pandas as pd
        return pd.read_csv(path, **kwargs)

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        import pandas as pd
        return pd.read_parquet(path, **kwargs)

    # -- SQL ----------------------------------------------------------------

    def query(self, sql: str, **kwargs: Any) -> Any:
        """Execute SQL via ``pandas.read_sql``.

        Requires a ``connection`` keyword argument (a SQLAlchemy engine or
        DBAPI2 connection).
        """
        import pandas as pd
        connection = kwargs.pop("connection", None)
        if connection is None:
            raise ValueError(
                "PandasEngine.query() requires a 'connection' keyword argument"
            )
        return pd.read_sql(sql, connection, **kwargs)

    # -- Transforms ---------------------------------------------------------

    def to_pandas(self, df: Any) -> Any:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return df
        # GeoPandas DataFrames are also pandas DataFrames, so this covers both.
        return pd.DataFrame(df)

    def groupby_agg(
        self,
        df: Any,
        group_cols: Sequence[str],
        agg_dict: Dict[str, str],
    ) -> Any:
        return df.groupby(list(group_cols)).agg(agg_dict).reset_index()

    def filter(self, df: Any, condition: Any) -> Any:
        return df.loc[condition].reset_index(drop=True)

    def join(
        self,
        left: Any,
        right: Any,
        on: Union[str, List[str]],
        how: str = "inner",
    ) -> Any:
        return left.merge(right, on=on, how=how)

    # -- Spatial -----------------------------------------------------------

    def read_spatial(self, path: str, *, crs: Optional[str] = None, **kwargs: Any) -> Any:
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        gdf = gpd.read_file(path, **kwargs)
        return reproject_if_needed(gdf, crs or get_default_crs())

    def spatial_join(self, left, right, how="inner", predicate="intersects",
                     *, left_geom="geometry", right_geom="geometry"):
        import geopandas as gpd
        if left.geometry.name != left_geom:
            left = left.set_geometry(left_geom)
        if right.geometry.name != right_geom:
            right = right.set_geometry(right_geom)
        return gpd.sjoin(left, right, how=how, predicate=predicate)

    def buffer(self, df, distance, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import reproject_if_needed
        gdf = df if isinstance(df, gpd.GeoDataFrame) else self.to_geodataframe(df, geometry_col)
        result = gdf.copy()
        result[geometry_col] = result[geometry_col].buffer(distance)
        return reproject_if_needed(result, crs) if crs else result

    def distance(self, df, other, geometry_col="geometry", other_geom="geometry"):
        from shapely.geometry.base import BaseGeometry
        if isinstance(other, BaseGeometry):
            return df[geometry_col].distance(other)
        if isinstance(other, str):
            from shapely import wkt
            return df[geometry_col].distance(wkt.loads(other))
        return df[geometry_col].distance(other[other_geom])

    def to_geodataframe(self, df, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        if isinstance(df, gpd.GeoDataFrame):
            return reproject_if_needed(df, crs or get_default_crs())
        if geometry_col in df.columns:
            from shapely import wkt
            geoms = df[geometry_col].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            return gpd.GeoDataFrame(df, geometry=geoms, crs=crs or get_default_crs())
        raise ValueError(f"Cannot construct GeoDataFrame: column '{geometry_col}' not found")


# ---------------------------------------------------------------------------
# DuckDB engine (lazy import)
# ---------------------------------------------------------------------------

class DuckDBEngine(DataFrameEngine):
    """Engine backed by DuckDB."""

    def __init__(self, **kwargs: Any) -> None:
        try:
            import duckdb  # noqa: F401
        except ImportError:
            raise ImportError(
                "DuckDB is not installed. Install it with: pip install duckdb"
            ) from None
        self._conn_kwargs = kwargs
        self._conn: Any = None
        self._spatial_loaded: bool = False

    @property
    def _connection(self) -> Any:
        if self._conn is None:
            import duckdb
            self._conn = duckdb.connect(**self._conn_kwargs)
        return self._conn

    @property
    def name(self) -> str:
        return DUCKDB

    # -- I/O ----------------------------------------------------------------

    def read_csv(self, path: str, **kwargs: Any) -> Any:
        return self._connection.execute(
            f"SELECT * FROM read_csv_auto('{path}')"
        ).fetchdf()

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        return self._connection.execute(
            f"SELECT * FROM read_parquet('{path}')"
        ).fetchdf()

    # -- SQL ----------------------------------------------------------------

    def query(self, sql: str, **kwargs: Any) -> Any:
        """Execute *sql* against the DuckDB connection.

        If a ``table`` keyword is supplied together with a pandas DataFrame
        value, that DataFrame is first registered as a virtual table so it
        can be referenced in *sql*.
        """
        table = kwargs.pop("table", None)
        df = kwargs.pop("df", None)
        if table is not None and df is not None:
            self._connection.register(table, df)
        return self._connection.execute(sql).fetchdf()

    # -- Transforms ---------------------------------------------------------

    def to_pandas(self, df: Any) -> Any:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return df
        # DuckDB relations have a .fetchdf() method
        if hasattr(df, "fetchdf"):
            return df.fetchdf()
        return pd.DataFrame(df)

    def groupby_agg(
        self,
        df: Any,
        group_cols: Sequence[str],
        agg_dict: Dict[str, str],
    ) -> Any:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return df.groupby(list(group_cols)).agg(agg_dict).reset_index()
        raise TypeError(
            "DuckDBEngine.groupby_agg expects a pandas DataFrame "
            "(use .query() with GROUP BY for pure-SQL workflows)"
        )

    def filter(self, df: Any, condition: Any) -> Any:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return df.loc[condition].reset_index(drop=True)
        raise TypeError(
            "DuckDBEngine.filter expects a pandas DataFrame "
            "(use .query() with WHERE for pure-SQL workflows)"
        )

    def join(
        self,
        left: Any,
        right: Any,
        on: Union[str, List[str]],
        how: str = "inner",
    ) -> Any:
        import pandas as pd
        if isinstance(left, pd.DataFrame) and isinstance(right, pd.DataFrame):
            return left.merge(right, on=on, how=how)
        raise TypeError(
            "DuckDBEngine.join expects pandas DataFrames "
            "(use .query() with JOIN for pure-SQL workflows)"
        )

    # -- Spatial -----------------------------------------------------------

    def _ensure_spatial(self) -> None:
        """Load DuckDB spatial extension if not already loaded."""
        if not self._spatial_loaded:
            self._connection.execute("INSTALL spatial; LOAD spatial;")
            self._spatial_loaded = True

    def read_spatial(self, path: str, *, crs: Optional[str] = None, **kwargs: Any) -> Any:
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        self._ensure_spatial()
        result = self._connection.execute(
            f"SELECT * FROM ST_Read('{path}')"
        ).fetchdf()
        # ST_Read returns geometry as WKB-hex; convert to shapely
        geom_col = "geom" if "geom" in result.columns else "geometry"
        if geom_col in result.columns:
            from shapely import wkb as shapely_wkb, wkt as shapely_wkt
            def _parse_geom(g):
                if g is None:
                    return None
                if isinstance(g, bytes):
                    return shapely_wkb.loads(g)
                if isinstance(g, str):
                    try:
                        return shapely_wkb.loads(g, hex=True)
                    except Exception:
                        return shapely_wkt.loads(g)
                return g
            result[geom_col] = result[geom_col].apply(_parse_geom)
            gdf = gpd.GeoDataFrame(result, geometry=geom_col, crs=crs or get_default_crs())
            return reproject_if_needed(gdf, crs or get_default_crs())
        return result

    def spatial_join(self, left, right, how="inner", predicate="intersects",
                     *, left_geom="geometry", right_geom="geometry"):
        # Delegate to GeoPandas for correctness
        import geopandas as gpd
        left_gdf = self.to_geodataframe(left, left_geom) if not isinstance(left, gpd.GeoDataFrame) else left
        right_gdf = self.to_geodataframe(right, right_geom) if not isinstance(right, gpd.GeoDataFrame) else right
        return gpd.sjoin(left_gdf, right_gdf, how=how, predicate=predicate)

    def buffer(self, df, distance, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import reproject_if_needed
        gdf = self.to_geodataframe(df, geometry_col) if not isinstance(df, gpd.GeoDataFrame) else df
        result = gdf.copy()
        result[geometry_col] = result[geometry_col].buffer(distance)
        return reproject_if_needed(result, crs) if crs else result

    def distance(self, df, other, geometry_col="geometry", other_geom="geometry"):
        import geopandas as gpd
        from shapely.geometry.base import BaseGeometry
        gdf = self.to_geodataframe(df, geometry_col) if not isinstance(df, gpd.GeoDataFrame) else df
        if isinstance(other, BaseGeometry):
            return gdf[geometry_col].distance(other)
        if isinstance(other, str):
            from shapely import wkt
            return gdf[geometry_col].distance(wkt.loads(other))
        other_gdf = self.to_geodataframe(other, other_geom) if not isinstance(other, gpd.GeoDataFrame) else other
        return gdf[geometry_col].distance(other_gdf[other_geom])

    def to_geodataframe(self, df, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        import pandas as pd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        if isinstance(df, gpd.GeoDataFrame):
            return reproject_if_needed(df, crs or get_default_crs())
        if isinstance(df, pd.DataFrame) and geometry_col in df.columns:
            from shapely import wkt as shapely_wkt, wkb as shapely_wkb
            from shapely.geometry.base import BaseGeometry
            sample = df[geometry_col].dropna().iloc[0] if len(df) > 0 else None
            if sample is not None and not isinstance(sample, BaseGeometry):
                if isinstance(sample, bytes):
                    geoms = df[geometry_col].apply(lambda g: shapely_wkb.loads(g) if g is not None else None)
                else:
                    geoms = df[geometry_col].apply(lambda g: shapely_wkt.loads(g) if isinstance(g, str) else g)
                return gpd.GeoDataFrame(df, geometry=geoms, crs=crs or get_default_crs())
            return gpd.GeoDataFrame(df, geometry=geometry_col, crs=crs or get_default_crs())
        raise ValueError(f"Cannot construct GeoDataFrame: column '{geometry_col}' not found")


# ---------------------------------------------------------------------------
# Spark engine (lazy import)
# ---------------------------------------------------------------------------

class SparkEngine(DataFrameEngine):
    """Engine backed by PySpark.

    Parameters
    ----------
    spark : optional
        An existing ``SparkSession``.  When *None* the engine creates or
        retrieves the active session on first use.
    """

    def __init__(self, spark: Any = None, *, enable_sedona: bool = False) -> None:
        try:
            import pyspark  # noqa: F401
        except ImportError:
            raise ImportError(
                "PySpark is not installed. Install it with: pip install pyspark"
            ) from None
        self._spark = spark
        self._enable_sedona = enable_sedona
        self._sedona_registered = False

    @property
    def _session(self) -> Any:
        if self._spark is None:
            from pyspark.sql import SparkSession
            self._spark = SparkSession.builder.getOrCreate()
        return self._spark

    @property
    def name(self) -> str:
        return SPARK

    # -- I/O ----------------------------------------------------------------

    def read_csv(self, path: str, **kwargs: Any) -> Any:
        header = kwargs.pop("header", True)
        infer_schema = kwargs.pop("inferSchema", True)
        return (
            self._session.read
            .option("header", header)
            .option("inferSchema", infer_schema)
            .csv(path, **kwargs)
        )

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        return self._session.read.parquet(path, **kwargs)

    # -- SQL ----------------------------------------------------------------

    def query(self, sql: str, **kwargs: Any) -> Any:
        return self._session.sql(sql)

    # -- Transforms ---------------------------------------------------------

    def to_pandas(self, df: Any) -> Any:
        if hasattr(df, "toPandas"):
            return df.toPandas()
        import pandas as pd
        return pd.DataFrame(df)

    def groupby_agg(
        self,
        df: Any,
        group_cols: Sequence[str],
        agg_dict: Dict[str, str],
    ) -> Any:
        from pyspark.sql import functions as F
        agg_exprs = [
            getattr(F, func)(col).alias(f"{col}")
            for col, func in agg_dict.items()
        ]
        return df.groupBy(*group_cols).agg(*agg_exprs)

    def filter(self, df: Any, condition: Any) -> Any:
        return df.filter(condition)

    def join(
        self,
        left: Any,
        right: Any,
        on: Union[str, List[str]],
        how: str = "inner",
    ) -> Any:
        return left.join(right, on=on, how=how)

    # -- Spatial -----------------------------------------------------------

    def _ensure_sedona(self) -> None:
        """Register Sedona UDFs if not already done."""
        if not self._sedona_registered:
            if self._enable_sedona:
                try:
                    from sedona.register import SedonaRegistrator
                    SedonaRegistrator.registerAll(self._session)
                    self._sedona_registered = True
                except ImportError:
                    pass  # Sedona not installed — spatial methods will fail with clear errors

    def read_spatial(self, path: str, *, crs: Optional[str] = None, **kwargs: Any) -> Any:
        # Fallback: read via GeoPandas, convert to Spark DataFrame
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        gdf = gpd.read_file(path, **kwargs)
        gdf = reproject_if_needed(gdf, crs or get_default_crs())
        # Convert geometry to WKT for Spark compatibility
        pdf = gdf.copy()
        pdf["geometry"] = pdf["geometry"].apply(lambda g: g.wkt if g is not None else None)
        return self._session.createDataFrame(pdf)

    def spatial_join(self, left, right, how="inner", predicate="intersects",
                     *, left_geom="geometry", right_geom="geometry"):
        self._ensure_sedona()
        left.createOrReplaceTempView("_sjoin_left")
        right.createOrReplaceTempView("_sjoin_right")
        st_func = f"ST_{predicate.capitalize()}"
        # Avoid column name collision by aliasing right geometry
        sql = (
            f"SELECT l.*, r.* "
            f"FROM _sjoin_left l {how.upper()} JOIN _sjoin_right r "
            f"ON {st_func}(ST_GeomFromText(l.{left_geom}), ST_GeomFromText(r.{right_geom}))"
        )
        return self._session.sql(sql)

    def buffer(self, df, distance, geometry_col="geometry", *, crs=None):
        self._ensure_sedona()
        df.createOrReplaceTempView("_buf_tbl")
        sql = (
            f"SELECT *, ST_AsText(ST_Buffer(ST_GeomFromText({geometry_col}), {distance})) "
            f"AS {geometry_col}_buffered FROM _buf_tbl"
        )
        return self._session.sql(sql)

    def distance(self, df, other, geometry_col="geometry", other_geom="geometry"):
        self._ensure_sedona()
        from shapely.geometry.base import BaseGeometry
        df.createOrReplaceTempView("_dist_left")
        if isinstance(other, (BaseGeometry, str)):
            wkt_str = other.wkt if isinstance(other, BaseGeometry) else other
            sql = (
                f"SELECT *, ST_Distance(ST_GeomFromText({geometry_col}), "
                f"ST_GeomFromText('{wkt_str}')) AS _distance FROM _dist_left"
            )
        else:
            other.createOrReplaceTempView("_dist_right")
            sql = (
                f"SELECT ST_Distance(ST_GeomFromText(l.{geometry_col}), "
                f"ST_GeomFromText(r.{other_geom})) AS _distance "
                f"FROM _dist_left l, _dist_right r"
            )
        return self._session.sql(sql)

    def to_geodataframe(self, df, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs
        from shapely import wkt
        pdf = df.toPandas()
        if geometry_col in pdf.columns:
            geoms = pdf[geometry_col].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            return gpd.GeoDataFrame(pdf, geometry=geoms, crs=crs or get_default_crs())
        raise ValueError(f"Cannot construct GeoDataFrame: column '{geometry_col}' not found")

    # -- Spatial overrides (Spark/Sedona native) ---------------------------

    def load_polygons(self, path, *, geometry_col="geometry", format="auto", crs=None):
        """Load polygons — Spark-native parquet/json reader."""
        if format == "auto":
            format = "parquet" if "parquet" in path.lower() or "/" == path[-1:] else "geojson"
        if format in ("parquet", "geoparquet"):
            df = self._session.read.parquet(path)
            if geometry_col not in df.columns and "geom" in df.columns:
                from pyspark.sql.functions import col
                df = df.withColumnRenamed("geom", geometry_col)
            return df
        # Fallback to GeoPandas for GeoJSON/Shapefile
        return self.read_spatial(path, crs=crs)

    def load_points(self, df, lat_col="lat", lon_col="lon", geometry_col="geometry"):
        """Create point geometries — Spark-native WKT string construction."""
        from pyspark.sql.functions import col, concat, lit
        return df.withColumn(
            geometry_col,
            concat(lit("POINT("), col(lon_col).cast("string"), lit(" "), col(lat_col).cast("string"), lit(")")),
        )

    def assign_boundaries(self, points, polygons, *, point_geom="geometry",
                          polygon_geom="geometry", how="left"):
        """Point-in-polygon — Sedona ST_Contains with optional broadcast."""
        self._ensure_sedona()
        from pyspark.sql.functions import broadcast
        points.createOrReplaceTempView("_assign_pts")
        broadcast(polygons).createOrReplaceTempView("_assign_poly")
        return self._session.sql(
            f"SELECT p.*, poly.* "
            f"FROM _assign_pts p {how.upper()} JOIN _assign_poly poly "
            f"ON ST_Contains(ST_GeomFromText(poly.{polygon_geom}), "
            f"ST_GeomFromText(p.{point_geom}))"
        )

    def nearest(self, points, targets, *, k=1, max_distance=None,
                point_geom="geometry", target_geom="geometry"):
        """K-nearest — Sedona ST_Distance with window function."""
        self._ensure_sedona()
        points.createOrReplaceTempView("_nn_pts")
        targets.createOrReplaceTempView("_nn_tgt")
        dist_filter = f"WHERE d <= {max_distance}" if max_distance else ""
        return self._session.sql(f"""
            SELECT * FROM (
                SELECT p.*, t.*,
                    ST_Distance(ST_GeomFromText(p.{point_geom}),
                                ST_GeomFromText(t.{target_geom})) AS d,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.{point_geom}
                        ORDER BY ST_Distance(ST_GeomFromText(p.{point_geom}),
                                             ST_GeomFromText(t.{target_geom}))
                    ) AS rn
                FROM _nn_pts p, _nn_tgt t
                {dist_filter}
            ) WHERE rn <= {k}
        """)


# ---------------------------------------------------------------------------
# PostGIS engine (lazy import)
# ---------------------------------------------------------------------------

class PostGISEngine(DataFrameEngine):
    """Engine backed by PostGIS via SQLAlchemy + GeoPandas.

    Parameters
    ----------
    connection_string : str
        A SQLAlchemy connection string, e.g.
        ``"postgresql://user:pass@host:5432/dbname"``.
    """

    def __init__(self, connection_string: str) -> None:
        try:
            import sqlalchemy  # noqa: F401
        except ImportError:
            raise ImportError(
                "SQLAlchemy is not installed. "
                "Install it with: pip install sqlalchemy psycopg2-binary"
            ) from None
        try:
            import geopandas  # noqa: F401
        except ImportError:
            raise ImportError(
                "GeoPandas is not installed. "
                "Install it with: pip install geopandas"
            ) from None
        self._connection_string = connection_string
        self._engine: Any = None

    @property
    def _sql_engine(self) -> Any:
        if self._engine is None:
            from sqlalchemy import create_engine
            self._engine = create_engine(self._connection_string)
        return self._engine

    @property
    def name(self) -> str:
        return POSTGIS

    # -- I/O ----------------------------------------------------------------

    def read_csv(self, path: str, **kwargs: Any) -> Any:
        import geopandas as gpd
        import pandas as pd
        df = pd.read_csv(path, **kwargs)
        # If there is a geometry column, parse it
        if "geometry" in df.columns:
            from shapely import wkt
            df["geometry"] = df["geometry"].apply(wkt.loads)
            return gpd.GeoDataFrame(df, geometry="geometry")
        return df

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        import geopandas as gpd
        try:
            return gpd.read_parquet(path, **kwargs)
        except Exception:
            import pandas as pd
            return pd.read_parquet(path, **kwargs)

    # -- SQL ----------------------------------------------------------------

    def query(self, sql: str, **kwargs: Any) -> Any:
        """Execute *sql* against the PostGIS database.

        If the query returns a geometry column, the result is a
        ``GeoDataFrame``; otherwise a plain ``DataFrame``.
        """
        import geopandas as gpd
        geom_col = kwargs.pop("geom_col", "geometry")
        try:
            return gpd.read_postgis(
                sql, self._sql_engine, geom_col=geom_col, **kwargs
            )
        except Exception:
            import pandas as pd
            return pd.read_sql(sql, self._sql_engine, **kwargs)

    # -- Transforms ---------------------------------------------------------

    def to_pandas(self, df: Any) -> Any:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return pd.DataFrame(df)  # strips GeoDataFrame wrapper if present
        return pd.DataFrame(df)

    def groupby_agg(
        self,
        df: Any,
        group_cols: Sequence[str],
        agg_dict: Dict[str, str],
    ) -> Any:
        return df.groupby(list(group_cols)).agg(agg_dict).reset_index()

    def filter(self, df: Any, condition: Any) -> Any:
        return df.loc[condition].reset_index(drop=True)

    def join(
        self,
        left: Any,
        right: Any,
        on: Union[str, List[str]],
        how: str = "inner",
    ) -> Any:
        return left.merge(right, on=on, how=how)

    # -- Spatial -----------------------------------------------------------

    def read_spatial(self, path: str, *, crs: Optional[str] = None, **kwargs: Any) -> Any:
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        if path.upper().startswith("SELECT"):
            return self.query(path, **kwargs)
        gdf = gpd.read_file(path, **kwargs)
        return reproject_if_needed(gdf, crs or get_default_crs())

    def spatial_join(self, left, right, how="inner", predicate="intersects",
                     *, left_geom="geometry", right_geom="geometry"):
        import geopandas as gpd
        left_gdf = left if isinstance(left, gpd.GeoDataFrame) else self.to_geodataframe(left, left_geom)
        right_gdf = right if isinstance(right, gpd.GeoDataFrame) else self.to_geodataframe(right, right_geom)
        return gpd.sjoin(left_gdf, right_gdf, how=how, predicate=predicate)

    def buffer(self, df, distance, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import reproject_if_needed
        gdf = df if isinstance(df, gpd.GeoDataFrame) else self.to_geodataframe(df, geometry_col)
        result = gdf.copy()
        result[geometry_col] = result[geometry_col].buffer(distance)
        return reproject_if_needed(result, crs) if crs else result

    def distance(self, df, other, geometry_col="geometry", other_geom="geometry"):
        import geopandas as gpd
        from shapely.geometry.base import BaseGeometry
        gdf = df if isinstance(df, gpd.GeoDataFrame) else self.to_geodataframe(df, geometry_col)
        if isinstance(other, BaseGeometry):
            return gdf[geometry_col].distance(other)
        if isinstance(other, str):
            from shapely import wkt
            return gdf[geometry_col].distance(wkt.loads(other))
        other_gdf = other if isinstance(other, gpd.GeoDataFrame) else self.to_geodataframe(other, other_geom)
        return gdf[geometry_col].distance(other_gdf[other_geom])

    def to_geodataframe(self, df, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed
        if isinstance(df, gpd.GeoDataFrame):
            return reproject_if_needed(df, crs or get_default_crs())
        import pandas as pd
        if isinstance(df, pd.DataFrame) and geometry_col in df.columns:
            from shapely import wkt
            geoms = df[geometry_col].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            return gpd.GeoDataFrame(df, geometry=geoms, crs=crs or get_default_crs())
        raise ValueError(f"Cannot construct GeoDataFrame: column '{geometry_col}' not found")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ENGINE_MAP: Dict[Engine, type] = {
    Engine.PANDAS: PandasEngine,
    Engine.DUCKDB: DuckDBEngine,
    Engine.SPARK: SparkEngine,
    Engine.POSTGIS: PostGISEngine,
}


def get_engine(name: Union[str, Engine], **kwargs: Any) -> DataFrameEngine:
    """Return an engine instance for the requested back-end.

    Parameters
    ----------
    name : str or Engine
        One of ``"pandas"``, ``"duckdb"``, ``"spark"``, ``"postgis"``
        (or the corresponding ``Engine`` enum member).
    **kwargs
        Passed to the engine constructor (e.g. ``connection_string`` for
        PostGIS, ``spark`` for Spark).

    Returns
    -------
    DataFrameEngine
    """
    if isinstance(name, str):
        try:
            name = Engine(name.lower())
        except ValueError:
            valid = ", ".join(e.value for e in Engine)
            raise ValueError(
                f"Unknown engine {name!r}. Choose from: {valid}"
            ) from None

    cls = _ENGINE_MAP[name]
    return cls(**kwargs)


__all__ = [
    "Engine",
    "PANDAS",
    "DUCKDB",
    "SPARK",
    "POSTGIS",
    "DataFrameEngine",
    "PandasEngine",
    "DuckDBEngine",
    "SparkEngine",
    "PostGISEngine",
    "get_engine",
]
