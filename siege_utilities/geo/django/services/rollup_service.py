"""
Service for demographic roll-up aggregation across geography levels.

Aggregates demographic data from a finer geography (e.g., tracts) to a
coarser geography (e.g., counties) using GEOID prefix hierarchy or
temporal crosswalk mappings.  Supports sum, avg, and weighted_avg
(population-weighted) operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)

__all__ = [
    'RollupResult',
    'DemographicRollupService',
]


def _canonical_level(level: str) -> str:
    """Return the canonical geography level name (e.g. 'blockgroup' -> 'block_group').

    Shares the registry vocabulary with CrosswalkPopulationService so crosswalk
    rows written by the loader are found here. Unrecognised names are returned
    unchanged and reported as unsupported by ``rollup``.
    """
    from siege_utilities.config.census_registry import resolve_geographic_level

    try:
        return resolve_geographic_level(level)
    except ValueError:
        return level


@dataclass
class RollupResult:
    """Result of a rollup aggregation run."""

    source_level: str
    target_level: str
    variable_code: str
    records_created: int = 0
    records_updated: int = 0
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
        overwrite: bool = False,
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
                ``crosswalk_year`` → ``year`` (at ``source_level``) and then
                truncate each crosswalk target GEOID to ``target_level``.
                Enables rollup across boundary changes.  The crosswalk weight
                is applied exactly once: it scales the value for ``sum`` and
                the contribution weight for ``avg``/``weighted_avg``.
            min_coverage: Minimum coverage ratio (0-1, default 0.5).  When
                fewer than ``min_coverage`` of the expected children have data,
                a warning is logged.  Expected children are the ``source_level``
                boundaries (latest vintage <= ``year``) in prefix mode, and the
                crosswalk source boundaries in crosswalk mode.
            overwrite: When False (default), a target snapshot that already
                holds ``variable`` is left unchanged and counted as skipped,
                so authoritative values (e.g. fetched from the Census API) are
                never replaced by derived aggregates.  When True, the value is
                replaced and counted in ``records_updated``.

        Returns:
            List of RollupResult (one per variable)
        """
        _VALID_OPERATIONS = {'sum', 'avg', 'weighted_avg'}
        if operation not in _VALID_OPERATIONS:
            raise ValueError(
                f"Unknown aggregation operation {operation!r}; "
                f"expected one of {sorted(_VALID_OPERATIONS)}"
            )

        from django.contrib.contenttypes.models import ContentType

        from ..models.demographics import DemographicSnapshot
        from ._bulk import bulk_insert_counted

        source_level = _canonical_level(source_level)
        target_level = _canonical_level(target_level)

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

        # Expected children, for the coverage ratio
        if crosswalk_map is None:
            expected_children = self._expected_children(
                source_model, source_level, year, state_fips
            )
        else:
            expected_children = set(crosswalk_map)
        if expected_children is None:
            log.warning(
                f"No {source_level} boundaries with vintage <= {year} are loaded; "
                f"coverage for {source_level}→{target_level} is measured against "
                f"existing snapshots only and cannot detect missing children"
            )
            expected_children = {snap.object_id for snap in snap_qs.iterator()}

        results = []

        for variable in variables:
            result = RollupResult(
                source_level=source_level,
                target_level=target_level,
                variable_code=variable,
            )

            # Group (value, weight, population) contributions by target GEOID.
            # weight is the crosswalk allocation (1.0 in prefix mode).
            contributions: Dict[str, List[Tuple[float, float, Optional[float]]]] = {}
            children_with_data: Set[str] = set()

            for snap in snap_qs.iterator():
                val = snap.values.get(variable)
                if val is None:
                    continue
                children_with_data.add(snap.object_id)

                if crosswalk_map is not None:
                    # One source may map to several targets; map each crosswalk
                    # target up to the target level.
                    mappings = [
                        (xw_target[:target_prefix_len], float(weight))
                        for xw_target, weight in crosswalk_map.get(snap.object_id, [])
                    ]
                else:
                    mappings = [(snap.object_id[:target_prefix_len], 1.0)]

                for target_geoid, weight in mappings:
                    if weight <= 0.0:
                        continue  # allocates nothing to this target
                    contributions.setdefault(target_geoid, []).append(
                        (val, weight, snap.total_population or None)
                    )

            # Coverage: children with data / expected children
            if expected_children:
                result.coverage_ratio = len(children_with_data & expected_children) / len(
                    expected_children
                )
            else:
                result.coverage_ratio = 0.0

            if result.coverage_ratio < min_coverage:
                log.warning(
                    f"Low coverage for {variable} ({source_level}→{target_level}): "
                    f"{result.coverage_ratio:.2%} < {min_coverage:.0%} threshold"
                )

            # Create aggregated snapshots for target
            to_create = []
            for target_geoid, parts in contributions.items():
                agg_value = self._aggregate(operation, parts)

                # Check if target snapshot already exists
                existing = DemographicSnapshot.objects.filter(
                    content_type=target_ct,
                    object_id=target_geoid,
                    dataset=self.dataset,
                    year=year,
                ).first()

                if existing is not None:
                    current = dict(existing.values or {})
                    if variable in current and not overwrite:
                        # Never replace an existing (possibly authoritative) value
                        result.records_skipped += 1
                        continue
                    current[variable] = agg_value
                    existing.values = current
                    existing.save()
                    result.records_updated += 1
                else:
                    # bulk_create skips save(); derive summaries here (#1539)
                    to_create.append(
                        DemographicSnapshot(
                            content_type=target_ct,
                            object_id=target_geoid,
                            dataset=self.dataset,
                            year=year,
                            values={variable: agg_value},
                        ).prepare_for_bulk()
                    )

            if to_create:
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i: i + batch_size]
                    # Count rows inserted, not rows offered (#1539)
                    result.records_created += bulk_insert_counted(
                        DemographicSnapshot.objects,
                        batch,
                        scope={
                            "content_type": target_ct,
                            "dataset": self.dataset,
                            "year": year,
                            "object_id__in": [snap.object_id for snap in batch],
                        },
                    )

            results.append(result)
            log.info(
                f"Rollup {variable} ({source_level}→{target_level}): "
                f"created={result.records_created}, updated={result.records_updated}, "
                f"skipped={result.records_skipped}, "
                f"coverage={result.coverage_ratio:.2%}"
            )

        return results

    @staticmethod
    def _aggregate(
        operation: str, parts: List[Tuple[float, float, Optional[float]]]
    ) -> float:
        """
        Aggregate (value, weight, population) contributions for one target.

        The weight is the crosswalk allocation share (1.0 in prefix mode) and
        is applied exactly once:

        - sum: Σ value·weight (the allocated share of each count)
        - avg: Σ value·weight / Σ weight (a split child counts once in total)
        - weighted_avg: Σ value·pop·weight / Σ pop·weight; falls back to the
          ``avg`` formula when any contribution lacks a population
        """
        if operation == 'sum':
            return sum(v * w for v, w, _ in parts)
        if operation == 'weighted_avg' and all(p for _, _, p in parts):
            total_pop = sum(p * w for _, w, p in parts)
            return sum(v * p * w for v, w, p in parts) / total_pop
        total_weight = sum(w for _, w, _ in parts)
        return sum(v * w for v, w, _ in parts) / total_weight

    @staticmethod
    def _expected_children(
        source_model,
        source_level: str,
        year: int,
        state_fips: Optional[str] = None,
    ) -> Optional[Set[str]]:
        """
        GEOIDs of the ``source_level`` boundaries expected to report for ``year``.

        Uses the latest boundary vintage <= ``year``.  Returns None when no
        such boundaries are loaded.
        """
        from django.db.models import Max

        qs = source_model.objects.filter(vintage_year__lte=year)
        if state_fips:
            qs = qs.filter(geoid__startswith=state_fips)
        vintage = qs.aggregate(latest=Max("vintage_year"))["latest"]
        if vintage is None:
            return None
        log.debug(f"Coverage for {source_level} uses boundary vintage {vintage}")
        return set(qs.filter(vintage_year=vintage).values_list("geoid", flat=True))

    def _build_crosswalk_map(
        self,
        source_level: str,
        source_year: int,
        target_year: int,
        state_fips: Optional[str] = None,
    ) -> Dict[str, List[tuple]]:
        """
        Build a mapping from source boundary IDs to (target_id, weight) pairs
        using TemporalCrosswalk records whose source and target are both at
        ``source_level`` (canonical name, e.g. 'block_group').

        Returns:
            Dict mapping source_boundary_id → [(target_boundary_id, weight), ...]
        """
        from ..models.crosswalks import TemporalCrosswalk

        source_level = _canonical_level(source_level)
        qs = TemporalCrosswalk.objects.filter(
            source_type=source_level,
            target_type=source_level,
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
        except LookupError as exc:
            log.warning("Could not resolve model: %s", exc)
            return None
