"""Tests for plan lifecycle tracking (SU#634)."""

from __future__ import annotations

from datetime import date

import pytest

from siege_utilities.geo.plan_lifecycle import (
    DictPlanLifecycleProvider,
    EnactedBy,
    PlanLifecycleEvent,
    PlanLifecycleStatus,
    PlanLineage,
    PlanType,
    RedistrictingPlan,
    build_lineage,
    resolve_plan_at,
)


def _event(status, dt, **kw):
    return PlanLifecycleEvent(
        status=status,
        effective_date=date.fromisoformat(dt) if isinstance(dt, str) else dt,
        **kw,
    )


def _plan(plan_id="P1", state="TX", plan_type=PlanType.CONGRESSIONAL,
          events=None, enacted_date=None, **kw):
    return RedistrictingPlan(
        plan_id=plan_id,
        state=state,
        plan_type=plan_type,
        events=events or [],
        enacted_date=date.fromisoformat(enacted_date) if isinstance(enacted_date, str) else enacted_date,
        **kw,
    )


class TestPlanLifecycleStatus:
    def test_values(self):
        assert PlanLifecycleStatus.PROPOSED.value == "proposed"
        assert PlanLifecycleStatus.ENACTED.value == "enacted"
        assert PlanLifecycleStatus.STRUCK.value == "struck"

    def test_string_enum(self):
        assert PlanLifecycleStatus("enacted") == PlanLifecycleStatus.ENACTED


class TestPlanLifecycleEvent:
    def test_defaults(self):
        e = PlanLifecycleEvent()
        assert e.status == PlanLifecycleStatus.PROPOSED
        assert e.effective_date is None

    def test_fields(self):
        e = _event(PlanLifecycleStatus.ENACTED, "2022-01-01", source="legislation")
        assert e.effective_date == date(2022, 1, 1)
        assert e.source == "legislation"


