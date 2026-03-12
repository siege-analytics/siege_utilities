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

    def __init__(self, spark: Any = None) -> None:
        try:
            import pyspark  # noqa: F401
        except ImportError:
            raise ImportError(
                "PySpark is not installed. Install it with: pip install pyspark"
            ) from None
        self._spark = spark

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
