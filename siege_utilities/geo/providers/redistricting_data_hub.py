"""
Redistricting Data Hub (RDH) API client for siege_utilities.

Provides authenticated access to redistrictingdatahub.org datasets:
- PL 94-171 redistricting data (population by race at block level)
- CVAP special tabulation (citizen voting age population)
- Legislative boundary shapefiles (enacted congressional + state leg)
- Precinct boundaries with election results
- ACS 5-year demographic estimates
- Population projections

Authentication requires a "designated API user" account.
Contact info@redistrictingdatahub.org to request access.

Usage::

    import os
    from siege_utilities.geo.providers.redistricting_data_hub import RDHClient

    # Prefer env vars (RDH_USERNAME / RDH_PASSWORD); never hardcode
    client = RDHClient(
        username=os.environ["RDH_USERNAME"],
        password=os.environ["RDH_PASSWORD"],
    )
    datasets = client.list_datasets(states=["VA"], format="csv")
    df = client.download_dataset(datasets[0])
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    def log_info(msg: str) -> None: pass
    def log_warning(msg: str) -> None: pass
    def log_error(msg: str) -> None: pass
    def log_debug(msg: str) -> None: pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RDH_BASE_URL = "https://redistrictingdatahub.org/wp-json/download/list"
RDH_SITE_URL = "https://redistrictingdatahub.org"

# Maximum datasets returned per request (WordPress API limit)
RDH_MAX_RESULTS = 1000

# US state abbreviations for iteration
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR",
]


class RDHDataFormat(str, Enum):
    """File format for RDH downloads."""
    CSV = "csv"
    SHAPEFILE = "shp"


class RDHDatasetType(str, Enum):
    """Categories of RDH datasets."""
    PL94171 = "pl94171"
    CVAP = "cvap"
    ACS5 = "acs5"
    ELECTION = "election"
    LEGISLATIVE = "legislative"
    PRECINCT = "precinct"
    VOTER_FILE = "voter_file"
    PROJECTION = "projection"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RDHDataset:
    """Metadata for a single RDH dataset entry."""
    title: str
    url: str
    state: str = ""
    format: str = ""
    year: str = ""
    geography: str = ""
    dataset_type: str = ""
    official: bool = False
    file_size: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def filename(self) -> str:
        """Extract filename from URL."""
        return self.url.rsplit("/", 1)[-1] if self.url else ""

    @property
    def is_shapefile(self) -> bool:
        return self.format.lower() in ("shp", "shapefile")

    @property
    def is_csv(self) -> bool:
        return self.format.lower() == "csv"


@dataclass
class CompactnessScores:
    """Compactness metrics for a district geometry."""
    district_id: str
    polsby_popper: float = 0.0
    reock: float = 0.0
    convex_hull_ratio: float = 0.0
    schwartzberg: float = 0.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class RDHClient:
    """Client for the Redistricting Data Hub download API.

    Parameters
    ----------
    username : str, optional
        RDH account email. Falls back to ``RDH_USERNAME`` env var.
    password : str, optional
        RDH account password. Falls back to ``RDH_PASSWORD`` env var.
    base_url : str, optional
        Override API endpoint (for testing).
    cache_dir : Path or str, optional
        Directory for caching downloaded files. Defaults to
        ``~/.cache/siege_utilities/rdh/``.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_url: str = RDH_BASE_URL,
        cache_dir: Optional[Union[str, Path]] = None,
    ):
        if not HAS_REQUESTS:
            raise ImportError(
                "requests is required for RDH integration. "
                "Install with: pip install requests"
            )

        self.username = username or os.environ.get("RDH_USERNAME", "")
        self.password = password or os.environ.get("RDH_PASSWORD", "")
        self.base_url = base_url

        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "siege_utilities" / "rdh"
        else:
            self.cache_dir = Path(cache_dir)

        self._session = requests.Session()

    # -- Authentication check -------------------------------------------------

    def validate_credentials(self) -> bool:
        """Test that credentials are set (non-empty)."""
        if not self.username or not self.password:
            log_warning("RDH credentials not set. Set RDH_USERNAME/RDH_PASSWORD or pass to constructor.")
            return False
        return True

    # -- Listing datasets -----------------------------------------------------

    def list_datasets(
        self,
        states: Optional[List[str]] = None,
        format: Optional[Union[str, RDHDataFormat]] = None,
        year: Optional[str] = None,
        dataset_type: Optional[str] = None,
        geography: Optional[str] = None,
        official: Optional[bool] = None,
    ) -> List[RDHDataset]:
        """List available datasets with optional filters.

        Parameters
        ----------
        states : list of str, optional
            State abbreviations to filter (e.g. ``["VA", "MD"]``).
            Due to API limits, queries more than 4 states sequentially.
        format : str, optional
            ``"csv"`` or ``"shp"``.
        year : str, optional
            Four-digit year.
        dataset_type : str, optional
            Filter keyword in title.
        geography : str, optional
            Geographic level filter.
        official : bool, optional
            If True, only return official/enacted datasets.

        Returns
        -------
        list of RDHDataset
        """
        if not self.validate_credentials():
            return []

        if format is not None:
            format = format.value if isinstance(format, RDHDataFormat) else format

        # Handle state batching (API returns max 1000 per request)
        if states and len(states) > 4:
            all_datasets = []
            for i in range(0, len(states), 4):
                batch = states[i:i + 4]
                all_datasets.extend(
                    self._fetch_datasets(batch, format, year, dataset_type, geography, official)
                )
            return all_datasets

        return self._fetch_datasets(states, format, year, dataset_type, geography, official)

    def _fetch_datasets(
        self,
        states: Optional[List[str]],
        format: Optional[str],
        year: Optional[str],
        dataset_type: Optional[str],
        geography: Optional[str],
        official: Optional[bool],
    ) -> List[RDHDataset]:
        """Perform a single API request to fetch dataset listings."""
        params: Dict[str, str] = {
            "username": self.username,
            "password": self.password,
        }
        if states:
            params["states"] = ",".join(states)
        if format:
            params["format"] = format
        if year:
            params["year"] = str(year)

        try:
            resp = self._session.get(self.base_url, params=params, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            log_error(f"RDH API request failed: {e}")
            return []

        raw_data = resp.json()
        if not isinstance(raw_data, list):
            raw_data = raw_data.get("data", []) if isinstance(raw_data, dict) else []

        datasets = []
        for entry in raw_data:
            ds = self._parse_dataset_entry(entry)
            if ds is None:
                continue

            # Apply client-side filters
            if dataset_type and dataset_type.lower() not in ds.title.lower():
                continue
            if geography and geography.lower() not in ds.title.lower():
                continue
            if official is not None and ds.official != official:
                continue

            datasets.append(ds)

        log_info(f"RDH: {len(datasets)} datasets found")
        return datasets

    def _parse_dataset_entry(self, entry: Dict[str, Any]) -> Optional[RDHDataset]:
        """Parse a raw API entry into an RDHDataset."""
        if not isinstance(entry, dict):
            return None

        title = entry.get("title", entry.get("name", ""))
        url = entry.get("url", entry.get("download_url", entry.get("link", "")))

        if not url:
            return None

        # Infer format from URL
        fmt = ""
        url_lower = url.lower()
        if url_lower.endswith(".csv") or "_csv" in url_lower:
            fmt = "csv"
        elif url_lower.endswith(".zip"):
            # Shapefiles come as ZIP
            fmt = "shp" if "shp" in url_lower or "shape" in url_lower else "zip"

        # Infer state from entry or title
        state = entry.get("state", "")
        if not state:
            for abbr in US_STATES:
                if f"_{abbr}_" in title or f" {abbr} " in title or title.startswith(f"{abbr}_"):
                    state = abbr
                    break

        return RDHDataset(
            title=title,
            url=url,
            state=state,
            format=entry.get("format", fmt),
            year=str(entry.get("year", "")),
            geography=entry.get("geography", ""),
            dataset_type=entry.get("type", ""),
            official=bool(entry.get("official", False)),
            file_size=str(entry.get("file_size", "")),
            raw=entry,
        )

    # -- Downloading ----------------------------------------------------------

    def download_dataset(
        self,
        dataset: Union[RDHDataset, str],
        output_dir: Optional[Union[str, Path]] = None,
        use_cache: bool = True,
    ) -> Path:
        """Download a dataset file.

        Parameters
        ----------
        dataset : RDHDataset or str
            Dataset object or direct download URL.
        output_dir : Path, optional
            Where to save. Defaults to cache_dir.
        use_cache : bool
            If True, skip download if file already exists.

        Returns
        -------
        Path to the downloaded file (or extracted directory for ZIPs).
        """
        if isinstance(dataset, str):
            url = dataset
            filename = url.rsplit("/", 1)[-1]
        else:
            url = dataset.url
            filename = dataset.filename

        if output_dir is None:
            output_dir = self.cache_dir
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        dest = output_dir / filename

        if use_cache and dest.exists():
            log_info(f"RDH: Using cached {filename}")
            return dest

        log_info(f"RDH: Downloading {filename}...")
        try:
            resp = self._session.get(url, timeout=300, stream=True)
            resp.raise_for_status()
        except requests.RequestException as e:
            log_error(f"RDH download failed: {e}")
            raise

        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        log_info(f"RDH: Saved {filename} ({dest.stat().st_size:,} bytes)")

        # Auto-extract ZIP files
        if dest.suffix.lower() == ".zip":
            return self._extract_zip(dest, output_dir)

        return dest

    def _extract_zip(self, zip_path: Path, output_dir: Path) -> Path:
        """Extract a ZIP archive and return the extraction directory."""
        extract_dir = output_dir / zip_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        log_info(f"RDH: Extracted to {extract_dir}")
        return extract_dir

    # -- Loading into DataFrames ----------------------------------------------

    def load_csv(
        self,
        dataset: Union[RDHDataset, str, Path],
        **kwargs,
    ) -> "pd.DataFrame":
        """Download (if needed) and load a CSV dataset into a DataFrame.

        Parameters
        ----------
        dataset : RDHDataset, str, or Path
            Dataset to load.
        **kwargs
            Passed to ``pd.read_csv()``.
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required to load CSV data")

        if isinstance(dataset, Path) and dataset.exists():
            path = dataset
        elif isinstance(dataset, (RDHDataset, str)):
            path = self.download_dataset(dataset)
        else:
            path = Path(dataset)

        if path.is_dir():
            # Find CSV in extracted directory
            csvs = list(path.glob("*.csv"))
            if not csvs:
                raise FileNotFoundError(f"No CSV files found in {path}")
            path = csvs[0]

        return pd.read_csv(path, **kwargs)

    def load_shapefile(
        self,
        dataset: Union[RDHDataset, str, Path],
        **kwargs,
    ) -> "gpd.GeoDataFrame":
        """Download (if needed) and load a shapefile into a GeoDataFrame.

        Parameters
        ----------
        dataset : RDHDataset, str, or Path
            Dataset to load.
        **kwargs
            Passed to ``gpd.read_file()``.
        """
        if not HAS_GEOPANDAS:
            raise ImportError(
                "geopandas is required to load shapefiles. "
                "Install with: pip install 'siege-utilities[geo]'"
            )

        if isinstance(dataset, Path) and dataset.exists():
            path = dataset
        elif isinstance(dataset, (RDHDataset, str)):
            path = self.download_dataset(dataset)
        else:
            path = Path(dataset)

        if path.is_dir():
            # Find .shp in extracted directory
            shps = list(path.glob("**/*.shp"))
            if not shps:
                raise FileNotFoundError(f"No .shp files found in {path}")
            path = shps[0]

        return gpd.read_file(path, **kwargs)

    # -- Convenience functions ------------------------------------------------

    def get_enacted_plans(
        self,
        state: str,
        chamber: str = "congress",
        year: Optional[str] = None,
        format: str = "shp",
    ) -> List[RDHDataset]:
        """Find enacted redistricting plan datasets for a state.

        Parameters
        ----------
        state : str
            Two-letter state abbreviation.
        chamber : str
            ``"congress"``, ``"state_senate"``, or ``"state_house"``.
        year : str, optional
            Filter by year.
        format : str, default "shp"
            Dataset format filter. Only ``"shp"`` is loadable via
            :meth:`load_shapefile`; other formats are returned as metadata
            only.
        """
        datasets = self.list_datasets(
            states=[state],
            format=format,
            year=year,
        )

        chamber_keywords = {
            "congress": ["congressional", "congress", "cd"],
            "state_senate": ["state senate", "upper", "sldl", "senate"],
            "state_house": ["state house", "lower", "sldu", "house"],
        }
        keywords = chamber_keywords.get(chamber.lower(), [chamber.lower()])

        return [
            ds for ds in datasets
            if any(kw in ds.title.lower() for kw in keywords)
            and ("enacted" in ds.title.lower() or "adopted" in ds.title.lower() or ds.official)
        ]

    def get_precinct_data(
        self,
        state: str,
        year: Optional[str] = None,
        format: str = "shp",
    ) -> List[RDHDataset]:
        """Find precinct-level datasets for a state."""
        datasets = self.list_datasets(
            states=[state],
            format=format,
            year=year,
        )
        return [
            ds for ds in datasets
            if "precinct" in ds.title.lower() or "vtd" in ds.title.lower()
        ]

    def get_cvap_data(
        self,
        state: str,
        year: Optional[str] = None,
    ) -> List[RDHDataset]:
        """Find CVAP (Citizen Voting Age Population) datasets."""
        datasets = self.list_datasets(
            states=[state],
            format="csv",
            year=year,
        )
        return [ds for ds in datasets if "cvap" in ds.title.lower()]

    def get_pl94171_data(
        self,
        state: str,
        year: Optional[str] = None,
    ) -> List[RDHDataset]:
        """Find PL 94-171 redistricting data datasets."""
        datasets = self.list_datasets(
            states=[state],
            year=year,
        )
        return [
            ds for ds in datasets
            if ("pl" in ds.title.lower() and "94" in ds.title.lower())
            or ("redistricting" in ds.title.lower() and "data" in ds.title.lower())
        ]

    # -- Cross-tabulation integration -----------------------------------------

    @staticmethod
    def to_crosstab_input(
        df: "pd.DataFrame",
        geography_col: str = "GEOID",
        variable_cols: Optional[List[str]] = None,
    ) -> "pd.DataFrame":
        """Reshape an RDH DataFrame into long format for cross-tabulation.

        Returns a DataFrame with columns ``[geography, variable, value]`` suitable
        for use with :func:`siege_utilities.data.cross_tabulation.contingency_table`.

        Parameters
        ----------
        df : DataFrame
            Wide-format data (one row per geography, numeric columns as variables).
        geography_col : str
            Column identifying the geographic unit.
        variable_cols : list of str, optional
            Columns to melt. If ``None``, all numeric columns except the geography
            column are used.

        Returns
        -------
        DataFrame with columns ``geography``, ``variable``, ``value``.
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required")

        if variable_cols is None:
            variable_cols = [
                c for c in df.columns
                if c != geography_col and df[c].dtype.kind in ("i", "f")
            ]

        melted = df[[geography_col] + variable_cols].melt(
            id_vars=[geography_col],
            var_name="variable",
            value_name="value",
        )
        melted = melted.rename(columns={geography_col: "geography"})
        return melted


# ---------------------------------------------------------------------------
# Compactness scoring
# ---------------------------------------------------------------------------

def polsby_popper(geometry) -> float:
    """Compute Polsby-Popper compactness score for a geometry.

    Score = (4 * pi * area) / perimeter^2
    Range: 0 (least compact) to 1 (circle).
    """
    import math
    if geometry is None or geometry.is_empty:
        return 0.0
    area = geometry.area
    perimeter = geometry.length
    if perimeter == 0:
        return 0.0
    return (4.0 * math.pi * area) / (perimeter ** 2)


def reock(geometry) -> float:
    """Compute Reock compactness score for a geometry.

    Score = area / area_of_minimum_bounding_circle
    Range: 0 (least compact) to 1 (circle).
    """
    import math
    if geometry is None or geometry.is_empty:
        return 0.0
    area = geometry.area
    # Approximate MBC using minimum rotated rectangle's diagonal
    mrr = geometry.minimum_rotated_rectangle
    if mrr is None or mrr.is_empty:
        return 0.0
    coords = list(mrr.exterior.coords)
    if len(coords) < 4:
        return 0.0
    # Diagonal of the minimum rotated rectangle as diameter estimate
    from shapely.geometry import Point
    p0, p1, p2 = Point(coords[0]), Point(coords[1]), Point(coords[2])
    side1 = p0.distance(p1)
    side2 = p1.distance(p2)
    diameter = max(side1, side2, (side1**2 + side2**2)**0.5)
    radius = diameter / 2.0
    circle_area = math.pi * radius**2
    if circle_area == 0:
        return 0.0
    return area / circle_area


def convex_hull_ratio(geometry) -> float:
    """Compute convex hull ratio for a geometry.

    Score = area / convex_hull_area
    Range: 0 to 1.
    """
    if geometry is None or geometry.is_empty:
        return 0.0
    hull = geometry.convex_hull
    if hull.is_empty or hull.area == 0:
        return 0.0
    return geometry.area / hull.area


def schwartzberg(geometry) -> float:
    """Compute Schwartzberg compactness score.

    Score = 1 / (perimeter / circumference_of_equal_area_circle)
    Range: 0 to 1.
    """
    import math
    if geometry is None or geometry.is_empty:
        return 0.0
    area = geometry.area
    perimeter = geometry.length
    if perimeter == 0 or area == 0:
        return 0.0
    circle_circumference = 2.0 * math.pi * math.sqrt(area / math.pi)
    return circle_circumference / perimeter


def compute_compactness(
    gdf: "gpd.GeoDataFrame",
    district_id_col: str = "GEOID",
    geometry_col: str = "geometry",
) -> "pd.DataFrame":
    """Compute all compactness metrics for a GeoDataFrame of districts.

    Parameters
    ----------
    gdf : GeoDataFrame
        Districts with geometry.
    district_id_col : str
        Column name for district identifiers.
    geometry_col : str
        Column name for geometry.

    Returns
    -------
    DataFrame with columns: district_id, polsby_popper, reock,
    convex_hull_ratio, schwartzberg.
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required")

    records = []
    for _, row in gdf.iterrows():
        geom = row[geometry_col]
        records.append({
            "district_id": row[district_id_col],
            "polsby_popper": polsby_popper(geom),
            "reock": reock(geom),
            "convex_hull_ratio": convex_hull_ratio(geom),
            "schwartzberg": schwartzberg(geom),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Plan comparison
# ---------------------------------------------------------------------------

def compare_plans(
    plan_a: "gpd.GeoDataFrame",
    plan_b: "gpd.GeoDataFrame",
    population_col: str = "TOTPOP",
    district_id_col: str = "GEOID",
) -> Dict[str, Any]:
    """Compare two redistricting plans on key metrics.

    Parameters
    ----------
    plan_a, plan_b : GeoDataFrame
        District plans with population and geometry.
    population_col : str
        Column with total population.
    district_id_col : str
        Column with district identifier.

    Returns
    -------
    dict with comparison metrics.
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required")

    def _plan_stats(gdf, label):
        pops = gdf[population_col]
        ideal = pops.sum() / len(pops)
        return {
            "label": label,
            "num_districts": len(gdf),
            "total_population": int(pops.sum()),
            "ideal_population": round(ideal, 1),
            "max_deviation": round((pops.max() - ideal) / ideal * 100, 2),
            "min_deviation": round((pops.min() - ideal) / ideal * 100, 2),
            "range_pct": round((pops.max() - pops.min()) / ideal * 100, 2),
            "std_dev": round(pops.std(), 1),
            "compactness_mean_pp": round(
                gdf.geometry.apply(polsby_popper).mean(), 4
            ),
        }

    stats_a = _plan_stats(plan_a, "Plan A")
    stats_b = _plan_stats(plan_b, "Plan B")

    return {
        "plan_a": stats_a,
        "plan_b": stats_b,
        "population_difference": abs(stats_a["total_population"] - stats_b["total_population"]),
        "district_count_match": stats_a["num_districts"] == stats_b["num_districts"],
        "compactness_delta": round(
            stats_a["compactness_mean_pp"] - stats_b["compactness_mean_pp"], 4
        ),
    }


# ---------------------------------------------------------------------------
# Demographic overlay
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# High-level fetch functions (list → download → load in one call)
# ---------------------------------------------------------------------------

def fetch_enacted_plan(
    state: str,
    chamber: str = "congress",
    year: Optional[str] = None,
    client: Optional["RDHClient"] = None,
) -> "gpd.GeoDataFrame":
    """Fetch enacted district plan as GeoDataFrame with boundaries + attributes.

    Parameters
    ----------
    state : str
        Two-letter state abbreviation.
    chamber : str
        ``"congress"``, ``"state_senate"``, or ``"state_house"``.
    year : str, optional
        Filter by year.
    client : RDHClient, optional
        Existing client instance.  Created from env vars if omitted.

    Returns
    -------
    GeoDataFrame with district boundaries and attributes.

    Raises
    ------
    FileNotFoundError
        If no matching enacted plan dataset is found.
    """
    if not HAS_GEOPANDAS:
        raise ImportError(
            "geopandas is required. Install with: pip install 'siege-utilities[geo]'"
        )
    c = client or RDHClient()
    datasets = c.get_enacted_plans(state, chamber=chamber, year=year)
    if not datasets:
        raise FileNotFoundError(
            f"No enacted {chamber} plan found for {state}"
            + (f" year={year}" if year else "")
        )
    return c.load_shapefile(datasets[0])


def fetch_precinct_results(
    state: str,
    year: Optional[str] = None,
    client: Optional["RDHClient"] = None,
) -> "gpd.GeoDataFrame":
    """Fetch precinct boundaries with election results as GeoDataFrame.

    Parameters
    ----------
    state : str
        Two-letter state abbreviation.
    year : str, optional
        Election year filter.
    client : RDHClient, optional
        Existing client instance.

    Returns
    -------
    GeoDataFrame with precinct boundaries and vote columns.
    """
    if not HAS_GEOPANDAS:
        raise ImportError(
            "geopandas is required. Install with: pip install 'siege-utilities[geo]'"
        )
    c = client or RDHClient()
    datasets = c.get_precinct_data(state, year=year, format="shp")
    if not datasets:
        raise FileNotFoundError(
            f"No precinct data found for {state}"
            + (f" year={year}" if year else "")
        )
    return c.load_shapefile(datasets[0])


def fetch_cvap(
    state: str,
    year: Optional[str] = None,
    geography: str = "tract",
    client: Optional["RDHClient"] = None,
) -> "pd.DataFrame":
    """Fetch CVAP (Citizen Voting Age Population) data as DataFrame.

    Parameters
    ----------
    state : str
        Two-letter state abbreviation.
    year : str, optional
        Data year filter.
    geography : str
        Geographic level hint for filtering (e.g. ``"tract"``, ``"block_group"``).
    client : RDHClient, optional
        Existing client instance.

    Returns
    -------
    DataFrame with CVAP estimates.
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required to load CVAP data")
    c = client or RDHClient()
    datasets = c.get_cvap_data(state, year=year)
    # Filter by geography keyword if multiple results
    if geography and len(datasets) > 1:
        filtered = [
            ds for ds in datasets
            if geography.lower() in ds.title.lower()
        ]
        if filtered:
            datasets = filtered
    if not datasets:
        raise FileNotFoundError(
            f"No CVAP data found for {state}"
            + (f" year={year}" if year else "")
        )
    return c.load_csv(datasets[0])


def fetch_pl94171(
    state: str,
    year: Optional[str] = None,
    geography: str = "block",
    client: Optional["RDHClient"] = None,
) -> "pd.DataFrame":
    """Fetch PL 94-171 redistricting population data as DataFrame.

    Parameters
    ----------
    state : str
        Two-letter state abbreviation.
    year : str, optional
        Decennial year filter.
    geography : str
        Geographic level hint (e.g. ``"block"``, ``"tract"``).
    client : RDHClient, optional
        Existing client instance.

    Returns
    -------
    DataFrame with PL 94-171 population data.
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required to load PL 94-171 data")
    c = client or RDHClient()
    datasets = c.get_pl94171_data(state, year=year)
    if geography and len(datasets) > 1:
        filtered = [
            ds for ds in datasets
            if geography.lower() in ds.title.lower()
        ]
        if filtered:
            datasets = filtered
    if not datasets:
        raise FileNotFoundError(
            f"No PL 94-171 data found for {state}"
            + (f" year={year}" if year else "")
        )
    return c.load_csv(datasets[0])


def fetch_demographic_summary(
    state: str,
    year: Optional[str] = None,
    client: Optional["RDHClient"] = None,
) -> "pd.DataFrame":
    """Fetch ACS 5-year demographic summary by district.

    Parameters
    ----------
    state : str
        Two-letter state abbreviation.
    year : str, optional
        ACS year filter.
    client : RDHClient, optional
        Existing client instance.

    Returns
    -------
    DataFrame with ACS demographic columns.
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required to load demographic data")
    c = client or RDHClient()
    datasets = c.list_datasets(
        states=[state],
        format="csv",
        year=year,
        dataset_type="acs",
    )
    if not datasets:
        raise FileNotFoundError(
            f"No ACS demographic data found for {state}"
            + (f" year={year}" if year else "")
        )
    return c.load_csv(datasets[0])


def demographic_profile(
    plan_gdf: "gpd.GeoDataFrame",
    census_gdf: "gpd.GeoDataFrame",
    district_id_col: str = "GEOID",
    population_cols: Optional[List[str]] = None,
) -> "pd.DataFrame":
    """Overlay Census ACS data onto a redistricting plan.

    Performs a spatial join between district geometries and Census
    block/tract geometries, then aggregates demographics per district.

    Parameters
    ----------
    plan_gdf : GeoDataFrame
        District plan with geometries.
    census_gdf : GeoDataFrame
        Census data with geometries and demographic columns.
    district_id_col : str
        Column in plan_gdf identifying districts.
    population_cols : list of str, optional
        Demographic columns to aggregate. Defaults to common ACS fields.

    Returns
    -------
    DataFrame with one row per district and summed demographic columns.
    """
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas is required for spatial overlay")

    if population_cols is None:
        # Common ACS fields
        population_cols = [
            c for c in census_gdf.columns
            if c.upper().startswith(("B01", "B02", "B03", "B19", "TOTPOP", "VAP"))
            and census_gdf[c].dtype in ("int64", "float64", "int32", "float32")
        ]

    if not population_cols:
        log_warning("No population columns found for demographic overlay")
        return pd.DataFrame()

    # Ensure same CRS
    if plan_gdf.crs != census_gdf.crs:
        census_gdf = census_gdf.to_crs(plan_gdf.crs)

    joined = gpd.sjoin(census_gdf, plan_gdf[[district_id_col, "geometry"]], predicate="within")

    result = joined.groupby(district_id_col)[population_cols].sum().reset_index()
    return result


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Client
    "RDHClient",
    "RDHDataset",
    "RDHDataFormat",
    "RDHDatasetType",
    # Constants
    "RDH_BASE_URL",
    "RDH_SITE_URL",
    "US_STATES",
    # Compactness
    "polsby_popper",
    "reock",
    "convex_hull_ratio",
    "schwartzberg",
    "compute_compactness",
    "CompactnessScores",
    # Plan analysis
    "compare_plans",
    "demographic_profile",
    # High-level fetch functions
    "fetch_enacted_plan",
    "fetch_precinct_results",
    "fetch_cvap",
    "fetch_pl94171",
    "fetch_demographic_summary",
]
