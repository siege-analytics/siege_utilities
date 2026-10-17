"""
Service for populating NLRB (National Labor Relations Board) region data.

This service creates registry rows with optional geometry. Dissolving counties
in the registry's primary states produces a state-level approximation, with
overlaps between regions, rather than authoritative NLRB jurisdictions.

Data source: manually maintained regional-office registry.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List

from django.db import transaction

log = logging.getLogger(__name__)

__all__ = [
    'NLRB_REGIONS',
    'NLRBPopulationResult',
    'NLRBPopulationService',
]

# NLRB Region definitions: region_number → {office, states}
# States listed approximate primary coverage; precise sub-state jurisdictions
# are deferred to https://github.com/siege-analytics/siege_utilities/issues/1713.
NLRB_REGIONS: Dict[int, dict] = {
    1: {"office": "Boston", "states": ["CT", "MA", "ME", "NH", "RI", "VT"]},
    2: {"office": "New York", "states": ["NY"]},
    3: {"office": "Buffalo", "states": ["NY"]},
    4: {"office": "Philadelphia", "states": ["DE", "PA"]},
    5: {"office": "Baltimore", "states": ["DC", "MD", "VA", "WV"]},
    6: {"office": "Pittsburgh", "states": ["PA", "WV"]},
    7: {"office": "Detroit", "states": ["MI"]},
    8: {"office": "Cleveland", "states": ["OH"]},
    9: {"office": "Cincinnati", "states": ["IN", "KY", "OH"]},
    10: {"office": "Atlanta", "states": ["AL", "GA", "NC", "SC", "TN"]},
    11: {"office": "Winston-Salem", "states": ["NC", "SC", "TN", "VA"]},
    12: {"office": "Tampa", "states": ["FL", "PR", "VI"]},
    13: {"office": "Chicago", "states": ["IL", "IN"]},
    14: {"office": "St. Louis", "states": ["IL", "MO"]},
    15: {"office": "New Orleans", "states": ["AL", "LA", "MS"]},
    16: {"office": "Fort Worth", "states": ["TX"]},
    17: {"office": "Kansas City", "states": ["IA", "KS", "MO", "NE"]},
    18: {"office": "Minneapolis", "states": ["MN", "ND", "SD", "WI"]},
    19: {"office": "Seattle", "states": ["AK", "ID", "MT", "OR", "WA", "WY"]},
    20: {"office": "San Francisco", "states": ["CA", "HI", "NV"]},
    21: {"office": "Los Angeles", "states": ["AZ", "CA", "HI", "NV"]},
    22: {"office": "Newark", "states": ["NJ"]},
    24: {"office": "Hato Rey", "states": ["PR", "VI"]},
    25: {"office": "Indianapolis", "states": ["IN"]},
    26: {"office": "Memphis", "states": ["AR", "MS", "TN"]},
    27: {"office": "Denver", "states": ["CO", "NM", "UT", "WY"]},
    # Phoenix also serves parts of TX/NV; retain primary-state approximation.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-28-phoenix
    28: {"office": "Phoenix", "states": ["AZ", "NM"]},
    29: {"office": "Brooklyn", "states": ["NY"]},
    31: {"office": "Los Angeles", "states": ["CA"]},
    # Oakland serves parts of CA/NV; precise assignments await #1713.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-32-oakland
    32: {"office": "Oakland", "states": ["CA"]},
}


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
                    if geometry is not None:
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
        (follow-up #1713). Returns MultiPolygon or None if no counties match.
        """
        try:
            from django.contrib.gis.db.models import Union
            from django.contrib.gis.geos import MultiPolygon

            from ..models.boundaries import County
            from siege_utilities.config.census_constants import STATE_FIPS_CODES

            fips_codes = []
            for abbr in state_abbreviations:
                fips = STATE_FIPS_CODES.get(abbr.upper())
                if fips:
                    fips_codes.append(fips)

            if not fips_codes:
                return None

            counties = County.objects.filter(
                geoid__regex=r"^(" + "|".join(fips_codes) + r")",
                vintage_year=vintage_year,
            ).exclude(geometry__isnull=True)

            dissolved = counties.aggregate(geometry=Union("geometry"))["geometry"]
            if dissolved is None:
                return None

            if not isinstance(dissolved, MultiPolygon):
                dissolved = MultiPolygon(dissolved, srid=dissolved.srid)

            return dissolved
        except (ValueError, TypeError, AttributeError) as e:
            log.debug(f"County dissolve unavailable: {e}")
            return None
