"""
NCES Urban-Centric Locale Classification for siege_utilities.

Implements the National Center for Education Statistics (NCES) 12-code locale
classification system. Classifies arbitrary geographic points and polygons
into City/Suburb/Town/Rural categories with size/distance subtypes.

Two modes of operation:
1. Pre-computed: Uses NCES-published locale boundary shapefiles (fastest)
2. On-the-fly: Computes from caller-supplied UA/UC/Place and population inputs

See docs/design/nces-locale-classification.md for full algorithm description.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional

from siege_utilities.conf import settings
from siege_utilities.config.nces_constants import (
    DISTANCE_THRESHOLDS,
    LOCALE_NUMERIC_CODES,
    POPULATION_THRESHOLDS,
    validate_locale_code,
)
from siege_utilities.geo._geographic_crs import (
    _geographic_geometries,
    _geographic_polygon,
)

log = logging.getLogger(__name__)

_VALID_METHODS = frozenset({"area_weighted", "majority", "distribution"})

__all__ = [
    "CITY_LARGE",
    "CITY_MIDSIZE",
    "CITY_SMALL",
    "LocaleCode",
    "LocaleIndex",
    "LocaleType",
    "NCESLocaleClassifier",
    "RURAL_DISTANT",
    "RURAL_FRINGE",
    "RURAL_REMOTE",
    "SUBURB_LARGE",
    "SUBURB_MIDSIZE",
    "SUBURB_SMALL",
    "TOWN_DISTANT",
    "TOWN_FRINGE",
    "TOWN_REMOTE",
    "locale_from_code",
]

# Meters per mile — used for distance conversion after CRS projection
_METERS_PER_MILE = 1_609.344

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

class LocaleIndex:
    """Precomputed GEOID → LocaleCode mapping for fast lookup.

    Built from any data source that pairs GEOIDs with NCES locale codes
    (e.g., NCES district data, school locations, or Census tract assignments).
    """

    def __init__(self, mapping: Optional[Dict[str, int]] = None):
        self._mapping: Dict[str, int] = mapping or {}

    def add(self, geoid: str, locale_code: int) -> None:
        self._mapping[geoid] = locale_code

    def add_bulk(self, pairs: Dict[str, int]) -> None:
        self._mapping.update(pairs)

    def get(self, geoid: str) -> Optional[LocaleCode]:
        code = self._mapping.get(geoid)
        if code is None:
            return None
        return locale_from_code(code)

    def __len__(self) -> int:
        return len(self._mapping)

    def __contains__(self, geoid: str) -> bool:
        return geoid in self._mapping

    @classmethod
    def from_dataframe(
        cls,
        df: Any,
        geoid_col: str = "geoid",
        locale_col: str = "locale_code",
    ) -> "LocaleIndex":
        mapping = {}
        for _, row in df.iterrows():
            geoid = str(row[geoid_col]).strip()
            try:
                code = int(row[locale_col])
                if validate_locale_code(code):
                    mapping[geoid] = code
            except (ValueError, TypeError):
                continue
        return cls(mapping)


class NCESLocaleClassifier:
    """Classify geographic points and polygons into NCES locale codes.

    Uses Census TIGER spatial data (Urbanized Areas, Urban Clusters, Places)
    and population thresholds to implement the NCES urban-centric locale
    classification algorithm (12-code system).

    The classifier can be initialized with pre-loaded GeoDataFrames (for
    testing or custom data) or constructed from published NCES boundaries via
    ``from_nces_boundaries``. ``from_census_year`` raises until the required
    population and principal-city sources are implemented.

    Args:
        urbanized_areas: GeoDataFrame of UA polygons (pop >= 50,000).
            Must contain a ``geometry`` column and a population field.
        urban_clusters: GeoDataFrame of UC polygons (pop 2,500-49,999).
            Must contain a ``geometry`` column. May be ``None`` for 2020+
            Census data where UCs were eliminated.
        principal_cities: GeoDataFrame of Place polygons that are designated
            principal cities of CBSAs.
        place_populations: Dict mapping 7-digit place GEOIDs (2-digit state
            FIPS + 5-digit PLACEFP) to population counts. Used to classify
            City subtypes (Large/Midsize/Small). Principal-city boundaries
            must carry GEOID or both STATEFP and PLACEFP (including 10/20
            suffixed variants).
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
        self._input_crs = f"EPSG:{settings.INPUT_CRS}"
        self._align_input_crs()

        self._locale_index: Optional[LocaleIndex] = None
        self._nces_boundaries = None
        self._nces_proj = None

        # Lazily projected copies (created on first classify call)
        self._ua_proj = None
        self._uc_proj = None

    def _align_input_crs(self) -> None:
        """Reproject boundary layers to input CRS if mismatched."""
        if self._ua is not None and self._ua.crs is not None:
            if str(self._ua.crs) != self._input_crs:
                self._ua = self._ua.to_crs(self._input_crs)
        if self._uc is not None and self._uc.crs is not None:
            if str(self._uc.crs) != self._input_crs:
                self._uc = self._uc.to_crs(self._input_crs)
        if self._principal_cities is not None and self._principal_cities.crs is not None:
            if str(self._principal_cities.crs) != self._input_crs:
                self._principal_cities = self._principal_cities.to_crs(self._input_crs)

    def _ensure_projected(self) -> None:
        """Project UA/UC layers to the configured CRS for distance ops."""
        import geopandas as gpd  # noqa: F401 — validates availability

        crs_string = f"EPSG:{self._projection_crs}"
        if self._nces_proj is None and self._nces_boundaries is not None:
            self._nces_proj = self._nces_boundaries.to_crs(crs_string)
        if self._ua_proj is None and self._ua is not None:
            self._ua_proj = self._ua.to_crs(crs_string)
        if self._uc_proj is None and self._uc is not None:
            self._uc_proj = self._uc.to_crs(crs_string)

    # ------------------------------------------------------------------
    # GEOID lookup
    # ------------------------------------------------------------------

    @property
    def locale_index(self) -> Optional[LocaleIndex]:
        return self._locale_index

    @locale_index.setter
    def locale_index(self, index: LocaleIndex) -> None:
        self._locale_index = index

    def classify_geoid(self, geoid: str) -> Optional[LocaleCode]:
        """Fast-path locale lookup by Census GEOID.

        Returns the precomputed locale code if the GEOID is in the index,
        or ``None`` if no index is set or the GEOID is not found.
        Use ``classify_geoid_or_point()`` for automatic fallback to
        spatial classification.
        """
        if self._locale_index is None:
            return None
        return self._locale_index.get(geoid)

    def classify_geoid_or_point(
        self, geoid: str, lon: float, lat: float,
    ) -> LocaleCode:
        """Classify by GEOID if available, falling back to spatial."""
        result = self.classify_geoid(geoid)
        if result is not None:
            return result
        return self.classify_point(lon, lat)

    # ------------------------------------------------------------------
    # Point classification
    # ------------------------------------------------------------------

    def classify_point(self, lon: float, lat: float) -> LocaleCode:
        """Classify a single geographic point.

        For published NCES boundaries, returns the polygon's locale code.
        Shared edges and overlaps use the first matching row in download
        order. Points outside the published coverage raise ValueError.

        For caller-supplied Census inputs, implements the NCES decision tree:
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

        point = Point(lon, lat)
        if self._nces_boundaries is not None:
            # Include boundary points; spatial-index order is not stable, so
            # select the first matching row by its positional index.
            matches = self._nces_boundaries.sindex.query(point, predicate="intersects")
            if len(matches) == 0:
                raise ValueError("Point is outside published NCES locale coverage")
            code = self._nces_boundaries.iloc[min(matches)]["locale_code"]
            return locale_from_code(int(code))

        self._ensure_projected()

        input_crs = f"EPSG:{settings.INPUT_CRS}"
        proj_crs = f"EPSG:{self._projection_crs}"

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
        """Extract population for a matched principal city; raise ValueError if unknown."""
        # PLACEFP alone is only unique within a state. Prefer a full GEOID,
        # or construct it from the state and place FIPS components.
        for suffix in ("", "20", "10"):
            for geoid_col in (f"GEOID{suffix}", f"geoid{suffix}"):
                if geoid_col in pc_match.columns:
                    geoid = str(pc_match[geoid_col].iloc[0]).zfill(7)
                    pop = self._place_populations.get(geoid)
                    if pop is not None:
                        return pop
            for state_col, place_col in (
                (f"STATEFP{suffix}", f"PLACEFP{suffix}"),
                (f"statefp{suffix}", f"placefp{suffix}"),
            ):
                if state_col in pc_match.columns and place_col in pc_match.columns:
                    geoid = (
                        str(pc_match[state_col].iloc[0]).zfill(2)
                        + str(pc_match[place_col].iloc[0]).zfill(5)
                    )
                    pop = self._place_populations.get(geoid)
                    if pop is not None:
                        return pop
        # Fallback: check for an inline population column
        for col in ("POP", "POPULATION", "pop", "population", "POP20", "POP10"):
            if col in pc_match.columns:
                try:
                    return int(pc_match[col].iloc[0])
                except (ValueError, TypeError, OverflowError) as exc:
                    raise ValueError("Invalid place population") from exc
        raise ValueError("Missing principal city population")

    def _get_ua_population(self, ua_match: Any) -> int:
        """Extract population for a matched UA; raise ValueError if unknown."""
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
                try:
                    return int(ua_match[col].iloc[0])
                except (ValueError, TypeError, OverflowError) as exc:
                    raise ValueError("Invalid ua population") from exc
        raise ValueError("Missing UA population")

    # ------------------------------------------------------------------
    # Bulk classification
    # ------------------------------------------------------------------

    def classify_points(self, gdf: Any, geometry_col: str = "geometry") -> Any:
        """Bulk classify a GeoDataFrame of points.

        Adds columns: ``locale_code`` (int), ``locale_category`` (str),
        ``locale_subcategory`` (str), ``locale_label`` (str).

        Args:
            gdf: GeoDataFrame with point geometries. Known CRSs are reprojected
                to ``settings.INPUT_CRS`` (EPSG:4269) for classification.
                Without a CRS, coordinates are assumed to be in that CRS.
            geometry_col: Name of the geometry column.

        Returns:
            A copy with locale columns added, retaining the input CRS and geometry.

        Raises:
            ValueError: If CRS is missing and longitude/latitude exceeds
                +/-180 or +/-90; the error names the function and value.
        """
        geometries = _geographic_geometries(
            gdf[geometry_col], f"EPSG:{settings.INPUT_CRS}", "classify_points",
        )
        results = []
        for geom in geometries:
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
            polygon: A Shapely polygon/multipolygon in ``settings.INPUT_CRS``
                (EPSG:4269), or a GeoDataFrame/GeoSeries whose polygons are
                reprojected to that CRS and combined. Inputs are not mutated.
            method: ``"area_weighted"``, ``"majority"``, or ``"distribution"``.

        Returns:
            If ``method="majority"``: ``{"locale_code": 21, "locale_label": "..."}``
            If ``method="distribution"`` or ``"area_weighted"``: dict of
            ``{code: fraction}`` pairs summing to ~1.0.

        Raises:
            ValueError: If *method* is invalid, or CRS is missing and coordinates
                exceed +/-180 longitude or +/-90 latitude.
        """
        if method not in _VALID_METHODS:
            raise ValueError(
                f"Invalid method {method!r}; must be one of {sorted(_VALID_METHODS)}"
            )
        import geopandas as gpd

        polygon = _geographic_polygon(
            polygon, f"EPSG:{settings.INPUT_CRS}", "classify_polygon",
        )
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

        if self._nces_proj is not None:
            matches = self._nces_proj.sindex.query(poly_proj, predicate="intersects")
            remaining = poly_proj
            for position in sorted(matches):
                row = self._nces_proj.iloc[position]
                intersection = remaining.intersection(row.geometry)
                if intersection.area > 0:
                    code = int(row["locale_code"])
                    code_areas[code] = code_areas.get(code, 0.0) + intersection.area
                    # Apply the same first-row tie-break as point lookup.
                    remaining = remaining.difference(row.geometry)

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
            code_areas[43] = code_areas.get(43, 0.0) + rural_area

        # Normalize to fractions
        distribution = {code: area / total_area for code, area in code_areas.items()}

        if method == "majority":
            majority_code = max(distribution, key=distribution.get)
            lc = locale_from_code(majority_code)
            return {"locale_code": majority_code, "locale_label": lc.label}

        # "distribution" or "area_weighted"
        return distribution

    def classify_polygons(
        self,
        gdf: Any,
        method: str = "majority",
        geometry_col: str = "geometry",
    ) -> Any:
        """Bulk classify a GeoDataFrame of polygons.

        For ``method="majority"``, adds columns: ``locale_code`` (int),
        ``locale_label`` (str).

        For ``method="distribution"`` or ``"area_weighted"``, adds a
        ``locale_distribution`` column containing per-row dicts of
        ``{code: fraction}`` pairs.

        Args:
            gdf: GeoDataFrame with polygon geometries. Known CRSs are reprojected
                to ``settings.INPUT_CRS`` (EPSG:4269) for classification.
                Without a CRS, coordinates are assumed to be in that CRS.
            method: ``"majority"``, ``"distribution"``, or ``"area_weighted"``.
            geometry_col: Name of the geometry column.

        Returns:
            A copy with locale columns added, retaining the input CRS and geometry.

        Raises:
            ValueError: If *method* is invalid, or CRS is missing and coordinates
                exceed +/-180 longitude or +/-90 latitude.
        """
        if method not in _VALID_METHODS:
            raise ValueError(
                f"Invalid method {method!r}; must be one of {sorted(_VALID_METHODS)}"
            )
        geometries = _geographic_geometries(
            gdf[geometry_col], f"EPSG:{settings.INPUT_CRS}", "classify_polygons",
        )
        gdf = gdf.copy()

        if method == "majority":
            codes = []
            labels = []
            for geometry in geometries:
                result = self.classify_polygon(geometry, method="majority")
                codes.append(result["locale_code"])
                labels.append(result["locale_label"])
            gdf["locale_code"] = codes
            gdf["locale_label"] = labels
            gdf["locale_category"] = [
                locale_from_code(c).category for c in codes
            ]
            gdf["locale_subcategory"] = [
                locale_from_code(c).subcategory for c in codes
            ]
        else:
            distributions = []
            for geometry in geometries:
                dist = self.classify_polygon(geometry, method=method)
                distributions.append(dist)
            gdf["locale_distribution"] = distributions

        return gdf

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
        """Reject construction from TIGER boundaries without required sources.

        TIGER UAC/PLACE shapefiles do not supply population counts. Correct
        classification requires PL 94-171 / DHC population data joined by
        UA ID and 7-digit place GEOID, plus PCICBSA / OMB principal-city
        designations. These source integrations are not implemented here.
        Population thresholds cannot substitute for principal-city status.

        Use ``from_nces_boundaries`` for published NCES classifications, or
        the direct constructor with externally sourced populations and
        principal-city boundaries. No downloads or approximations are made.

        Args:
            year: Requested Census year.
            cache_dir: Retained for API compatibility.
            projection_crs: Retained for API compatibility.

        Raises:
            ValueError: Always, until the required source integrations exist.
        """
        raise ValueError(
            f"Cannot construct an NCES locale classifier from {year} TIGER "
            "boundaries alone: PL 94-171 / DHC population data (keyed by UA ID "
            "and 7-digit place GEOID) and PCICBSA / OMB principal-city "
            "designations are required but are not sourced by from_census_year. "
            "Use from_nces_boundaries() or supply these data to the direct "
            "NCESLocaleClassifier constructor."
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

        Points are looked up directly in the published ``locale_code``
        polygons, without synthetic populations or distance-based reclassification.
        Polygon edges are included. If multiple polygons match, the first row
        in download order wins; NCES territories normally partition space.
        Points outside coverage raise ValueError instead of inventing a locale.

        Args:
            year: NCES publication year.
            cache_dir: Local directory for caching downloaded shapefiles.
            projection_crs: EPSG code for distance computation.

        Returns:
            An initialized ``NCESLocaleClassifier``.
        """

        from .providers.nces_download import NCESDownloader

        downloader = NCESDownloader(cache_dir=cache_dir)
        boundaries = downloader.download_locale_boundaries(year)
        classifier = cls(
            urbanized_areas=None,
            urban_clusters=None,
            principal_cities=None,
            place_populations={},
            projection_crs=projection_crs,
        )
        classifier._nces_boundaries = boundaries[["locale_code", "geometry"]].to_crs(
            classifier._input_crs,
        )
        return classifier

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
