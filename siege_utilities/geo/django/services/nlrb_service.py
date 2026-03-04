"""
Service for populating NLRB (National Labor Relations Board) region data.

NLRB divides the US into 26 active regions (numbered 1-31 with gaps).
Boundaries are county-based and change infrequently.  Since the NLRB does
not publish shapefiles, this service builds region geometries by dissolving
county boundaries for the counties assigned to each region.

Data source: NLRB region-to-county mapping (manual maintenance).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from django.db import transaction

log = logging.getLogger(__name__)

# NLRB Region definitions: region_number → {office, states, counties}
# States listed are the primary states covered; county-level precision
# would require a full FIPS mapping that the NLRB doesn't publish openly.
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
    28: {"office": "Memphis", "states": ["AL", "AR", "MS"]},
    29: {"office": "Brooklyn", "states": ["NY"]},
    31: {"office": "Los Angeles", "states": ["CA"]},
}


@dataclass
class NLRBPopulationResult:
    """Result of an NLRB region population run."""

    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list = field(default_factory=list)

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

        Args:
            vintage_year: Vintage year for the records.
            update_existing: If True, update existing records instead of skipping.
            dissolve_counties: If True, attempt to build region geometry by
                dissolving county boundaries (requires populated County model).

        Returns:
            NLRBPopulationResult with counts.
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
                    continue

                geometry = None
                if dissolve_counties:
                    geometry = self._dissolve_county_geometry(info["states"])

                if existing:
                    existing.region_office = info["office"]
                    existing.states_covered = info["states"]
                    if geometry is not None:
                        existing.geometry = geometry
                    existing.save()
                    result.records_updated += 1
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
                    }
                    if geometry is not None:
                        kwargs["geometry"] = geometry
                    NLRBRegion.objects.create(**kwargs)
                    result.records_created += 1

        log.info(
            f"NLRB populate: created={result.records_created}, "
            f"updated={result.records_updated}, skipped={result.records_skipped}"
        )
        return result

    def _dissolve_county_geometry(
        self, state_abbreviations: List[str]
    ):
        """
        Attempt to build a dissolved geometry from county boundaries.

        Returns MultiPolygon or None if counties not available.
        """
        try:
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
            ).exclude(geometry__isnull=True)

            if not counties.exists():
                return None

            dissolved = counties.first().geometry
            for county in counties[1:]:
                if county.geometry:
                    dissolved = dissolved.union(county.geometry)

            if not isinstance(dissolved, MultiPolygon):
                dissolved = MultiPolygon(dissolved)

            return dissolved
        except Exception as e:
            log.debug(f"County dissolve unavailable: {e}")
            return None
