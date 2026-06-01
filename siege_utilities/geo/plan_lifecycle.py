"""Redistricting plan lifecycle tracking.

Models the lifecycle of redistricting plans: proposed -> adopted ->
enacted -> challenged -> stayed/struck -> superseded. Supports
court-order branching and temporal queries ("what plan was in effect
for TX congress on 2023-09-15?").
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

log = logging.getLogger(__name__)

__all__ = [
    "ACTIVE_STATUSES",
    "DictPlanLifecycleProvider",
    "EnactedBy",
    "PlanLifecycleEvent",
    "PlanLifecycleProvider",
    "PlanLifecycleStatus",
    "PlanLineage",
    "PlanType",
    "RedistrictingPlan",
    "TERMINAL_STATUSES",
    "build_lineage",
    "resolve_plan_at",
]


class PlanLifecycleStatus(str, Enum):
    """Status in the lifecycle of a redistricting plan."""

    PROPOSED = "proposed"
    ADOPTED = "adopted"
    ENACTED = "enacted"
    CHALLENGED = "challenged"
    STAYED = "stayed"
    STRUCK = "struck"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class PlanType(str, Enum):
    """Type of redistricting plan."""

    CONGRESSIONAL = "congressional"
    STATE_SENATE = "state_senate"
    STATE_HOUSE = "state_house"


class EnactedBy(str, Enum):
    """Authority that enacted the plan."""

    LEGISLATURE = "legislature"
    COMMISSION = "commission"
    COURT = "court"
    SPECIAL_MASTER = "special_master"


TERMINAL_STATUSES = frozenset({
    PlanLifecycleStatus.STRUCK,
    PlanLifecycleStatus.SUPERSEDED,
    PlanLifecycleStatus.EXPIRED,
})

ACTIVE_STATUSES = frozenset({
    PlanLifecycleStatus.ENACTED,
    PlanLifecycleStatus.CHALLENGED,
    PlanLifecycleStatus.STAYED,
})


@dataclass
class PlanLifecycleEvent:
    """A lifecycle transition for a redistricting plan.

    Attributes:
        plan_id: Identifier of the plan this event belongs to.
        status: New lifecycle status after this event.
        effective_date: When this status took effect.
        source: What triggered the transition (legislation, court order, etc.).
        notes: Human-readable description.
        court_case: Case citation if court-ordered.
    """

    plan_id: str = ""
    status: PlanLifecycleStatus = PlanLifecycleStatus.PROPOSED
    effective_date: Optional[date] = None
    source: str = ""
    notes: str = ""
    court_case: str = ""


@dataclass
class RedistrictingPlan:
    """A redistricting plan with lifecycle events.

    Attributes:
        plan_id: Unique identifier.
        state: Two-letter state abbreviation.
        plan_type: Congressional, state senate, or state house.
        plan_name: Official name or identifier.
        enacted_by: Authority that enacted the plan.
        enacted_date: When the plan was enacted.
        supersedes_id: ID of the plan this one replaces.
        court_case: Court case citation if court-ordered.
        events: Ordered lifecycle events.
    """

    plan_id: str = ""
    state: str = ""
    plan_type: PlanType = PlanType.CONGRESSIONAL
    plan_name: str = ""
    enacted_by: EnactedBy = EnactedBy.LEGISLATURE
    enacted_date: Optional[date] = None
    supersedes_id: Optional[str] = None
    court_case: str = ""
    events: list[PlanLifecycleEvent] = field(default_factory=list)

    @property
    def current_status(self) -> Optional[PlanLifecycleStatus]:
        if not self.events:
            return None
        return self.latest_event.status

    @property
    def latest_event(self) -> Optional[PlanLifecycleEvent]:
        if not self.events:
            return None
        dated = [e for e in self.events if e.effective_date is not None]
        if not dated:
            return self.events[-1]
        return max(dated, key=lambda e: e.effective_date)

    @property
    def is_terminal(self) -> bool:
        status = self.current_status
        return status is not None and status in TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        status = self.current_status
        return status is not None and status in ACTIVE_STATUSES

    def status_at(self, when: date) -> Optional[PlanLifecycleStatus]:
        applicable = [
            e for e in self.events
            if e.effective_date is not None and e.effective_date <= when
        ]
        if not applicable:
            return None
        return max(applicable, key=lambda e: e.effective_date).status

    def was_active_at(self, when: date) -> bool:
        status = self.status_at(when)
        return status is not None and status in ACTIVE_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "state": self.state,
            "plan_type": self.plan_type.value,
            "plan_name": self.plan_name,
            "enacted_by": self.enacted_by.value,
            "enacted_date": self.enacted_date.isoformat() if self.enacted_date else None,
            "supersedes_id": self.supersedes_id,
            "court_case": self.court_case,
            "current_status": self.current_status.value if self.current_status else None,
            "events": [
                {
                    "status": e.status.value,
                    "effective_date": e.effective_date.isoformat() if e.effective_date else None,
                    "source": e.source,
                    "notes": e.notes,
                    "court_case": e.court_case,
                }
                for e in self.events
            ],
        }


@dataclass
class PlanLineage:
    """Chain of plans linked by supersession.

    Attributes:
        plans: Plans in chronological order (oldest first).
        state: State abbreviation.
        plan_type: Type of plan.
    """

    plans: list[RedistrictingPlan] = field(default_factory=list)
    state: str = ""
    plan_type: PlanType = PlanType.CONGRESSIONAL

    @property
    def current_plan(self) -> Optional[RedistrictingPlan]:
        active = [p for p in self.plans if p.is_active]
        if active:
            return active[-1]
        return None

    def plan_at(self, when: date) -> Optional[RedistrictingPlan]:
        candidates = [p for p in self.plans if p.was_active_at(when)]
        if not candidates:
            return None
        return candidates[-1]


class PlanLifecycleProvider(abc.ABC):
    """Protocol for querying redistricting plan lifecycle data."""

    @abc.abstractmethod
    def get_plans(
        self,
        state: str,
        plan_type: Optional[PlanType] = None,
    ) -> list[RedistrictingPlan]:
        """Get all plans for a state, optionally filtered by type."""

    @abc.abstractmethod
    def get_plan(self, plan_id: str) -> Optional[RedistrictingPlan]:
        """Get a single plan by ID."""


class DictPlanLifecycleProvider(PlanLifecycleProvider):
    """In-memory plan lifecycle provider for testing."""

    def __init__(self):
        self._plans: dict[str, RedistrictingPlan] = {}

    def add(self, plan: RedistrictingPlan):
        self._plans[plan.plan_id] = plan

    def get_plans(
        self,
        state: str,
        plan_type: Optional[PlanType] = None,
    ) -> list[RedistrictingPlan]:
        results = [
            p for p in self._plans.values()
            if p.state.upper() == state.upper()
        ]
        if plan_type is not None:
            results = [p for p in results if p.plan_type == plan_type]
        return results

    def get_plan(self, plan_id: str) -> Optional[RedistrictingPlan]:
        return self._plans.get(plan_id)


def build_lineage(
    plans: list[RedistrictingPlan],
) -> PlanLineage:
    """Build a supersession lineage from a list of related plans.

    Plans are ordered by enacted_date.

    Args:
        plans: Plans that form a lineage (same state + type).
    """
    if not plans:
        return PlanLineage()

    sorted_plans = sorted(
        plans,
        key=lambda p: p.enacted_date or date.min,
    )

    return PlanLineage(
        plans=sorted_plans,
        state=sorted_plans[0].state,
        plan_type=sorted_plans[0].plan_type,
    )


def resolve_plan_at(
    provider: PlanLifecycleProvider,
    state: str,
    plan_type: PlanType,
    when: date,
) -> Optional[RedistrictingPlan]:
    """Resolve which plan was in effect at a given date.

    Queries the provider for all plans of the given state and type,
    then finds the one that was active at the specified date.

    Args:
        provider: Source for plan lifecycle data.
        state: Two-letter state abbreviation.
        plan_type: Type of plan to resolve.
        when: Date to query.

    Returns:
        The RedistrictingPlan that was in effect, or None.
    """
    plans = provider.get_plans(state, plan_type)
    if not plans:
        return None

    lineage = build_lineage(plans)
    return lineage.plan_at(when)
