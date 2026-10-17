"""
Service for populating NLRB (National Labor Relations Board) region data.

This service creates registry rows with optional geometry. Dissolving counties
in the registry's primary states produces a state-level approximation, with
overlaps between regions, rather than authoritative NLRB jurisdictions.

Data source: manually maintained regional-office registry.
"""

import logging
from dataclasses import dataclass, field
from typing import List

from django.db import transaction

from siege_utilities.geo.providers.nlrb_regions import NLRB_REGIONS

log = logging.getLogger(__name__)

__all__ = [
    'NLRB_REGIONS',
    'NLRBPopulationResult',
    'NLRBPopulationService',
]


@dataclass
class NLRBPopulationResult:
    """Result of an NLRB region population run."""

    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list = field(default_factory=list)
    records_without_geometry: int = 0

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class NLRBPopulationService:
    """
    Populate NLRBRegion model instances from the built-in region registry.

    Since the NLRB does not publish GIS shapefiles, this service creates
    region records with state-level metadata.  When county boundaries are
    available in the database, it can optionally dissolve them into region
    geometries.

    Example:
        >>> service = NLRBPopulationService()
        >>> result = service.populate(vintage_year=2024)
        >>> print(f"Created {result.records_created} regions")
    """

    def populate(
        self,
        vintage_year: int = 2024,
        update_existing: bool = False,
        dissolve_counties: bool = False,
    ) -> NLRBPopulationResult:
        """
        Populate NLRBRegion records from the built-in registry.

        Registry-only rows have NULL geometry. Optional dissolves are a
        state-level approximation: whole states shared by multiple regions
        produce overlapping polygons, not precise county/sub-county
        jurisdictions. Authoritative mapping is deferred to #1713.

        Args:
            vintage_year: Vintage year for both region records and counties.
            update_existing: If True, update existing records instead of skipping.
            dissolve_counties: If True, attempt to build region geometry by
                dissolving county boundaries (requires populated County model).

        Returns:
            NLRBPopulationResult with counts, including records_without_geometry
            for all registry rows visited (created, updated, or skipped).
        """
        from ..models.federal import NLRBRegion

        result = NLRBPopulationResult()

        with transaction.atomic():
            for region_num, info in NLRB_REGIONS.items():
                feature_id = f"NLRB-{region_num:02d}"

                existing = NLRBRegion.objects.filter(
                    feature_id=feature_id,
                    vintage_year=vintage_year,
                ).first()

                if existing and not update_existing:
                    result.records_skipped += 1
                    if existing.geometry is None:
                        result.records_without_geometry += 1
                    continue

                geometry = None
                if dissolve_counties:
                    geometry = self._dissolve_county_geometry(
                        info["states"], vintage_year=vintage_year,
                    )

                if existing:
                    existing.region_office = info["office"]
                    existing.states_covered = info["states"]
                    if dissolve_counties:
                        existing.geometry = geometry
                    existing.save()
                    result.records_updated += 1
                    if existing.geometry is None:
                        result.records_without_geometry += 1
                else:
                    kwargs = {
                        "feature_id": feature_id,
                        "boundary_id": feature_id,
                        "region_number": region_num,
                        "region_office": info["office"],
                        "states_covered": info["states"],
                        "vintage_year": vintage_year,
                        "source": "NLRB",
                        "name": f"NLRB Region {region_num}",
                        "geometry": geometry,
                    }
                    NLRBRegion.objects.create(**kwargs)
                    result.records_created += 1
                    if geometry is None:
                        result.records_without_geometry += 1

        if result.records_without_geometry:
            log.warning(
                "NLRB populate: %s regions have no geometry (vintage_year=%s)",
                result.records_without_geometry, vintage_year,
            )
        log.info(
            f"NLRB populate: created={result.records_created}, "
            f"updated={result.records_updated}, skipped={result.records_skipped}"
        )
        return result

    def _dissolve_county_geometry(
        self, state_abbreviations: List[str], vintage_year: int
    ):
        """
        Union one vintage's counties in the database.

        This is a state-level approximation: states shared by regions produce
        overlapping polygons. It does not resolve true sub-state jurisdictions
        (follow-up #1713). Returns MultiPolygon only if every requested state
        has counties with geometry at this vintage; otherwise returns None.
        This checks state presence, not whether every county has been loaded.
        """
        try:
            from django.contrib.gis.db.models import Union
            from django.contrib.gis.geos import MultiPolygon
            from django.db.models import Count
            from django.db.models.functions import Substr

            from ..models.boundaries import County
            from siege_utilities.config.census_constants import STATE_FIPS_CODES

            fips_codes = set()
            for abbr in state_abbreviations:
                fips = STATE_FIPS_CODES.get(abbr.upper())
                if not fips:
                    return None
                fips_codes.add(fips)

            if not fips_codes:
                return None

            counties = County.objects.filter(
                geoid__regex=r"^(" + "|".join(sorted(fips_codes)) + r")",
                vintage_year=vintage_year,
            ).exclude(geometry__isnull=True)

            # Check state presence in the same query and vintage as the union.
            coverage = counties.aggregate(
                geometry=Union("geometry"),
                state_count=Count(Substr("geoid", 1, 2), distinct=True),
            )
            if coverage["state_count"] != len(fips_codes):
                return None
            dissolved = coverage["geometry"]
            if dissolved is None or dissolved.empty:
                return None

            if not isinstance(dissolved, MultiPolygon):
                dissolved = MultiPolygon(dissolved, srid=dissolved.srid)

            return dissolved
        except (ValueError, TypeError, AttributeError) as e:
            log.debug(f"County dissolve unavailable: {e}")
            return None
