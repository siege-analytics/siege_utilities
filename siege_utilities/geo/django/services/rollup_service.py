"""
Service for demographic roll-up aggregation across geography levels.

Aggregates demographic data from a finer geography (e.g., tracts) to a
coarser geography (e.g., counties) using GEOID prefix hierarchy or
temporal crosswalk mappings.  Supports sum, avg, and weighted_avg
(population-weighted) operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class RollupResult:
    """Result of a rollup aggregation run."""

    source_level: str
    target_level: str
    variable_code: str
    records_created: int = 0
    records_skipped: int = 0
    coverage_ratio: float = 1.0
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
        crosswalk_year: Optional[int] = None,
        min_coverage: float = 0.5,
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
            crosswalk_year: When set, use TemporalCrosswalk mappings from
                ``crosswalk_year`` → ``year`` instead of GEOID prefix truncation.
                Enables rollup across boundary changes.
            min_coverage: Minimum coverage ratio (0-1, default 0.5).  When a
                target geography has data for fewer than ``min_coverage`` of its
                expected children, a warning is logged.

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

        # Build crosswalk lookup if requested
        crosswalk_map: Optional[Dict[str, List[tuple]]] = None
        if crosswalk_year is not None:
            crosswalk_map = self._build_crosswalk_map(
                source_level, crosswalk_year, year, state_fips
            )

        # Get source snapshots
        snap_qs = DemographicSnapshot.objects.filter(
            content_type=source_ct,
            dataset=self.dataset,
            year=year,
        )
        if state_fips:
            snap_qs = snap_qs.filter(object_id__startswith=state_fips)

        # Count total children per target (for coverage calculation)
        total_children_per_target: Dict[str, int] = {}
        if crosswalk_map is None:
            for snap in snap_qs.iterator():
                tg = snap.object_id[:target_prefix_len]
                total_children_per_target[tg] = total_children_per_target.get(tg, 0) + 1
            # Reset iterator by re-evaluating
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

            # Group source values by target GEOID
            target_groups: Dict[str, list] = {}
            pop_groups: Dict[str, list] = {}
            children_with_data: Dict[str, int] = {}

            for snap in snap_qs.iterator():
                val = snap.values.get(variable)
                if val is None:
                    continue

                if crosswalk_map is not None:
                    # Use crosswalk: one source may map to multiple targets
                    mappings = crosswalk_map.get(snap.object_id, [])
                    for target_geoid, weight in mappings:
                        weighted_val = val * float(weight)
                        target_groups.setdefault(target_geoid, []).append(weighted_val)
                        children_with_data[target_geoid] = children_with_data.get(target_geoid, 0) + 1

                        if operation == 'weighted_avg' and snap.total_population:
                            pop_groups.setdefault(target_geoid, []).append(
                                snap.total_population * float(weight)
                            )
                else:
                    # Use GEOID prefix truncation
                    target_geoid = snap.object_id[:target_prefix_len]
                    target_groups.setdefault(target_geoid, []).append(val)
                    children_with_data[target_geoid] = children_with_data.get(target_geoid, 0) + 1

                    if operation == 'weighted_avg' and snap.total_population:
                        pop_groups.setdefault(target_geoid, []).append(
                            snap.total_population
                        )

            # Compute coverage ratio across all target geographies
            if total_children_per_target:
                total_expected = sum(total_children_per_target.values())
                total_with_data = sum(children_with_data.values())
                result.coverage_ratio = (
                    total_with_data / total_expected if total_expected > 0 else 0.0
                )
            elif target_groups:
                result.coverage_ratio = 1.0
            else:
                result.coverage_ratio = 0.0

            if result.coverage_ratio < min_coverage:
                log.warning(
                    f"Low coverage for {variable} ({source_level}→{target_level}): "
                    f"{result.coverage_ratio:.2%} < {min_coverage:.0%} threshold"
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
                f"created={result.records_created}, skipped={result.records_skipped}, "
                f"coverage={result.coverage_ratio:.2%}"
            )

        return results

    def _build_crosswalk_map(
        self,
        source_level: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> Dict[str, List[tuple]]:
        """
        Build a mapping from source boundary IDs to (target_id, weight) pairs
        using TemporalCrosswalk records.

        Returns:
            Dict mapping source_boundary_id → [(target_boundary_id, weight), ...]
        """
        from ..models.crosswalks import TemporalCrosswalk

        qs = TemporalCrosswalk.objects.filter(
            source_type=source_level,
            source_vintage_year=source_year,
            target_vintage_year=target_year,
        )
        if state_fips:
            qs = qs.filter(state_fips=state_fips)

        mapping: Dict[str, List[tuple]] = {}
        for xw in qs.iterator():
            mapping.setdefault(xw.source_boundary_id, []).append(
                (xw.target_boundary_id, xw.weight)
            )
        return mapping

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
