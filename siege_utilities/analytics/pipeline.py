"""
Pipeline coverage and velocity metrics.

Composable pipeline health metrics: coverage ratio, stage count ratios,
velocity, aging alerts, and concentration risk.
"""

from __future__ import annotations

import logging
import math
import warnings
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StageMetrics:
    """Metrics for a single pipeline stage."""

    stage: str
    count: int
    total_value: float
    avg_value: float


@dataclass(frozen=True)
class StageRatio:
    """Ratio of independent counts in consecutive stages.

    This snapshot has no stage-transition history or shared cohort. The
    ratio is next-stage count / current-stage count, can exceed 1.0, and
    is None when the current stage is empty. It is not a conversion rate.
    """

    from_stage: str
    to_stage: str
    ratio: float | None
    from_count: int
    to_count: int


@dataclass(frozen=True)
class VelocityMetrics:
    """Time-in-stage metrics."""

    stage: str
    avg_days: float
    max_days: float
    aging_items: list[str]


@dataclass(frozen=True)
class ConcentrationAlert:
    """Alert when a single item dominates the pipeline."""

    item_id: str
    share: float
    stage: str
    value: float


@dataclass(frozen=True)
class PipelineReport:
    """Complete pipeline health report."""

    coverage_ratio: float | None
    stage_metrics: list[StageMetrics]
    stage_ratios: list[StageRatio]
    velocity: list[VelocityMetrics]
    concentration_alerts: list[ConcentrationAlert]
    total_value: float
    target: float | None


@dataclass(frozen=True)
class PipelineItem:
    """A single item in the pipeline.

    Parameters
    ----------
    item_id : str
        Unique identifier.
    stage : str
        Current pipeline stage.
    value : float
        Item value (dollars, record count, etc.).
    entered_stage : datetime | None
        When the item entered this stage. Required for velocity metrics.
    """

    item_id: str
    stage: str
    value: float
    entered_stage: datetime | None = None

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty")
        if not self.stage:
            raise ValueError("stage must not be empty")
        if self.value < 0:
            raise ValueError(
                f"value must be non-negative, got {self.value}"
            )


