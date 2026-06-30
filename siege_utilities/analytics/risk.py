"""
Multi-signal risk stacking.

Composable risk assessment that stacks N weighted signals into a
composite risk score with tier classification and optional
intervention mapping.
"""

from __future__ import annotations

import enum
import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class SignalType(enum.Enum):
    """Types of risk signals."""

    DECLINE = "decline"
    THRESHOLD = "threshold"
    ABSENCE = "absence"
    ANOMALY = "anomaly"


class RiskTier(enum.Enum):
    """Risk classification tiers, ordered by severity."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True)
class RiskSignal:
    """A named risk signal with type and weight.

    Parameters
    ----------
    name : str
        Signal identifier.
    signal_type : SignalType
        Category of risk this signal measures.
    weight : float
        Relative weight (0, 100]. All signals' weights must sum to 100.
    """

    name: str
    signal_type: SignalType
    weight: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Signal name must not be empty")
        if not isinstance(self.signal_type, SignalType):
            raise ValueError(
                f"signal_type must be a SignalType enum, got {type(self.signal_type)}"
            )
        if not (0 < self.weight <= 100):
            raise ValueError(
                f"Signal weight must be in (0, 100], got {self.weight}"
            )


@dataclass(frozen=True)
class RiskTierConfig:
    """Thresholds for risk tier classification.

    Scores >= critical_min are Critical, >= high_min are High, etc.
    """

    critical_min: float = 80.0
    high_min: float = 60.0
    medium_min: float = 40.0

    def __post_init__(self) -> None:
        if not (self.medium_min < self.high_min < self.critical_min):
            raise ValueError(
                f"Thresholds must be ordered: medium_min ({self.medium_min}) "
                f"< high_min ({self.high_min}) < critical_min ({self.critical_min})"
            )

    def classify(self, score: float) -> RiskTier:
        if score >= self.critical_min:
            return RiskTier.CRITICAL
        if score >= self.high_min:
            return RiskTier.HIGH
        if score >= self.medium_min:
            return RiskTier.MEDIUM
        return RiskTier.LOW


@dataclass(frozen=True)
class RiskAssessment:
    """Result of a risk assessment."""

    entity_id: str
    composite_score: float
    tier: RiskTier
    signal_scores: dict[str, float]
    signal_types: dict[str, SignalType]
    intervention: str | None = None


class RiskAnalyzer:
    """Multi-signal risk stacking engine.

    Parameters
    ----------
    signals : list[RiskSignal]
        Risk signals to evaluate. Weights must sum to 100.
    tier_config : RiskTierConfig, optional
        Tier classification thresholds.
    interventions : dict[RiskTier, str], optional
        Mapping from risk tier to recommended intervention.

    Raises
    ------
    ValueError
        If signals is empty or weights don't sum to 100.
    """

    def __init__(
        self,
        signals: list[RiskSignal],
        tier_config: RiskTierConfig | None = None,
        interventions: dict[RiskTier, str] | None = None,
    ) -> None:
        if not signals:
            raise ValueError("At least one risk signal is required")

        total_weight = sum(s.weight for s in signals)
        if not math.isclose(total_weight, 100.0, abs_tol=0.01):
            raise ValueError(
                f"Signal weights must sum to 100, got {total_weight}"
            )

        self._signals = list(signals)
        self._tier_config = tier_config or RiskTierConfig()
        self._interventions = dict(interventions or {})

        logger.info(
            "RiskAnalyzer initialized with %d signals: %s",
            len(self._signals),
            ", ".join(
                f"{s.name}({s.signal_type.value},{s.weight}%)"
                for s in self._signals
            ),
        )

    @property
    def signal_names(self) -> list[str]:
        return [s.name for s in self._signals]

    def assess(
        self,
        entity_id: str,
        scores: dict[str, float],
    ) -> RiskAssessment:
        """Assess risk for an entity.

        Parameters
        ----------
        entity_id : str
            Identifier for the entity.
        scores : dict[str, float]
            Per-signal risk scores (0-100). Higher = more risk.

        Returns
        -------
        RiskAssessment

        Raises
        ------
        ValueError
            If scores dict is missing signals or values are out of range.
        """
        missing = set(self.signal_names) - set(scores.keys())
        if missing:
            raise ValueError(f"Missing scores for signals: {missing}")

        for name, value in scores.items():
            if name not in self.signal_names:
                raise ValueError(f"Unknown signal: {name!r}")
            if not (0 <= value <= 100):
                raise ValueError(
                    f"Score for {name!r} must be in [0, 100], got {value}"
                )

        composite = sum(
            scores[s.name] * s.weight / 100.0 for s in self._signals
        )

        tier = self._tier_config.classify(composite)
        intervention = self._interventions.get(tier)

        signal_scores = {s.name: scores[s.name] for s in self._signals}
        signal_types = {s.name: s.signal_type for s in self._signals}

        result = RiskAssessment(
            entity_id=entity_id,
            composite_score=round(composite, 2),
            tier=tier,
            signal_scores=signal_scores,
            signal_types=signal_types,
            intervention=intervention,
        )

        logger.info(
            "Risk assessed %s: %.1f (%s)%s",
            entity_id,
            result.composite_score,
            tier.value,
            f" → {intervention}" if intervention else "",
        )

        return result

    def assess_batch(
        self,
        entities: list[dict[str, Any]],
    ) -> list[RiskAssessment]:
        """Assess risk for multiple entities.

        Each dict must have 'entity_id' and 'scores' keys.

        Returns
        -------
        list[RiskAssessment]
        """
        results = []
        for entity in entities:
            if "entity_id" not in entity or "scores" not in entity:
                raise ValueError(
                    "Each entity dict must have 'entity_id' and 'scores' keys"
                )
            results.append(
                self.assess(
                    entity_id=entity["entity_id"],
                    scores=entity["scores"],
                )
            )

        logger.info("Assessed risk for %d entities in batch", len(results))
        return results
