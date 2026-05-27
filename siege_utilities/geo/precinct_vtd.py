"""Precinct-to-VTD reconciliation.

Reconciles RDH precinct shapefiles with Census VTDs (Voting Tabulation
Districts) using spatial overlap, name matching, and official crosswalks.
"""

from __future__ import annotations

import abc
import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Optional

log = logging.getLogger(__name__)


class ReconciliationMethod(str, Enum):
    """How a precinct-VTD mapping was determined."""

    SPATIAL = "spatial"
    NAME_MATCH = "name_match"
    OFFICIAL_CROSSWALK = "official_crosswalk"
    COMBINED = "combined"


class ConfidenceLevel(str, Enum):
    """Confidence tier for a reconciliation mapping."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _confidence_level(score: float) -> ConfidenceLevel:
    if score >= 0.85:
        return ConfidenceLevel.HIGH
    if score >= 0.60:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


@dataclass
class PrecinctVTDMapping:
    """A single precinct-to-VTD mapping with confidence metadata.

    Attributes:
        precinct_id: Identifier from the precinct shapefile.
        vtd_geoid: Census VTD GEOID.
        overlap_pct: Fraction of precinct area covered by this VTD (0-1).
        confidence: Confidence score (0-1).
        confidence_level: Categorical confidence tier.
        method: How this mapping was determined.
        name_similarity: Similarity score from name matching (0-1), if applicable.
        notes: Human-readable explanation.
    """

    precinct_id: str = ""
    vtd_geoid: str = ""
    overlap_pct: float = 0.0
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    method: ReconciliationMethod = ReconciliationMethod.SPATIAL
    name_similarity: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "precinct_id": self.precinct_id,
            "vtd_geoid": self.vtd_geoid,
            "overlap_pct": round(self.overlap_pct, 4),
            "confidence": round(self.confidence, 4),
            "confidence_level": self.confidence_level.value,
            "method": self.method.value,
        }
        if self.name_similarity is not None:
            d["name_similarity"] = round(self.name_similarity, 4)
        if self.notes:
            d["notes"] = self.notes
        return d


@dataclass
class ReconciliationResult:
    """Complete result of precinct-VTD reconciliation.

    Attributes:
        mappings: All precinct-VTD mappings.
        total_precincts: Number of precincts processed.
        matched_precincts: Number of precincts with at least one mapping.
        unmatched_precincts: Precinct IDs with no mapping.
        method_counts: Count of mappings by method.
        errors: Any errors encountered.
    """

    mappings: list[PrecinctVTDMapping] = field(default_factory=list)
    total_precincts: int = 0
    matched_precincts: int = 0
    unmatched_precincts: list[str] = field(default_factory=list)
    method_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        if self.total_precincts == 0:
            return 0.0
        return self.matched_precincts / self.total_precincts

    @property
    def high_confidence_count(self) -> int:
        return sum(1 for m in self.mappings if m.confidence_level == ConfidenceLevel.HIGH)

    def for_precinct(self, precinct_id: str) -> list[PrecinctVTDMapping]:
        return [m for m in self.mappings if m.precinct_id == precinct_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_precincts": self.total_precincts,
            "matched_precincts": self.matched_precincts,
            "match_rate": round(self.match_rate, 4),
            "high_confidence_count": self.high_confidence_count,
            "method_counts": self.method_counts,
            "unmatched_precincts": self.unmatched_precincts,
            "mappings": [m.to_dict() for m in self.mappings],
            "errors": self.errors,
        }


@dataclass
class SpatialOverlap:
    """Spatial overlap between a precinct and a VTD.

    Attributes:
        precinct_id: Precinct identifier.
        vtd_geoid: VTD GEOID.
        overlap_area: Area of intersection (in source CRS units).
        precinct_area: Total area of the precinct.
        vtd_area: Total area of the VTD.
        overlap_pct: Fraction of precinct covered by VTD.
    """

    precinct_id: str = ""
    vtd_geoid: str = ""
    overlap_area: float = 0.0
    precinct_area: float = 0.0
    vtd_area: float = 0.0
    overlap_pct: float = 0.0


@dataclass
class OfficialCrosswalkEntry:
    """Entry from an official precinct-to-VTD crosswalk.

    Attributes:
        precinct_id: Precinct identifier as published.
        vtd_geoid: VTD GEOID as published.
        state: State abbreviation.
        county: County name or FIPS.
        source: Source of the crosswalk (e.g., "NC SBE 2022").
    """

    precinct_id: str = ""
    vtd_geoid: str = ""
    state: str = ""
    county: str = ""
    source: str = ""


class SpatialOverlapProvider(abc.ABC):
    """Protocol for computing spatial overlaps between precincts and VTDs."""

    @abc.abstractmethod
    def compute_overlaps(
        self,
        precinct_ids: list[str],
    ) -> list[SpatialOverlap]:
        """Compute spatial overlaps for the given precincts."""


class DictSpatialOverlapProvider(SpatialOverlapProvider):
    """In-memory spatial overlap provider for testing."""

    def __init__(self):
        self._overlaps: list[SpatialOverlap] = []

    def add(self, overlap: SpatialOverlap):
        self._overlaps.append(overlap)

    def compute_overlaps(self, precinct_ids: list[str]) -> list[SpatialOverlap]:
        ids = set(precinct_ids)
        return [o for o in self._overlaps if o.precinct_id in ids]


class NameMatchProvider(abc.ABC):
    """Protocol for matching precinct names to VTD names."""

    @abc.abstractmethod
    def get_precinct_names(self, precinct_ids: list[str]) -> dict[str, str]:
        """Get display names for precincts."""

    @abc.abstractmethod
    def get_vtd_names(self) -> dict[str, str]:
        """Get display names for VTDs (geoid → name)."""


class DictNameMatchProvider(NameMatchProvider):
    """In-memory name match provider for testing."""

    def __init__(self):
        self._precinct_names: dict[str, str] = {}
        self._vtd_names: dict[str, str] = {}

    def add_precinct(self, precinct_id: str, name: str):
        self._precinct_names[precinct_id] = name

    def add_vtd(self, vtd_geoid: str, name: str):
        self._vtd_names[vtd_geoid] = name

    def get_precinct_names(self, precinct_ids: list[str]) -> dict[str, str]:
        return {pid: self._precinct_names[pid] for pid in precinct_ids if pid in self._precinct_names}

    def get_vtd_names(self) -> dict[str, str]:
        return dict(self._vtd_names)


_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]")


def _normalize_name(name: str) -> str:
    return _NORMALIZE_RE.sub("", name.lower()).strip()


def _name_similarity(a: str, b: str) -> float:
    na, nb = _normalize_name(a), _normalize_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


MIN_OVERLAP_PCT = 0.01
MIN_NAME_SIMILARITY = 0.50
SPATIAL_WEIGHT = 0.7
NAME_WEIGHT = 0.3


def reconcile_spatial(
    overlaps: list[SpatialOverlap],
) -> list[PrecinctVTDMapping]:
    """Create mappings from spatial overlaps."""
    mappings = []
    for ov in overlaps:
        if ov.overlap_pct < MIN_OVERLAP_PCT:
            continue
        confidence = ov.overlap_pct
        mappings.append(PrecinctVTDMapping(
            precinct_id=ov.precinct_id,
            vtd_geoid=ov.vtd_geoid,
            overlap_pct=ov.overlap_pct,
            confidence=confidence,
            confidence_level=_confidence_level(confidence),
            method=ReconciliationMethod.SPATIAL,
        ))
    return mappings


def reconcile_names(
    precinct_names: dict[str, str],
    vtd_names: dict[str, str],
) -> list[PrecinctVTDMapping]:
    """Create mappings from fuzzy name matching."""
    mappings = []
    for pid, pname in precinct_names.items():
        best_geoid = ""
        best_sim = 0.0
        for vgeoid, vname in vtd_names.items():
            sim = _name_similarity(pname, vname)
            if sim > best_sim:
                best_sim = sim
                best_geoid = vgeoid
        if best_sim >= MIN_NAME_SIMILARITY and best_geoid:
            mappings.append(PrecinctVTDMapping(
                precinct_id=pid,
                vtd_geoid=best_geoid,
                overlap_pct=0.0,
                confidence=best_sim,
                confidence_level=_confidence_level(best_sim),
                method=ReconciliationMethod.NAME_MATCH,
                name_similarity=best_sim,
            ))
    return mappings


def reconcile_official(
    crosswalk: list[OfficialCrosswalkEntry],
) -> list[PrecinctVTDMapping]:
    """Create mappings from an official crosswalk."""
    return [
        PrecinctVTDMapping(
            precinct_id=entry.precinct_id,
            vtd_geoid=entry.vtd_geoid,
            overlap_pct=1.0,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            method=ReconciliationMethod.OFFICIAL_CROSSWALK,
            notes=f"Official crosswalk: {entry.source}" if entry.source else "Official crosswalk",
        )
        for entry in crosswalk
    ]


def _merge_mappings(
    spatial: list[PrecinctVTDMapping],
    names: list[PrecinctVTDMapping],
    official: list[PrecinctVTDMapping],
) -> list[PrecinctVTDMapping]:
    """Merge mappings from all methods, preferring official > spatial > name."""
    by_precinct: dict[str, dict[str, PrecinctVTDMapping]] = {}

    for m in official:
        by_precinct.setdefault(m.precinct_id, {})[m.vtd_geoid] = m

    for m in spatial:
        bucket = by_precinct.setdefault(m.precinct_id, {})
        if m.vtd_geoid not in bucket:
            bucket[m.vtd_geoid] = m
        else:
            existing = bucket[m.vtd_geoid]
            if existing.method != ReconciliationMethod.OFFICIAL_CROSSWALK:
                if m.confidence > existing.confidence:
                    bucket[m.vtd_geoid] = m

    for m in names:
        bucket = by_precinct.setdefault(m.precinct_id, {})
        if m.vtd_geoid not in bucket:
            bucket[m.vtd_geoid] = m

    # Boost spatial mappings that have name confirmation
    name_lookup: dict[tuple[str, str], float] = {
        (m.precinct_id, m.vtd_geoid): m.name_similarity or 0.0
        for m in names
    }
    result = []
    for pid, vtd_map in sorted(by_precinct.items()):
        for vgeoid, mapping in sorted(vtd_map.items()):
            key = (pid, vgeoid)
            if (
                mapping.method == ReconciliationMethod.SPATIAL
                and key in name_lookup
                and name_lookup[key] >= MIN_NAME_SIMILARITY
            ):
                combined_confidence = (
                    SPATIAL_WEIGHT * mapping.confidence
                    + NAME_WEIGHT * name_lookup[key]
                )
                mapping = PrecinctVTDMapping(
                    precinct_id=pid,
                    vtd_geoid=vgeoid,
                    overlap_pct=mapping.overlap_pct,
                    confidence=combined_confidence,
                    confidence_level=_confidence_level(combined_confidence),
                    method=ReconciliationMethod.COMBINED,
                    name_similarity=name_lookup[key],
                )
            result.append(mapping)
    return result


class PrecinctVTDReconciler:
    """Reconciles precinct boundaries with Census VTDs.

    Uses spatial overlap, name matching, and official crosswalks
    (when available) to produce precinct-to-VTD mappings with
    confidence scores.

    Args:
        spatial_provider: Source for spatial overlap computation.
        name_provider: Source for precinct/VTD name matching.
        official_crosswalk: Pre-loaded official crosswalk entries.
    """

    def __init__(
        self,
        spatial_provider: Optional[SpatialOverlapProvider] = None,
        name_provider: Optional[NameMatchProvider] = None,
        official_crosswalk: Optional[list[OfficialCrosswalkEntry]] = None,
    ):
        self._spatial = spatial_provider
        self._names = name_provider
        self._crosswalk = official_crosswalk or []

    def reconcile(
        self,
        precinct_ids: list[str],
    ) -> ReconciliationResult:
        """Reconcile the given precincts against VTDs.

        Args:
            precinct_ids: List of precinct identifiers to reconcile.

        Returns:
            ReconciliationResult with mappings and diagnostics.
        """
        if not precinct_ids:
            return ReconciliationResult()

        spatial_mappings: list[PrecinctVTDMapping] = []
        name_mappings: list[PrecinctVTDMapping] = []
        official_mappings: list[PrecinctVTDMapping] = []
        errors: list[str] = []

        relevant_crosswalk = [
            e for e in self._crosswalk if e.precinct_id in set(precinct_ids)
        ]
        if relevant_crosswalk:
            official_mappings = reconcile_official(relevant_crosswalk)

        if self._spatial is not None:
            try:
                overlaps = self._spatial.compute_overlaps(precinct_ids)
                spatial_mappings = reconcile_spatial(overlaps)
            except Exception as exc:
                errors.append(f"Spatial reconciliation error: {exc}")

        if self._names is not None:
            try:
                pnames = self._names.get_precinct_names(precinct_ids)
                vnames = self._names.get_vtd_names()
                if pnames and vnames:
                    name_mappings = reconcile_names(pnames, vnames)
            except Exception as exc:
                errors.append(f"Name matching error: {exc}")

        merged = _merge_mappings(spatial_mappings, name_mappings, official_mappings)

        matched_ids = set(m.precinct_id for m in merged)
        unmatched = [pid for pid in precinct_ids if pid not in matched_ids]

        method_counts: dict[str, int] = {}
        for m in merged:
            method_counts[m.method.value] = method_counts.get(m.method.value, 0) + 1

        return ReconciliationResult(
            mappings=merged,
            total_precincts=len(precinct_ids),
            matched_precincts=len(matched_ids),
            unmatched_precincts=unmatched,
            method_counts=method_counts,
            errors=errors,
        )
