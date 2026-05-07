"""Redistricting plan resolution by date (issue #361).

Models a redistricting plan as a named, dated artifact and exposes a
:class:`PlanRegistry` that resolves the plan in effect for a
``(state_fips, district_type, date)`` tuple. Replaces the
decade-keyed ``CensusVintageConfig`` for callers that need to handle
mid-cycle court orders (Alabama 2023, Louisiana 2024, etc.).

This is the foundational module — it has no consumer code yet.
Downstream PRs wire ``RDHProvider`` and ``assign_boundaries`` to
consult the registry.
"""

from .models import PlanAuthority, PlanDistrict, RedistrictingPlan
from .registry import (
    PlanOverlapError,
    PlanRegistry,
    PlanResolutionError,
    get_default_plan_registry,
)

__all__ = [
    "PlanAuthority",
    "PlanDistrict",
    "RedistrictingPlan",
    "PlanRegistry",
    "PlanResolutionError",
    "PlanOverlapError",
    "get_default_plan_registry",
]
