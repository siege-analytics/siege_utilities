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

    from siege_utilities.files.operations import atomic_write_path

    if fmt is SpatialFormat.GEOPARQUET:
        with atomic_write_path(path) as tmp:
            gdf.to_parquet(str(tmp), **kwargs)

    elif fmt is SpatialFormat.PARQUET:
        import pandas as pd

        df = pd.DataFrame(gdf.drop(columns="geometry"))
        with atomic_write_path(path) as tmp:
            df.to_parquet(str(tmp), **kwargs)

    elif fmt is SpatialFormat.GPKG:
        with atomic_write_path(path) as tmp:
            gdf.to_file(str(tmp), driver="GPKG", **kwargs)

    elif fmt is SpatialFormat.GEOJSON:
        with atomic_write_path(path) as tmp:
            gdf.to_file(str(tmp), driver="GeoJSON", **kwargs)

    elif fmt is SpatialFormat.TOPOJSON:
        try:
            import topojson as tp
        except ImportError as exc:
            raise ImportError(
                "topojson is required for TopoJSON output. "
                "Install with: pip install topojson"
            ) from exc
        topo = tp.Topology(gdf, **kwargs)
        with atomic_write_path(path) as tmp:
            tmp.write_text(topo.to_json())

    elif fmt is SpatialFormat.CSV:
        import pandas as pd

        df = gdf.copy()
        df["geometry"] = df.geometry.astype(str)
        with atomic_write_path(path) as tmp:
            pd.DataFrame(df).to_csv(str(tmp), index=False, **kwargs)

    elif fmt is SpatialFormat.SHAPEFILE:
        from siege_utilities.files.operations import atomic_write_shapefile
        atomic_write_shapefile(gdf, path, **kwargs)

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

    from siege_utilities.files.operations import atomic_write_path

    if fmt is TabularFormat.PARQUET:
        with atomic_write_path(path) as tmp:
            df.to_parquet(str(tmp), **kwargs)

    elif fmt is TabularFormat.CSV:
        with atomic_write_path(path) as tmp:
            df.to_csv(str(tmp), index=False, **kwargs)

    elif fmt is TabularFormat.EXCEL:
        with atomic_write_path(path) as tmp:
            df.to_excel(str(tmp), index=False, **kwargs)

    elif fmt is TabularFormat.JSON:
        with atomic_write_path(path) as tmp:
            df.to_json(str(tmp), orient="records", **kwargs)

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
