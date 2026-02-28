"""
NCES data download infrastructure for locale boundaries and school locations.

Downloads pre-computed locale boundary polygons, school geocoded locations,
and district administrative data from the NCES EDGE program.

Uses siege_utilities.files.remote for HTTP downloads and caches locally
to avoid re-downloading.
"""

from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from siege_utilities.config.nces_constants import (
    AVAILABLE_NCES_YEARS,
    DEFAULT_NCES_YEAR,
    NCES_DOWNLOAD_ENDPOINTS,
    NCES_FILE_PATTERNS,
)

log = logging.getLogger(__name__)

# Column name mappings for NCES locale boundary shapefiles
LOCALE_BOUNDARY_COLUMNS = {
    "LOCALE": "locale_code",
    "LOCALE_TYPE": "locale_category",
    "NAME": "name",
}

# Column name mappings for school location files
SCHOOL_LOCATION_COLUMNS = {
    "NCESSCH": "ncessch",
    "SCH_NAME": "school_name",
    "LEAID": "lea_id",
    "ST": "state_abbr",
    "LOCALE": "locale_code",
    "LAT": "latitude",
    "LON": "longitude",
    "SURVYEAR": "survey_year",
}

# Column name mappings for district administrative data
DISTRICT_DATA_COLUMNS = {
    "LEAID": "lea_id",
    "LEA_NAME": "lea_name",
    "ST": "state_abbr",
    "LOCALE": "locale_code",
    "SURVYEAR": "survey_year",
}


class NCESDownloadError(Exception):
    """Raised when an NCES download fails."""


