"""
Multi-dimensional entity health scoring.

Composable weighted-dimension scorer for evaluating entities across
configurable dimensions with segment-aware thresholds and trend detection.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Dimension:
    """A scoring dimension with a name and weight (0-100)."""

    name: str
    weight: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Dimension name must not be empty")
        if not (0 < self.weight <= 100):
            raise ValueError(
                f"Dimension weight must be in (0, 100], got {self.weight}"
            )


@dataclass(frozen=True)
class ThresholdConfig:
    """Tier thresholds for score classification.

    Scores >= green_min are Green, >= yellow_min are Yellow, else Red.
    """

    green_min: float = 70.0
    yellow_min: float = 40.0

    def __post_init__(self) -> None:
        if self.yellow_min >= self.green_min:
            raise ValueError(
                f"yellow_min ({self.yellow_min}) must be less than "
                f"green_min ({self.green_min})"
            )

    def classify(self, score: float) -> str:
        if score >= self.green_min:
            return "Green"
        if score >= self.yellow_min:
            return "Yellow"
        return "Red"


@dataclass(frozen=True)
class EntityScore:
    """Result of scoring an entity."""

    entity_id: str
    composite_score: float
    tier: str
    dimension_scores: dict[str, float]
    segment: str | None = None
    trend: float | None = None
    trend_direction: str | None = None


class HealthScorer:
    """Weighted multi-dimensional entity scorer.

    Parameters
    ----------
    dimensions : list[Dimension]
        Scoring dimensions. Weights must sum to 100.
    default_thresholds : ThresholdConfig, optional
        Default tier thresholds. Can be overridden per-segment.
    segment_thresholds : dict[str, ThresholdConfig], optional
        Per-segment threshold overrides.

    Raises
    ------
    ValueError
        If dimensions is empty or weights don't sum to 100.
    """

    def __init__(
        self,
        dimensions: list[Dimension],
        default_thresholds: ThresholdConfig | None = None,
        segment_thresholds: dict[str, ThresholdConfig] | None = None,
    ) -> None:
        if not dimensions:
            raise ValueError("At least one dimension is required")

        total_weight = sum(d.weight for d in dimensions)
        if not math.isclose(total_weight, 100.0, abs_tol=0.01):
            raise ValueError(
                f"Dimension weights must sum to 100, got {total_weight}"
            )

        self._dimensions = list(dimensions)
        self._default_thresholds = default_thresholds or ThresholdConfig()
        self._segment_thresholds = dict(segment_thresholds or {})

        logger.info(
            "HealthScorer initialized with %d dimensions: %s",
            len(self._dimensions),
            ", ".join(f"{d.name}({d.weight}%)" for d in self._dimensions),
        )

    @property
    def dimension_names(self) -> list[str]:
        return [d.name for d in self._dimensions]

    def score(
        self,
        entity_id: str,
        scores: dict[str, float],
        *,
        segment: str | None = None,
        previous_score: float | None = None,
    ) -> EntityScore:
        """Score an entity across all dimensions.

        Parameters
        ----------
        entity_id : str
            Identifier for the entity being scored.
        scores : dict[str, float]
            Per-dimension scores (0-100). Must include all dimensions.
        segment : str, optional
            Segment for threshold selection.
        previous_score : float, optional
            Previous composite score for trend detection.

        Returns
        -------
        EntityScore

        Raises
        ------
        ValueError
            If scores dict is missing dimensions or values are out of range.
        """
        missing = set(self.dimension_names) - set(scores.keys())
        if missing:
            raise ValueError(f"Missing scores for dimensions: {missing}")

        for name, value in scores.items():
            if name not in self.dimension_names:
                raise ValueError(f"Unknown dimension: {name!r}")
            if not (0 <= value <= 100):
                raise ValueError(
                    f"Score for {name!r} must be in [0, 100], got {value}"
                )

        composite = sum(
            scores[d.name] * d.weight / 100.0 for d in self._dimensions
        )

        thresholds = self._segment_thresholds.get(
            segment, self._default_thresholds
        ) if segment else self._default_thresholds

        tier = thresholds.classify(composite)

        trend = None
        trend_direction = None
        if previous_score is not None:
            trend = composite - previous_score
            if trend > 0:
                trend_direction = "improving"
            elif trend < 0:
                trend_direction = "declining"
            else:
                trend_direction = "stable"

        dimension_scores = {d.name: scores[d.name] for d in self._dimensions}

        result = EntityScore(
            entity_id=entity_id,
            composite_score=round(composite, 2),
            tier=tier,
            dimension_scores=dimension_scores,
            segment=segment,
            trend=round(trend, 2) if trend is not None else None,
            trend_direction=trend_direction,
        )

        logger.info(
            "Scored %s: %.1f (%s)%s",
            entity_id,
            result.composite_score,
            tier,
            f" trend={trend_direction}" if trend_direction else "",
        )

        return result

    def score_batch(
        self,
        entities: list[dict[str, Any]],
    ) -> list[EntityScore]:
        """Score multiple entities.

        Each dict must have 'entity_id' and 'scores' keys.
        Optional: 'segment', 'previous_score'.

        Parameters
        ----------
        entities : list[dict]
            List of entity dicts with keys: entity_id, scores,
            and optionally segment, previous_score.

        Returns
        -------
        list[EntityScore]

        Raises
        ------
        ValueError
            If any entity dict is missing required keys.
        """
        results = []
        for entity in entities:
            if "entity_id" not in entity or "scores" not in entity:
                raise ValueError(
                    "Each entity dict must have 'entity_id' and 'scores' keys"
                )
            results.append(
                self.score(
                    entity_id=entity["entity_id"],
                    scores=entity["scores"],
                    segment=entity.get("segment"),
                    previous_score=entity.get("previous_score"),
                )
            )

        logger.info("Scored %d entities in batch", len(results))
        return results
