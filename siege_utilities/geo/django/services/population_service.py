"""
Service for populating Census boundary data from TIGER/Line shapefiles.

Uses the existing siege_utilities.geo.spatial_data module to download
boundaries, then loads them into Django models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from django.db import transaction

from siege_utilities.conf import settings

if TYPE_CHECKING:
    import geopandas as gpd

logger = logging.getLogger(__name__)


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

    # Mapping from geography type to model class
    GEOGRAPHY_MODELS = {
        "state": "State",
        "county": "County",
        "tract": "Tract",
        "blockgroup": "BlockGroup",
        "block": "Block",
        "place": "Place",
        "zcta": "ZCTA",
        "cd": "CongressionalDistrict",
    }

    # TIGER/Line geography type names
    TIGER_TYPES = {
        "state": "STATE",
        "county": "COUNTY",
        "tract": "TRACT",
        "blockgroup": "BG",
        "block": "TABBLOCK",
        "place": "PLACE",
        "zcta": "ZCTA5",
        "cd": "CD",
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
        from ..models import (
            State,
            County,
            Tract,
            BlockGroup,
            Block,
            Place,
            ZCTA,
            CongressionalDistrict,
        )

        models = {
            "state": State,
            "county": County,
            "tract": Tract,
            "blockgroup": BlockGroup,
            "block": Block,
            "place": Place,
            "zcta": ZCTA,
            "cd": CongressionalDistrict,
        }
        return models.get(geography_type.lower())

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
        """
        from siege_utilities.geo import get_geographic_boundaries

        tiger_type = self.TIGER_TYPES.get(geography_type.lower())
        if not tiger_type:
            raise ValueError(f"Unknown geography type: {geography_type}")

        logger.info(f"Downloading {tiger_type} boundaries for year {year}")

        gdf = get_geographic_boundaries(
            state_identifier=state_fips,
            boundary_type=tiger_type,
            year=year,
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
        import geopandas as gpd

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

        # Rename columns
        gdf = gdf.rename(columns=column_mappings)

        # Ensure geometry matches storage CRS
        if gdf.crs and gdf.crs.to_epsg() != settings.STORAGE_CRS:
            gdf = gdf.to_crs(epsg=settings.STORAGE_CRS)

        return gdf

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
            PopulationResult with statistics
        """
        from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

        model = self._get_model(geography_type)
        if not model:
            return PopulationResult(
                geography_type=geography_type,
                year=year,
                state_fips=state_fips,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=[f"Unknown geography type: {geography_type}"],
            )

        # Download data
        try:
            gdf = self._download_boundaries(geography_type, year, state_fips)
            gdf = self._normalize_geodataframe(gdf, geography_type)
        except Exception as e:
            logger.error(f"Error downloading boundaries: {e}")
            return PopulationResult(
                geography_type=geography_type,
                year=year,
                state_fips=state_fips,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=[str(e)],
            )

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
                    existing.save()
                    updated += 1
                else:
                    # Create
                    objects_to_create.append(model(**kwargs))

                    # Batch create
                    if len(objects_to_create) >= batch_size:
                        model.objects.bulk_create(
                            objects_to_create, ignore_conflicts=True
                        )
                        created += len(objects_to_create)
                        objects_to_create = []

            except Exception as e:
                logger.error(f"Error processing record {idx}: {e}")
                errors.append(f"Record {idx}: {e}")

        # Create remaining
        if objects_to_create:
            model.objects.bulk_create(objects_to_create, ignore_conflicts=True)
            created += len(objects_to_create)

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

        For example, link counties to states, tracts to counties, etc.

        Args:
            geography_type: Type of child geography
            year: Census year
            state_fips: Optional state filter

        Returns:
            Number of relationships linked
        """
        model = self._get_model(geography_type)
        if not model:
            return 0

        # Define parent relationships
        parent_map = {
            "county": ("state", "State", "state_fips"),
            "tract": ("county", "County", "state_fips", "county_fips"),
            "blockgroup": ("tract", "Tract", "state_fips", "county_fips", "tract_code"),
            "block": ("blockgroup", "BlockGroup", "state_fips", "county_fips", "tract_code", "block_group"),
            "place": ("state", "State", "state_fips"),
            "cd": ("state", "State", "state_fips"),
        }

        if geography_type not in parent_map:
            return 0

        parent_info = parent_map[geography_type]
        parent_field = parent_info[0]
        parent_model_name = parent_info[1]
        key_fields = parent_info[2:]

        parent_model = self._get_model(parent_field)
        if not parent_model:
            return 0

        # Get all child records
        qs = model.objects.filter(vintage_year=year)
        if state_fips:
            qs = qs.filter(state_fips=state_fips)

        linked = 0
        for child in qs.filter(**{f"{parent_field}__isnull": True}):
            # Build parent lookup
            lookup = {"vintage_year": year}
            for field in key_fields:
                lookup[field] = getattr(child, field)

            parent = parent_model.objects.filter(**lookup).first()
            if parent:
                setattr(child, parent_field, parent)
                child.save(update_fields=[parent_field])
                linked += 1

        logger.info(f"Linked {linked} {geography_type} records to parents")
        return linked