class NCESDownloader:
    """Download NCES locale boundaries, school locations, and district data.

    Downloads from the NCES EDGE (Education Demographic and Geographic
    Estimates) program and returns data as GeoDataFrames.

    Args:
        cache_dir: Directory for caching downloaded files. Defaults to
            a temporary directory.
        timeout: HTTP request timeout in seconds.

    Example::

        downloader = NCESDownloader(cache_dir="./nces_cache")
        boundaries = downloader.download_locale_boundaries(2023)
        # GeoDataFrame with 12 locale territory polygons
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        timeout: int = 120,
    ):
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = Path(tempfile.mkdtemp(prefix="nces_"))
        self.timeout = timeout

    def _validate_year(self, year: int) -> None:
        """Validate that the requested year is available."""
        if year not in AVAILABLE_NCES_YEARS:
            raise ValueError(
                f"NCES year {year} not available. "
                f"Available years: {AVAILABLE_NCES_YEARS}"
            )

    def _build_url(self, data_type: str, year: int) -> str:
        """Build the download URL for a given data type and year."""
        base = NCES_DOWNLOAD_ENDPOINTS[data_type]
        filename = NCES_FILE_PATTERNS[data_type].format(year=year)
        return f"{base}/{filename}"

    def _check_url_accessible(self, url: str) -> bool:
        """Check if a URL is accessible via HEAD request."""
        from siege_utilities.files.remote import is_downloadable

        return is_downloadable(url, timeout=self.timeout)

    def _download_and_extract(self, url: str, data_type: str, year: int) -> Path:
        """Download a ZIP file and extract it, returning the extract directory."""
        from siege_utilities.files.remote import download_file

        # Check cache first
        extract_dir = self.cache_dir / f"{data_type}_{year}"
        if extract_dir.exists() and any(extract_dir.iterdir()):
            log.info(f"Using cached {data_type} data for {year} at {extract_dir}")
            return extract_dir

        # Download
        zip_path = str(self.cache_dir / f"{data_type}_{year}.zip")
        log.info(f"Downloading {data_type} data for {year} from {url}")

        result = download_file(url, zip_path, timeout=self.timeout)
        if not result:
            raise NCESDownloadError(
                f"Failed to download {data_type} for year {year} from {url}"
            )

        # Extract
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        log.info(f"Extracted {data_type} data to {extract_dir}")

        # Clean up zip
        try:
            os.remove(zip_path)
        except OSError:
            pass

        return extract_dir

    def _find_shapefile(self, directory: Path) -> Path:
        """Find the .shp file in a directory."""
        shapefiles = list(directory.rglob("*.shp"))
        if not shapefiles:
            raise NCESDownloadError(
                f"No shapefile found in {directory}"
            )
        if len(shapefiles) > 1:
            log.warning(
                f"Multiple shapefiles found in {directory}, using first: {shapefiles[0]}"
            )
        return shapefiles[0]

    def _find_csv(self, directory: Path) -> Path:
        """Find a CSV file in a directory."""
        csvfiles = list(directory.rglob("*.csv"))
        if not csvfiles:
            # Fall back to xlsx
            xlsxfiles = list(directory.rglob("*.xlsx"))
            if xlsxfiles:
                return xlsxfiles[0]
            raise NCESDownloadError(
                f"No CSV or XLSX file found in {directory}"
            )
        return csvfiles[0]

    def download_locale_boundaries(self, year: int = DEFAULT_NCES_YEAR):
        """Download NCES locale boundary polygons.

        Returns a GeoDataFrame with 12 rows — one polygon per locale territory
        (codes 11-43). Each polygon represents the geographic extent of that
        locale classification.

        Args:
            year: NCES publication year.

        Returns:
            GeoDataFrame with columns: locale_code, locale_category,
            locale_subcategory, name, geometry.
        """
        import geopandas as gpd

        from siege_utilities.config.nces_constants import (
            get_locale_category,
            get_locale_subcategory,
        )
        from siege_utilities.conf import settings

        self._validate_year(year)
        url = self._build_url("locale_boundaries", year)

        extract_dir = self._download_and_extract(url, "locale_boundaries", year)
        shp_path = self._find_shapefile(extract_dir)

        gdf = gpd.read_file(shp_path)

        # Normalize column names — NCES shapefiles vary by year
        col_upper = {c: c.upper() for c in gdf.columns if c != "geometry"}
        gdf = gdf.rename(columns=col_upper)

        # Find locale code column
        locale_col = None
        for candidate in ("LOCALE", "ULOCALE", "LOCALE_CODE"):
            if candidate in gdf.columns:
                locale_col = candidate
                break

        if locale_col is None:
            raise NCESDownloadError(
                f"No locale code column found in {shp_path}. "
                f"Available columns: {list(gdf.columns)}"
            )

        # Ensure integer codes
        gdf["locale_code"] = gdf[locale_col].astype(int)

        # Add derived columns
        gdf["locale_category"] = gdf["locale_code"].apply(get_locale_category)
        gdf["locale_subcategory"] = gdf["locale_code"].apply(get_locale_subcategory)

        # Add name column if not present
        if "NAME" not in gdf.columns:
            gdf["name"] = gdf["locale_subcategory"].str.replace("_", " ").str.title()
        else:
            gdf["name"] = gdf["NAME"]

        # Reproject to storage CRS
        if gdf.crs and gdf.crs.to_epsg() != settings.STORAGE_CRS:
            gdf = gdf.to_crs(epsg=settings.STORAGE_CRS)

        # Select final columns
        keep_cols = ["locale_code", "locale_category", "locale_subcategory", "name", "geometry"]
        gdf = gdf[[c for c in keep_cols if c in gdf.columns]]

        log.info(f"Loaded {len(gdf)} locale boundary polygons for year {year}")
        return gdf

    def download_school_locations(
        self,
        year: int = DEFAULT_NCES_YEAR,
        state_abbr: Optional[str] = None,
    ):
        """Download geocoded school locations.

        Returns a GeoDataFrame of school point locations with NCES locale codes.

        Args:
            year: NCES publication year.
            state_abbr: Optional 2-letter state abbreviation to filter.

        Returns:
            GeoDataFrame with columns: ncessch, school_name, lea_id,
            state_abbr, locale_code, locale_category, locale_subcategory, geometry.
        """
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import Point

        from siege_utilities.config.nces_constants import (
            get_locale_category,
            get_locale_subcategory,
        )
        from siege_utilities.conf import settings

        self._validate_year(year)
        url = self._build_url("school_locations", year)

        extract_dir = self._download_and_extract(url, "school_locations", year)

        # School location data may be shapefile or CSV with lat/lon
        try:
            shp_path = self._find_shapefile(extract_dir)
            gdf = gpd.read_file(shp_path)
        except NCESDownloadError:
            # Try CSV with lat/lon columns
            csv_path = self._find_csv(extract_dir)
            df = pd.read_csv(csv_path, dtype=str, low_memory=False)
            # Normalize column names
            col_upper = {c: c.upper() for c in df.columns}
            df = df.rename(columns=col_upper)

            lat_col = next((c for c in ("LAT", "LATITUDE", "LAT1920") if c in df.columns), None)
            lon_col = next((c for c in ("LON", "LONGITUDE", "LON1920") if c in df.columns), None)

            if lat_col is None or lon_col is None:
                raise NCESDownloadError(
                    f"Cannot find lat/lon columns in {csv_path}. "
                    f"Available: {list(df.columns)}"
                )

            df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
            df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
            valid = df[lat_col].notna() & df[lon_col].notna()
            df = df[valid]

            geometry = [Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col])]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        # Normalize column names
        col_upper = {c: c.upper() for c in gdf.columns if c != "geometry"}
        gdf = gdf.rename(columns=col_upper)

        # Map to standard names
        rename_map = {}
        for src, dst in SCHOOL_LOCATION_COLUMNS.items():
            if src in gdf.columns:
                rename_map[src] = dst
        gdf = gdf.rename(columns=rename_map)

        # Filter by state if requested
        if state_abbr and "state_abbr" in gdf.columns:
            gdf = gdf[gdf["state_abbr"] == state_abbr.upper()].copy()

        # Add locale classification columns
        if "locale_code" in gdf.columns:
            gdf["locale_code"] = pd.to_numeric(gdf["locale_code"], errors="coerce").fillna(0).astype(int)
            valid_codes = gdf["locale_code"].between(11, 43)
            gdf.loc[valid_codes, "locale_category"] = gdf.loc[valid_codes, "locale_code"].apply(get_locale_category)
            gdf.loc[valid_codes, "locale_subcategory"] = gdf.loc[valid_codes, "locale_code"].apply(get_locale_subcategory)

        # Reproject to storage CRS
        if gdf.crs and gdf.crs.to_epsg() != settings.STORAGE_CRS:
            gdf = gdf.to_crs(epsg=settings.STORAGE_CRS)

        log.info(f"Loaded {len(gdf)} school locations for year {year}")
        return gdf

    def download_district_data(self, year: int = DEFAULT_NCES_YEAR):
        """Download district administrative data with locale codes.

        Returns a DataFrame (not GeoDataFrame) of school district
        administrative records keyed by LEA ID.

        Args:
            year: NCES publication year.

        Returns:
            DataFrame with columns: lea_id, lea_name, state_abbr,
            locale_code, locale_category, locale_subcategory, survey_year.
        """
        import pandas as pd

        from siege_utilities.config.nces_constants import (
            get_locale_category,
            get_locale_subcategory,
        )

        self._validate_year(year)
        url = self._build_url("district_boundaries", year)

        extract_dir = self._download_and_extract(url, "district_boundaries", year)
        csv_path = self._find_csv(extract_dir)

        df = pd.read_csv(csv_path, dtype=str, low_memory=False)

        # Normalize column names
        col_upper = {c: c.upper() for c in df.columns}
        df = df.rename(columns=col_upper)

        # Map to standard names
        rename_map = {}
        for src, dst in DISTRICT_DATA_COLUMNS.items():
            if src in df.columns:
                rename_map[src] = dst
        df = df.rename(columns=rename_map)

        # Parse locale codes
        if "locale_code" in df.columns:
            df["locale_code"] = pd.to_numeric(df["locale_code"], errors="coerce").fillna(0).astype(int)
            valid_codes = df["locale_code"].between(11, 43)
            df.loc[valid_codes, "locale_category"] = df.loc[valid_codes, "locale_code"].apply(get_locale_category)
            df.loc[valid_codes, "locale_subcategory"] = df.loc[valid_codes, "locale_code"].apply(get_locale_subcategory)

        log.info(f"Loaded {len(df)} district records for year {year}")
        return df
