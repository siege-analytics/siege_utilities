"""
Deterministic intervention mapping.

Rule-based signal-to-action mapping with priority ordering,
effectiveness tracking, and override support.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MappingRule:
    """A signal-to-action mapping rule.

    Parameters
    ----------
    signal : str
        The categorical input signal.
    action : str
        The recommended action.
    priority : int
        Lower number = higher priority. Used when multiple rules match.
    """

    signal: str
    action: str
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.signal or not self.signal.strip():
            raise ValueError("Signal must not be empty")
        if not self.action or not self.action.strip():
            raise ValueError("Action must not be empty")


@dataclass
class Outcome:
    """Recorded outcome for an intervention."""

    signal: str
    action: str
    success: bool
    overridden: bool = False
    override_reason: str | None = None


@dataclass(frozen=True)
class EffectivenessReport:
    """Effectiveness statistics for one action."""

    action: str
    total: int
    successes: int
    success_rate: float


class InterventionMapper:
    """Rule-based intervention mapping engine.

    Parameters
    ----------
    rules : list[MappingRule]
        Signal-to-action mapping rules.
    default_action : str | None
        Action for unmapped signals. If None, unmapped signals raise.
    strict : bool
        If True, unmapped signals raise ValueError. If False, warn
        and return default_action.

    Raises
    ------
    ValueError
        If rules is empty or strict=False without default_action.
    """

    def __init__(
        self,
        rules: list[MappingRule],
        default_action: str | None = None,
        strict: bool = True,
    ) -> None:
        if not rules:
            raise ValueError("At least one mapping rule is required")

        if not strict and default_action is None:
            raise ValueError(
                "default_action is required when strict=False"
            )

        if default_action is not None and not default_action.strip():
            raise ValueError("default_action must not be empty")

        sorted_rules = sorted(rules, key=lambda r: r.priority)
        self._rule_map: dict[str, str] = {}
        for rule in sorted_rules:
            if rule.signal not in self._rule_map:
                self._rule_map[rule.signal] = rule.action

        self._default_action = default_action
        self._strict = strict
        self._outcomes: list[Outcome] = []

        logger.info(
            "InterventionMapper initialized with %d rules (%d unique signals)",
            len(rules),
            len(self._rule_map),
        )

    @property
    def signals(self) -> list[str]:
        return sorted(self._rule_map.keys())

    def map(
        self,
        signal: str,
        *,
        override_action: str | None = None,
        override_reason: str | None = None,
    ) -> str:
        """Map a signal to an action.

        Parameters
        ----------
        signal : str
            The categorical input signal.
        override_action : str, optional
            Override the mapped action. Must include override_reason.
        override_reason : str, optional
            Reason for the override (mandatory when overriding).

        Returns
        -------
        str
            The recommended action.

        Raises
        ------
        ValueError
            If signal is unmapped and strict=True, or if override
            is given without a reason.
        """
        if override_action is not None and (
            not override_reason or not override_reason.strip()
        ):
            raise ValueError(
                "override_reason is required when providing override_action"
            )

        if override_action is not None:
            mapped_action = self._rule_map.get(signal)
            logger.info(
                "Override for signal %r: %r → %r (reason: %s)",
                signal,
                mapped_action,
                override_action,
                override_reason,
            )
            return override_action

        mapped_action = self._rule_map.get(signal)

        if mapped_action is None:
            if self._strict:
                raise ValueError(
                    f"Unmapped signal: {signal!r}. "
                    f"Known signals: {self.signals}"
                )
            warnings.warn(
                f"Unmapped signal {signal!r}; using default action "
                f"{self._default_action!r}",
                UserWarning,
                stacklevel=2,
            )
            mapped_action = self._default_action

        return mapped_action

    def record_outcome(
        self,
        signal: str,
        action: str,
        success: bool,
        *,
        overridden: bool = False,
        override_reason: str | None = None,
    ) -> None:
        """Record the outcome of an intervention.

        Parameters
        ----------
        signal : str
            The signal that triggered the intervention.
        action : str
            The action taken.
        success : bool
            Whether the intervention succeeded.
        overridden : bool
            Whether the action was an override.
        override_reason : str, optional
            Reason for override (required if overridden=True).

        Raises
        ------
        ValueError
            If overridden=True without override_reason.
        """
        if overridden and (not override_reason or not override_reason.strip()):
            raise ValueError(
                "override_reason is required when overridden=True"
            )

        outcome = Outcome(
            signal=signal,
            action=action,
            success=success,
            overridden=overridden,
            override_reason=override_reason,
        )
        self._outcomes.append(outcome)

        logger.info(
            "Outcome recorded: signal=%r action=%r success=%s%s",
            signal,
            action,
            success,
            f" (override: {override_reason})" if overridden else "",
        )

    def effectiveness(self) -> list[EffectivenessReport]:
        """Compute effectiveness per action.

        Returns
        -------
        list[EffectivenessReport]
            One entry per distinct action, sorted by success rate ascending.

        Raises
        ------
        ValueError
            If no outcomes have been recorded.
        """
        if not self._outcomes:
            raise ValueError("No outcomes recorded yet")

        action_stats: dict[str, tuple[int, int]] = {}
        for outcome in self._outcomes:
            total, successes = action_stats.get(outcome.action, (0, 0))
            total += 1
            if outcome.success:
                successes += 1
            action_stats[outcome.action] = (total, successes)

        reports = []
        for action, (total, successes) in action_stats.items():
            rate = successes / total if total > 0 else 0.0
            reports.append(EffectivenessReport(
                action=action,
                total=total,
                successes=successes,
                success_rate=round(rate, 4),
            ))

        reports.sort(key=lambda r: r.success_rate)
        return reports
