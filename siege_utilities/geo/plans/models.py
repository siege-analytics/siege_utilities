"""Data models for redistricting plans and their districts.

A *plan* is a named, dated cartographic artifact: e.g. "Alabama 2023
court-interim congressional map". Plans replace each other over time —
the same state has multiple plans for the same district type within a
single decennial cycle when a court intervenes (Alabama 2022/2023,
Louisiana 2023/2024, New York 2022/2024, Georgia 2023/2024).

The existing ``CensusVintageConfig`` in this package keys boundaries by
decade ("2010 → 2010-2019"), which cannot represent a donation made in
AL-7 in March 2023 vs the same address in September 2023 (different
geometry). These models give consumers a date-resolvable shape.

This module is the foundation of the redistricting-plan resolution
system (issue #361). The matching :mod:`siege_utilities.geo.plans.registry`
provides date-based lookup; downstream PRs wire ``RDHProvider`` and
``assign_boundaries`` to use it.
"""

from __future__ import annotations

import datetime as _dt
import enum
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

__all__ = [
    "PlanAuthority",
    "PlanDistrict",
    "RedistrictingPlan",
]


class PlanAuthority(str, enum.Enum):
    """Who drew the plan — legally meaningful for citation and audit."""

    #: Enacted by the state legislature (the default cycle path).
    LEGISLATURE = "legislature"
    #: Court-imposed map (interim or final).
    COURT = "court"
    #: Independent or politician redistricting commission.
    COMMISSION = "commission"
    #: Pre-decennial-shift baseline; used by the legacy resolver when no
    #: explicit plan covers a date.
    DEFAULT = "default"


@dataclass(frozen=True)
class PlanDistrict:
    """A single district within a redistricting plan.

    All boundaries fields are optional — many consumers only need the
    *identity* (which plan, which district, valid when) and resolve the
    geometry separately via a :class:`BoundaryProvider`.

    Attributes:
        state_fips: 2-character state FIPS code (e.g. ``"01"`` for Alabama).
        district_type: Lowercase district class — ``"cd"``, ``"sldu"``,
            ``"sldl"``, ``"county_commission"``, etc. Match the keys used
            by ``CensusTIGERProvider``.
        district_id: District identifier *within* the plan. ``"7"`` for
            AL-7, ``"01"`` for SLDU 1, etc. Stored as the string form so
            leading-zero district numbers (sometimes used by states) are
            preserved.
        plan_name: Stable, human-readable plan identifier
            (e.g. ``"AL_2023_CD_INTERIM"``). Conventional but not enforced.
        authority: Who drew the plan (see :class:`PlanAuthority`).
        effective_from: First date the district is in legal effect.
        effective_to: Last date the district is in legal effect, **or
            ``None`` for an open-ended plan (the currently active one)**.
        geometry_source: Optional pointer to the geometry — a URL, a local
            path, an RDH dataset slug, or any string the consuming
            ``BoundaryProvider`` understands. ``None`` is fine if callers
            only need identity resolution.
        notes: Free-text annotation (e.g. court docket, statute citation).
            Goes through to logs and audit trails verbatim.
    """

    state_fips: str
    district_type: str
    district_id: str
    plan_name: str
    authority: PlanAuthority
    effective_from: _dt.date
    effective_to: Optional[_dt.date] = None
    geometry_source: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError(
                f"PlanDistrict {self.plan_name}/{self.district_id}: "
                f"effective_to ({self.effective_to}) is before "
                f"effective_from ({self.effective_from})."
            )

    def covers_date(self, when: _dt.date) -> bool:
        """Return True iff *when* falls within this district's effective span.

        Half-open at the upper end: ``effective_to`` is inclusive (if the
        new plan starts the next day, encode that as
        ``effective_from = old_to + timedelta(days=1)``). This matches how
        court orders are typically written ("effective for elections on
        or after DATE") and avoids the off-by-one trap of half-open
        Python slices.
        """
        if when < self.effective_from:
            return False
        if self.effective_to is not None and when > self.effective_to:
            return False
        return True


@dataclass(frozen=True)
class RedistrictingPlan:
    """A full plan: a collection of districts plus plan-level metadata.

    The plan is the *unit* of court orders, statutes, and commission
    actions; the individual :class:`PlanDistrict` rows just decompose it
    for query convenience. ``effective_from`` / ``effective_to`` on the
    plan should match the values on its constituent districts.

    Attributes:
        plan_name: Same convention as :attr:`PlanDistrict.plan_name`.
        state_fips: 2-character state FIPS.
        district_type: ``"cd"``, ``"sldu"``, etc.
        authority: Who drew it.
        effective_from: First date the plan is in legal effect.
        effective_to: Last date in effect, or ``None`` if currently active.
        districts: Tuple of :class:`PlanDistrict` rows under this plan.
            A frozen tuple so the dataclass remains hashable.
        metadata: Free-form mapping for citation, source URLs, court
            docket numbers, etc. Not used for resolution — consumers can
            stuff whatever they want here.
    """

    plan_name: str
    state_fips: str
    district_type: str
    authority: PlanAuthority
    effective_from: _dt.date
    effective_to: Optional[_dt.date] = None
    districts: Tuple[PlanDistrict, ...] = field(default_factory=tuple)
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError(
                f"RedistrictingPlan {self.plan_name}: "
                f"effective_to ({self.effective_to}) is before "
                f"effective_from ({self.effective_from})."
            )
        # Validate that constituent districts are consistent.
        for d in self.districts:
            if d.plan_name != self.plan_name:
                raise ValueError(
                    f"RedistrictingPlan {self.plan_name}: district "
                    f"{d.district_id} has plan_name {d.plan_name!r}."
                )
            if d.state_fips != self.state_fips:
                raise ValueError(
                    f"RedistrictingPlan {self.plan_name}: district "
                    f"{d.district_id} has state_fips {d.state_fips!r}, "
                    f"plan has {self.state_fips!r}."
                )
            if d.district_type != self.district_type:
                raise ValueError(
                    f"RedistrictingPlan {self.plan_name}: district "
                    f"{d.district_id} has district_type {d.district_type!r}, "
                    f"plan has {self.district_type!r}."
                )

    def covers_date(self, when: _dt.date) -> bool:
        """Return True iff *when* falls within this plan's effective span."""
        if when < self.effective_from:
            return False
        if self.effective_to is not None and when > self.effective_to:
            return False
        return True

    def district(self, district_id: str) -> Optional[PlanDistrict]:
        """Find a district within this plan by id, or ``None``."""
        for d in self.districts:
            if d.district_id == district_id:
                return d
        return None
