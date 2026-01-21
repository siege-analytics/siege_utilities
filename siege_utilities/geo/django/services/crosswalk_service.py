"""
Service for populating boundary crosswalk data.

Uses the existing siege_utilities.geo.crosswalk module to load
crosswalk relationships into Django models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from django.db import transaction

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CrosswalkPopulationResult:
    """Result of a crosswalk population operation."""

    geography_type: str
    source_year: int
    target_year: int
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


class CrosswalkPopulationService:
    """
    Service for populating boundary crosswalk data.

    This service integrates with the existing siege_utilities.geo.crosswalk
    module to load crosswalk relationships into BoundaryCrosswalk models.

    Example:
        >>> service = CrosswalkPopulationService()
        >>> result = service.populate(
        ...     geography_type='tract',
        ...     source_year=2010,
        ...     target_year=2020,
        ...     state_fips='06'
        ... )
        >>> print(f"Created {result.records_created} crosswalk records")
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the service.

        Args:
            cache_dir: Directory for caching downloaded crosswalk files
        """
        self.cache_dir = cache_dir

    def _load_crosswalk_data(
        self,
        geography_type: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> "pd.DataFrame":
        """
        Load crosswalk data using siege_utilities.geo.crosswalk.

        Args:
            geography_type: Type of geography
            source_year: Source Census year
            target_year: Target Census year
            state_fips: Optional state filter

        Returns:
            DataFrame with crosswalk data
        """
        from siege_utilities.geo.crosswalk import get_crosswalk

        logger.info(
            f"Loading {geography_type} crosswalk from {source_year} to {target_year}"
        )

        df = get_crosswalk(
            geography_type=geography_type,
            source_year=source_year,
            target_year=target_year,
            state_fips=state_fips,
        )

        return df

    def _determine_relationship(
        self, row: dict, all_rows_for_source: list
    ) -> str:
        """
        Determine the relationship type based on weight and other records.

        Args:
            row: Current crosswalk row
            all_rows_for_source: All rows with the same source GEOID

        Returns:
            Relationship type string
        """
        weight = float(row.get("weight", row.get("WEIGHT", 1.0)))

        if weight >= 0.9999:
            # Check if target GEOID equals source GEOID
            source = str(row.get("source_geoid", row.get("GEOID_SOURCE", "")))
            target = str(row.get("target_geoid", row.get("GEOID_TARGET", "")))
            if source == target:
                return "IDENTICAL"
            else:
                return "RENAMED"

        if len(all_rows_for_source) > 1:
            return "SPLIT"

        return "PARTIAL"

    @transaction.atomic
    def populate(
        self,
        geography_type: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
        weight_type: str = "population",
        update_existing: bool = False,
        batch_size: int = 1000,
    ) -> CrosswalkPopulationResult:
        """
        Populate crosswalk data for a geography type.

        Args:
            geography_type: Type of geography (tract, blockgroup, etc.)
            source_year: Source Census year (earlier)
            target_year: Target Census year (later)
            state_fips: Optional state filter
            weight_type: Type of weight (population, housing, area)
            update_existing: If True, update existing records; otherwise skip
            batch_size: Number of records per database batch

        Returns:
            CrosswalkPopulationResult with statistics
        """
        from ..models import BoundaryCrosswalk, CrosswalkDataset

        # Load crosswalk data
        try:
            df = self._load_crosswalk_data(
                geography_type, source_year, target_year, state_fips
            )
        except Exception as e:
            logger.error(f"Error loading crosswalk data: {e}")
            return CrosswalkPopulationResult(
                geography_type=geography_type,
                source_year=source_year,
                target_year=target_year,
                state_fips=state_fips,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=[str(e)],
            )

        if df is None or df.empty:
            return CrosswalkPopulationResult(
                geography_type=geography_type,
                source_year=source_year,
                target_year=target_year,
                state_fips=state_fips,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=["No crosswalk data available"],
            )

        created = 0
        updated = 0
        skipped = 0
        errors = []

        objects_to_create = []

        # Normalize column names
        col_map = {
            "GEOID_SOURCE": "source_geoid",
            "GEOID_TARGET": "target_geoid",
            "WEIGHT": "weight",
            "POP_SOURCE": "source_population",
            "POP_TARGET": "target_population",
            "POP_ALLOCATED": "allocated_population",
            "AREALAND_INT": "area_sq_meters",
        }
        df = df.rename(columns=col_map)

        # Group by source GEOID to determine relationships
        source_groups = df.groupby("source_geoid").apply(
            lambda x: x.to_dict("records")
        ).to_dict()

        for _, row in df.iterrows():
            try:
                source_geoid = str(row.get("source_geoid", ""))
                target_geoid = str(row.get("target_geoid", ""))

                if not source_geoid or not target_geoid:
                    skipped += 1
                    continue

                # Extract state FIPS from GEOID
                row_state_fips = source_geoid[:2] if len(source_geoid) >= 2 else ""

                # Check if exists
                existing = BoundaryCrosswalk.objects.filter(
                    source_geoid=source_geoid,
                    target_geoid=target_geoid,
                    source_year=source_year,
                    target_year=target_year,
                    weight_type=weight_type,
                ).first()

                if existing and not update_existing:
                    skipped += 1
                    continue

                # Determine relationship
                all_rows_for_source = source_groups.get(source_geoid, [])
                relationship = self._determine_relationship(row, all_rows_for_source)

                # Get weight
                weight = float(row.get("weight", 1.0))
                if weight > 1.0:
                    weight = 1.0
                if weight < 0.0:
                    weight = 0.0

                kwargs = {
                    "source_geoid": source_geoid,
                    "target_geoid": target_geoid,
                    "source_year": source_year,
                    "target_year": target_year,
                    "geography_type": geography_type,
                    "relationship": relationship,
                    "weight": weight,
                    "weight_type": weight_type,
                    "state_fips": row_state_fips,
                    "source_population": row.get("source_population"),
                    "target_population": row.get("target_population"),
                    "allocated_population": row.get("allocated_population"),
                    "area_sq_meters": row.get("area_sq_meters"),
                }

                if existing:
                    for key, value in kwargs.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                else:
                    objects_to_create.append(BoundaryCrosswalk(**kwargs))

                    if len(objects_to_create) >= batch_size:
                        BoundaryCrosswalk.objects.bulk_create(
                            objects_to_create, ignore_conflicts=True
                        )
                        created += len(objects_to_create)
                        objects_to_create = []

            except Exception as e:
                source = row.get("source_geoid", "unknown")
                target = row.get("target_geoid", "unknown")
                logger.error(f"Error processing {source} -> {target}: {e}")
                errors.append(f"{source} -> {target}: {e}")

        # Create remaining
        if objects_to_create:
            BoundaryCrosswalk.objects.bulk_create(
                objects_to_create, ignore_conflicts=True
            )
            created += len(objects_to_create)

        # Record the dataset
        dataset_name = f"{source_year}-{target_year} {geography_type.title()} Crosswalk"
        if state_fips:
            dataset_name += f" (State {state_fips})"

        CrosswalkDataset.objects.update_or_create(
            name=dataset_name,
            defaults={
                "source_year": source_year,
                "target_year": target_year,
                "geography_type": geography_type,
                "record_count": created + updated,
                "states_covered": [state_fips] if state_fips else [],
            },
        )

        logger.info(
            f"Populated crosswalk: {created} created, {updated} updated, {skipped} skipped"
        )

        return CrosswalkPopulationResult(
            geography_type=geography_type,
            source_year=source_year,
            target_year=target_year,
            state_fips=state_fips,
            records_created=created,
            records_updated=updated,
            records_skipped=skipped,
            errors=errors,
        )

    def populate_tract_crosswalk(
        self,
        source_year: int = 2010,
        target_year: int = 2020,
        state_fips: Optional[str] = None,
        **kwargs,
    ) -> CrosswalkPopulationResult:
        """Populate tract crosswalk data."""
        return self.populate(
            "tract", source_year, target_year, state_fips, **kwargs
        )

    def populate_block_group_crosswalk(
        self,
        source_year: int = 2010,
        target_year: int = 2020,
        state_fips: Optional[str] = None,
        **kwargs,
    ) -> CrosswalkPopulationResult:
        """Populate block group crosswalk data."""
        return self.populate(
            "blockgroup", source_year, target_year, state_fips, **kwargs
        )

    def populate_county_crosswalk(
        self,
        source_year: int = 2010,
        target_year: int = 2020,
        state_fips: Optional[str] = None,
        **kwargs,
    ) -> CrosswalkPopulationResult:
        """Populate county crosswalk data."""
        return self.populate(
            "county", source_year, target_year, state_fips, **kwargs
        )
