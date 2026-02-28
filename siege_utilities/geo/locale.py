"""
NCES Urban-Centric Locale Classification for siege_utilities.

Implements the National Center for Education Statistics (NCES) 12-code locale
classification system. Classifies arbitrary geographic points and polygons
into City/Suburb/Town/Rural categories with size/distance subtypes.

Two modes of operation:
1. Pre-computed: Uses NCES-published locale boundary shapefiles (fastest)
2. On-the-fly: Computes from Census UA/UC/Place inputs (any year)

See docs/design/nces-locale-classification.md for full algorithm description.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union

from siege_utilities.conf import settings
from siege_utilities.config.nces_constants import (
    DISTANCE_THRESHOLDS,
    LOCALE_CODE_TO_NUMERIC,
    LOCALE_NUMERIC_CODES,
    POPULATION_THRESHOLDS,
    validate_locale_code,
)

log = logging.getLogger(__name__)

# Meters per mile — used for distance conversion after CRS projection
_METERS_PER_MILE = 1_609.344

# Population threshold separating Urbanized Areas (>= 50k) from Urban Clusters (< 50k)
_UA_POP_THRESHOLD = 50_000

# Column name candidates for population fields on Census shapefiles
_POPULATION_COLUMNS = (
    "POP20", "POP10", "POP", "POPULATION", "pop20", "pop10", "pop",
    "population",
)

# Column name candidates for UA/UC identifier fields
_UA_ID_COLUMNS = (
    "UACE20", "UACE10", "GEOID20", "GEOID10", "GEOID",
    "uace20", "uace10", "geoid20", "geoid10", "geoid",
)

# Column name candidates for Place identifier fields
_PLACE_ID_COLUMNS = (
    "PLACEFP", "PLACEFP20", "PLACEFP10", "GEOID20", "GEOID10", "GEOID",
    "placefp", "placefp20", "placefp10", "geoid20", "geoid10", "geoid",
)


def _find_column(gdf: Any, candidates: tuple) -> Optional[str]:
    """Return the first column name from *candidates* found in *gdf*, or None."""
    if gdf is None or not hasattr(gdf, "columns"):
        return None
    for col in candidates:
        if col in gdf.columns:
            return col
    return None


# ---------------------------------------------------------------------------
# LocaleType enum
# ---------------------------------------------------------------------------

class LocaleType(IntEnum):
    """NCES major locale types."""
    CITY = 1
    SUBURB = 2
    TOWN = 3
    RURAL = 4


# ---------------------------------------------------------------------------
# LocaleCode dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LocaleCode:
    """An NCES 12-code locale classification result.

    Attributes:
        code: Integer locale code (11-43).
        category: Major type — ``city``, ``suburban``, ``town``, or ``rural``.
        subcategory: Full subtype — ``city_large``, ``rural_remote``, etc.
        label: Human-readable label — ``City-Large``, ``Rural-Remote``, etc.
    """
    code: int
    category: str
    subcategory: str
    label: str

    @classmethod
    def from_code(cls, code: int) -> "LocaleCode":
        """Construct a ``LocaleCode`` from an integer code (11-43).

        Raises:
            ValueError: If the code is not a valid NCES locale code.
        """
        if not validate_locale_code(code):
            raise ValueError(f"Invalid NCES locale code: {code}")

        subcategory = LOCALE_NUMERIC_CODES[code]
        # Derive category from the tens digit
        tens = code // 10
        category_map = {1: "city", 2: "suburban", 3: "town", 4: "rural"}
        category = category_map[tens]

        # Build human label: "City-Large", "Suburb-Midsize", "Rural-Remote"
        parts = subcategory.split("_", 1)
        type_label = parts[0].title()
        if type_label == "Suburb":
            type_label = "Suburb"
        subtype_label = parts[1].title() if len(parts) > 1 else ""
        label = f"{type_label}-{subtype_label}"

        return cls(code=code, category=category, subcategory=subcategory, label=label)


# Pre-built constants for all 12 locale codes
CITY_LARGE = LocaleCode.from_code(11)
CITY_MIDSIZE = LocaleCode.from_code(12)
CITY_SMALL = LocaleCode.from_code(13)
SUBURB_LARGE = LocaleCode.from_code(21)
SUBURB_MIDSIZE = LocaleCode.from_code(22)
SUBURB_SMALL = LocaleCode.from_code(23)
TOWN_FRINGE = LocaleCode.from_code(31)
TOWN_DISTANT = LocaleCode.from_code(32)
TOWN_REMOTE = LocaleCode.from_code(33)
RURAL_FRINGE = LocaleCode.from_code(41)
RURAL_DISTANT = LocaleCode.from_code(42)
RURAL_REMOTE = LocaleCode.from_code(43)

ALL_LOCALE_CODES: List[LocaleCode] = [
    CITY_LARGE, CITY_MIDSIZE, CITY_SMALL,
    SUBURB_LARGE, SUBURB_MIDSIZE, SUBURB_SMALL,
    TOWN_FRINGE, TOWN_DISTANT, TOWN_REMOTE,
    RURAL_FRINGE, RURAL_DISTANT, RURAL_REMOTE,
]

# Lookup from integer code → pre-built LocaleCode
_CODE_LOOKUP: Dict[int, LocaleCode] = {lc.code: lc for lc in ALL_LOCALE_CODES}


def locale_from_code(code: int) -> LocaleCode:
    """Fast lookup of a pre-built ``LocaleCode`` by integer code.

    Returns the pre-built constant when possible, avoiding dataclass construction.
    """
    result = _CODE_LOOKUP.get(code)
    if result is not None:
        return result
    return LocaleCode.from_code(code)


# ---------------------------------------------------------------------------
# NCESLocaleClassifier
# ---------------------------------------------------------------------------

class NCESLocaleClassifier:
    """Classify geographic points and polygons into NCES locale codes.

    Uses Census TIGER spatial data (Urbanized Areas, Urban Clusters, Places)
    and population thresholds to implement the NCES urban-centric locale
    classification algorithm (12-code system).

    The classifier can be initialized with pre-loaded GeoDataFrames (for
    testing or custom data) or constructed from Census downloads via the
    ``from_census_year`` and ``from_nces_boundaries`` factory methods.

    Args:
        urbanized_areas: GeoDataFrame of UA polygons (pop >= 50,000).
            Must contain a ``geometry`` column and a population field.
        urban_clusters: GeoDataFrame of UC polygons (pop 2,500-49,999).
            Must contain a ``geometry`` column. May be ``None`` for 2020+
            Census data where UCs were eliminated.
        principal_cities: GeoDataFrame of Place polygons that are designated
            principal cities of CBSAs.
        place_populations: Dict mapping place identifiers to population counts.
            Used to classify City subtypes (Large/Midsize/Small).
        ua_populations: Optional dict mapping UA identifiers to populations.
            Used to classify Suburb subtypes. If ``None``, reads from the
            ``urbanized_areas`` GeoDataFrame attributes.
        projection_crs: EPSG code for distance computations. Defaults to
            ``settings.PROJECTION_CRS`` (2163, US National Atlas Equal Area).
            Override for Alaska (3338) or Hawaii (26963).
    """

    def __init__(
        self,
        urbanized_areas: Any,
        urban_clusters: Optional[Any],
        principal_cities: Any,
        place_populations: Dict[str, int],
        ua_populations: Optional[Dict[str, int]] = None,
        projection_crs: Optional[int] = None,
    ):
        self._ua = urbanized_areas
        self._uc = urban_clusters
        self._principal_cities = principal_cities
        self._place_populations = place_populations
        self._ua_populations = ua_populations or {}
        self._projection_crs = projection_crs or settings.PROJECTION_CRS

        # Lazily projected copies (created on first classify call)
        self._ua_proj = None
        self._uc_proj = None

    def _ensure_projected(self) -> None:
        """Project UA/UC layers to the configured CRS for distance ops."""
        import geopandas as gpd  # noqa: F401 — validates availability

        crs_string = f"EPSG:{self._projection_crs}"
        if self._ua_proj is None and self._ua is not None:
            self._ua_proj = self._ua.to_crs(crs_string)
        if self._uc_proj is None and self._uc is not None:
            self._uc_proj = self._uc.to_crs(crs_string)

    # ------------------------------------------------------------------
    # Point classification
    # ------------------------------------------------------------------

    def classify_point(self, lon: float, lat: float) -> LocaleCode:
        """Classify a single geographic point.

        Implements the NCES decision tree:
        1. Spatial join against Urbanized Areas
        2. If in UA: check principal city → City or Suburb
        3. If not in UA: check Urban Cluster → Town (by distance to UA)
        4. If not in UA/UC → Rural (by distance to UA and UC)

        Args:
            lon: Longitude in the input CRS (default NAD83/WGS84).
            lat: Latitude in the input CRS (default NAD83/WGS84).

        Returns:
            A ``LocaleCode`` describing the point's NCES classification.
        """
        import geopandas as gpd
        from shapely.geometry import Point

        self._ensure_projected()

        input_crs = f"EPSG:{settings.INPUT_CRS}"
        proj_crs = f"EPSG:{self._projection_crs}"

        point = Point(lon, lat)
        point_gdf = gpd.GeoDataFrame(
            {"id": [0]}, geometry=[point], crs=input_crs,
        )
        point_proj = point_gdf.to_crs(proj_crs)

        # Step 1: Is the point inside an Urbanized Area?
        if self._ua is not None and len(self._ua) > 0:
            ua_match = gpd.sjoin(
                point_gdf, self._ua, how="inner", predicate="within",
            )
            if len(ua_match) > 0:
                return self._classify_ua_point(point_gdf, ua_match)

        # Step 2: Is the point inside an Urban Cluster?
        if self._uc is not None and len(self._uc) > 0:
            uc_match = gpd.sjoin(
                point_gdf, self._uc, how="inner", predicate="within",
            )
            if len(uc_match) > 0:
                return self._classify_town(point_proj)

        # Step 3: Rural — classify by distances to UA and UC
        return self._classify_rural(point_proj)

    def _classify_ua_point(self, point_gdf: Any, ua_match: Any) -> LocaleCode:
        """Classify a point known to be inside a UA."""
        import geopandas as gpd

        # Check if point is inside a principal city
        pc_match = gpd.sjoin(
            point_gdf, self._principal_cities, how="inner", predicate="within",
        )

        if len(pc_match) > 0:
            # CITY — subtype by principal city population
            # Try to get population from place_populations dict
            pop = self._get_place_population(pc_match)
            if pop >= POPULATION_THRESHOLDS["large_city"]:
                return CITY_LARGE
            if pop >= POPULATION_THRESHOLDS["midsize_city"]:
                return CITY_MIDSIZE
            return CITY_SMALL
        else:
            # SUBURB — subtype by UA population
            ua_pop = self._get_ua_population(ua_match)
            if ua_pop >= POPULATION_THRESHOLDS["large_city"]:
                return SUBURB_LARGE
            if ua_pop >= POPULATION_THRESHOLDS["midsize_city"]:
                return SUBURB_MIDSIZE
            return SUBURB_SMALL

    def _classify_town(self, point_proj: Any) -> LocaleCode:
        """Classify a point inside a UC as Town subtype by distance to nearest UA."""
        d_ua = self._distance_to_nearest_ua(point_proj)
        if d_ua <= 10.0:
            return TOWN_FRINGE
        if d_ua <= 35.0:
            return TOWN_DISTANT
        return TOWN_REMOTE

    def _classify_rural(self, point_proj: Any) -> LocaleCode:
        """Classify a rural point by distance to nearest UA and UC."""
        d_ua = self._distance_to_nearest_ua(point_proj)
        d_uc = self._distance_to_nearest_uc(point_proj)

        if d_ua <= DISTANCE_THRESHOLDS["fringe_max"] or d_uc <= 2.5:
            return RURAL_FRINGE
        if d_ua <= DISTANCE_THRESHOLDS["distant_max"] or d_uc <= 10.0:
            return RURAL_DISTANT
        return RURAL_REMOTE

    def _distance_to_nearest_ua(self, point_proj: Any) -> float:
        """Euclidean distance from projected point to nearest UA, in miles."""
        if self._ua_proj is None or len(self._ua_proj) == 0:
            return float("inf")
        geom = point_proj.geometry.iloc[0]
        min_dist_m = self._ua_proj.geometry.distance(geom).min()
        return min_dist_m / _METERS_PER_MILE

    def _distance_to_nearest_uc(self, point_proj: Any) -> float:
        """Euclidean distance from projected point to nearest UC, in miles."""
        if self._uc_proj is None or len(self._uc_proj) == 0:
            return float("inf")
        geom = point_proj.geometry.iloc[0]
        min_dist_m = self._uc_proj.geometry.distance(geom).min()
        return min_dist_m / _METERS_PER_MILE

    def _get_place_population(self, pc_match: Any) -> int:
        """Extract population for a matched principal city."""
        # Try common column names for place identifier
        for col in ("PLACEFP", "GEOID", "placefp", "geoid", "NAME", "name"):
            if col in pc_match.columns:
                place_id = str(pc_match[col].iloc[0])
                pop = self._place_populations.get(place_id)
                if pop is not None:
                    return pop
        # Fallback: check for an inline population column
        for col in ("POP", "POPULATION", "pop", "population", "POP20", "POP10"):
            if col in pc_match.columns:
                return int(pc_match[col].iloc[0])
        # Default to small city if no population data available
        log.warning("No population data found for principal city match; defaulting to small city")
        return 0

    def _get_ua_population(self, ua_match: Any) -> int:
        """Extract population for a matched UA."""
        # Try ua_populations dict first
        for col in ("UACE20", "UACE10", "GEOID", "uace20", "uace10", "geoid"):
            if col in ua_match.columns:
                ua_id = str(ua_match[col].iloc[0])
                pop = self._ua_populations.get(ua_id)
                if pop is not None:
                    return pop
        # Fallback: inline population column
        for col in ("POP", "POPULATION", "POP20", "POP10", "pop"):
            if col in ua_match.columns:
                return int(ua_match[col].iloc[0])
        log.warning("No population data found for UA match; defaulting to small suburb")
        return 0

    # ------------------------------------------------------------------
    # Bulk classification
    # ------------------------------------------------------------------

    def classify_points(self, gdf: Any, geometry_col: str = "geometry") -> Any:
        """Bulk classify a GeoDataFrame of points.

        Adds columns: ``locale_code`` (int), ``locale_category`` (str),
        ``locale_subcategory`` (str), ``locale_label`` (str).

        Args:
            gdf: GeoDataFrame with point geometries.
            geometry_col: Name of the geometry column.

        Returns:
            The input GeoDataFrame with locale columns added.
        """
        results = []
        for _, row in gdf.iterrows():
            geom = row[geometry_col]
            lc = self.classify_point(geom.x, geom.y)
            results.append(lc)

        gdf = gdf.copy()
        gdf["locale_code"] = [r.code for r in results]
        gdf["locale_category"] = [r.category for r in results]
        gdf["locale_subcategory"] = [r.subcategory for r in results]
        gdf["locale_label"] = [r.label for r in results]
        return gdf

    # ------------------------------------------------------------------
    # Polygon classification
    # ------------------------------------------------------------------

    def classify_polygon(
        self,
        polygon: Any,
        method: str = "area_weighted",
    ) -> dict:
        """Classify a polygon by locale distribution.

        Args:
            polygon: A Shapely polygon or multipolygon geometry.
            method: ``"area_weighted"``, ``"majority"``, or ``"distribution"``.

        Returns:
            If ``method="majority"``: ``{"locale_code": 21, "locale_label": "..."}``
            If ``method="distribution"`` or ``"area_weighted"``: dict of
            ``{code: fraction}`` pairs summing to ~1.0.
        """
        import geopandas as gpd

        self._ensure_projected()
        proj_crs = f"EPSG:{self._projection_crs}"

        # Build locale territory by intersecting polygon with UA/UC layers
        poly_gdf = gpd.GeoDataFrame(
            {"id": [0]}, geometry=[polygon],
            crs=f"EPSG:{settings.INPUT_CRS}",
        ).to_crs(proj_crs)
        poly_proj = poly_gdf.geometry.iloc[0]
        total_area = poly_proj.area

        if total_area == 0:
            return {"locale_code": 43, "locale_label": RURAL_REMOTE.label}

        code_areas: Dict[int, float] = {}

        # Intersect with UA polygons
        if self._ua_proj is not None and len(self._ua_proj) > 0:
            for _, ua_row in self._ua_proj.iterrows():
                intersection = poly_proj.intersection(ua_row.geometry)
                if not intersection.is_empty:
                    # Simplification: classify all UA intersections as suburb-large
                    # A full implementation would check principal city overlap per fragment
                    code_areas.setdefault(21, 0.0)
                    code_areas[21] += intersection.area

        # Intersect with UC polygons
        if self._uc_proj is not None and len(self._uc_proj) > 0:
            for _, uc_row in self._uc_proj.iterrows():
                intersection = poly_proj.intersection(uc_row.geometry)
                if not intersection.is_empty:
                    code_areas.setdefault(31, 0.0)
                    code_areas[31] += intersection.area

        # Remaining area is rural
        covered = sum(code_areas.values())
        rural_area = max(0.0, total_area - covered)
        if rural_area > 0:
            code_areas[43] = rural_area

        # Normalize to fractions
        distribution = {code: area / total_area for code, area in code_areas.items()}

        if method == "majority":
            majority_code = max(distribution, key=distribution.get)
            lc = locale_from_code(majority_code)
            return {"locale_code": majority_code, "locale_label": lc.label}

        # "distribution" or "area_weighted"
        return distribution

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def from_census_year(
        cls,
        year: int = 2020,
        cache_dir: Optional[str] = None,
        projection_crs: Optional[int] = None,
    ) -> "NCESLocaleClassifier":
        """Construct a classifier from Census TIGER downloads.

        Downloads UA/UC (uac), Place, and CBSA shapefiles for the given year,
        identifies principal cities from population thresholds, and loads
        population estimates from shapefile attributes.

        For 2020+ Census data where Urban Clusters were eliminated, this
        method derives a UC-equivalent set by filtering urban areas with
        population < 50,000 (the original UC threshold). This ensures Town
        codes (31-33) remain reachable.

        Principal cities are identified by population threshold (>= 25,000),
        not from the OMB CBSA delineation file. This is a best-effort
        approximation. For precise NCES-matching classification, use
        ``from_nces_boundaries()`` when available.

        Args:
            year: Census year for boundary data (2010 or 2020 recommended).
            cache_dir: Local directory for caching downloaded shapefiles.
            projection_crs: EPSG code for distance computation.

        Returns:
            An initialized ``NCESLocaleClassifier``.

        Raises:
            ImportError: If geopandas is not available.
        """
        from .spatial_data import CensusDataSource

        census = CensusDataSource()
        log.info(f"Loading Census TIGER data for year {year}...")

        # Download UAC layer (contains both UAs and UCs)
        uac_gdf = census.get_geographic_boundaries(
            year=year, geographic_level="uac",
        )

        # Split UA vs UC based on Census type field
        # 2010 Census: UATYP10 == 'U' (UA) or 'C' (UC)
        # 2020 Census: UCs eliminated — all records are UAs
        ua_col = None
        for col in ("UATYP10", "UATYP20", "uatyp10", "uatyp20"):
            if col in uac_gdf.columns:
                ua_col = col
                break

        # Find population column on the UAC layer
        uac_pop_col = _find_column(uac_gdf, _POPULATION_COLUMNS)

        if ua_col is not None:
            urbanized_areas = uac_gdf[uac_gdf[ua_col] == "U"].copy()
            urban_clusters = uac_gdf[uac_gdf[ua_col] == "C"].copy()
        else:
            # 2020+: UCs were eliminated. Derive a UC-equivalent set from
            # urban areas with population < 50,000 (the original UC threshold).
            if uac_pop_col is not None:
                urbanized_areas = uac_gdf[uac_gdf[uac_pop_col] >= _UA_POP_THRESHOLD].copy()
                urban_clusters = uac_gdf[uac_gdf[uac_pop_col] < _UA_POP_THRESHOLD].copy()
                log.info(
                    f"2020+ Census: derived UC-equivalent set from urban areas "
                    f"with pop < {_UA_POP_THRESHOLD:,} "
                    f"({len(urbanized_areas)} UAs, {len(urban_clusters)} UC-equivalents)"
                )
            else:
                # No population column — can't split. Treat all as UA and
                # warn that Town codes will be unreachable.
                urbanized_areas = uac_gdf.copy()
                urban_clusters = None
                log.warning(
                    "2020+ Census UAC data has no population column; "
                    "cannot derive UC-equivalent set. Town codes (31-33) "
                    "will be unreachable."
                )

        # Extract UA/UC populations from shapefile attributes
        uac_id_col = _find_column(uac_gdf, _UA_ID_COLUMNS)
        ua_populations: Dict[str, int] = {}
        if uac_pop_col and uac_id_col:
            for _, row in urbanized_areas.iterrows():
                ua_populations[str(row[uac_id_col])] = int(row[uac_pop_col])

        # Download Place boundaries
        try:
            places_gdf = census.get_geographic_boundaries(
                year=year, geographic_level="place",
            )
        except Exception:
            log.warning("Could not load Place boundaries; principal city detection limited")
            import geopandas as gpd
            places_gdf = gpd.GeoDataFrame()

        # Extract place populations from shapefile attributes
        place_populations: Dict[str, int] = {}
        place_pop_col = _find_column(places_gdf, _POPULATION_COLUMNS)
        place_id_col = _find_column(places_gdf, _PLACE_ID_COLUMNS)

        if place_pop_col and place_id_col:
            for _, row in places_gdf.iterrows():
                try:
                    place_populations[str(row[place_id_col])] = int(row[place_pop_col])
                except (ValueError, TypeError):
                    continue

        # Filter principal cities: places meeting the small_city population
        # threshold. This is a best-effort approximation of the OMB CBSA
        # principal city designation. A full implementation would cross-
        # reference with the OMB CBSA delineation file.
        small_city_threshold = POPULATION_THRESHOLDS["small_city"]
        if place_pop_col is not None and len(places_gdf) > 0:
            principal_cities = places_gdf[
                places_gdf[place_pop_col] >= small_city_threshold
            ].copy()
            log.info(
                f"Identified {len(principal_cities)} principal cities "
                f"(places with pop >= {small_city_threshold:,})"
            )
        else:
            # Degraded mode: no population data to filter on.
            # Use all places and warn.
            principal_cities = places_gdf
            if len(places_gdf) > 0:
                log.warning(
                    "No population column found on Places layer; using all "
                    f"places ({len(places_gdf)}) as potential principal cities. "
                    "City/Suburb size classification may be inaccurate."
                )

        return cls(
            urbanized_areas=urbanized_areas,
            urban_clusters=urban_clusters,
            principal_cities=principal_cities,
            place_populations=place_populations,
            ua_populations=ua_populations,
            projection_crs=projection_crs,
        )

    @classmethod
    def from_nces_boundaries(
        cls,
        year: int = 2023,
        cache_dir: Optional[str] = None,
        projection_crs: Optional[int] = None,
    ) -> "NCESLocaleClassifier":
        """Construct a classifier from NCES pre-computed locale boundary shapefiles.

        NCES publishes locale territory polygons that are already classified
        with locale codes (11-43). This is faster than computing from Census
        inputs but limited to years NCES has published.

        The downloaded boundaries are split into:
        - Urbanized Area proxies: City (11-13) + Suburb (21-23) territories
        - Urban Cluster proxies: Town (31-33) territories
        - Principal city proxies: City (11-13) territories only

        The classifier then works identically to the Census-based one.

        Args:
            year: NCES publication year.
            cache_dir: Local directory for caching downloaded shapefiles.
            projection_crs: EPSG code for distance computation.

        Returns:
            An initialized ``NCESLocaleClassifier``.
        """
        import geopandas as gpd

        from .nces_download import NCESDownloader

        downloader = NCESDownloader(cache_dir=cache_dir)
        boundaries = downloader.download_locale_boundaries(year)

        proj = projection_crs or settings.PROJECTION_CRS

        # Split boundaries into UA-like and UC-like territories.
        # City + Suburb codes (11-23) approximate Urbanized Areas.
        # Town codes (31-33) approximate Urban Clusters.
        city_mask = boundaries["locale_code"].between(11, 13)
        suburb_mask = boundaries["locale_code"].between(21, 23)
        town_mask = boundaries["locale_code"].between(31, 33)

        ua_gdf = boundaries[city_mask | suburb_mask].copy()
        uc_gdf = boundaries[town_mask].copy()
        pc_gdf = boundaries[city_mask].copy()

        # Build synthetic population dicts keyed by index.
        # City-Large (11) → 250k+, City-Midsize (12) → 100k+, etc.
        _pop_map = {
            11: 500_000, 12: 150_000, 13: 50_000,
            21: 500_000, 22: 150_000, 23: 50_000,
        }
        place_pops = {}
        for idx, row in pc_gdf.iterrows():
            place_pops[str(idx)] = _pop_map.get(row["locale_code"], 50_000)

        ua_pops = {}
        for idx, row in ua_gdf.iterrows():
            ua_pops[str(idx)] = _pop_map.get(row["locale_code"], 100_000)

        return cls(
            urbanized_areas=ua_gdf,
            urban_clusters=uc_gdf,
            principal_cities=pc_gdf,
            place_populations=place_pops,
            ua_populations=ua_pops,
            projection_crs=proj,
        )

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def locale_label(code: int) -> str:
        """Convert an integer locale code to a human-readable label.

        >>> NCESLocaleClassifier.locale_label(11)
        'City-Large'
        >>> NCESLocaleClassifier.locale_label(43)
        'Rural-Remote'
        """
        return locale_from_code(code).label
