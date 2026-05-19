"""
Engine-agnostic DataFrame operations.

Provides a thin abstraction so the same analytical operations can run on
DuckDB, Spark, or PostGIS instead of only pandas/GeoPandas.

Why one abstraction
-------------------
The point is **not** that the back-ends are interchangeable in performance --
they are not. The point is that **consumer code should not branch on
back-end**. A reporting module asked to summarise voter rolls should not
care whether the frame came from a 10-million-row Spark job or a 5-row
pandas test fixture; it calls ``engine.groupby_agg(...)`` and is done.

This is load-bearing. The anti-pattern to avoid: ``if isinstance(df,
pd.DataFrame): ... else: ...`` scattered through ``reporting/``. If you
find yourself reaching for it, the right fix is a new method on the
``DataFrameEngine`` interface -- not a special case in the consumer.

Usage::

    from siege_utilities.engines.dataframe_engine import get_engine, Engine

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


# Shared across all engines; see docs/engines/INVARIANTS.md groupby_agg.
# "avg" is the Spark spelling; "mean" is the pandas spelling. Both are
# accepted at the validator and normalised inside each engine.
#
# This set is the intersection: agg names every engine implements.
# SparkEngine accepts additional Spark-native aggregations (e.g.
# approx_count_distinct) via its own validation path; see
# SparkEngine.groupby_agg below.
_SUPPORTED_AGG_NAMES = frozenset({
    "sum", "mean", "avg", "count", "min", "max",
    "first", "last", "stddev", "variance",
})

# SparkEngine-only aggregations. Defined here for visibility so the
# capability surface is grep-able from one place; see SparkEngine.
_SPARK_EXTRA_AGG_NAMES = frozenset({"approx_count_distinct"})


def _validate_agg_names(agg_dict: "Dict[str, str]", engine_name: str) -> None:
    if not agg_dict:
        raise ValueError(
            f"{engine_name}.groupby_agg: agg_dict must not be empty; "
            f"pass at least one column -> aggregation name mapping."
        )
    unknown = sorted({f for f in agg_dict.values() if f not in _SUPPORTED_AGG_NAMES})
    if unknown:
        raise ValueError(
            f"{engine_name}.groupby_agg: unsupported aggregation "
            f"function(s) {unknown}. Supported: "
            f"{sorted(_SUPPORTED_AGG_NAMES)}."
        )


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

    # -- Grid indexing (concrete defaults; engines may override) -----------

    def index_points(
        self,
        df: Any,
        lat_col: str,
        lon_col: str,
        *,
        grid: Optional[str] = None,
        resolution: Optional[int] = None,
        level: Optional[int] = None,
        as_token: bool = True,
    ) -> Any:
        """Compute a grid (H3 or S2) cell ID for each row.

        Default: round-trip through pandas. Engines that benefit from a
        native path (Spark via pandas UDF, DuckDB via SQL when the
        spatial extension is loaded) should override.

        See :func:`siege_utilities.geo.grids.index_points` for the kwarg
        inference rules -- pass ``resolution=`` for H3, ``level=`` for S2,
        or set ``grid=`` explicitly.

        Returns the same engine-native frame type as ``df`` would have
        been augmented with -- for the default, that's a column appended
        to a pandas-converted copy. Engines that override return their
        native shape.
        """
        from ..geo.grids import index_points as _index_points, infer_grid
        pdf = self.to_pandas(df).copy()
        if grid is None and resolution is None and level is None:
            # No hint at all -> default to S2 level 12 (the most useful
            # data-warehouse path; H3 callers are expected to pass
            # resolution=).
            level = 12
            grid = "s2"
        # Resolve the chosen grid up front so the output column name
        # matches what was computed (otherwise resolution=8 alone would
        # produce h3_index in the data but be labelled s2_index).
        chosen = infer_grid(grid, {"resolution": resolution, "level": level})
        cells = _index_points(
            pdf, lat_col, lon_col,
            grid=grid, resolution=resolution, level=level,
            **({"as_token": as_token} if chosen == "s2" else {}),
        )
        col = "h3_index" if chosen == "h3" else "s2_index"
        pdf[col] = cells.values
        return pdf

    def index_polygon(
        self,
        geometry: Any,
        *,
        grid: Optional[str] = None,
        resolution: Optional[int] = None,
        level: Optional[int] = None,
        max_cells: Optional[int] = None,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None,
        refine: bool = True,
    ) -> Any:
        """Cover a polygon with grid cells.

        Engine-agnostic by construction -- the input is a single geometry,
        not a frame, so no engine-specific dispatch is required at this
        level. Provided here for API symmetry with :meth:`index_points`
        and so consumer code can accept ``engine`` as a config knob and
        call ``engine.index_polygon(...)`` uniformly.
        """
        from ..geo.grids import index_polygon as _index_polygon
        return _index_polygon(
            geometry,
            grid=grid,
            resolution=resolution,
            level=level,
            max_cells=max_cells,
            min_level=min_level,
            max_level=max_level,
            refine=refine,
        )

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

        The default implementation ignores ``format`` and ``geometry_col``;
        it delegates to ``read_spatial`` which infers the format from the
        path. ``SparkEngine.load_polygons`` overrides this method and
        honours both parameters (parquet vs geojson branching, and
        renaming a ``geom`` column to ``geometry_col`` when present).
        Other engines may add similar overrides; until then, callers that
        rely on these parameters should test with the engine they intend
        to use.
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

        Same interface as :meth:`load_polygons` -- works for roads, rivers,
        transit routes, or any linear feature. The default implementation
        ignores ``format`` and ``geometry_col`` (same shape as the default
        ``load_polygons``); engines that override may honour them.
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

        # Detect zero-area sources BEFORE gpd.overlay. A degenerate source
        # polygon that produces no intersection rows would otherwise
        # disappear entirely -- the post-overlay check missed exactly the
        # data-loss case it was trying to surface.
        import logging as _logging
        _log = _logging.getLogger(__name__)
        src = src.assign(_src_area=src.geometry.area)
        zero_area_src = src["_src_area"] <= 0
        if zero_area_src.any():
            _log.warning(
                "apportion: %d source polygon(s) have zero area; their "
                "weights are dropped before overlay.",
                int(zero_area_src.sum()),
            )
            src = src.loc[~zero_area_src].copy()

        # Compute intersection. We carry _src_area through so the ratio
        # computation doesn't have to re-index against the original src.
        overlay = gpd.overlay(src, tgt, how="intersection")
        overlay["_isect_area"] = overlay.geometry.area
        overlay["_ratio"] = overlay["_isect_area"] / overlay["_src_area"]
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

        Calls :meth:`assign_boundaries` for each layer and renames every
        polygon-side column to be ``{layer_name}_{column}`` so layers do
        not collide on shared schemas (TIGER layers share ``geoid`` /
        ``name`` columns -- without prefixing, the second join silently
        overwrites the first layer's columns).

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
            Points enriched with ``{layer_name}_*`` columns for every
            polygon-side column from each boundary layer. Bare polygon
            column names never appear in the output.
        """
        # Snapshot point-side schema before the first join so we know
        # exactly which columns belong to the points and which were
        # added by assign_boundaries. Use to_pandas() rather than a
        # native columns probe because the abstract default cannot
        # assume an engine-native columns accessor exists across all
        # implementations -- subclasses may override for efficiency.
        point_cols = set(self.to_pandas(points).columns)

        result = points
        for layer_name, polygons in boundary_layers.items():
            assigned = self.assign_boundaries(
                result, polygons,
                point_geom=point_geom, polygon_geom="geometry",
                how="left",
            )
            assigned_pdf = self.to_pandas(assigned)
            new_cols = {}
            for col in assigned_pdf.columns:
                if col in point_cols or col == point_geom:
                    continue
                new_cols[col] = f"{layer_name}_{col}"
            if new_cols:
                assigned_pdf = assigned_pdf.rename(columns=new_cols)
            # Update point_cols for the next iteration so the just-added
            # layer's prefixed columns are preserved (not re-prefixed).
            point_cols = set(assigned_pdf.columns)
            result = assigned_pdf

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
        _validate_agg_names(agg_dict, "PandasEngine")
        # pandas accepts "mean" but not "avg"; normalise so the shared
        # agg-name set is honored across engines.
        normalised = {col: ("mean" if fn == "avg" else fn) for col, fn in agg_dict.items()}
        return df.groupby(list(group_cols)).agg(normalised).reset_index()

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
        """Read a CSV via DuckDB's ``read_csv_auto``.

        Engine-specific kwargs (DuckDB's ``read_csv_auto`` options like
        ``header``, ``delim``, ``columns``) are not yet forwarded; pass
        the equivalent options inside a custom SQL via :meth:`query`
        if you need to override auto-detection.
        """
        if kwargs:
            raise NotImplementedError(
                f"DuckDBEngine.read_csv does not yet forward kwargs "
                f"(got {sorted(kwargs.keys())}); use .query() with an "
                f"explicit `SELECT ... FROM read_csv_auto(path, <opts>)` "
                f"if you need to pass DuckDB-specific options. "
                f"Tracked separately for proper kwargs forwarding."
            )
        # Parameter-bind the path so it can't break out of the string
        # literal in read_csv_auto's argument slot.
        return self._connection.execute(
            "SELECT * FROM read_csv_auto(?)", [path]
        ).fetchdf()

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        """Read a Parquet file via DuckDB's ``read_parquet``.

        Engine-specific kwargs are not yet forwarded; use :meth:`query`
        for DuckDB-specific options.
        """
        if kwargs:
            raise NotImplementedError(
                f"DuckDBEngine.read_parquet does not yet forward kwargs "
                f"(got {sorted(kwargs.keys())}); use .query() with an "
                f"explicit `SELECT ... FROM read_parquet(path, <opts>)`."
            )
        return self._connection.execute(
            "SELECT * FROM read_parquet(?)", [path]
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
        _validate_agg_names(agg_dict, "DuckDBEngine")
        import pandas as pd
        normalised = {col: ("mean" if fn == "avg" else fn) for col, fn in agg_dict.items()}
        if isinstance(df, pd.DataFrame):
            return df.groupby(list(group_cols)).agg(normalised).reset_index()
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
                    # WKB-hex strings are pure hexadecimal; WKT strings
                    # start with a geometry-type keyword (POINT, POLYGON,
                    # MULTIPOLYGON, etc.). Introspect rather than try/
                    # except so a corrupt WKB string doesn't silently fall
                    # through to WKT parsing of garbage.
                    head = g[:32].strip() if g else ""
                    if head and all(c in "0123456789abcdefABCDEF" for c in head):
                        return shapely_wkb.loads(g, hex=True)
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
            # Predicate must be on the dropped Series -- len(df) > 0 can
            # be true while df[geometry_col] is all-null, which would
            # IndexError on .iloc[0].
            non_null = df[geometry_col].dropna()
            sample = non_null.iloc[0] if not non_null.empty else None
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
        """Execute *sql* via Spark SQL.

        SparkEngine.query accepts no engine-specific kwargs;
        ``self._session.sql()`` takes no options beyond the SQL text. The
        ``**kwargs`` parameter is present for interface symmetry with
        DuckDBEngine (which accepts ``table`` / ``df``) and PostGISEngine
        (which accepts ``geom_col``). A non-empty kwargs is a caller
        error and is raised to surface the mistake rather than silently
        ignored.
        """
        if kwargs:
            raise NotImplementedError(
                f"SparkEngine.query takes no engine-specific kwargs (got "
                f"{sorted(kwargs.keys())}); DuckDBEngine.query accepts "
                f"'table' and 'df'; PostGISEngine.query accepts 'geom_col'. "
                f"For Spark SQL options, configure them on the SparkSession "
                f"before calling query()."
            )
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
        # SparkEngine accepts the intersection set plus Spark-specific
        # extensions (approx_count_distinct via F.approx_count_distinct).
        # The validator is local to SparkEngine because the central
        # _validate_agg_names enforces the intersection only.
        spark_supported = _SUPPORTED_AGG_NAMES | _SPARK_EXTRA_AGG_NAMES
        if not agg_dict:
            raise ValueError(
                "SparkEngine.groupby_agg: agg_dict must not be empty; "
                "pass at least one column -> aggregation name mapping."
            )
        unknown = sorted({f for f in agg_dict.values() if f not in spark_supported})
        if unknown:
            raise ValueError(
                f"SparkEngine.groupby_agg: unsupported aggregation "
                f"function(s) {unknown}. Supported: "
                f"{sorted(spark_supported)}."
            )
        # pyspark.sql.functions exposes the function as F.avg, with mean
        # only available as a Column method. Normalise so callers can
        # pass either spelling.
        _spark_fn = {"mean": "avg"}
        agg_exprs = [
            getattr(F, _spark_fn.get(func, func))(col).alias(col)
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
        """Register Sedona UDFs if not already done.

        Emits a debug-level log line on every call path so the caller
        can confirm which branch ran from log output alone (per
        writing-code:11 floor (b)). The three observable states are:

        - already-registered (no-op): "Sedona UDFs already registered"
        - sedona-disabled-by-config: "Sedona registration skipped (_enable_sedona=False)"
        - fresh-registration: "Sedona UDFs registered"

        Raises ImportError with the install command when Sedona is not
        installed but registration was requested. Failing here surfaces
        the missing dependency at the first spatial call rather than
        producing a confusing Spark SQL error about ST_Foo being
        unknown (writing-code:7-correct: error path is loud).
        """
        import logging as _logging
        _log = _logging.getLogger(__name__)
        if self._sedona_registered:
            _log.debug("Sedona UDFs already registered")
            return
        if not self._enable_sedona:
            _log.debug("Sedona registration skipped (_enable_sedona=False)")
            return
        try:
            from sedona.register import SedonaRegistrator
            SedonaRegistrator.registerAll(self._session)
        except ImportError as exc:
            raise ImportError(
                "SparkEngine spatial methods require Apache Sedona. "
                "Install it with: pip install apache-sedona[spark] "
                "and ensure the JARs are on the SparkSession classpath."
            ) from exc
        self._sedona_registered = True
        _log.debug("Sedona UDFs registered")

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
        from siege_utilities.core.sql_safety import (
            validate_sql_identifier_in as validate_identifier_in,
        )
        validate_identifier_in(left_geom, left.columns, label="left geometry column")
        validate_identifier_in(right_geom, right.columns, label="right geometry column")
        # `validate_sql_identifier` only checks shape -- Sedona doesn't have
        # ``ST_Foo``, so accept only the documented predicate set.
        supported_predicates = {
            "intersects", "contains", "within", "touches", "crosses", "overlaps",
        }
        if predicate.lower() not in supported_predicates:
            raise ValueError(
                f"unsupported spatial predicate {predicate!r} -- "
                f"expected one of {sorted(supported_predicates)}"
            )
        if how.lower() not in ("inner", "left", "right", "outer", "full"):
            raise ValueError(f"unsupported join type {how!r}")
        # Unique per-call temp-view names so concurrent calls don't
        # collide on a shared `_sjoin_left` and so a failed previous
        # call doesn't leave stale state in the catalog. The returned
        # DataFrame is lazy -- we can't drop the views in this scope.
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:8]
        lv = f"_sjoin_left_{tag}"
        rv = f"_sjoin_right_{tag}"
        left.createOrReplaceTempView(lv)
        right.createOrReplaceTempView(rv)
        st_func = f"ST_{predicate.capitalize()}"
        sql = (
            f"SELECT l.*, r.* "
            f"FROM {lv} l {how.upper()} JOIN {rv} r "
            f"ON {st_func}(ST_GeomFromText(l.{left_geom}), ST_GeomFromText(r.{right_geom}))"
        )
        return self._session.sql(sql)

    def buffer(self, df, distance, geometry_col="geometry", *, crs=None):
        self._ensure_sedona()
        from siege_utilities.core.sql_safety import validate_sql_identifier_in as validate_identifier_in
        validate_identifier_in(geometry_col, df.columns, label="geometry column")
        # `distance` is interpolated as a float -- coerce so a malicious
        # caller can't sneak SQL via a string.
        distance_lit = float(distance)
        import uuid as _uuid
        view = f"_buf_tbl_{_uuid.uuid4().hex[:8]}"
        df.createOrReplaceTempView(view)
        sql = (
            f"SELECT *, ST_AsText(ST_Buffer(ST_GeomFromText({geometry_col}), {distance_lit})) "
            f"AS {geometry_col}_buffered FROM {view}"
        )
        return self._session.sql(sql)

    def distance(self, df, other, geometry_col="geometry", other_geom="geometry"):
        self._ensure_sedona()
        from shapely.geometry.base import BaseGeometry
        from siege_utilities.core.sql_safety import (
            escape_sql_string_literal as escape_string_literal,
            validate_sql_identifier_in as validate_identifier_in,
        )
        validate_identifier_in(geometry_col, df.columns, label="geometry column")
        import uuid as _uuid
        lv = f"_dist_left_{_uuid.uuid4().hex[:8]}"
        df.createOrReplaceTempView(lv)
        if isinstance(other, (BaseGeometry, str)):
            wkt_str = other.wkt if isinstance(other, BaseGeometry) else other
            wkt_escaped = escape_string_literal(wkt_str)
            sql = (
                f"SELECT *, ST_Distance(ST_GeomFromText({geometry_col}), "
                f"ST_GeomFromText('{wkt_escaped}')) AS _distance FROM {lv}"
            )
        else:
            validate_identifier_in(other_geom, other.columns, label="other geometry column")
            rv = f"_dist_right_{_uuid.uuid4().hex[:8]}"
            other.createOrReplaceTempView(rv)
            sql = (
                f"SELECT ST_Distance(ST_GeomFromText(l.{geometry_col}), "
                f"ST_GeomFromText(r.{other_geom})) AS _distance "
                f"FROM {lv} l, {rv} r"
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
        """Load polygons -- Spark-native parquet/json reader."""
        if format == "auto":
            format = "parquet" if "parquet" in path.lower() or "/" == path[-1:] else "geojson"
        if format in ("parquet", "geoparquet"):
            df = self._session.read.parquet(path)
            if geometry_col not in df.columns and "geom" in df.columns:
                df = df.withColumnRenamed("geom", geometry_col)
            return df
        # Fallback to GeoPandas for GeoJSON/Shapefile
        return self.read_spatial(path, crs=crs)

    def load_points(self, df, lat_col="lat", lon_col="lon", geometry_col="geometry"):
        """Create point geometries -- Spark-native WKT string construction."""
        from pyspark.sql.functions import col, concat, lit
        return df.withColumn(
            geometry_col,
            concat(lit("POINT("), col(lon_col).cast("string"), lit(" "), col(lat_col).cast("string"), lit(")")),
        )

    def assign_boundaries(self, points, polygons, *, point_geom="geometry",
                          polygon_geom="geometry", how="left"):
        """Point-in-polygon -- Sedona ST_Contains with optional broadcast."""
        self._ensure_sedona()
        from pyspark.sql.functions import broadcast
        from siege_utilities.core.sql_safety import validate_sql_identifier_in as validate_identifier_in
        validate_identifier_in(point_geom, points.columns, label="point geometry column")
        validate_identifier_in(polygon_geom, polygons.columns, label="polygon geometry column")
        if how.lower() not in ("inner", "left", "right", "outer", "full"):
            raise ValueError(f"unsupported join type {how!r}")
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:8]
        pv = f"_assign_pts_{tag}"
        poly_v = f"_assign_poly_{tag}"
        points.createOrReplaceTempView(pv)
        broadcast(polygons).createOrReplaceTempView(poly_v)
        return self._session.sql(
            f"SELECT p.*, poly.* "
            f"FROM {pv} p {how.upper()} JOIN {poly_v} poly "
            f"ON ST_Contains(ST_GeomFromText(poly.{polygon_geom}), "
            f"ST_GeomFromText(p.{point_geom}))"
        )

    def nearest(self, points, targets, *, k=1, max_distance=None,
                point_geom="geometry", target_geom="geometry"):
        """K-nearest -- Sedona ST_Distance with window function."""
        self._ensure_sedona()
        from siege_utilities.core.sql_safety import validate_sql_identifier_in as validate_identifier_in
        validate_identifier_in(point_geom, points.columns, label="point geometry column")
        validate_identifier_in(target_geom, targets.columns, label="target geometry column")
        # Coerce numeric inputs so they can't carry SQL.
        k_lit = int(k)
        max_distance_lit = float(max_distance) if max_distance is not None else None
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:8]
        pv = f"_nn_pts_{tag}"
        tv = f"_nn_tgt_{tag}"
        points.createOrReplaceTempView(pv)
        targets.createOrReplaceTempView(tv)
        # WHERE on a SELECT-list alias is invalid in Spark SQL; re-expand
        # the ST_Distance expression in the predicate.
        if max_distance_lit is not None:
            dist_filter = (
                f"WHERE ST_Distance(ST_GeomFromText(p.{point_geom}), "
                f"ST_GeomFromText(t.{target_geom})) <= {max_distance_lit}"
            )
        else:
            dist_filter = ""
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
                FROM {pv} p, {tv} t
                {dist_filter}
            ) WHERE rn <= {k_lit}
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

    # -- Grid indexing (overrides the ABC default to surface a useful path) -

    def index_points(
        self,
        df: Any,
        lat_col: str,
        lon_col: str,
        *,
        grid: Optional[str] = None,
        resolution: Optional[int] = None,
        level: Optional[int] = None,
        as_token: bool = True,
    ) -> Any:
        """PostGIS does not natively compute H3 / S2 cell IDs.

        For S2-keyed warehouse joins, the recommended pattern is:

          1. Compute cell IDs ONCE during ingest (e.g. via the PandasEngine
             or in your ETL job using ``s2_index_points``).
          2. Store as a ``BIGINT`` column on the row.
          3. For region queries, generate ``(range_min, range_max)`` pairs
             via :func:`s2_cells_to_ranges` and filter with
             ``WHERE s2_cell BETWEEN range_min AND range_max``.

        Computing cell IDs at query time over PostGIS would defeat the
        whole point -- the database can't index a value it has to compute
        per-row. Hence this engine raises rather than silently degrade.
        """
        raise NotImplementedError(
            "PostGISEngine.index_points: compute cell IDs at ingest time "
            "(via PandasEngine or s2_index_points), store as BIGINT column, "
            "and use s2_cells_to_ranges() for region queries. "
            "See engine.index_points docstring for the pattern."
        )

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
        """Read a parquet file. Returns a ``GeoDataFrame`` when the file
        carries GeoParquet metadata, a plain ``DataFrame`` otherwise.

        The decision is by file inspection (pyarrow schema metadata),
        not by exception-fallback. An earlier implementation tried
        ``gpd.read_parquet`` first and silently fell back to
        ``pd.read_parquet`` on any exception -- that pattern hid real
        gpd errors (a corrupt geoparquet file, an out-of-date geopandas)
        as "this must not be a geoparquet file." The current path checks
        the parquet metadata directly so the decision is explicit.
        """
        import geopandas as gpd
        import pandas as pd
        import pyarrow.parquet as pq
        schema_metadata = pq.read_schema(path).metadata or {}
        # GeoParquet files carry a 'geo' key in the schema metadata.
        is_geoparquet = b"geo" in schema_metadata
        if is_geoparquet:
            return gpd.read_parquet(path, **kwargs)
        return pd.read_parquet(path, **kwargs)

    # -- SQL ----------------------------------------------------------------

    def query(self, sql: str, **kwargs: Any) -> Any:
        """Execute *sql* against the PostGIS database.

        Pass ``geom_col="<column>"`` to indicate a geometry column in the
        result; the query then returns a ``GeoDataFrame`` with that
        column parsed as geometry. Omit ``geom_col`` (or pass an empty
        string) for queries that return no geometry; the result is a
        plain ``DataFrame``.

        The Geo-vs-plain decision is made by the caller (via the
        presence of ``geom_col``), not by exception-fallback. An earlier
        implementation tried ``gpd.read_postgis`` first and silently
        fell back to ``pd.read_sql`` on any exception -- that pattern
        hid real PostGIS errors (a malformed SQL, a missing column) as
        "this must not have a geometry column."
        """
        geom_col = kwargs.pop("geom_col", None)
        if geom_col:
            import geopandas as gpd
            return gpd.read_postgis(
                sql, self._sql_engine, geom_col=geom_col, **kwargs
            )
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
        _validate_agg_names(agg_dict, "PostGISEngine")
        normalised = {col: ("mean" if fn == "avg" else fn) for col, fn in agg_dict.items()}
        return df.groupby(list(group_cols)).agg(normalised).reset_index()

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

# Module-load-time exhaustiveness check: if a new Engine enum member is
# added and the mapping is not updated, get_engine() would raise KeyError
# at first use. Failing here at import time turns a runtime data-dependent
# bug into a deterministic load-time error, which is the right place to
# notice this mismatch.
_missing_engines = set(Engine) - set(_ENGINE_MAP)
if _missing_engines:
    raise RuntimeError(
        "_ENGINE_MAP is not exhaustive over the Engine enum; missing: "
        f"{sorted(e.value for e in _missing_engines)}. "
        "Add a mapping entry for every Engine member."
    )
del _missing_engines


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
