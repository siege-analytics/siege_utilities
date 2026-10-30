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
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Union

log = logging.getLogger(__name__)


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

# pandas attrs carry per-column CRS across eager DuckDB WKB materialization.
_GEOMETRY_CRS_ATTR = "siege_geometry_crs"


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


# The shared agg-name set uses the Spark/SQL spellings (avg, stddev, variance).
# pandas-family engines (Pandas, DuckDB, PostGIS driver-side) call
# DataFrame.agg, whose method names are mean, std, var. Map every shared name
# to its pandas spelling before dispatch; names that already match pass through.
_PANDAS_AGG_SPELLING = {"avg": "mean", "stddev": "std", "variance": "var"}


def _normalise_pandas_aggs(agg_dict: "Dict[str, str]") -> "Dict[str, str]":
    return {col: _PANDAS_AGG_SPELLING.get(fn, fn) for col, fn in agg_dict.items()}


def _aggregate_pandas_groups(grouped: Any, normalised: Dict[str, str]) -> Any:
    """Aggregate with SQL NULL sums while retaining pandas' native operations."""
    result = grouped.agg(normalised)
    sum_cols = [col for col, fn in normalised.items() if fn == "sum"]
    if sum_cols:
        # pandas sums all-null groups to zero. Mask only those groups, keeping
        # real zero sums and nullable dtypes; equivalent to sum(min_count=1).
        result[sum_cols] = result[sum_cols].where(grouped[sum_cols].count() > 0)
    return result.reset_index()


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
        An existing GeoDataFrame retains its CRS unless ``crs`` is supplied.
        Text geometry without CRS metadata uses the configured default CRS.
        """

    def from_geodataframe(
        self,
        gdf: Any,
        geometry_col: str = "geometry",
    ) -> Any:
        """Convert a GeoPandas ``GeoDataFrame`` to this engine's native format.

        The inverse of :meth:`to_geodataframe`.  Geometry is serialized
        as WKB-hex (DuckDB) or WKT (Spark/PostGIS) for engine-native
        spatial operations.

        Subclasses should override this for engine-specific conversion.
        The default implementation returns the GeoDataFrame unchanged
        (suitable for PandasEngine).
        """
        return gdf

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
        *,
        crs: Optional[str] = None,
        **agg_kwargs: Any,
    ) -> Any:
        """Dissolve/merge geometries grouped by *by* columns.

        Default converts to GeoDataFrame and uses ``gdf.dissolve()``.
        Engines may override for native performance.
        Preserve the input CRS unless a target ``crs`` is supplied.
        """
        gdf = self.to_geodataframe(df, geometry_col=geometry_col, crs=crs)
        return gdf.dissolve(by=by, **agg_kwargs).reset_index()

    # -- Spatial geometry loading (concrete defaults) ----------------------

    # Mapping from user-facing format names to Fiona/GDAL driver strings.
    # ``"auto"`` is handled specially (no driver kwarg → infer from path).
    _FORMAT_DRIVERS: Dict[str, str] = {
        "geojson": "GeoJSON",
        "shapefile": "ESRI Shapefile",
        "gpkg": "GPKG",
        "geopackage": "GPKG",
    }
    # Formats that require ``gpd.read_parquet`` instead of ``gpd.read_file``.
    _PARQUET_FORMATS = frozenset({"parquet", "geoparquet"})

    def _load_spatial(
        self,
        path: str,
        *,
        geometry_col: str = "geometry",
        format: str = "auto",
        crs: Optional[str] = None,
    ) -> Any:
        """Shared implementation for :meth:`load_polygons` and :meth:`load_lines`.

        Handles explicit ``format`` selection and ``geometry_col`` renaming
        so that the public API contract is honoured by the default engine.
        """
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs, reproject_if_needed

        fmt = format.lower().strip() if format else "auto"

        if fmt == "auto":
            gdf = gpd.read_file(path)
        elif fmt in self._PARQUET_FORMATS:
            gdf = gpd.read_parquet(path)
        elif fmt in self._FORMAT_DRIVERS:
            gdf = gpd.read_file(path, driver=self._FORMAT_DRIVERS[fmt])
        else:
            supported = sorted(
                list(self._FORMAT_DRIVERS.keys())
                + list(self._PARQUET_FORMATS)
                + ["auto"]
            )
            raise ValueError(
                f"Unsupported format {format!r}. "
                f"Supported formats: {supported}."
            )

        gdf = reproject_if_needed(gdf, crs or get_default_crs())

        # Honour geometry_col: rename the active geometry column if needed.
        active_geom = gdf.geometry.name
        if geometry_col != active_geom:
            if geometry_col in gdf.columns:
                # A non-geometry column with the target name exists; set it
                # as the active geometry (caller asserts it *is* geometry).
                gdf = gdf.set_geometry(geometry_col)
            else:
                # Rename the current geometry column to the requested name.
                gdf = gdf.rename_geometry(geometry_col)

        return gdf

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

        Parameters
        ----------
        path : str
            Path to the spatial file.
        geometry_col : str
            Name for the geometry column in the returned DataFrame. If the
            source data uses a different column name it will be renamed.
        format : str
            Spatial format hint. ``"auto"`` (default) infers from the file
            extension. Explicit values: ``"geojson"``, ``"shapefile"``,
            ``"gpkg"``, ``"geopackage"``, ``"parquet"``, ``"geoparquet"``.
        crs : str or None
            Target CRS. Defaults to ``EPSG:4326`` via ``get_default_crs()``.
        """
        return self._load_spatial(
            path, geometry_col=geometry_col, format=format, crs=crs,
        )

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
        transit routes, or any linear feature.

        Parameters
        ----------
        path : str
            Path to the spatial file.
        geometry_col : str
            Name for the geometry column in the returned DataFrame. If the
            source data uses a different column name it will be renamed.
        format : str
            Spatial format hint. ``"auto"`` (default) infers from the file
            extension. Explicit values: ``"geojson"``, ``"shapefile"``,
            ``"gpkg"``, ``"geopackage"``, ``"parquet"``, ``"geoparquet"``.
        crs : str or None
            Target CRS. Defaults to ``EPSG:4326`` via ``get_default_crs()``.
        """
        return self._load_spatial(
            path, geometry_col=geometry_col, format=format, crs=crs,
        )

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
        crs: Optional[str] = None,
    ) -> Any:
        """Apportion a value from source polygons to target polygons by overlap.

        Distributes ``weight_col`` from source to target proportional to
        the fraction of source area that overlaps each target. Example:
        apportion tract population to congressional districts.

        Default: intersect, compute area ratios via GeoPandas, aggregate.
        Engines may override for native area computation (Sedona ST_Area,
        PostGIS ST_Area, etc.).
        Areas use the input's projected CRS. For geographic inputs, supply
        a projected ``crs`` (preferably equal-area) to reproject both inputs.
        Without a target CRS, inputs must have the same projected CRS.
        The result is a table of target attributes and apportioned values.
        """
        import geopandas as gpd

        src = self.to_geodataframe(source_polys, source_geom, crs=crs)
        tgt = self.to_geodataframe(target_polys, target_geom, crs=crs)
        self._require_projected_crs(src, tgt, "apportion")

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
        crs: Optional[str] = None,
    ) -> Any:
        """Find the k nearest targets for each point.

        Default: brute-force via GeoPandas sjoin_nearest (supports k=1 only).
        Engines should override for native spatial indexing (Sedona KNN,
        PostGIS ST_DWithin + ORDER BY distance, DuckDB spatial) and k>1.
        Distances and ``max_distance`` use the input's projected CRS units.
        Preserve that CRS unless a target ``crs`` is supplied to reproject
        both inputs. Geographic or unknown CRS inputs require a projected CRS;
        different input CRSes require a shared target CRS.

        Raises
        ------
        NotImplementedError
            If k > 1 (base implementation only supports single-nearest).
        """
        if k > 1:
            # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
            raise NotImplementedError(
                f"Base GeoPandas engine only supports k=1 (got k={k}). "
                "Use a spatial-database engine (PostGIS, Sedona, DuckDB) for k-nearest."
            )
        import geopandas as gpd

        pts = self.to_geodataframe(points, point_geom, crs=crs)
        tgts = self.to_geodataframe(targets, target_geom, crs=crs)
        self._require_projected_crs(pts, tgts, "nearest")

        return gpd.sjoin_nearest(
            pts, tgts,
            how="left",
            max_distance=max_distance,
            distance_col="distance",
        )

    @staticmethod
    def _require_projected_crs(left, right, operation):
        if left.crs != right.crs:
            raise ValueError(f"CRS mismatch in {operation}: {left.crs} and {right.crs}; supply a shared crs")
        if left.crs is None or not left.crs.is_projected:
            raise ValueError(f"{operation} requires a projected CRS for area/distance math; supply crs")

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
            column names never appear in the output. The join's generated
            right index is dropped. Point-side column names are preserved;
            a prefixed layer name colliding with a point column raises ValueError.
        """
        import geopandas as gpd

        result = points
        for layer_name, polygons in boundary_layers.items():
            if not isinstance(polygons, gpd.GeoDataFrame):
                polygons = self.to_geodataframe(polygons)
            names = self._boundary_column_names(polygons.columns, layer_name, result.columns)
            result = self.assign_boundaries(
                result, polygons.rename(columns=names).reset_index(drop=True),
                point_geom=point_geom, polygon_geom="geometry",
                how="left",
            ).drop(columns=["index_right"], errors="ignore")
        return result

    @staticmethod
    def _boundary_column_names(columns, layer_name, point_columns):
        """Prefix attributes before joining so point names cannot be suffixed."""
        names = {c: f"{layer_name}_{c}" for c in columns if c != "geometry"}
        collisions = set(names.values()) & set(point_columns)
        if collisions:
            raise ValueError(f"multi_assign: layer columns collide with point columns: {sorted(collisions)}")
        return names


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
        """Read a CSV file.

        **kwargs: Forwarded to :func:`pandas.read_csv`.
        """
        import pandas as pd
        return pd.read_csv(path, **kwargs)

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        """Read a Parquet file.

        **kwargs: Forwarded to :func:`pandas.read_parquet`.
        """
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
        normalised = _normalise_pandas_aggs(agg_dict)
        grouped = df.groupby(list(group_cols), dropna=False)
        return _aggregate_pandas_groups(grouped, normalised)

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
        """Read a spatial file.

        **kwargs: Forwarded to :func:`geopandas.read_file`.
        """
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
        if left.crs is not None and right.crs is not None and left.crs != right.crs:
            raise ValueError(
                f"CRS mismatch in spatial_join: left has {left.crs}, "
                f"right has {right.crs}. Reproject one input to match the other."
            )
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
        from siege_utilities.geo.crs import get_default_crs
        if isinstance(df, gpd.GeoDataFrame):
            if crs is None:
                return df
            return df.to_crs(crs) if df.crs is not None else df.set_crs(crs)
        if geometry_col in df.columns:
            from shapely import wkt
            target_crs = crs or get_default_crs()
            parsed = df[geometry_col].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            # Bind the parsed geometry back under geometry_col as the active
            # GeoSeries. Passing geometry=<Series> to GeoDataFrame leaves the
            # requested column as plain strings, so df[geometry_col] would not
            # be a GeoSeries and .buffer()/.distance() would raise.
            out = df.copy()
            out[geometry_col] = gpd.GeoSeries(parsed.values, index=out.index, crs=target_crs)
            return gpd.GeoDataFrame(out, geometry=geometry_col, crs=target_crs)
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
            # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
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
            # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
            raise NotImplementedError(
                f"DuckDBEngine.read_parquet does not yet forward kwargs "
                f"(got {sorted(kwargs.keys())}); use .query() with an "
                f"explicit `SELECT ... FROM read_parquet(path, <opts>)`."
            )
        return self._connection.execute(
            "SELECT * FROM read_parquet(?)", [path]
        ).fetchdf()

    # -- SQL ----------------------------------------------------------------

    def query(self, sql: str, *, parameters: Any = None, **kwargs: Any) -> Any:
        """Execute *sql* against the DuckDB connection.

        If a ``table`` keyword is supplied together with a pandas DataFrame
        value, that DataFrame is first registered as a virtual table so it
        can be referenced in *sql*.
        Row and status results are eagerly materialized pandas DataFrames,
        independent of the connection lifetime and subsequent source mutations.
        Output columns whose DuckDB type is GEOMETRY (including DML RETURNING)
        are converted to standard WKB by column position before fetching;
        nested geometry values and other spatial types are not converted.
        Duplicate names retain their distinct values
        and receive DuckDB's usual suffixes. :meth:`to_pandas` returns this
        frame unchanged; :meth:`to_geodataframe` decodes its WKB geometry.
        DML without RETURNING retains its affected-row Count; PREPARE returns
        its empty Success status without executing the prepared statement.
        Spatial is loaded only for geometry conversion or SQL requiring it.
        ``parameters`` (or ``params``) binds a sequence or named mapping to a
        single statement. Parameterized multi-statement SQL and unknown keywords
        are rejected before execution. Geometry CRS is retained per column in
        the returned frame's ``attrs['siege_geometry_crs']`` mapping.
        """
        table = kwargs.pop("table", None)
        df = kwargs.pop("df", None)
        params = kwargs.pop("params", None)
        if kwargs:
            raise TypeError(f"DuckDBEngine.query: unexpected keyword argument(s): {sorted(kwargs)}")
        if parameters is not None and params is not None:
            raise TypeError("DuckDBEngine.query: pass only one of parameters or params")
        if parameters is None:
            parameters = params
        if (table is None) != (df is None):
            raise ValueError("DuckDBEngine.query: table and df must be supplied together")
        # Bind each statement separately: a spatial bind failure must not
        # replay preceding DML. Relations are strictly internal and always
        # materialized before returning to the caller.
        statements = self._connection.extract_statements(sql)
        if parameters is not None and len(statements) != 1:
            raise ValueError("DuckDBEngine.query: parameters require a single statement")
        if table is not None:
            self._connection.register(table, df)
        for statement in statements[:-1]:
            self._bind_spatial_if_needed(self._connection.execute, statement)
        if not statements:
            return self._connection.execute(sql).fetchdf()
        statement = statements[-1]
        if self._statement_returns_rows(statement):
            bindings = {"params": parameters} if parameters is not None else {}
            relation = self._bind_spatial_if_needed(self._connection.sql, statement, **bindings)
            return self._materialize_geometry_wkb(relation)
        bindings = {"parameters": parameters} if parameters is not None else {}
        return self._bind_spatial_if_needed(
            self._connection.execute, statement, **bindings,
        ).fetchdf()

    def _statement_returns_rows(self, statement: Any) -> bool:
        """Select the typed-result API without executing a mutation to probe it.

        DuckDB's sql() discards affected-row Counts, while execute() loses
        geometry types on fetch. Statement metadata identifies queries; DML
        metadata allows both rows and Counts, so inspect its RETURNING clause
        with DuckDB's tokenizer (ignoring strings, comments and subqueries).
        """
        import duckdb

        if statement.type == duckdb.StatementType.EXECUTE:
            # EXECUTE's metadata says QUERY_RESULT even for prepared DML that
            # only reports Count. Inspect its definition without executing it.
            import re

            tokens = duckdb.tokenize(statement.query)
            if len(tokens) < 2:
                raise ValueError("Cannot extract prepared statement name from EXECUTE")
            position = tokens[1][0]
            # The tokenizer skips leading comments and reports byte offsets.
            # Match DuckDB's identifier bytes: ASCII letters/underscore or
            # high-bit bytes, followed also by digits/$ (not Python's \s).
            # DuckDB has already normalized its Unicode space separators in
            # statement.query; other non-ASCII characters belong to the name.
            match = re.match(
                rb'"(?:[^"]|"")*"|[A-Za-z_\x80-\xff][A-Za-z_0-9$\x80-\xff]*',
                statement.query.encode("utf-8")[position:],
            )
            if match is None:
                raise ValueError("Cannot extract prepared statement name from EXECUTE")
            identifier = match.group().decode("utf-8")
            name = identifier[1:-1].replace('""', '"') if identifier.startswith('"') else identifier
            # Session collations must not merge distinct catalog identifiers.
            lookup = 'SELECT statement FROM duckdb_prepared_statements() WHERE name = ? COLLATE "binary"'
            prepared = self._connection.execute(
                lookup, [name],
            ).fetchone()
            if prepared is None:
                # DuckDB identifiers ignore ASCII case only. Resolve an ASCII
                # alias to the stored spelling, then bind that exact name.
                # Unicode lower() would conflate distinct names such as é/É.
                ascii_fold = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
                names = self._connection.execute("SELECT name FROM duckdb_prepared_statements()").fetchall()
                for (stored_name,) in names:
                    if stored_name.translate(ascii_fold) == name.translate(ascii_fold):
                        prepared = self._connection.execute(lookup, [stored_name]).fetchone()
                        break
            if prepared is None:
                # Let execute() raise the normal missing-prepared-statement error.
                return False
            return self._statement_returns_rows(self._connection.extract_statements(prepared[0])[0])
        if statement.expected_result_type == [duckdb.ExpectedResultType.QUERY_RESULT]:
            return True
        if duckdb.ExpectedResultType.QUERY_RESULT not in statement.expected_result_type:
            # Only inspect RETURNING when the outer statement can return rows.
            # PREPARE has a status result even when its definition has RETURNING.
            return False
        sql = statement.query.encode("utf-8")  # Token positions are byte offsets.
        depth = 0
        for position, kind in duckdb.tokenize(statement.query):
            if kind == duckdb.token_type.operator:
                if sql[position:position + 1] == b"(":
                    depth += 1
                elif sql[position:position + 1] == b")":
                    depth -= 1
            elif depth == 0 and kind == duckdb.token_type.keyword:
                if sql[position:position + 9].upper() == b"RETURNING":
                    return True
        return False

    def _bind_spatial_if_needed(self, operation, statement, **kwargs):
        """Retry only a bind failure that explicitly requires spatial."""
        import duckdb

        try:
            return operation(statement, **kwargs)
        except duckdb.CatalogException as exc:
            if self._spatial_loaded or "exists in the spatial extension" not in str(exc):
                raise
            self._ensure_spatial()
            return operation(statement, **kwargs)

    # -- Transforms ---------------------------------------------------------

    def to_pandas(self, df: Any) -> Any:
        """Return a pandas frame, converting GEOMETRY columns in typed relations.

        Frames returned by :meth:`query` are already materialized and are
        returned unchanged. Relation columns typed exactly GEOMETRY become WKB;
        nested geometry values and other spatial types are not converted.
        Use :meth:`to_geodataframe` to decode the WKB.
        """
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return df
        df = self._materialize_geometry_wkb(df)
        if isinstance(df, pd.DataFrame):
            return df
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
        normalised = _normalise_pandas_aggs(agg_dict)
        if isinstance(df, pd.DataFrame):
            grouped = df.groupby(list(group_cols), dropna=False)
            return _aggregate_pandas_groups(grouped, normalised)
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
            suffixes = ("_x", "_y")
            # Resolve the CRS of every coalesced geometry key BEFORE merging, so
            # a conflicting or outer-unjoinable pair is rejected before any rows
            # are produced.
            key_crs = self._resolve_geometry_key_crs(left, right, on, how)
            result = left.merge(right, on=on, how=how, suffixes=suffixes)
            # pandas.merge drops DataFrame.attrs, where per-column geometry CRS
            # lives. Re-attach it so a known CRS survives an attribute join,
            # remapping any non-key column the merge suffixed.
            merged_crs = self._merge_geometry_crs(
                left, right, result, on, suffixes, key_crs
            )
            if merged_crs:
                result.attrs[_GEOMETRY_CRS_ATTR] = merged_crs
            return result
        raise TypeError(
            "DuckDBEngine.join expects pandas DataFrames "
            "(use .query() with JOIN for pure-SQL workflows)"
        )

    @staticmethod
    def _crs_equal(left_crs: Any, right_crs: Any) -> bool:
        """Compare two known CRS values semantically, not by raw string.

        Stored CRS values are heterogeneous strings (``EPSG:n``, WKT, PROJJSON,
        proj4). Identical strings short-circuit; otherwise both sides are
        canonicalized through :func:`siege_utilities.geo.crs._normalize_crs`
        (which pulls in pyproj) before comparing.
        """
        if left_crs == right_crs:
            return True
        from siege_utilities.geo.crs import _normalize_crs

        return _normalize_crs(left_crs) == _normalize_crs(right_crs)

    @classmethod
    def _coalesce_key_crs(
        cls, left_crs: Any, right_crs: Any, how: str, key: Any,
    ) -> Any:
        """Resolve the CRS of one coalesced geometry join key.

        Two different KNOWN CRSes are rejected in every mode. A known-vs-None
        pair is source-selected for inner/left/right (the CRS of the side that
        supplies the surviving key) but rejected for outer, which keeps
        unmatched rows from both sides. None/None stays None.
        """
        left_known = left_crs is not None
        right_known = right_crs is not None
        if left_known and right_known:
            if cls._crs_equal(left_crs, right_crs):
                return left_crs
            raise ValueError(
                f"join key {key!r} has conflicting geometry CRS: "
                f"left {left_crs!r} vs right {right_crs!r}; reproject one side "
                f"to a common CRS before joining"
            )
        if how == "outer":
            if not left_known and not right_known:
                return None
            raise ValueError(
                f"outer join on geometry key {key!r} needs a known CRS on both "
                f"sides; got left {left_crs!r} and right {right_crs!r}. An outer "
                f"join keeps unmatched rows from both frames, so the key column "
                f"cannot carry one known and one unknown CRS; set the CRS on "
                f"both sides before joining"
            )
        # inner/left/right: the surviving key comes from the left frame for
        # inner and left joins, and from the right frame for a right join.
        return right_crs if how == "right" else left_crs

    @classmethod
    def _resolve_geometry_key_crs(
        cls, left: Any, right: Any, on: Union[str, List[str]], how: str,
    ) -> dict:
        """Resolve/validate the CRS of each coalesced geometry join key.

        A key is a geometry key when it is present in either input's CRS map
        (a scalar key is absent from both maps and carries no CRS). Each such
        key is resolved independently, so the rule applies per component of a
        composite key. Raises before the merge on a conflicting or
        outer-unjoinable CRS pair.
        """
        on_cols = {on} if isinstance(on, str) else set(on)
        left_map = left.attrs.get(_GEOMETRY_CRS_ATTR, {})
        right_map = right.attrs.get(_GEOMETRY_CRS_ATTR, {})
        resolved: dict = {}
        for key in on_cols:
            if key not in left_map and key not in right_map:
                continue
            resolved[key] = cls._coalesce_key_crs(
                left_map.get(key), right_map.get(key), how, key
            )
        return resolved

    @staticmethod
    def _merge_geometry_crs(
        left: Any, right: Any, result: Any, on: Union[str, List[str]],
        suffixes: tuple, key_crs: dict,
    ) -> dict:
        """Carry per-column geometry CRS across a pandas merge.

        pandas.merge does not preserve ``DataFrame.attrs``, so the CRS map stored
        by ``_materialize_geometry_wkb`` is lost. Rebuild it from both inputs,
        applying the merge suffix to any non-key column present in both frames.

        Coalesced geometry keys take the CRS resolved by
        :meth:`_resolve_geometry_key_crs`. Non-key overlapping geometry columns
        keep each side's own CRS under its suffix.
        """
        on_cols = {on} if isinstance(on, str) else set(on)
        overlap = (set(left.columns) & set(right.columns)) - on_cols
        merged: dict = {}
        for key, crs in key_crs.items():
            if key in result.columns:
                merged[key] = crs
        for frame, suffix in ((left, suffixes[0]), (right, suffixes[1])):
            crs_map = frame.attrs.get(_GEOMETRY_CRS_ATTR, {})
            for col, crs in crs_map.items():
                if col in on_cols:
                    continue
                new_col = f"{col}{suffix}" if col in overlap else col
                if new_col in result.columns:
                    merged[new_col] = crs
        return merged

    # -- Spatial -----------------------------------------------------------

    def _ensure_spatial(self) -> None:
        """Load spatial only for a geometry operation, installing if absent."""
        if not self._spatial_loaded:
            import duckdb
            try:
                self._connection.execute("LOAD spatial")
            except duckdb.IOException:
                self._connection.execute("INSTALL spatial")
                self._connection.execute("LOAD spatial")
            self._spatial_loaded = True

    @staticmethod
    def _quote_ident(name: Any) -> str:
        """Quote a DuckDB identifier, escaping any embedded double quotes.

        DuckDB quotes identifiers with double quotes; a literal double quote
        inside the name must be doubled (``a"b`` -> ``"a""b"``). Emitting the
        name un-escaped produces an unterminated-identifier ParserException.
        """
        return '"' + str(name).replace('"', '""') + '"'

    @staticmethod
    def _decode_geometry_text(value: str) -> Any:
        """Decode hex WKB or WKT without hiding malformed geometry errors."""
        from shapely import wkb as shapely_wkb, wkt as shapely_wkt

        # WKB-hex has a pure hexadecimal head; WKT starts with a geometry
        # keyword. Do not fall back to WKT after a corrupt WKB parse.
        head = value[:32].strip() if value else ""
        if head and all(c in "0123456789abcdefABCDEF" for c in head):
            return shapely_wkb.loads(value, hex=True)
        return shapely_wkt.loads(value)

    @staticmethod
    def _geometry_column_positions(relation: Any) -> List[int]:
        """Return zero-based positions of SCALAR GEOMETRY columns.

        Match a bare ``GEOMETRY`` or a parametrized ``GEOMETRY('EPSG:4326')``
        (DuckDB spatial 1.5.x reports the parametrized form where 1.4.x reported
        the bare name, so an exact-equality check misses it). Do NOT match any
        array/list form -- bare ``GEOMETRY[]`` / ``GEOMETRY[1]`` OR the
        CRS-qualified collection ``GEOMETRY('EPSG:4326')[]`` that ``list(geom)``
        aggregation produces -- because ``ST_AsWKB`` cannot be applied to a
        geometry array.

        Discriminate on the terminal character, not on the presence of a
        bracket: a scalar geometry type is bare ``GEOMETRY`` or ends with ``)``
        (``GEOMETRY(<crs>)``), while every collection spelling ends with ``]``.
        A custom CRS carried as PROJJSON puts ``[...]`` INSIDE the parentheses
        (``GEOMETRY('PROJCS[...]')``), so a ``"[" not in up`` guard would wrongly
        drop a valid scalar geometry; the ``endswith(")")`` test keeps it.
        """
        positions = []
        for i, dtype in enumerate(relation.types):
            up = str(dtype).upper()
            if up == "GEOMETRY" or (up.startswith("GEOMETRY(") and up.endswith(")")):
                positions.append(i)
        return positions

    @staticmethod
    def _dedupe_names(names: List[str]) -> List[str]:
        """Deduplicate column names pandas-style: ``x`` -> ``x``, ``x_1``, ...

        Reproduces the output naming that DuckDB spatial 1.4.x produced natively
        when a feature property name collided with the geometry column name;
        1.5.x leaves both columns identically named, so the clash is resolved
        here instead. The first occurrence keeps the original name.
        """
        seen: dict = {}
        out: List[str] = []
        for name in names:
            if name not in seen:
                seen[name] = 0
                out.append(name)
                continue
            seen[name] += 1
            candidate = f"{name}_{seen[name]}"
            while candidate in seen:
                seen[name] += 1
                candidate = f"{name}_{seen[name]}"
            seen[candidate] = 0
            out.append(candidate)
        return out

    def _spatial_meta_layer(self, path: str) -> dict:
        """Return the first layer's fields and geometry CRS from ST_Read_Meta.

        Metadata-read failures propagate: a scan failure and a metadata failure
        must behave consistently (both raise), never silently yield a different
        schema. An absent or empty layer is an error, not an empty schema.
        Driver-injected columns that ST_Read_Meta does not list (for example the
        leading ``OGC_FID`` on DuckDB spatial 1.5.x) are NOT in these fields; the
        caller drops them so the output matches metadata and 1.4.x.
        """
        meta_rows = self._connection.sql(
            "SELECT layers FROM ST_Read_Meta(?)", params=[path]
        ).fetchall()
        if not meta_rows or not meta_rows[0][0]:
            raise ValueError(f"ST_Read_Meta returned no layer for {path!r}")
        return meta_rows[0][0][0]

    def _materialize_geometry_wkb(self, df: Any) -> Any:
        """Eagerly fetch a typed result with columns typed GEOMETRY in WKB.

        DuckDB's one-based positional references preserve distinct columns
        even when their aliases coincide. fetchdf then deduplicates the output
        names using DuckDB's usual rules (x, x_1, ...).
        CRS is read from the geometry type before WKB drops it, including for
        empty and all-null results. A bare GEOMETRY type has unknown CRS.
        """
        import duckdb

        if not isinstance(df, duckdb.DuckDBPyRelation):
            return df
        positions = self._geometry_column_positions(df)
        if not positions:
            return df.fetchdf()
        self._ensure_spatial()
        column_crs = {}
        for i in positions:
            dtype = str(df.types[i])
            # Qualified GEOMETRY and ST_CRS arrived together in DuckDB 1.5.
            # Inspect a typed NULL, never scan/re-execute the input relation.
            column_crs[i] = (
                self._connection.sql(f"SELECT ST_CRS(NULL::{dtype})").fetchone()[0]
                if dtype.upper() != "GEOMETRY" else None
            )
        projection = ", ".join(
            f'ST_AsWKB(#{i + 1}) AS {self._quote_ident(name)}'
            if i in positions else f'#{i + 1} AS {self._quote_ident(name)}'
            for i, name in enumerate(df.columns)
        )
        result = df.project(projection).fetchdf()
        result.attrs[_GEOMETRY_CRS_ATTR] = {result.columns[i]: crs for i, crs in column_crs.items()}
        return result

    def read_spatial(self, path: str, *, crs: Optional[str] = None, **kwargs: Any) -> Any:
        """Read a spatial file via DuckDB's ``ST_Read``.

        Geometry columns are identified by scalar type, not name, so a feature
        property named ``geom`` does not shadow the real geometry. The real
        columns are the attribute ``fields`` plus ``geometry_fields`` reported by
        ``ST_Read_Meta``. The scan is bound with collision-proof positional
        aliases (DuckDB spatial 1.5.x rejects a ``SELECT *`` over duplicate
        source names instead of auto-renaming them); any leading driver-injected
        column such as ``OGC_FID`` -- which 1.5.x emits, 1.4.x does not, and
        metadata does not list -- is dropped so the output schema is identical
        across DuckDB versions. Names are then restored from metadata with
        pandas-style deduplication, so a clashing ``geom`` property stays
        addressable while the real geometry becomes ``geom_1``.
        Preserve each geometry field's source CRS from file metadata; unknown
        CRS stays None. A supplied target ``crs`` reprojects the active geometry
        and requires a known source CRS.

        **kwargs: Forwarded for interface compatibility (unused in the current
        DuckDB path).
        """
        import geopandas as gpd
        self._ensure_spatial()
        layer = self._spatial_meta_layer(path)
        geometry_fields = layer.get("geometry_fields", []) or []
        meta_names = [f["name"] for f in (layer.get("fields", []) or [])]
        meta_names += [g["name"] for g in geometry_fields]
        ncols_expected = len(meta_names)
        # Collision-proof aliases wide enough for the real columns plus a margin
        # for any driver-injected columns. The prefix cannot clash with a real
        # attribute name, and scaling the width to the metadata count means a
        # legitimate column (even one literally named ``c0``) is always aliased
        # rather than left to collide with a generated alias.
        alias_width = ncols_expected + 16
        aliases = ", ".join(f"__su_geo_col_{i}__" for i in range(alias_width))
        relation = self._connection.sql(
            f"SELECT * FROM ST_Read(?) t({aliases})", params=[path]
        )
        positions = self._geometry_column_positions(relation)
        result = self._materialize_geometry_wkb(relation)
        # Drop leading driver-injected columns the metadata does not describe.
        drop = len(result.columns) - ncols_expected
        if drop > 0:
            result = result.iloc[:, drop:].copy()
            positions = [p - drop for p in positions if p >= drop]
        if ncols_expected > 0 and len(result.columns) == ncols_expected:
            result.columns = self._dedupe_names(meta_names)
        if not positions:
            return result
        geom_cols = [result.columns[i] for i in positions]
        from shapely import wkb as shapely_wkb
        def _parse_geom(g):
            if g is None:
                return None
            if isinstance(g, (bytes, bytearray)):
                return shapely_wkb.loads(bytes(g))
            if isinstance(g, str):
                return self._decode_geometry_text(g)
            # Scalar NA (pd.NA / NaN) or unexpected type -> missing geometry.
            return None
        # Parse every geometry column so a multi-geometry file keeps all of
        # them; the first becomes the active geometry.
        source_crses = {}
        for gc, field in zip(geom_cols, geometry_fields):
            metadata = field.get("crs") or {}
            authority = metadata.get("auth_name")
            code = metadata.get("auth_code")
            source_crs = (
                metadata.get("wkt") or metadata.get("projjson")
                or (f"{authority}:{code}" if authority and code else None)
                or metadata.get("proj4")
            )
            source_crses[gc] = source_crs
            parsed = result[gc].apply(_parse_geom)
            result[gc] = gpd.GeoSeries(parsed, index=result.index, crs=source_crs)
        result.attrs[_GEOMETRY_CRS_ATTR] = source_crses
        active_geom = geom_cols[0]
        gdf = gpd.GeoDataFrame(result, geometry=active_geom)
        return gdf.to_crs(crs) if crs is not None else gdf

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
        """Decode the selected WKB column of a materialized query result.

        Also accepts typed DuckDB relations (materialized via :meth:`to_pandas`),
        frames containing hex WKB, WKT or Shapely geometry, and GeoDataFrames.
        WKB uses the per-column CRS retained in pandas attrs; absent metadata
        means unknown CRS, not the default. WKT text retains default-CRS
        normalization. ``crs`` reprojects known CRS or assigns unknown CRS.
        """
        import geopandas as gpd
        import pandas as pd
        from siege_utilities.geo.crs import get_default_crs
        df = self.to_pandas(df)
        if isinstance(df, gpd.GeoDataFrame):
            if crs is None:
                return df
            return df.to_crs(crs) if df.crs is not None else df.set_crs(crs)
        if isinstance(df, pd.DataFrame) and geometry_col in df.columns:
            from shapely import wkb as shapely_wkb
            from shapely.geometry.base import BaseGeometry
            # Predicate must be on the dropped Series -- len(df) > 0 can
            # be true while df[geometry_col] is all-null, which would
            # IndexError on .iloc[0].
            non_null = df[geometry_col].dropna()
            sample = non_null.iloc[0] if not non_null.empty else None
            metadata = df.attrs.get(_GEOMETRY_CRS_ATTR, {})
            source_crs = metadata.get(geometry_col)
            if geometry_col not in metadata:
                source_crs = getattr(df[geometry_col], "crs", None)
                # Hex WKB, unlike WKT text, must not acquire the text default.
                if isinstance(sample, str):
                    head = sample[:32].strip()
                    is_hex = head and all(c in "0123456789abcdefABCDEF" for c in head)
                    if not is_hex:
                        source_crs = crs if crs is not None else get_default_crs()
            geoms = df[geometry_col]
            if sample is not None and not isinstance(sample, BaseGeometry):
                if isinstance(sample, (bytes, bytearray, memoryview)):
                    # DuckDB returns pd.NA (not None) for null geometry; guard
                    # with pd.isna so a null row does not reach shapely_wkb.loads.
                    geoms = df[geometry_col].apply(
                        lambda g: shapely_wkb.loads(bytes(g))
                        if (g is not None and not pd.isna(g)) else None
                    )
                else:
                    geoms = df[geometry_col].apply(
                        lambda g: self._decode_geometry_text(g) if isinstance(g, str) else g
                    )
            out = df.copy()
            out[geometry_col] = gpd.GeoSeries(geoms.values, index=out.index, crs=source_crs)
            result = gpd.GeoDataFrame(out, geometry=geometry_col, crs=source_crs)
            if crs is not None:
                return result.to_crs(crs) if result.crs is not None else result.set_crs(crs)
            return result
        raise ValueError(f"Cannot construct GeoDataFrame: column '{geometry_col}' not found")

    def from_geodataframe(self, gdf, geometry_col="geometry"):
        """Convert to standard WKB with the geometry column's CRS in pandas attrs."""
        import pandas as pd

        self._ensure_spatial()
        source_crs = getattr(gdf[geometry_col], "crs", None)
        metadata = {geometry_col: str(source_crs) if source_crs is not None else None}

        attr_cols = [c for c in gdf.columns if c != geometry_col]
        df = pd.DataFrame({c: gdf[c].values for c in attr_cols})
        df["_geom_wkb"] = [
            g.wkb_hex if (g is not None and not pd.isna(g)) else None
            for g in gdf[geometry_col]
        ]

        if df.empty:
            result = pd.DataFrame(columns=attr_cols + [geometry_col])
            result.attrs[_GEOMETRY_CRS_ATTR] = metadata
            return result

        tbl_name = f"_boundary_{id(gdf) % 100000}"
        self._connection.register(tbl_name, df)

        col_list = ", ".join(self._quote_ident(c) for c in attr_cols)
        # Emit standard WKB (ST_AsWKB) rather than DuckDB's internal GEOMETRY
        # type: fetchdf() would otherwise hand back bytes that are not valid
        # WKB, so to_geodataframe() fails with "Unknown WKB type 0". Guard the
        # leading comma so a geometry-only frame does not produce "SELECT ,".
        col_prefix = f"{col_list}, " if col_list else ""
        sql = (
            f"SELECT {col_prefix}"
            f"ST_AsWKB(ST_GeomFromWKB(UNHEX(_geom_wkb))) AS {self._quote_ident(geometry_col)} "
            f"FROM {tbl_name}"
        )
        result = self._connection.execute(sql).fetchdf()
        self._connection.unregister(tbl_name)
        result.attrs[_GEOMETRY_CRS_ATTR] = metadata
        return result


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
        """Read a CSV file via Spark.

        **kwargs: Forwarded to Spark's ``DataFrameReader.csv()``.
        """
        header = kwargs.pop("header", True)
        infer_schema = kwargs.pop("inferSchema", True)
        return (
            self._session.read
            .option("header", header)
            .option("inferSchema", infer_schema)
            .csv(path, **kwargs)
        )

    def read_parquet(self, path: str, **kwargs: Any) -> Any:
        """Read a Parquet file via Spark.

        **kwargs: Forwarded to Spark's ``DataFrameReader.parquet()``.
        """
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
            # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
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
        """Read a spatial file via GeoPandas and convert to a Spark DataFrame.

        **kwargs: Forwarded to :func:`geopandas.read_file`.
        """
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
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:8]
        lv = f"_sjoin_left_{tag}"
        rv = f"_sjoin_right_{tag}"
        st_func = f"ST_{predicate.capitalize()}"
        # Compute the projection -- which rejects a suffix collision with a
        # ValueError -- BEFORE registering any temp view, so a rejected join
        # leaves nothing behind in the session catalog (#1479 B2). Every view
        # registration happens INSIDE the cleanup scope and is tracked, so a
        # failure at any registration or at SQL analysis drops every view
        # registered so far (#1852 R2); the success path keeps the views for the
        # returned lazy frame.
        projection = self._spatial_join_projection(left, right, left_geom, right_geom, "l", "r")
        registered: list = []
        try:
            left.createOrReplaceTempView(lv)
            registered.append(lv)
            right.createOrReplaceTempView(rv)
            registered.append(rv)
            sql = (
                f"SELECT {projection} "
                f"FROM {lv} l {how.upper()} JOIN {rv} r "
                f"ON {st_func}(ST_GeomFromText(l.{left_geom}), ST_GeomFromText(r.{right_geom}))"
            )
            return self._session.sql(sql)
        except Exception:
            for view in registered:
                self._session.catalog.dropTempView(view)
            raise

    def _spatial_join_projection(self, left, right, left_geom, right_geom, left_alias, right_alias):
        """Keep the left geometry and apply the invariant's attribute suffixes."""
        from collections import Counter

        right_columns = [c for c in right.columns if c != right_geom]
        shared = set(left.columns) & set(right_columns)
        output = [
            (left_alias, c, c + "_left" if c in shared and c != left_geom else c)
            for c in left.columns
        ] + [(right_alias, c, c + "_right" if c in shared else c) for c in right_columns]
        case_sensitive = self._session.conf.get("spark.sql.caseSensitive", "false").lower() == "true"
        counts = Counter(name if case_sensitive else name.lower() for _, _, name in output)
        duplicates = sorted(name for name, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"SparkEngine spatial join: duplicate output column names: {duplicates}")

        def quote(name):
            return "`" + name.replace("`", "``") + "`"

        return ", ".join(f"{alias}.{quote(column)} AS {quote(name)}" for alias, column, name in output)

    def buffer(self, df, distance, geometry_col="geometry", *, crs=None):
        self._ensure_sedona()
        if crs is not None:
            # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
            raise NotImplementedError(
                "CRS reprojection before buffer is not yet supported in the "
                "Sedona engine. Reproject your data beforehand, or omit crs."
            )
        from siege_utilities.core.sql_safety import validate_sql_identifier_in as validate_identifier_in
        validate_identifier_in(geometry_col, df.columns, label="geometry column")
        # `distance` is interpolated as a float -- coerce so a malicious
        # caller can't sneak SQL via a string.
        distance_lit = float(distance)
        import uuid as _uuid
        view = f"_buf_tbl_{_uuid.uuid4().hex[:8]}"
        df.createOrReplaceTempView(view)
        # Replace the geometry column in place (contract: buffer replaces the
        # geometry) so a subsequent default spatial op uses the buffered
        # geometry on Spark, matching the pandas path. Emitting a separate
        # geometry_buffered column left the original geometry active.
        other_cols = [c for c in df.columns if c != geometry_col]
        select_list = ", ".join(
            [f"`{c}`" for c in other_cols]
            + [
                f"ST_AsText(ST_Buffer(ST_GeomFromText(`{geometry_col}`), "
                f"{distance_lit})) AS `{geometry_col}`"
            ]
        )
        sql = f"SELECT {select_list} FROM {view}"
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
            wkt_escaped = escape_string_literal(wkt_str, dialect="spark")
            sql = (
                f"SELECT *, ST_Distance(ST_GeomFromText({geometry_col}), "
                f"ST_GeomFromText('{wkt_escaped}')) AS _distance FROM {lv}"
            )
        else:
            # Contract: a DataFrame 'other' means row-aligned pairwise distance
            # (row i of df paired with row i of other). Spark DataFrames have no
            # positional row order, so `FROM l, r` is a Cartesian product, not
            # aligned pairs, and the projection dropped every identifier. Reject
            # rather than return a silently wrong N*M result.
            raise NotImplementedError(
                "SparkEngine.distance does not support DataFrame-to-DataFrame "
                "row-aligned pairwise distance: Spark has no positional row "
                "alignment, so pairing by position is undefined (a cross join "
                "would be N*M rows, not N aligned pairs). Pass a single geometry, "
                "or join the two frames on an explicit key first and compute "
                "ST_Distance on the joined geometry columns."
            )
        return self._session.sql(sql)

    def to_geodataframe(self, df, geometry_col="geometry", *, crs=None):
        import geopandas as gpd
        from siege_utilities.geo.crs import get_default_crs
        from shapely import wkt
        pdf = df.toPandas()
        if geometry_col in pdf.columns:
            # Spark/Sedona carries no CRS metadata, so the stored WKT
            # coordinates are in whatever CRS the caller wrote them in
            # (read_spatial(crs="EPSG:3857") stores projected metres). We
            # ASSIGN the requested crs (default EPSG:4326) to the parsed
            # geometry -- we do NOT reproject, because the stored numbers
            # are already in the caller-declared CRS. Reprojecting here
            # would treat projected metres as degrees and blow up to
            # POINT(inf inf). Round-trip CRS fidelity is the caller's
            # responsibility: pass the crs the coordinates are actually in.
            target_crs = crs or get_default_crs()
            parsed = pdf[geometry_col].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            # Bind the parsed geometry back under geometry_col as the active
            # GeoSeries (not via the GeoDataFrame geometry= kwarg, which would
            # leave the column as plain strings). This keeps .buffer()/
            # .distance() working on the returned frame.
            pdf[geometry_col] = gpd.GeoSeries(parsed.values, index=pdf.index, crs=target_crs)
            return gpd.GeoDataFrame(pdf, geometry=geometry_col, crs=target_crs)
        raise ValueError(f"Cannot construct GeoDataFrame: column '{geometry_col}' not found")

    def from_geodataframe(self, gdf, geometry_col="geometry"):
        """Convert a GeoDataFrame to a Spark DataFrame with WKT geometry.

        The base implementation returns the GeoDataFrame unchanged, which left
        boundary-provider conversion handing a GeoDataFrame into Spark-only
        calls (createOrReplaceTempView). Serialize geometry to WKT and build a
        real Spark DataFrame so the Spark spatial methods (which read
        ST_GeomFromText(geometry_col)) receive engine-native input.

        Spark/Sedona carries no CRS metadata. Coordinates are serialized to
        WKT exactly as they are in *gdf* -- no reprojection -- so a
        read_spatial(crs=...) -> from_geodataframe -> to_geodataframe(crs=...)
        round-trip preserves the numbers unchanged. The caller is responsible
        for passing the same crs to to_geodataframe that the coordinates are
        actually in; normalizing to a default CRS here would corrupt data
        that entered in a projected CRS.
        """
        import pandas as pd

        if len(gdf) == 0:
            raise ValueError(
                "Cannot convert an empty GeoDataFrame to Spark: there are no "
                "rows to infer a schema from. Provide at least one row."
            )

        if getattr(gdf, "crs", None) is None:
            log.warning(
                "from_geodataframe received a GeoDataFrame with no CRS. "
                "Coordinates are serialized as-is and Spark/Sedona stores no "
                "CRS metadata; pass the matching crs to to_geodataframe on "
                "read-back to avoid mislabeling."
            )

        attr_cols = [c for c in gdf.columns if c != geometry_col]
        geoms = [(g.wkt if g is not None else None) for g in gdf[geometry_col]]
        pdf = pd.DataFrame({c: gdf[c].values for c in attr_cols})

        if any(v is not None for v in geoms):
            pdf[geometry_col] = geoms
            return self._session.createDataFrame(pdf)

        # All geometries are null. Spark cannot infer the type of an all-null
        # column, so build from the attribute columns and attach geometry as an
        # explicitly-typed null StringType column (mirrors geopandas_to_spark's
        # #1338 handling). Requires at least one attribute column.
        if not attr_cols:
            raise ValueError(
                "Cannot convert a GeoDataFrame whose only column is an all-null "
                "geometry: Spark has no column to infer a schema from."
            )
        from pyspark.sql.functions import lit
        from pyspark.sql.types import StringType
        sdf = self._session.createDataFrame(pdf)
        return sdf.withColumn(geometry_col, lit(None).cast(StringType()))

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
        # Reject a suffix collision before registering any temp view (#1479 B2).
        # Every view registration happens INSIDE the cleanup scope and is tracked,
        # so a failure at any registration or at SQL analysis drops every view
        # registered so far (#1852 R2); the success path keeps the views for the
        # returned lazy frame.
        projection = self._spatial_join_projection(points, polygons, point_geom, polygon_geom, "p", "poly")
        registered: list = []
        try:
            points.createOrReplaceTempView(pv)
            registered.append(pv)
            broadcast(polygons).createOrReplaceTempView(poly_v)
            registered.append(poly_v)
            return self._session.sql(
                f"SELECT {projection} "
                f"FROM {pv} p {how.upper()} JOIN {poly_v} poly "
                f"ON ST_Contains(ST_GeomFromText(poly.{polygon_geom}), "
                f"ST_GeomFromText(p.{point_geom}))"
            )
        except Exception:
            for view in registered:
                self._session.catalog.dropTempView(view)
            raise

    def multi_assign(self, points, boundary_layers, *, point_geom="geometry"):
        """Assign all layers lazily without collecting a Spark frame."""
        from pyspark.sql import functions as F

        result = points
        for layer_name, polygons in boundary_layers.items():
            names = self._boundary_column_names(polygons.columns, layer_name, result.columns)
            prefixed = polygons.select(*[
                F.col("`" + c.replace("`", "``") + "`").alias(names.get(c, c))
                for c in polygons.columns
            ])
            result = self.assign_boundaries(result, prefixed, point_geom=point_geom)
        return result

    def nearest(self, points, targets, *, k=1, max_distance=None,
                point_geom="geometry", target_geom="geometry"):
        """Find up to k targets per point, retaining unmatched points with nulls.

        Keep the point geometry and suffix shared attributes with _left/_right.
        Spark has no index, so index_right is a generated target row identifier
        (unique, not necessarily contiguous). The lazy plan assigns point
        identities once, without checkpoints or session temporary views.
        A single-sided input distance is replaced by the computed distance.
        Shared input distance columns are preserved as distance_left and
        distance_right. An input index_right or duplicate output names raise
        ValueError. Drop or rename index_right before passing a previous nearest
        result into another join.
        """
        from collections import Counter
        from pyspark.sql import Window, functions as F
        from siege_utilities.core.sql_safety import validate_sql_identifier_in as validate_identifier_in
        if "index_right" in points.columns or "index_right" in targets.columns:
            raise ValueError("'index_right' cannot be a column name in the frames being joined")
        validate_identifier_in(point_geom, points.columns, label="point geometry column")
        validate_identifier_in(target_geom, targets.columns, label="target geometry column")
        k_lit = int(k)
        max_distance_lit = float(max_distance) if max_distance is not None else None

        shared_distance = "distance" in points.columns and "distance" in targets.columns
        point_columns = [c for c in points.columns if c != "distance" or shared_distance]
        target_columns = [
            c for c in targets.columns if c != target_geom and (c != "distance" or shared_distance)
        ]
        shared = set(point_columns) & set(target_columns)
        point_output = [(c, c + "_left" if c in shared and c != point_geom else c) for c in point_columns]
        target_output = [(c, c + "_right" if c in shared else c) for c in target_columns]
        output_names = (
            [name for _, name in point_output] + ["index_right"]
            + [name for _, name in target_output] + ["distance"]
        )
        # Spark normally resolves names without regard to case.
        case_sensitive = self._session.conf.get("spark.sql.caseSensitive", "false").lower() == "true"
        name_counts = Counter(name if case_sensitive else name.lower() for name in output_names)
        duplicates = sorted(name for name, count in name_counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"SparkEngine.nearest: duplicate output column names: {duplicates}")

        self._ensure_sedona()
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:8]
        point_id = f"_nn_point_id_{tag}"
        target_id = f"_nn_target_id_{tag}"
        distance = f"_nn_distance_{tag}"
        rank = f"_nn_rank_{tag}"

        def quote(column):
            return "`" + column.replace("`", "``") + "`"

        # Each point occurs in one branch, so its identity needs no checkpoint.
        point_rows = points.withColumn(point_id, F.monotonically_increasing_id()).alias("p")
        target_rows = targets.withColumn(target_id, F.monotonically_increasing_id()).alias("t")
        candidates = point_rows.join(target_rows, F.lit(True), "left").withColumn(
            distance,
            F.expr(
                f"ST_Distance(ST_GeomFromText(p.{quote(point_geom)}), "
                f"ST_GeomFromText(t.{quote(target_geom)}))"
            ),
        )
        # Rank eligible distances first and retain one null row if none qualify.
        # Computing distance after the outer join also supports Python SQL UDFs,
        # which Spark cannot evaluate in a two-sided outer-join predicate.
        eligible = F.col(distance).isNotNull() & F.lit(k_lit > 0)
        if max_distance_lit is not None:
            eligible = eligible & (F.col(distance) <= F.lit(max_distance_lit))
        candidates = candidates.withColumn(distance, F.when(eligible, F.col(distance)))
        window = Window.partitionBy(point_id).orderBy(F.col(distance).asc_nulls_last(), F.col(target_id))
        ranked = candidates.withColumn(rank, F.row_number().over(window))
        matched = F.col(distance).isNotNull()
        selected = ranked.where(
            (F.col(rank) <= max(k_lit, 1)) & (matched | (F.col(rank) == 1))
        )
        output = [
            F.col(f"p.{quote(column)}").alias(name) for column, name in point_output
        ]
        output.append(F.when(matched, F.col(target_id)).alias("index_right"))
        output.extend(
            F.when(matched, F.col(f"t.{quote(column)}")).alias(name)
            for column, name in target_output
        )
        output.append(F.col(distance).alias("distance"))
        return selected.select(*output)


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
        # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
        raise NotImplementedError(
            "PostGISEngine.index_points: compute cell IDs at ingest time "
            "(via PandasEngine or s2_index_points), store as BIGINT column, "
            "and use s2_cells_to_ranges() for region queries. "
            "See engine.index_points docstring for the pattern."
        )

    # -- I/O ----------------------------------------------------------------

    def read_csv(self, path: str, **kwargs: Any) -> Any:
        """Read a CSV file.

        **kwargs: Forwarded to :func:`pandas.read_csv`.
        """
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
        normalised = _normalise_pandas_aggs(agg_dict)
        grouped = df.groupby(list(group_cols), dropna=False)
        return _aggregate_pandas_groups(grouped, normalised)

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
        """Read a spatial file or execute a spatial SQL query.

        **kwargs: Forwarded to :func:`geopandas.read_file`.
        """
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
        from siege_utilities.geo.crs import get_default_crs
        if isinstance(df, gpd.GeoDataFrame):
            if crs is None:
                return df
            return df.to_crs(crs) if df.crs is not None else df.set_crs(crs)
        import pandas as pd
        if isinstance(df, pd.DataFrame) and geometry_col in df.columns:
            from shapely import wkt
            target_crs = crs or get_default_crs()
            parsed = df[geometry_col].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            out = df.copy()
            out[geometry_col] = gpd.GeoSeries(parsed.values, index=out.index, crs=target_crs)
            return gpd.GeoDataFrame(out, geometry=geometry_col, crs=target_crs)
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
