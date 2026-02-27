"""
Service for demographic roll-up aggregation across geography levels.

Aggregates demographic data from a finer geography (e.g., tracts) to a
coarser geography (e.g., counties) using GEOID prefix hierarchy.
Supports sum, avg, and weighted_avg (population-weighted) operations.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class RollupResult:
    """Result of a rollup aggregation run."""

    source_level: str
    target_level: str
    variable_code: str
    records_created: int = 0
    records_skipped: int = 0
    errors: list = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class DemographicRollupService:
    """
    Aggregate demographic values from child geographies to parent geographies.

    Uses GEOID prefix hierarchy for parent resolution:
    - Block (15) → Tract (11) → County (5) → State (2)
    - BlockGroup (12) → Tract (11) → County (5) → State (2)

    Supports operations:
    - sum: Sum of child values (e.g., population)
    - avg: Simple average of child values
    - weighted_avg: Population-weighted average (e.g., median income)

    Example:
        service = DemographicRollupService()
        result = service.rollup(
            source_level='tract',
            target_level='county',
            year=2022,
            variables=['B01001_001E'],
            operation='sum',
        )
    """

    def __init__(self, dataset: str = 'acs5'):
        self.dataset = dataset

    # GEOID prefix lengths for parent resolution
    GEOID_PREFIX_LENGTHS = {
        'state': 2,
        'county': 5,
        'tract': 11,
        'block_group': 12,
        'block': 15,
    }

    def rollup(
        self,
        source_level: str,
        target_level: str,
        year: int,
        variables: List[str],
        operation: str = 'sum',
        state_fips: Optional[str] = None,
        batch_size: int = 500,
    ) -> List[RollupResult]:
        """
        Aggregate demographic data from source to target geography level.

        Args:
            source_level: Source (finer) geography ('tract', 'block_group', etc.)
            target_level: Target (coarser) geography ('county', 'state', etc.)
            year: Census year for the demographic data
            variables: List of variable codes to aggregate
            operation: Aggregation operation ('sum', 'avg', 'weighted_avg')
            state_fips: Optional state filter
            batch_size: Bulk create batch size

        Returns:
            List of RollupResult (one per variable)
        """
        from django.contrib.contenttypes.models import ContentType

        from ..models.demographics import DemographicSnapshot

        source_prefix_len = self.GEOID_PREFIX_LENGTHS.get(source_level)
        target_prefix_len = self.GEOID_PREFIX_LENGTHS.get(target_level)

        if source_prefix_len is None or target_prefix_len is None:
            return [
                RollupResult(
                    source_level=source_level,
                    target_level=target_level,
                    variable_code=v,
                    errors=[f"Unsupported level: {source_level} or {target_level}"],
                )
                for v in variables
            ]

        if target_prefix_len >= source_prefix_len:
            return [
                RollupResult(
                    source_level=source_level,
                    target_level=target_level,
                    variable_code=v,
                    errors=[
                        f"Target level ({target_level}) must be coarser than "
                        f"source level ({source_level})"
                    ],
                )
                for v in variables
            ]

        # Resolve target model for content type
        target_model = self._resolve_model(target_level)
        if target_model is None:
            return [
                RollupResult(
                    source_level=source_level,
                    target_level=target_level,
                    variable_code=v,
                    errors=[f"Cannot resolve model for {target_level}"],
                )
                for v in variables
            ]

        # Resolve source model content type
        source_model = self._resolve_model(source_level)
        if source_model is None:
            return [
                RollupResult(
                    source_level=source_level,
                    target_level=target_level,
                    variable_code=v,
                    errors=[f"Cannot resolve model for {source_level}"],
                )
                for v in variables
            ]

        source_ct = ContentType.objects.get_for_model(source_model)
        target_ct = ContentType.objects.get_for_model(target_model)

        # Get source snapshots
        snap_qs = DemographicSnapshot.objects.filter(
            content_type=source_ct,
            dataset=self.dataset,
            year=year,
        )
        if state_fips:
            snap_qs = snap_qs.filter(object_id__startswith=state_fips)

        results = []

        for variable in variables:
            result = RollupResult(
                source_level=source_level,
                target_level=target_level,
                variable_code=variable,
            )

            # Group source values by target GEOID prefix
            target_groups = {}  # target_geoid → [values]
            pop_groups = {}  # target_geoid → [populations] (for weighted_avg)

            for snap in snap_qs.iterator():
                val = snap.values.get(variable)
                if val is None:
                    continue

                target_geoid = snap.object_id[:target_prefix_len]
                target_groups.setdefault(target_geoid, []).append(val)

                if operation == 'weighted_avg' and snap.total_population:
                    pop_groups.setdefault(target_geoid, []).append(
                        snap.total_population
                    )

            # Create aggregated snapshots for target
            to_create = []
            for target_geoid, values in target_groups.items():
                if operation == 'sum':
                    agg_value = sum(values)
                elif operation == 'avg':
                    agg_value = sum(values) / len(values) if values else 0
                elif operation == 'weighted_avg':
                    pops = pop_groups.get(target_geoid, [])
                    if pops and len(pops) == len(values):
                        total_pop = sum(pops)
                        if total_pop > 0:
                            agg_value = sum(
                                v * p for v, p in zip(values, pops)
                            ) / total_pop
                        else:
                            agg_value = sum(values) / len(values)
                    else:
                        agg_value = sum(values) / len(values)
                else:
                    result.errors.append(f"Unknown operation: {operation}")
                    break

                # Check if target snapshot already exists
                existing = DemographicSnapshot.objects.filter(
                    content_type=target_ct,
                    object_id=target_geoid,
                    dataset=self.dataset,
                    year=year,
                ).first()

                if existing:
                    existing.values[variable] = agg_value
                    existing.save()
                    result.records_skipped += 1
                else:
                    to_create.append(
                        DemographicSnapshot(
                            content_type=target_ct,
                            object_id=target_geoid,
                            dataset=self.dataset,
                            year=year,
                            values={variable: agg_value},
                        )
                    )

            if to_create:
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i: i + batch_size]
                    DemographicSnapshot.objects.bulk_create(
                        batch, ignore_conflicts=True
                    )
                result.records_created = len(to_create)

            results.append(result)
            log.info(
                f"Rollup {variable} ({source_level}→{target_level}): "
                f"created={result.records_created}, skipped={result.records_skipped}"
            )

        return results

    def _resolve_model(self, geography_level: str):
        """Resolve a geography level string to a Django model class."""
        from django.apps import apps

        LEVEL_TO_MODEL = {
            "state": "State",
            "county": "County",
            "tract": "Tract",
            "block_group": "BlockGroup",
            "block": "Block",
            "place": "Place",
            "zcta": "ZCTA",
            "cd": "CongressionalDistrict",
            "sldu": "StateLegislativeUpper",
            "sldl": "StateLegislativeLower",
            "vtd": "VTD",
        }
        model_name = LEVEL_TO_MODEL.get(geography_level)
        if model_name is None:
            return None
        try:
            return apps.get_model("siege_geo", model_name)
        except LookupError:
            return None
