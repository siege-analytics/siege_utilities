"""Date-resolvable registry of redistricting plans.

Consumers register :class:`RedistrictingPlan` instances and then ask
"which plan was active in Alabama for congressional districts on
2023-09-15?" — the registry returns the right plan (or raises if there
is overlap or a gap, depending on strictness).

The registry is in-memory by design. File-backed plan catalogs (RDH
manifest, NCSL plan registry) are loaded *into* an instance via
:meth:`PlanRegistry.register_plan` at consumer startup; the resolver
itself doesn't know about disk.

A module-level singleton (:func:`get_default_plan_registry`) is provided
for the common case where one process has one global view of plans.
Consumers that need isolation (multi-tenant, tests) instantiate their
own.
"""

from __future__ import annotations

import datetime as _dt
import logging
import threading
from typing import Dict, Iterable, List, Optional, Tuple

from .models import PlanDistrict, RedistrictingPlan

__all__ = [
    "PlanRegistry",
    "PlanResolutionError",
    "PlanOverlapError",
    "get_default_plan_registry",
]

log = logging.getLogger(__name__)


class PlanResolutionError(LookupError):
    """No plan covers the requested (state, district_type, date) tuple."""


class PlanOverlapError(ValueError):
    """Two registered plans cover the same date for the same state+type.

    Raised by :meth:`PlanRegistry.resolve_plan_at_date` when the registry
    finds more than one match in strict mode. Caller can rerun with
    ``strict=False`` to get the first match (and a warning), or fix the
    underlying plan data.
    """


_StateTypeKey = Tuple[str, str]


class PlanRegistry:
    """Stores redistricting plans and resolves them by date.

    Plans are keyed by ``(state_fips, district_type)``. Within a key,
    plans should be temporally non-overlapping; the registry detects
    overlap at registration time (warn) and at resolution time (raise
    in strict mode).

    Thread-safe for concurrent readers; mutation under a lock.
    """

    def __init__(self) -> None:
        self._plans: Dict[_StateTypeKey, List[RedistrictingPlan]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register_plan(self, plan: RedistrictingPlan) -> None:
        """Add *plan* to the registry.

        Logs a warning if it overlaps an already-registered plan for the
        same ``(state_fips, district_type)``. Does **not** raise on
        overlap — registration is forgiving so consumers can load
        partial data; resolution is the strict gate.
        """
        key = (plan.state_fips, plan.district_type)
        with self._lock:
            existing = self._plans.setdefault(key, [])
            for other in existing:
                if _spans_overlap(plan, other):
                    log.warning(
                        "Plan overlap detected for %s/%s: %r vs %r",
                        plan.state_fips, plan.district_type,
                        plan.plan_name, other.plan_name,
                    )
            existing.append(plan)
            existing.sort(key=lambda p: p.effective_from)

    def register_plans(self, plans: Iterable[RedistrictingPlan]) -> None:
        """Bulk-register an iterable of plans."""
        for p in plans:
            self.register_plan(p)

    def clear(self) -> None:
        """Remove all registered plans (mostly for tests)."""
        with self._lock:
            self._plans.clear()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def plans_for_state(
        self,
        state_fips: str,
        district_type: str,
    ) -> List[RedistrictingPlan]:
        """Return all registered plans for *state_fips* / *district_type*.

        Sorted by ``effective_from`` ascending. Empty list if none.
        """
        return list(self._plans.get((state_fips, district_type), ()))

    def resolve_plan_at_date(
        self,
        state_fips: str,
        district_type: str,
        when: _dt.date,
        *,
        strict: bool = True,
    ) -> RedistrictingPlan:
        """Find the plan in effect for *state_fips* / *district_type* on *when*.

        Args:
            state_fips: 2-char state FIPS.
            district_type: ``"cd"``, ``"sldu"``, ``"sldl"``, etc.
            when: The date to resolve.
            strict: If ``True`` (default), raise :class:`PlanOverlapError`
                when more than one plan covers *when*. If ``False``, log
                a warning and return the most recently *enacted* one
                (latest ``effective_from``) — appropriate when court
                interim/final pairs both technically cover the same day.

        Raises:
            :class:`PlanResolutionError`: No plan covers the date.
            :class:`PlanOverlapError`: Multiple plans cover the date and
                ``strict=True``.
        """
        candidates = [
            p for p in self.plans_for_state(state_fips, district_type)
            if p.covers_date(when)
        ]
        if not candidates:
            raise PlanResolutionError(
                f"No registered plan covers {state_fips}/{district_type} on {when}. "
                f"Registered plans: "
                f"{[p.plan_name for p in self.plans_for_state(state_fips, district_type)]}"
            )
        if len(candidates) > 1:
            if strict:
                raise PlanOverlapError(
                    f"{len(candidates)} plans cover {state_fips}/{district_type} on {when}: "
                    f"{[p.plan_name for p in candidates]}. "
                    "Resolve overlap in source data, or call with strict=False."
                )
            log.warning(
                "Plan overlap on %s for %s/%s: %s — taking most-recently-enacted",
                when, state_fips, district_type,
                [p.plan_name for p in candidates],
            )
            candidates.sort(key=lambda p: p.effective_from)
        return candidates[-1]

    def resolve_district_at_date(
        self,
        state_fips: str,
        district_type: str,
        district_id: str,
        when: _dt.date,
        *,
        strict: bool = True,
    ) -> PlanDistrict:
        """Find the specific district covering *when*.

        Convenience wrapper: resolves the plan, then looks up the
        district by id. Raises :class:`PlanResolutionError` if the plan
        does not contain *district_id*.
        """
        plan = self.resolve_plan_at_date(
            state_fips, district_type, when, strict=strict,
        )
        district = plan.district(district_id)
        if district is None:
            raise PlanResolutionError(
                f"Plan {plan.plan_name} contains no district {district_id!r}. "
                f"Districts: {[d.district_id for d in plan.districts]}"
            )
        return district


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_registry: Optional[PlanRegistry] = None
_default_registry_lock = threading.Lock()


def get_default_plan_registry() -> PlanRegistry:
    """Return the process-global default :class:`PlanRegistry`.

    Lazily instantiated on first call. Consumers that need isolation
    (multi-tenant code, unit tests) should instantiate
    :class:`PlanRegistry` directly instead.
    """
    global _default_registry
    if _default_registry is None:
        with _default_registry_lock:
            if _default_registry is None:
                _default_registry = PlanRegistry()
    return _default_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spans_overlap(a: RedistrictingPlan, b: RedistrictingPlan) -> bool:
    """Inclusive interval overlap; ``effective_to=None`` means open-ended."""
    a_to = a.effective_to or _dt.date.max
    b_to = b.effective_to or _dt.date.max
    return a.effective_from <= b_to and b.effective_from <= a_to