class TestRedistrictingPlan:
    def test_defaults(self):
        p = RedistrictingPlan()
        assert p.current_status is None
        assert not p.is_terminal
        assert not p.is_active

    def test_current_status(self):
        p = _plan(events=[
            _event(PlanLifecycleStatus.PROPOSED, "2021-01-01"),
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
        ])
        assert p.current_status == PlanLifecycleStatus.ENACTED

    def test_latest_event_by_date(self):
        e1 = _event(PlanLifecycleStatus.PROPOSED, "2021-06-01")
        e2 = _event(PlanLifecycleStatus.ENACTED, "2022-01-01")
        p = _plan(events=[e2, e1])  # out of order
        assert p.latest_event.status == PlanLifecycleStatus.ENACTED

    def test_latest_event_undated_fallback(self):
        e1 = PlanLifecycleEvent(plan_id="P1", status=PlanLifecycleStatus.PROPOSED)
        e2 = PlanLifecycleEvent(plan_id="P1", status=PlanLifecycleStatus.ENACTED)
        p = _plan(events=[e1, e2])
        assert p.latest_event.status == PlanLifecycleStatus.ENACTED

    def test_is_terminal(self):
        p = _plan(events=[_event(PlanLifecycleStatus.STRUCK, "2023-01-01")])
        assert p.is_terminal

    def test_is_active(self):
        p = _plan(events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")])
        assert p.is_active

    def test_challenged_is_active(self):
        p = _plan(events=[
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
            _event(PlanLifecycleStatus.CHALLENGED, "2023-03-01"),
        ])
        assert p.is_active

    def test_superseded_is_terminal(self):
        p = _plan(events=[_event(PlanLifecycleStatus.SUPERSEDED, "2024-01-01")])
        assert p.is_terminal

    def test_status_at(self):
        p = _plan(events=[
            _event(PlanLifecycleStatus.PROPOSED, "2021-01-01"),
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
            _event(PlanLifecycleStatus.CHALLENGED, "2023-06-01"),
        ])
        assert p.status_at(date(2021, 6, 1)) == PlanLifecycleStatus.PROPOSED
        assert p.status_at(date(2022, 6, 1)) == PlanLifecycleStatus.ENACTED
        assert p.status_at(date(2023, 12, 1)) == PlanLifecycleStatus.CHALLENGED

    def test_status_at_before_any_event(self):
        p = _plan(events=[_event(PlanLifecycleStatus.PROPOSED, "2021-06-01")])
        assert p.status_at(date(2020, 1, 1)) is None

    def test_was_active_at(self):
        p = _plan(events=[
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
            _event(PlanLifecycleStatus.STRUCK, "2024-01-01"),
        ])
        assert p.was_active_at(date(2023, 1, 1))
        assert not p.was_active_at(date(2024, 6, 1))
        assert not p.was_active_at(date(2021, 1, 1))

    def test_to_dict(self):
        p = _plan(
            plan_id="TX-CD-2022",
            state="TX",
            enacted_date="2021-10-25",
            events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")],
        )
        d = p.to_dict()
        assert d["plan_id"] == "TX-CD-2022"
        assert d["enacted_date"] == "2021-10-25"
        assert d["current_status"] == "enacted"
        assert len(d["events"]) == 1

    def test_to_dict_no_events(self):
        d = RedistrictingPlan().to_dict()
        assert d["current_status"] is None
        assert d["events"] == []

    def test_supersedes_id(self):
        p = _plan(supersedes_id="OLD-PLAN")
        assert p.supersedes_id == "OLD-PLAN"


class TestPlanLineage:
    def test_empty(self):
        lin = PlanLineage()
        assert lin.current_plan is None
        assert lin.plan_at(date(2023, 1, 1)) is None

    def test_current_plan(self):
        p1 = _plan(plan_id="P1", events=[
            _event(PlanLifecycleStatus.ENACTED, "2012-01-01"),
            _event(PlanLifecycleStatus.SUPERSEDED, "2022-01-01"),
        ])
        p2 = _plan(plan_id="P2", events=[
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
        ])
        lin = PlanLineage(plans=[p1, p2])
        assert lin.current_plan.plan_id == "P2"

    def test_plan_at(self):
        p1 = _plan(plan_id="P1", events=[
            _event(PlanLifecycleStatus.ENACTED, "2012-01-01"),
            _event(PlanLifecycleStatus.SUPERSEDED, "2022-01-01"),
        ])
        p2 = _plan(plan_id="P2", events=[
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
        ])
        lin = PlanLineage(plans=[p1, p2])
        assert lin.plan_at(date(2015, 6, 1)).plan_id == "P1"
        assert lin.plan_at(date(2023, 6, 1)).plan_id == "P2"

    def test_no_active_plan(self):
        p = _plan(events=[_event(PlanLifecycleStatus.STRUCK, "2023-01-01")])
        lin = PlanLineage(plans=[p])
        assert lin.current_plan is None


class TestBuildLineage:
    def test_empty(self):
        lin = build_lineage([])
        assert lin.plans == []

    def test_sorts_by_enacted_date(self):
        p1 = _plan(plan_id="P1", enacted_date="2022-01-01")
        p2 = _plan(plan_id="P2", enacted_date="2012-01-01")
        lin = build_lineage([p1, p2])
        assert lin.plans[0].plan_id == "P2"
        assert lin.plans[1].plan_id == "P1"

    def test_sets_state_and_type(self):
        p = _plan(state="AL", plan_type=PlanType.STATE_SENATE)
        lin = build_lineage([p])
        assert lin.state == "AL"
        assert lin.plan_type == PlanType.STATE_SENATE


class TestDictProvider:
    def test_empty(self):
        prov = DictPlanLifecycleProvider()
        assert prov.get_plans("TX") == []
        assert prov.get_plan("X") is None

    def test_add_and_get(self):
        prov = DictPlanLifecycleProvider()
        p = _plan(plan_id="P1", state="TX")
        prov.add(p)
        assert prov.get_plan("P1") is p
        assert len(prov.get_plans("TX")) == 1

    def test_filter_by_type(self):
        prov = DictPlanLifecycleProvider()
        prov.add(_plan(plan_id="CD", state="TX", plan_type=PlanType.CONGRESSIONAL))
        prov.add(_plan(plan_id="SS", state="TX", plan_type=PlanType.STATE_SENATE))
        assert len(prov.get_plans("TX", plan_type=PlanType.CONGRESSIONAL)) == 1

    def test_case_insensitive_state(self):
        prov = DictPlanLifecycleProvider()
        prov.add(_plan(state="TX"))
        assert len(prov.get_plans("tx")) == 1


class TestResolvePlanAt:
    def test_basic(self):
        prov = DictPlanLifecycleProvider()
        p = _plan(
            plan_id="P1",
            state="TX",
            enacted_date="2022-01-01",
            events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")],
        )
        prov.add(p)
        result = resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2023, 1, 1))
        assert result.plan_id == "P1"

    def test_no_plans(self):
        prov = DictPlanLifecycleProvider()
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2023, 1, 1)) is None

    def test_supersession(self):
        prov = DictPlanLifecycleProvider()
        p1 = _plan(
            plan_id="P1", state="TX", enacted_date="2012-01-01",
            events=[
                _event(PlanLifecycleStatus.ENACTED, "2012-01-01"),
                _event(PlanLifecycleStatus.SUPERSEDED, "2022-01-01"),
            ],
        )
        p2 = _plan(
            plan_id="P2", state="TX", enacted_date="2022-01-01",
            supersedes_id="P1",
            events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")],
        )
        prov.add(p1)
        prov.add(p2)

        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2015, 1, 1)).plan_id == "P1"
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2023, 1, 1)).plan_id == "P2"

    def test_court_order_branch(self):
        prov = DictPlanLifecycleProvider()
        original = _plan(
            plan_id="AL-CD-2021", state="AL", enacted_date="2021-11-01",
            events=[
                _event(PlanLifecycleStatus.ENACTED, "2021-11-01"),
                _event(PlanLifecycleStatus.CHALLENGED, "2022-01-24",
                       court_case="Allen v. Milligan"),
                _event(PlanLifecycleStatus.STRUCK, "2023-06-08",
                       court_case="Allen v. Milligan"),
            ],
        )
        court_plan = _plan(
            plan_id="AL-CD-2023-COURT", state="AL", enacted_date="2023-10-05",
            enacted_by=EnactedBy.COURT,
            supersedes_id="AL-CD-2021",
            court_case="Allen v. Milligan",
            events=[_event(PlanLifecycleStatus.ENACTED, "2023-10-05")],
        )
        prov.add(original)
        prov.add(court_plan)

        assert resolve_plan_at(prov, "AL", PlanType.CONGRESSIONAL, date(2022, 6, 1)).plan_id == "AL-CD-2021"
        assert resolve_plan_at(prov, "AL", PlanType.CONGRESSIONAL, date(2024, 1, 1)).plan_id == "AL-CD-2023-COURT"
        assert resolve_plan_at(prov, "AL", PlanType.CONGRESSIONAL, date(2023, 8, 1)) is None
