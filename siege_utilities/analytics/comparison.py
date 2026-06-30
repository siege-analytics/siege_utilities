"""
Evidence-based comparative analysis.

Structured comparison framework for scoring and comparing N entities
across M dimensions with mandatory evidence citation, feature matrix
construction, and gap analysis.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DimensionScore:
    """A score for one entity on one dimension.

    Parameters
    ----------
    score : int
        Score on a 1-5 scale.
    evidence : str
        Citation supporting the score (URL, doc reference, test result).
    """

    score: int
    evidence: str

    def __post_init__(self) -> None:
        if not isinstance(self.score, int) or not (1 <= self.score <= 5):
            raise ValueError(
                f"Score must be an integer in [1, 5], got {self.score!r}"
            )
        if not self.evidence or not self.evidence.strip():
            raise ValueError("Evidence citation must not be empty")


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing entities across dimensions."""

    dimensions: list[str]
    entities: list[str]
    scores: dict[str, dict[str, DimensionScore]]
    weighted_totals: dict[str, float]
    gap_analysis: list[tuple[str, float]]


@dataclass(frozen=True)
class FeatureMatrix:
    """Boolean feature support matrix with coverage scoring."""

    entities: list[str]
    features: list[str]
    matrix: dict[str, dict[str, bool]]
    coverage: dict[str, float]


class ComparativeAnalyzer:
    """N-entity x M-dimension comparison engine.

    Parameters
    ----------
    dimensions : list[str]
        Dimension names for comparison.
    weights : dict[str, float] | None
        Optional dimension weights. If provided, must cover all
        dimensions. If omitted, equal weights are used.

    Raises
    ------
    ValueError
        If dimensions is empty or weights don't match dimensions.
    """

    def __init__(
        self,
        dimensions: list[str],
        weights: dict[str, float] | None = None,
    ) -> None:
        if not dimensions:
            raise ValueError("At least one dimension is required")

        if len(dimensions) != len(set(dimensions)):
            raise ValueError("Dimension names must be unique")

        self._dimensions = list(dimensions)

        if weights is not None:
            missing = set(dimensions) - set(weights.keys())
            if missing:
                raise ValueError(f"Missing weights for dimensions: {missing}")
            extra = set(weights.keys()) - set(dimensions)
            if extra:
                raise ValueError(f"Weights for unknown dimensions: {extra}")
            self._weights = dict(weights)
        else:
            equal_weight = 1.0 / len(dimensions)
            self._weights = {d: equal_weight for d in dimensions}

        logger.info(
            "ComparativeAnalyzer initialized with %d dimensions: %s",
            len(self._dimensions),
            ", ".join(self._dimensions),
        )

    def compare(
        self,
        entity_scores: dict[str, dict[str, DimensionScore]],
    ) -> ComparisonResult:
        """Compare entities across all dimensions.

        Parameters
        ----------
        entity_scores : dict[str, dict[str, DimensionScore]]
            Outer key = entity name, inner key = dimension name.

        Returns
        -------
        ComparisonResult

        Raises
        ------
        ValueError
            If any entity is missing a dimension score.
        """
        if not entity_scores:
            raise ValueError("At least one entity is required")

        for entity, scores in entity_scores.items():
            missing = set(self._dimensions) - set(scores.keys())
            if missing:
                raise ValueError(
                    f"Entity {entity!r} missing scores for: {missing}"
                )

        weighted_totals: dict[str, float] = {}
        for entity, scores in entity_scores.items():
            total = sum(
                scores[d].score * self._weights[d]
                for d in self._dimensions
            )
            weighted_totals[entity] = round(total, 4)

        gap_analysis = self._compute_gap_analysis(entity_scores)

        entities = sorted(entity_scores.keys())

        result = ComparisonResult(
            dimensions=list(self._dimensions),
            entities=entities,
            scores=entity_scores,
            weighted_totals=weighted_totals,
            gap_analysis=gap_analysis,
        )

        logger.info(
            "Compared %d entities across %d dimensions. "
            "Highest variance: %s (%.2f)",
            len(entities),
            len(self._dimensions),
            gap_analysis[0][0] if gap_analysis else "N/A",
            gap_analysis[0][1] if gap_analysis else 0.0,
        )

        return result

    def _compute_gap_analysis(
        self,
        entity_scores: dict[str, dict[str, DimensionScore]],
    ) -> list[tuple[str, float]]:
        """Identify dimensions with largest score variance across entities."""
        if len(entity_scores) < 2:
            return [(d, 0.0) for d in self._dimensions]

        variances: list[tuple[str, float]] = []
        for dim in self._dimensions:
            dim_scores = [
                scores[dim].score for scores in entity_scores.values()
            ]
            variance = statistics.variance(dim_scores)
            variances.append((dim, round(variance, 4)))

        variances.sort(key=lambda x: x[1], reverse=True)
        return variances

    @staticmethod
    def build_feature_matrix(
        entity_features: dict[str, dict[str, bool]],
    ) -> FeatureMatrix:
        """Build a boolean feature support matrix with coverage scores.

        Parameters
        ----------
        entity_features : dict[str, dict[str, bool]]
            Outer key = entity name, inner key = feature name.

        Returns
        -------
        FeatureMatrix

        Raises
        ------
        ValueError
            If no entities or no features are provided.
        """
        if not entity_features:
            raise ValueError("At least one entity is required")

        all_features: set[str] = set()
        for features in entity_features.values():
            all_features.update(features.keys())

        if not all_features:
            raise ValueError("At least one feature is required")

        sorted_features = sorted(all_features)
        entities = sorted(entity_features.keys())

        normalized: dict[str, dict[str, bool]] = {}
        coverage: dict[str, float] = {}

        for entity in entities:
            features = entity_features[entity]
            row = {f: features.get(f, False) for f in sorted_features}
            normalized[entity] = row
            supported = sum(1 for v in row.values() if v)
            coverage[entity] = round(supported / len(sorted_features) * 100, 2)

        logger.info(
            "Feature matrix: %d entities × %d features",
            len(entities),
            len(sorted_features),
        )

        return FeatureMatrix(
            entities=entities,
            features=sorted_features,
            matrix=normalized,
            coverage=coverage,
        )
