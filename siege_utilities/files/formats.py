"""Unified output format support for spatial and tabular data.

Provides ``save_spatial()`` and ``save_tabular()`` dispatchers that write
data to disk in the requested format.  Enum types ``SpatialFormat`` and
``TabularFormat`` enumerate supported file types.

Usage::

    from siege_utilities.files.formats import save_spatial, SpatialFormat

    save_spatial(gdf, "/tmp/districts.parquet", SpatialFormat.GEOPARQUET)
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from pandas import DataFrame
    from geopandas import GeoDataFrame

log = logging.getLogger(__name__)

FilePath = Union[str, Path]


# ---------------------------------------------------------------------------
# Format enumerations
# ---------------------------------------------------------------------------

class SpatialFormat(str, Enum):
    """Supported spatial output formats."""

    GEOPARQUET = "geoparquet"
    PARQUET = "parquet"
    GPKG = "gpkg"
    GEOJSON = "geojson"
    TOPOJSON = "topojson"
    CSV = "csv"
    SHAPEFILE = "shp"


class TabularFormat(str, Enum):
    """Supported tabular output formats."""

    PARQUET = "parquet"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


# ---------------------------------------------------------------------------
# Spatial save
# ---------------------------------------------------------------------------

def save_spatial(
    gdf: GeoDataFrame,
    path: FilePath,
    fmt: SpatialFormat = SpatialFormat.GEOPARQUET,
    **kwargs,
) -> Path:
    """Write a GeoDataFrame to *path* in the requested format.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Data to write.
    path : str or Path
        Destination file path.
    fmt : SpatialFormat
        Output format (default ``GEOPARQUET``).
    **kwargs
        Passed through to the underlying writer.

    Returns
    -------
    Path to the written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt is SpatialFormat.GEOPARQUET:
        gdf.to_parquet(str(path), **kwargs)

    elif fmt is SpatialFormat.PARQUET:
        # Drop geometry, write plain parquet via pandas
        import pandas as pd

        df = pd.DataFrame(gdf.drop(columns="geometry"))
        df.to_parquet(str(path), **kwargs)

    elif fmt is SpatialFormat.GPKG:
        gdf.to_file(str(path), driver="GPKG", **kwargs)

    elif fmt is SpatialFormat.GEOJSON:
        gdf.to_file(str(path), driver="GeoJSON", **kwargs)

    elif fmt is SpatialFormat.TOPOJSON:
        try:
            import topojson as tp
        except ImportError as exc:
            raise ImportError(
                "topojson is required for TopoJSON output. "
                "Install with: pip install topojson"
            ) from exc
        topo = tp.Topology(gdf, **kwargs)
        path.write_text(topo.to_json())

    elif fmt is SpatialFormat.CSV:
        import pandas as pd

        df = gdf.copy()
        df["geometry"] = df.geometry.astype(str)
        pd.DataFrame(df).to_csv(str(path), index=False, **kwargs)

    elif fmt is SpatialFormat.SHAPEFILE:
        gdf.to_file(str(path), driver="ESRI Shapefile", **kwargs)

    else:
        raise ValueError(f"Unsupported spatial format: {fmt}")

    log.info("Saved spatial data to %s (%s)", path, fmt.value)
    return path


# ---------------------------------------------------------------------------
# Tabular save
# ---------------------------------------------------------------------------

def save_tabular(
    df: DataFrame,
    path: FilePath,
    fmt: TabularFormat = TabularFormat.PARQUET,
    **kwargs,
) -> Path:
    """Write a DataFrame to *path* in the requested format.

    Parameters
    ----------
    df : pandas.DataFrame
        Data to write.
    path : str or Path
        Destination file path.
    fmt : TabularFormat
        Output format (default ``PARQUET``).
    **kwargs
        Passed through to the underlying writer.

    Returns
    -------
    Path to the written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt is TabularFormat.PARQUET:
        df.to_parquet(str(path), **kwargs)

    elif fmt is TabularFormat.CSV:
        df.to_csv(str(path), index=False, **kwargs)

    elif fmt is TabularFormat.EXCEL:
        df.to_excel(str(path), index=False, **kwargs)

    elif fmt is TabularFormat.JSON:
        df.to_json(str(path), orient="records", **kwargs)

    else:
        raise ValueError(f"Unsupported tabular format: {fmt}")

    log.info("Saved tabular data to %s (%s)", path, fmt.value)
    return path


__all__ = [
    "SpatialFormat",
    "TabularFormat",
    "save_spatial",
    "save_tabular",
]
