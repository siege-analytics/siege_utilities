"""
Service for populating demographic data from Census API.

Uses the existing siege_utilities.geo.census_api_client module to fetch
demographic data, then loads it into Django models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DemographicPopulationResult:
    """Result of a demographic population operation."""

    geography_type: str
    year: int
    dataset: str
    state_fips: Optional[str]
    variable_group: str
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


class DemographicPopulationService:
    """
    Service for populating demographic data from Census API.

    This service integrates with the existing siege_utilities.geo.census_api_client
    to fetch demographic data and store it in DemographicSnapshot models.

    Example:
        >>> service = DemographicPopulationService(api_key='your-key')
        >>> result = service.populate(
        ...     geography_type='tract',
        ...     year=2022,
        ...     state_fips='06',
        ...     variable_group='income'
        ... )
        >>> print(f"Created {result.records_created} demographic snapshots")
    """

    # Mapping from geography type to Census API geography string
    CENSUS_GEOGRAPHIES = {
        "state": "state:*",
        "county": "county:*",
        "tract": "tract:*",
        "blockgroup": "block group:*",
        "place": "place:*",
    }

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize the service.

        Args:
            api_key: Census API key (or use CENSUS_API_KEY env var)
            cache_dir: Directory for caching API responses
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        self._client = None

    @property
    def client(self):
        """Lazy-load the Census API client."""
        if self._client is None:
            from siege_utilities.geo import CensusAPIClient

            self._client = CensusAPIClient(
                api_key=self.api_key, cache_dir=self.cache_dir
            )
        return self._client

    def _get_model(self, geography_type: str):
        """Get the Django model class for a geography type."""
        from ..models import (
            State,
            County,
            Tract,
            BlockGroup,
            Place,
        )

        models = {
            "state": State,
            "county": County,
            "tract": Tract,
            "blockgroup": BlockGroup,
            "place": Place,
        }
        return models.get(geography_type.lower())

    def _get_content_type(self, geography_type: str) -> ContentType:
        """Get ContentType for a geography model."""
        model = self._get_model(geography_type)
        if not model:
            raise ValueError(f"Unknown geography type: {geography_type}")
        return ContentType.objects.get_for_model(model)

    @transaction.atomic
    def populate(
        self,
        geography_type: str,
        year: int,
        state_fips: str,
        variable_group: str = "demographics_basic",
        dataset: str = "acs5",
        update_existing: bool = False,
        batch_size: int = 500,
    ) -> DemographicPopulationResult:
        """
        Populate demographic data for boundaries.

        Args:
            geography_type: Type of geography (state, county, tract, etc.)
            year: ACS/Census year
            state_fips: State FIPS code
            variable_group: Variable group name (income, education, housing, etc.)
            dataset: Census dataset (acs5, acs1, dec)
            update_existing: If True, update existing records; otherwise skip
            batch_size: Number of records per database batch

        Returns:
            DemographicPopulationResult with statistics
        """
        from ..models import DemographicSnapshot

        model = self._get_model(geography_type)
        if not model:
            return DemographicPopulationResult(
                geography_type=geography_type,
                year=year,
                dataset=dataset,
                state_fips=state_fips,
                variable_group=variable_group,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=[f"Unknown geography type: {geography_type}"],
            )

        # Fetch data from Census API
        try:
            logger.info(
                f"Fetching {variable_group} data for {geography_type} in state {state_fips}"
            )
            df = self.client.fetch_data(
                variables=variable_group,
                year=year,
                dataset=dataset,
                geography=geography_type,
                state_fips=state_fips,
            )
        except Exception as e:
            logger.error(f"Error fetching demographics: {e}")
            return DemographicPopulationResult(
                geography_type=geography_type,
                year=year,
                dataset=dataset,
                state_fips=state_fips,
                variable_group=variable_group,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=[str(e)],
            )

        if df is None or df.empty:
            return DemographicPopulationResult(
                geography_type=geography_type,
                year=year,
                dataset=dataset,
                state_fips=state_fips,
                variable_group=variable_group,
                records_created=0,
                records_updated=0,
                records_skipped=0,
                errors=["No data returned from Census API"],
            )

        content_type = self._get_content_type(geography_type)
        created = 0
        updated = 0
        skipped = 0
        errors = []

        objects_to_create = []

        # Identify variable columns (exclude GEOID and geography columns)
        geo_cols = {"GEOID", "geoid", "state", "county", "tract", "block group", "place"}
        variable_cols = [c for c in df.columns if c not in geo_cols and not c.startswith("_")]

        # Split into estimates and MOEs
        estimate_cols = [c for c in variable_cols if c.endswith("E")]
        moe_cols = [c for c in variable_cols if c.endswith("M")]

        for _, row in df.iterrows():
            try:
                geoid = str(row.get("GEOID", row.get("geoid", "")))
                if not geoid:
                    skipped += 1
                    continue

                # Check if exists
                existing = DemographicSnapshot.objects.filter(
                    content_type=content_type,
                    object_id=geoid,
                    year=year,
                    dataset=dataset,
                ).first()

                if existing and not update_existing:
                    skipped += 1
                    continue

                # Build values dict
                values = {}
                for col in estimate_cols:
                    val = row.get(col)
                    if val is not None and val != "" and str(val) != "nan":
                        try:
                            values[col] = float(val) if "." in str(val) else int(val)
                        except (ValueError, TypeError):
                            values[col] = val

                moe_values = {}
                for col in moe_cols:
                    val = row.get(col)
                    if val is not None and val != "" and str(val) != "nan":
                        try:
                            moe_values[col] = float(val) if "." in str(val) else int(val)
                        except (ValueError, TypeError):
                            moe_values[col] = val

                if existing:
                    # Update - merge values
                    existing.values.update(values)
                    existing.moe_values.update(moe_values)
                    existing.save()
                    updated += 1
                else:
                    # Create
                    snapshot = DemographicSnapshot(
                        content_type=content_type,
                        object_id=geoid,
                        year=year,
                        dataset=dataset,
                        values=values,
                        moe_values=moe_values,
                    )
                    objects_to_create.append(snapshot)

                    if len(objects_to_create) >= batch_size:
                        DemographicSnapshot.objects.bulk_create(
                            objects_to_create, ignore_conflicts=True
                        )
                        created += len(objects_to_create)
                        objects_to_create = []

            except Exception as e:
                logger.error(f"Error processing GEOID {row.get('GEOID', 'unknown')}: {e}")
                errors.append(f"GEOID {row.get('GEOID', 'unknown')}: {e}")

        # Create remaining
        if objects_to_create:
            DemographicSnapshot.objects.bulk_create(
                objects_to_create, ignore_conflicts=True
            )
            created += len(objects_to_create)

        logger.info(
            f"Populated demographics: {created} created, {updated} updated, {skipped} skipped"
        )

        return DemographicPopulationResult(
            geography_type=geography_type,
            year=year,
            dataset=dataset,
            state_fips=state_fips,
            variable_group=variable_group,
            records_created=created,
            records_updated=updated,
            records_skipped=skipped,
            errors=errors,
        )

    def populate_income(
        self, geography_type: str, year: int, state_fips: str, **kwargs
    ) -> DemographicPopulationResult:
        """Populate income demographic data."""
        return self.populate(
            geography_type, year, state_fips, variable_group="income", **kwargs
        )

    def populate_education(
        self, geography_type: str, year: int, state_fips: str, **kwargs
    ) -> DemographicPopulationResult:
        """Populate education demographic data."""
        return self.populate(
            geography_type, year, state_fips, variable_group="education", **kwargs
        )

    def populate_housing(
        self, geography_type: str, year: int, state_fips: str, **kwargs
    ) -> DemographicPopulationResult:
        """Populate housing demographic data."""
        return self.populate(
            geography_type, year, state_fips, variable_group="housing", **kwargs
        )

    def populate_race_ethnicity(
        self, geography_type: str, year: int, state_fips: str, **kwargs
    ) -> DemographicPopulationResult:
        """Populate race/ethnicity demographic data."""
        return self.populate(
            geography_type, year, state_fips, variable_group="race_ethnicity", **kwargs
        )

    def populate_all_groups(
        self,
        geography_type: str,
        year: int,
        state_fips: str,
        groups: Optional[list[str]] = None,
        **kwargs,
    ) -> list[DemographicPopulationResult]:
        """
        Populate multiple demographic variable groups.

        Args:
            geography_type: Type of geography
            year: ACS year
            state_fips: State FIPS code
            groups: List of variable groups (defaults to all standard groups)
            **kwargs: Additional arguments passed to populate()

        Returns:
            List of results for each group
        """
        if groups is None:
            groups = [
                "total_population",
                "demographics_basic",
                "race_ethnicity",
                "income",
                "education",
                "housing",
            ]

        results = []
        for group in groups:
            result = self.populate(
                geography_type, year, state_fips, variable_group=group, **kwargs
            )
            results.append(result)

        return results
