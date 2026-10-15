"""
Service for populating Census boundary data from TIGER/Line shapefiles.

Uses the existing siege_utilities.geo.spatial_data module to download
boundaries, then loads them into Django models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from django.db import IntegrityError, transaction

from siege_utilities.conf import settings

if TYPE_CHECKING:
    import geopandas as gpd
    from django.db.models import Model

logger = logging.getLogger(__name__)

__all__ = [
    'PopulationResult',
    'BoundaryPopulationService',
]


@dataclass
class PopulationResult:
    """Result of a boundary population operation."""

    geography_type: str
    year: int
    state_fips: Optional[str]
    records_created: int
    records_updated: int
    records_skipped: int
    errors: list[str]

    @property
    def total_processed(self) -> int:
        return self.records_created + self.records_updated + self.records_skipped

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class BoundaryPopulationService:
    """
    Service for populating Census boundary models from TIGER/Line data.

    This service integrates with the existing siege_utilities.geo module
    to download TIGER/Line shapefiles and load them into Django models.

    Example:
        >>> service = BoundaryPopulationService()
        >>> result = service.populate_counties(year=2020, state_fips='06')
        >>> print(f"Created {result.records_created} counties")

        >>> # Or use the generic method
        >>> result = service.populate(
        ...     geography_type='tract',
        ...     year=2020,
        ...     state_fips='06'
        ... )
    """

    # Mapping from geography type to model class name
    GEOGRAPHY_MODELS = {
        "state": "State",
        "county": "County",
        "tract": "Tract",
        "blockgroup": "BlockGroup",
        "block": "Block",
        "place": "Place",
        "zcta": "ZCTA",
        "cd": "CongressionalDistrict",
        "sldu": "StateLegislativeUpper",
        "sldl": "StateLegislativeLower",
        "vtd": "VTD",
        "precinct": "Precinct",
        "cbsa": "CBSA",
        "urbanarea": "UrbanArea",
        "elsd": "SchoolDistrictElementary",
        "scsd": "SchoolDistrictSecondary",
        "unsd": "SchoolDistrictUnified",
    }

    # fetch_geographic_boundaries accepts discovery level names, not TIGER codes.
    GEOGRAPHIC_LEVELS = {
        "state": "state",
        "county": "county",
        "tract": "tract",
        "blockgroup": "block_group",
        "block": "block",
        "place": "place",
        "zcta": "zcta",
        "cd": "cd",
        "sldu": "sldu",
        "sldl": "sldl",
        "vtd": "vtd",
        "cbsa": "cbsa",
        "urbanarea": "uac",
        "elsd": "elsd",
        "scsd": "scsd",
        "unsd": "unsd",
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the service.

        Args:
            cache_dir: Directory for caching downloaded shapefiles
        """
        self.cache_dir = cache_dir

    def _get_model(self, geography_type: str):
        """Get the Django model class for a geography type."""
        from .. import models as model_module

        model_name = self.GEOGRAPHY_MODELS.get(geography_type.lower())
        if model_name:
            return getattr(model_module, model_name, None)
        return None

    def _download_boundaries(
        self, geography_type: str, year: int, state_fips: Optional[str] = None
    ) -> "gpd.GeoDataFrame":
        """
        Download boundary data using siege_utilities.geo.

        Args:
            geography_type: Type of geography (state, county, tract, etc.)
            year: Census year
            state_fips: State FIPS code (required for sub-state geographies)

        Returns:
            GeoDataFrame with boundary data

        Raises:
            ValueError: If the geography type has no supported fetch level.
            BoundaryRetrievalError: If retrieval fails or returns no boundaries.
        """
        from siege_utilities.geo import fetch_geographic_boundaries
        from siege_utilities.geo.boundary_result import BoundaryRetrievalError

        geography_type = geography_type.lower()
        geographic_level = self.GEOGRAPHIC_LEVELS.get(geography_type)
        if geographic_level is None:
            if geography_type in self.GEOGRAPHY_MODELS:
                raise ValueError(
                    f"Unsupported geography type: {geography_type}; "
                    "no Census fetch level is available"
                )
            raise ValueError(f"Unknown geography type: {geography_type}")

        logger.info("Downloading %s boundaries for year %s", geographic_level, year)

        result = fetch_geographic_boundaries(
            year=year,
            geographic_level=geographic_level,
            state_fips=state_fips,
        )
        context = {
            "year": year,
            "geographic_level": geographic_level,
            "state_fips": state_fips,
        }
        if result is None:
            raise BoundaryRetrievalError(
                f"No boundary result returned for {geography_type} "
                f"(year={year}, state_fips={state_fips})",
                stage="download",
                context=context,
            )
        if not result.success:
            result.raise_on_error()

        gdf = result.geodataframe
        if gdf is None or gdf.empty:
            raise BoundaryRetrievalError(
                f"No boundaries returned for {geography_type} "
                f"(year={year}, state_fips={state_fips})",
                stage="parse",
                context={**result.context, **context},
            )

        return gdf

    def _normalize_geodataframe(
        self, gdf: "gpd.GeoDataFrame", geography_type: str
    ) -> "gpd.GeoDataFrame":
        """
        Normalize column names from various TIGER/Line formats.

        Args:
            gdf: Input GeoDataFrame
            geography_type: Type of geography

        Returns:
            GeoDataFrame with normalized column names
        """

        # Standard column mappings
        column_mappings = {
            # State
            "STATEFP": "state_fips",
            "STUSPS": "abbreviation",
            # County
            "COUNTYFP": "county_fips",
            "NAMELSAD": "county_name",
            # Tract
            "TRACTCE": "tract_code",
            # Block Group
            "BLKGRPCE": "block_group",
            # Block
            "BLOCKCE": "block_code",
            # Place
            "PLACEFP": "place_fips",
            # ZCTA
            "ZCTA5CE": "zcta5",
            "ZCTA5CE20": "zcta5",
            "ZCTA5CE10": "zcta5",
            # Congressional District
            "CDFP": "district_number",
            "CD116FP": "district_number",
            "CD118FP": "district_number",
            # Common
            "GEOID": "GEOID",
            "GEOID20": "GEOID",
            "GEOID10": "GEOID",
            "NAME": "NAME",
            "NAME20": "NAME",
            "NAME10": "NAME",
            "ALAND": "ALAND",
            "ALAND20": "ALAND",
            "ALAND10": "ALAND",
            "AWATER": "AWATER",
            "AWATER20": "AWATER",
            "AWATER10": "AWATER",
            "FUNCSTAT": "functional_status",
            "FUNCSTAT20": "functional_status",
            "LSAD": "legal_statistical_area",
        }

        # fetch_geographic_boundaries lowercases TIGER columns; accept both
        # its output and raw TIGER names, including decennial suffixes.
        gdf = gdf.rename(columns={
            column: column_mappings.get(column.upper(), column)
            for column in gdf.columns
        })

        # Ensure geometry matches storage CRS
        if gdf.crs and gdf.crs.to_epsg() != settings.STORAGE_CRS:
            gdf = gdf.to_crs(epsg=settings.STORAGE_CRS)

        return gdf

    def _bulk_create_with_savepoints(
        self, model: type[Model], objects: list[Model]
    ) -> tuple[int, list[str]]:
        """Insert a batch, retrying rows only after a rolled-back integrity failure."""
        try:
            with transaction.atomic():
                model.objects.bulk_create(objects)
            return len(objects), []
        except IntegrityError:
            # The batch savepoint must roll back before any retry queries run.
            created = 0
            errors = []
            for obj in objects:
                try:
                    with transaction.atomic():
                        model.objects.bulk_create([obj])
                    created += 1
                except IntegrityError as exc:
                    error = f"GEOID {obj.geoid}: {exc}"
                    logger.warning("Skipping %s", error)
                    errors.append(error)
            return created, errors

    @transaction.atomic
    def populate(
        self,
        geography_type: str,
        year: int,
        state_fips: Optional[str] = None,
        update_existing: bool = False,
        batch_size: int = 500,
    ) -> PopulationResult:
        """
        Populate boundary data for a geography type.

        Args:
            geography_type: Type of geography (state, county, tract, etc.)
            year: Census year
            state_fips: State FIPS code (required for sub-state geographies)
            update_existing: If True, update existing records; otherwise skip
            batch_size: Number of records per database batch

        Returns:
            PopulationResult with statistics. Rows rejected by database integrity
            constraints are logged with their GEOID, counted as skipped, and
            included in errors; valid rows are retained.

        Raises:
            ValueError: If geography_type is unknown or unsupported.
            BoundaryRetrievalError: If retrieval fails or returns no boundaries.
                Download and normalization exceptions also propagate to callers.
        """
        from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

        model = self._get_model(geography_type)
        if not model:
            raise ValueError(f"Unknown geography type: {geography_type}")

        gdf = self._download_boundaries(geography_type, year, state_fips)
        gdf = self._normalize_geodataframe(gdf, geography_type)

        created = 0
        updated = 0
        skipped = 0
        errors = []

        # Process each record
        objects_to_create = []

        for idx, row in gdf.iterrows():
            try:
                geoid = str(row.get("GEOID", ""))
                if not geoid:
                    skipped += 1
                    continue

                # Check if exists
                existing = model.objects.filter(geoid=geoid, vintage_year=year).first()

                if existing and not update_existing:
                    skipped += 1
                    continue

                # Build geometry
                geom = GEOSGeometry(row.geometry.wkt, srid=settings.STORAGE_CRS)
                if geom.geom_type == "Polygon":
                    geom = MultiPolygon(geom, srid=settings.STORAGE_CRS)

                # Parse GEOID
                parsed = model.parse_geoid(geoid)

                # Build kwargs
                kwargs = {
                    "geoid": geoid,
                    "name": str(row.get("NAME", "")),
                    "geometry": geom,
                    "vintage_year": year,
                    "area_land": row.get("ALAND"),
                    "area_water": row.get("AWATER"),
                }
                kwargs.update(parsed)

                # Add model-specific fields
                if hasattr(model, "abbreviation") and "abbreviation" in row:
                    kwargs["abbreviation"] = row["abbreviation"]
                if hasattr(model, "county_name") and "county_name" in row:
                    kwargs["county_name"] = row["county_name"]
                if "functional_status" in row:
                    kwargs["funcstat"] = row.get("functional_status", "")
                if "legal_statistical_area" in row:
                    kwargs["lsad"] = row.get("legal_statistical_area", "")

                if existing:
                    # Update
                    for key, value in kwargs.items():
                        setattr(existing, key, value)
                    with transaction.atomic():
                        existing.save()
                    updated += 1
                else:
                    # Create
                    objects_to_create.append(model(**kwargs))

                    # Batch create
                    if len(objects_to_create) >= batch_size:
                        batch_created, batch_errors = self._bulk_create_with_savepoints(
                            model, objects_to_create
                        )
                        created += batch_created
                        skipped += len(batch_errors)
                        errors.extend(batch_errors)
                        objects_to_create = []

            except IntegrityError as e:
                error = f"GEOID {geoid}: {e}"
                logger.warning("Skipping %s", error)
                errors.append(error)
                skipped += 1
            except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
                logger.error(f"Error processing record {idx}: {e}")
                errors.append(f"Record {idx}: {e}")

        # Create remaining
        if objects_to_create:
            batch_created, batch_errors = self._bulk_create_with_savepoints(
                model, objects_to_create
            )
            created += batch_created
            skipped += len(batch_errors)
            errors.extend(batch_errors)

        logger.info(
            f"Populated {geography_type}: {created} created, {updated} updated, {skipped} skipped"
        )

        return PopulationResult(
            geography_type=geography_type,
            year=year,
            state_fips=state_fips,
            records_created=created,
            records_updated=updated,
            records_skipped=skipped,
            errors=errors,
        )

    def populate_states(self, year: int, **kwargs) -> PopulationResult:
        """Populate state boundaries."""
        return self.populate("state", year, **kwargs)

    def populate_counties(
        self, year: int, state_fips: Optional[str] = None, **kwargs
    ) -> PopulationResult:
        """Populate county boundaries."""
        return self.populate("county", year, state_fips, **kwargs)

    def populate_tracts(
        self, year: int, state_fips: str, **kwargs
    ) -> PopulationResult:
        """Populate tract boundaries (requires state)."""
        return self.populate("tract", year, state_fips, **kwargs)

    def populate_block_groups(
        self, year: int, state_fips: str, **kwargs
    ) -> PopulationResult:
        """Populate block group boundaries (requires state)."""
        return self.populate("blockgroup", year, state_fips, **kwargs)

    def populate_blocks(
        self, year: int, state_fips: str, **kwargs
    ) -> PopulationResult:
        """Populate block boundaries (requires state)."""
        return self.populate("block", year, state_fips, **kwargs)

    def populate_places(
        self, year: int, state_fips: Optional[str] = None, **kwargs
    ) -> PopulationResult:
        """Populate place boundaries."""
        return self.populate("place", year, state_fips, **kwargs)

    def populate_zctas(self, year: int, **kwargs) -> PopulationResult:
        """Populate ZCTA boundaries."""
        return self.populate("zcta", year, **kwargs)

    def populate_congressional_districts(
        self, year: int, state_fips: Optional[str] = None, **kwargs
    ) -> PopulationResult:
        """Populate congressional district boundaries."""
        return self.populate("cd", year, state_fips, **kwargs)

    def link_parent_relationships(
        self, geography_type: str, year: int, state_fips: Optional[str] = None
    ) -> int:
        """
        Link child boundaries to their parent boundaries.

        Resolve every missing FIPS-based parent at the same vintage. Existing
        links are preserved. VTD congressional-district assignment requires a
        spatial/crosswalk policy and is not resolved from FIPS components.

        Args:
            geography_type: Type of child geography
            year: Census year
            state_fips: Optional state filter

        Returns:
            Number of relationships linked

        Raises:
            ValueError: If geography_type is unknown.
        """
        geography_type = geography_type.lower()
        model = self._get_model(geography_type)
        if not model:
            raise ValueError(f"Unknown geography type: {geography_type}")

        # These are model FK names. Block.block_group is a derived code,
        # while Block.block_group_ref is its FK to BlockGroup.
        parent_map = {
            "county": ("state",),
            "tract": ("state", "county"),
            "blockgroup": ("state", "county", "tract"),
            "block": ("state", "county", "tract", "block_group_ref"),
            "place": ("state",),
            "cd": ("state",),
            "sldu": ("state",),
            "sldl": ("state",),
            "vtd": ("state", "county"),
            "precinct": ("state", "county"),
            "elsd": ("state",),
            "scsd": ("state",),
            "unsd": ("state",),
        }
        parent_keys = {
            "state": ("state_fips",),
            "county": ("state_fips", "county_fips"),
            "tract": ("state_fips", "county_fips", "tract_code"),
            "block_group_ref": (
                "state_fips", "county_fips", "tract_code", "block_group"
            ),
        }

        # Get all child records
        qs = model.objects.filter(vintage_year=year)
        if state_fips:
            qs = qs.filter(state_fips=state_fips)

        linked = 0
        for parent_field in parent_map.get(geography_type, ()):
            parent_model = model._meta.get_field(parent_field).remote_field.model
            for child in qs.filter(**{f"{parent_field}__isnull": True}):
                lookup = {"vintage_year": year}
                for field in parent_keys[parent_field]:
                    lookup[field] = getattr(child, field)

                parent = parent_model.objects.filter(**lookup).first()
                if parent:
                    setattr(child, parent_field, parent)
                    child.save(update_fields=[parent_field])
                    linked += 1

        logger.info("Linked %s %s parent relationships", linked, geography_type)
        return linked
