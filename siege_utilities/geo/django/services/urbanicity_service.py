"""
Urbanicity classification service for Census tracts.

Computes NCES-style locale codes (11-43) for tracts in years where official
NCES locale data is not available.  Uses tract population (from
DemographicSnapshot) and distance to the nearest Census Urban Area boundary
to apply the NCES classification thresholds.

Usage::

    from siege_utilities.geo.django.services import UrbanicityClassificationService

    service = UrbanicityClassificationService()
    result = service.classify(year=2020, state_fips="06")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

from siege_utilities.config.nces_constants import (
    LOCALE_CODE_TO_NUMERIC,
    classify_urbanicity,
)

log = logging.getLogger(__name__)


# Meters per mile — used to convert GeoDjango distance (meters) to miles
# for the NCES threshold comparisons.
_METERS_PER_MILE = 1_609.344


@dataclass
class ClassificationResult:
    """Result of an urbanicity classification run."""

    classified: int = 0
    skipped_no_population: int = 0
    skipped_no_urban_area: int = 0
    skipped_no_point: int = 0
    errors: list = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return (
            self.classified
            + self.skipped_no_population
            + self.skipped_no_urban_area
            + self.skipped_no_point
        )


class UrbanicityClassificationService:
    """
    Classify Census tracts into NCES locale codes using population and
    distance-to-urban-area.

    Algorithm:
        1. For each tract, look up total population from DemographicSnapshot.
        2. Compute geodesic distance from the tract's internal_point to the
           nearest UrbanArea boundary.
        3. Pass (population, distance_miles) to ``classify_urbanicity()`` to
           get the subcategory string (e.g. ``"city_large"``).
        4. Convert subcategory to the numeric NCES code (e.g. 11).
        5. Bulk-update ``Tract.urbanicity_code``.
    """

    def classify(
        self,
        year: int,
        state_fips: Optional[str] = None,
        urban_area_year: Optional[int] = None,
        dataset: str = "acs5",
        batch_size: int = 500,
        overwrite: bool = False,
        srid: int = 4326,
    ) -> ClassificationResult:
        """
        Classify tracts for the given vintage year.

        Args:
            year: Census vintage year for tracts and demographics.
            state_fips: Limit to a single state (2-digit FIPS).  If None,
                classifies all states.
            urban_area_year: Vintage year for UrbanArea boundaries.
                Defaults to *year*.
            dataset: Census dataset used for the DemographicSnapshot
                (default ``"acs5"``).
            batch_size: Number of tracts to update per bulk_update call.
            overwrite: If False (default), skip tracts that already have a
                non-null urbanicity_code.
            srid: SRID for spatial operations (default 4326).

        Returns:
            ClassificationResult with counts.
        """
        from django.contrib.contenttypes.models import ContentType

        from siege_utilities.geo.django.models import Tract, UrbanArea
        from siege_utilities.geo.django.models.demographics import DemographicSnapshot

        urban_area_year = urban_area_year or year
        result = ClassificationResult()

        # Pre-fetch urban areas for the year
        urban_areas = UrbanArea.objects.filter(vintage_year=urban_area_year)
        if not urban_areas.exists():
            result.errors.append(
                f"No UrbanArea boundaries for vintage_year={urban_area_year}"
            )
            return result

        # Build tract queryset
        tracts_qs = Tract.objects.filter(vintage_year=year)
        if state_fips:
            tracts_qs = tracts_qs.filter(state_fips=state_fips)
        if not overwrite:
            tracts_qs = tracts_qs.filter(urbanicity_code__isnull=True)

        tract_ct = ContentType.objects.get_for_model(Tract)

        # Build a dict of geoid → population from DemographicSnapshot
        population_map = {}
        snapshots = DemographicSnapshot.objects.filter(
            content_type=tract_ct,
            dataset=dataset,
            year=year,
        ).values_list("object_id", "total_population")
        for geoid, pop in snapshots:
            if pop is not None:
                population_map[geoid] = pop

        log.info(
            "Classifying %d tracts (year=%d, state=%s, overwrite=%s). "
            "%d population records available.",
            tracts_qs.count(),
            year,
            state_fips or "ALL",
            overwrite,
            len(population_map),
        )

        to_update = []

        for tract in tracts_qs.iterator():
            # Need internal_point for distance computation
            point = tract.internal_point
            if point is None:
                result.skipped_no_point += 1
                continue

            # Look up population
            population = population_map.get(tract.geoid)
            if population is None:
                result.skipped_no_population += 1
                continue

            # Find nearest urban area and compute distance
            nearest_ua = (
                urban_areas.filter(geometry__isnull=False)
                .annotate(dist=Distance("geometry", point))
                .order_by("dist")
                .first()
            )

            if nearest_ua is None:
                result.skipped_no_urban_area += 1
                continue

            distance_meters = nearest_ua.dist.m
            distance_miles = distance_meters / _METERS_PER_MILE

            # Classify using NCES thresholds
            try:
                subcategory = classify_urbanicity(population, distance_miles)
                numeric_code = LOCALE_CODE_TO_NUMERIC.get(subcategory)
                if numeric_code is None:
                    result.errors.append(
                        f"Tract {tract.geoid}: unknown subcategory '{subcategory}'"
                    )
                    continue

                tract.urbanicity_code = numeric_code
                to_update.append(tract)
                result.classified += 1

            except Exception as exc:
                result.errors.append(f"Tract {tract.geoid}: {exc}")

            # Flush batch
            if len(to_update) >= batch_size:
                Tract.objects.bulk_update(to_update, ["urbanicity_code"])
                to_update = []

        # Final flush
        if to_update:
            Tract.objects.bulk_update(to_update, ["urbanicity_code"])

        log.info(
            "Classification complete: %d classified, %d skipped (no pop), "
            "%d skipped (no UA), %d skipped (no point), %d errors",
            result.classified,
            result.skipped_no_population,
            result.skipped_no_urban_area,
            result.skipped_no_point,
            len(result.errors),
        )

        return result