class PipelineAnalyzer:
    """Pipeline health metrics engine.

    Parameters
    ----------
    stages : list[str]
        Ordered stage names (first = entry, last = exit).
    target : float | None
        Target pipeline value for coverage ratio calculation.
    aging_threshold : float
        Maximum days in a stage before an aging alert (default 30 days).
        Items older than this bound trigger alerts, even in a one-item stage.
        This absolute bound does not depend on the stage's sample average.
    concentration_threshold : float
        Maximum single-item share before alert (default 0.40 = 40%).

    Raises
    ------
    ValueError
        If stages is empty or thresholds are invalid.
    """

    def __init__(
        self,
        stages: list[str],
        target: float | None = None,
        aging_threshold: float = 30.0,
        concentration_threshold: float = 0.40,
    ) -> None:
        if not stages:
            raise ValueError("At least one stage is required")
        if len(stages) != len(set(stages)):
            raise ValueError("Stage names must be unique")
        if not math.isfinite(aging_threshold) or aging_threshold <= 0:
            raise ValueError(
                f"aging_threshold must be positive and finite, got {aging_threshold}"
            )
        if not (0 < concentration_threshold <= 1):
            raise ValueError(
                f"concentration_threshold must be in (0, 1], "
                f"got {concentration_threshold}"
            )

        self._stages = list(stages)
        self._target = target
        self._aging_threshold = aging_threshold
        self._concentration_threshold = concentration_threshold

        logger.info(
            "PipelineAnalyzer initialized with %d stages: %s",
            len(self._stages),
            " → ".join(self._stages),
        )

    def analyze(
        self,
        items: list[PipelineItem],
        *,
        as_of: datetime | None = None,
    ) -> PipelineReport:
        """Analyze pipeline health.

        Parameters
        ----------
        items : list[PipelineItem]
            Items currently in the pipeline.
        as_of : datetime, optional
            Reference time for velocity calculation.
            Defaults to datetime.now().

        Returns
        -------
        PipelineReport

        Raises
        ------
        ValueError
            If items is empty or contains unknown stages.
        """
        if not items:
            raise ValueError("At least one pipeline item is required")

        for item in items:
            if item.stage not in self._stages:
                raise ValueError(
                    f"Unknown stage {item.stage!r} for item {item.item_id!r}. "
                    f"Valid stages: {self._stages}"
                )

        if as_of is None:
            as_of = datetime.now()

        stage_metrics = self._compute_stage_metrics(items)
        stage_ratios = self._compute_stage_ratios(stage_metrics)
        velocity = self._compute_velocity(items, as_of)
        concentration_alerts = self._check_concentration(items)
        total_value = sum(item.value for item in items)

        coverage_ratio = None
        if self._target is not None and self._target > 0:
            coverage_ratio = round(total_value / self._target, 2)

        report = PipelineReport(
            coverage_ratio=coverage_ratio,
            stage_metrics=stage_metrics,
            stage_ratios=stage_ratios,
            velocity=velocity,
            concentration_alerts=concentration_alerts,
            total_value=total_value,
            target=self._target,
        )

        logger.info(
            "Pipeline analysis: %d items, total=%.0f%s, %d concentration alerts",
            len(items),
            total_value,
            f", coverage={coverage_ratio:.1f}x" if coverage_ratio else "",
            len(concentration_alerts),
        )

        return report

    def _compute_stage_metrics(
        self,
        items: list[PipelineItem],
    ) -> list[StageMetrics]:
        stage_items: dict[str, list[PipelineItem]] = {
            s: [] for s in self._stages
        }
        for item in items:
            stage_items[item.stage].append(item)

        results = []
        for stage in self._stages:
            items_in_stage = stage_items[stage]
            count = len(items_in_stage)
            total = sum(i.value for i in items_in_stage)
            avg = total / count if count > 0 else 0.0
            results.append(StageMetrics(
                stage=stage,
                count=count,
                total_value=round(total, 2),
                avg_value=round(avg, 2),
            ))

        return results

    def _compute_stage_ratios(
        self,
        stage_metrics: list[StageMetrics],
    ) -> list[StageRatio]:
        ratios = []
        for i in range(len(stage_metrics) - 1):
            from_stage = stage_metrics[i]
            to_stage = stage_metrics[i + 1]
            if from_stage.count > 0:
                ratio = round(to_stage.count / from_stage.count, 4)
            else:
                ratio = None
            ratios.append(StageRatio(
                from_stage=from_stage.stage,
                to_stage=to_stage.stage,
                ratio=ratio,
                from_count=from_stage.count,
                to_count=to_stage.count,
            ))
        return ratios

    def _compute_velocity(
        self,
        items: list[PipelineItem],
        as_of: datetime,
    ) -> list[VelocityMetrics]:
        has_timestamps = any(i.entered_stage is not None for i in items)
        if not has_timestamps:
            warnings.warn(
                "No items have entered_stage timestamps; "
                "velocity metrics skipped. Provide entered_stage "
                "for time-in-stage analysis.",
                UserWarning,
                stacklevel=2,
            )
            return []

        stage_durations: dict[str, list[tuple[str, float]]] = {
            s: [] for s in self._stages
        }
        for item in items:
            if item.entered_stage is None:
                continue
            days = (as_of - item.entered_stage).total_seconds() / 86400
            stage_durations[item.stage].append((item.item_id, max(days, 0)))

        results = []
        for stage in self._stages:
            durations = stage_durations[stage]
            if not durations:
                continue
            days_list = [d for _, d in durations]
            avg = sum(days_list) / len(days_list)
            max_d = max(days_list)
            aging = [
                item_id for item_id, d in durations if d > self._aging_threshold
            ]
            results.append(VelocityMetrics(
                stage=stage,
                avg_days=round(avg, 1),
                max_days=round(max_d, 1),
                aging_items=aging,
            ))

        return results

    def _check_concentration(
        self,
        items: list[PipelineItem],
    ) -> list[ConcentrationAlert]:
        total = sum(i.value for i in items)
        if total == 0:
            return []

        alerts = []
        for item in items:
            share = item.value / total
            if share > self._concentration_threshold:
                alerts.append(ConcentrationAlert(
                    item_id=item.item_id,
                    share=round(share, 4),
                    stage=item.stage,
                    value=item.value,
                ))

        return alerts
