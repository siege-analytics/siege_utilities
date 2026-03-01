"""
Pure-Python persistence for temporal boundaries and demographics.

Storage layout (Parquet default):
    {root}/boundaries/{geography_type}/{vintage_year}.parquet
    {root}/demographics/{geography_type}/{dataset}_{year}.parquet
    {root}/timeseries/{geography_type}/{variable_code}_{dataset}.parquet

GeoPackage is available as an alternative via format="gpkg" (boundaries only).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import geopandas as gpd
    import pandas as pd

log = logging.getLogger(__name__)

_DEFAULT_ROOT = Path.home() / ".siege_utilities" / "store" / "temporal"
_SINGLETON: Optional["TemporalDataStore"] = None


class TemporalDataStore:
    """Pure-Python persistence for temporal geographic data.

    Follows the CrosswalkClient pattern: class with module-level convenience
    functions for the common case.
    """

    SUPPORTED_FORMATS = ("parquet", "gpkg")

    def __init__(
        self,
        root_dir: str | Path | None = None,
        format: str = "parquet",
    ) -> None:
        self.root = Path(root_dir) if root_dir else _DEFAULT_ROOT
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format {format!r}; choose from {self.SUPPORTED_FORMATS}"
            )
        self.format = format

    # ------------------------------------------------------------------
    # Boundaries
    # ------------------------------------------------------------------

    def save_boundaries(
        self,
        gdf: "gpd.GeoDataFrame",
        geography_type: str,
        vintage_year: int,
    ) -> Path:
        """Persist a GeoDataFrame of boundaries."""
        dest = self._boundaries_path(geography_type, vintage_year)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if self.format == "gpkg":
            gdf.to_file(str(dest), driver="GPKG")
        else:
            gdf.to_parquet(str(dest), index=False)

        log.info("Saved %d boundaries to %s", len(gdf), dest)
        return dest

    def load_boundaries(
        self,
        geography_type: str,
        vintage_year: int,
        state_fips: str | None = None,
    ) -> "gpd.GeoDataFrame":
        """Load boundaries for a geography type and vintage year."""
        import geopandas as _gpd

        path = self._boundaries_path(geography_type, vintage_year)
        if not path.exists():
            raise FileNotFoundError(
                f"No boundaries for {geography_type}/{vintage_year} at {path}"
            )

        if self.format == "gpkg":
            gdf = _gpd.read_file(str(path))
        else:
            gdf = _gpd.read_parquet(str(path))

        if state_fips and "state_fips" in gdf.columns:
            gdf = gdf[gdf["state_fips"] == state_fips].copy()

        return gdf

    def query_boundaries_at_date(
        self,
        geography_type: str,
        query_date: date,
        state_fips: str | None = None,
    ) -> "gpd.GeoDataFrame":
        """Load the best-matching vintage for a given date.

        If boundaries have valid_from/valid_to columns, those are checked.
        Otherwise, the nearest vintage_year <= query_date.year is used.
        """
        vintages = self.list_available_vintages(geography_type)
        if not vintages:
            raise FileNotFoundError(
                f"No vintages found for {geography_type}"
            )

        # Pick the most recent vintage on or before query_date
        candidates = [v for v in vintages if v <= query_date.year]
        if not candidates:
            candidates = vintages  # fall back to earliest available
        best = max(candidates)

        gdf = self.load_boundaries(geography_type, best, state_fips)

        # Apply valid_from/valid_to filtering if columns exist
        if "valid_from" in gdf.columns and "valid_to" in gdf.columns:
            from .query import temporal_filter
            gdf = temporal_filter(
                gdf, query_date,
                valid_from_col="valid_from",
                valid_to_col="valid_to",
            )

        return gdf

    def list_available_vintages(self, geography_type: str) -> list[int]:
        """List vintage years available on disk for a geography type."""
        dir_path = self.root / "boundaries" / geography_type
        if not dir_path.exists():
            return []

        ext = ".gpkg" if self.format == "gpkg" else ".parquet"
        vintages = []
        for p in dir_path.glob(f"*{ext}"):
            try:
                vintages.append(int(p.stem))
            except ValueError:
                continue
        return sorted(vintages)

    # ------------------------------------------------------------------
    # Demographics
    # ------------------------------------------------------------------

    def save_demographics(
        self,
        snapshots: "pd.DataFrame",
        geography_type: str,
        dataset: str = "acs5",
        year: int | None = None,
    ) -> Path:
        """Persist demographic snapshot data as Parquet."""
        import pandas as _pd

        if year is None:
            if "year" in snapshots.columns:
                year = int(snapshots["year"].iloc[0])
            else:
                raise ValueError("year must be provided or present in DataFrame")

        dest = self._demographics_path(geography_type, dataset, year)
        dest.parent.mkdir(parents=True, exist_ok=True)
        snapshots.to_parquet(str(dest), index=False)
        log.info("Saved %d demographic rows to %s", len(snapshots), dest)
        return dest

    def load_demographics(
        self,
        geography_type: str,
        year: int | None = None,
        dataset: str = "acs5",
    ) -> "pd.DataFrame":
        """Load demographic data. If year is None, loads all available years."""
        import pandas as _pd

        base = self.root / "demographics" / geography_type
        if not base.exists():
            raise FileNotFoundError(
                f"No demographics for {geography_type} at {base}"
            )

        if year is not None:
            path = self._demographics_path(geography_type, dataset, year)
            if not path.exists():
                raise FileNotFoundError(
                    f"No demographics for {geography_type}/{dataset}_{year}"
                )
            return _pd.read_parquet(str(path))

        # Load all matching files
        pattern = f"{dataset}_*.parquet"
        frames = []
        for p in sorted(base.glob(pattern)):
            frames.append(_pd.read_parquet(str(p)))
        if not frames:
            raise FileNotFoundError(
                f"No {dataset} demographics found for {geography_type}"
            )
        return _pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Time Series
    # ------------------------------------------------------------------

    def save_timeseries(
        self,
        series: "pd.DataFrame",
        geography_type: str,
        variable_code: str | None = None,
        dataset: str = "acs5",
    ) -> Path:
        """Persist pre-computed time-series data as Parquet."""
        if variable_code is None:
            if "variable_code" in series.columns:
                variable_code = str(series["variable_code"].iloc[0])
            else:
                raise ValueError(
                    "variable_code must be provided or present in DataFrame"
                )

        dest = self._timeseries_path(geography_type, variable_code, dataset)
        dest.parent.mkdir(parents=True, exist_ok=True)
        series.to_parquet(str(dest), index=False)
        log.info("Saved %d timeseries rows to %s", len(series), dest)
        return dest

    def load_timeseries(
        self,
        geography_type: str,
        variable_code: str,
        dataset: str = "acs5",
    ) -> "pd.DataFrame":
        """Load pre-computed time-series data."""
        import pandas as _pd

        path = self._timeseries_path(geography_type, variable_code, dataset)
        if not path.exists():
            raise FileNotFoundError(
                f"No timeseries for {geography_type}/{variable_code}_{dataset}"
            )
        return _pd.read_parquet(str(path))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _boundaries_path(self, geography_type: str, vintage_year: int) -> Path:
        ext = ".gpkg" if self.format == "gpkg" else ".parquet"
        return self.root / "boundaries" / geography_type / f"{vintage_year}{ext}"

    def _demographics_path(
        self, geography_type: str, dataset: str, year: int
    ) -> Path:
        return (
            self.root / "demographics" / geography_type / f"{dataset}_{year}.parquet"
        )

    def _timeseries_path(
        self, geography_type: str, variable_code: str, dataset: str
    ) -> Path:
        return (
            self.root / "timeseries" / geography_type
            / f"{variable_code}_{dataset}.parquet"
        )


# ------------------------------------------------------------------
# Module-level convenience functions
# ------------------------------------------------------------------


def get_temporal_store(
    root_dir: str | Path | None = None,
    format: str = "parquet",
) -> TemporalDataStore:
    """Get or create the singleton TemporalDataStore."""
    global _SINGLETON
    if _SINGLETON is None or (root_dir is not None):
        _SINGLETON = TemporalDataStore(root_dir=root_dir, format=format)
    return _SINGLETON


def save_boundaries(
    gdf: "gpd.GeoDataFrame",
    geography_type: str,
    vintage_year: int,
    **kwargs,
) -> Path:
    """Save boundaries via the default store."""
    return get_temporal_store(**kwargs).save_boundaries(gdf, geography_type, vintage_year)


def load_boundaries(
    geography_type: str,
    vintage_year: int,
    state_fips: str | None = None,
    **kwargs,
) -> "gpd.GeoDataFrame":
    """Load boundaries via the default store."""
    return get_temporal_store(**kwargs).load_boundaries(
        geography_type, vintage_year, state_fips
    )


def query_boundaries_at_date(
    geography_type: str,
    query_date: date,
    state_fips: str | None = None,
    **kwargs,
) -> "gpd.GeoDataFrame":
    """Query boundaries at a date via the default store."""
    return get_temporal_store(**kwargs).query_boundaries_at_date(
        geography_type, query_date, state_fips
    )


def save_demographics(
    snapshots: "pd.DataFrame",
    geography_type: str,
    dataset: str = "acs5",
    year: int | None = None,
    **kwargs,
) -> Path:
    """Save demographics via the default store."""
    return get_temporal_store(**kwargs).save_demographics(
        snapshots, geography_type, dataset, year
    )


def load_demographics(
    geography_type: str,
    year: int | None = None,
    dataset: str = "acs5",
    **kwargs,
) -> "pd.DataFrame":
    """Load demographics via the default store."""
    return get_temporal_store(**kwargs).load_demographics(
        geography_type, year, dataset
    )
