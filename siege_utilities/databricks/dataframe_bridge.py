"""Bridges for Pandas/GeoPandas and Spark DataFrames."""

from typing import Any, Optional

import pandas as pd

from .session import get_active_spark_session


def pandas_to_spark(dataframe: pd.DataFrame, spark: Optional[Any] = None) -> Any:
    """Convert a Pandas DataFrame to a Spark DataFrame."""
    if spark is None:
        spark = get_active_spark_session(create_if_missing=True)
    return spark.createDataFrame(dataframe)


def spark_to_pandas(dataframe: Any, limit: Optional[int] = None) -> pd.DataFrame:
    """Convert a Spark DataFrame to a Pandas DataFrame, with optional limit."""
    if limit is not None:
        dataframe = dataframe.limit(int(limit))
    return dataframe.toPandas()


def _validate_geometry_format(geometry_format: str) -> str:
    """Validate supported geometry format names."""
    clean_format = geometry_format.lower().strip()
    if clean_format not in {"wkt", "wkb_hex"}:
        raise ValueError("geometry_format must be one of: wkt, wkb_hex")
    return clean_format


def geopandas_to_spark(
    dataframe: Any,
    spark: Optional[Any] = None,
    geometry_column: str = "geometry",
    geometry_format: str = "wkt",
    crs_column: str = "geometry_crs",
) -> Any:
    """
    Convert a GeoPandas DataFrame to Spark using a serializable geometry column.

    Geometry is serialized as WKT or WKB hex to avoid runtime-specific geospatial
    library requirements on Spark clusters.
    """
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise ImportError("GeoPandas not available. Install with: pip install geopandas") from exc

    geom_format = _validate_geometry_format(geometry_format)
    if not isinstance(dataframe, gpd.GeoDataFrame):
        raise TypeError("dataframe must be a GeoPandas GeoDataFrame")
    if geometry_column not in dataframe.columns:
        raise ValueError(f"geometry column not found: {geometry_column}")

    pdf = pd.DataFrame(dataframe.copy())

    if geom_format == "wkt":
        pdf[geometry_column] = dataframe[geometry_column].apply(
            lambda geom: None if geom is None else geom.wkt
        )
    else:
        pdf[geometry_column] = dataframe[geometry_column].apply(
            lambda geom: None if geom is None else geom.wkb_hex
        )

    pdf[crs_column] = str(dataframe.crs) if dataframe.crs else None
    return pandas_to_spark(pdf, spark=spark)


def spark_to_geopandas(
    dataframe: Any,
    geometry_column: str = "geometry",
    geometry_format: str = "wkt",
    crs: Optional[str] = None,
) -> Any:
    """
    Convert Spark DataFrame with serialized geometry into GeoPandas DataFrame.

    Supports WKT and WKB hex serialization formats.
    """
    try:
        import geopandas as gpd
        from shapely import wkb, wkt
    except ImportError as exc:
        raise ImportError(
            "GeoPandas and Shapely are required. Install with: pip install geopandas shapely"
        ) from exc

    geom_format = _validate_geometry_format(geometry_format)
    pdf = spark_to_pandas(dataframe)

    if geometry_column not in pdf.columns:
        raise ValueError(f"geometry column not found: {geometry_column}")

    if geom_format == "wkt":
        pdf[geometry_column] = pdf[geometry_column].apply(
            lambda value: None if value is None else wkt.loads(value)
        )
    else:
        pdf[geometry_column] = pdf[geometry_column].apply(
            lambda value: None if value is None else wkb.loads(bytes.fromhex(value))
        )

    return gpd.GeoDataFrame(pdf, geometry=geometry_column, crs=crs)
