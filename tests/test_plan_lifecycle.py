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


class TestPlanLifecycleResolutionRegressions:
    @pytest.mark.parametrize("when", [date(2023, 3, 1), date(2023, 6, 1)])
    def test_stayed_plan_is_not_in_effect(self, when):
        p = _plan(enacted_date="2022-01-01", events=[
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
            _event(PlanLifecycleStatus.STAYED, "2023-03-01"),
        ])
        prov = DictPlanLifecycleProvider()
        prov.add(p)
        lineage = build_lineage([p])

        assert p.status_at(when) == PlanLifecycleStatus.STAYED
        assert not p.was_active_at(when)
        assert not p.is_active
        assert lineage.current_plan is None
        assert lineage.plan_at(when) is None
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, when) is None

    def test_stayed_successor_falls_back_to_active_challenged_plan(self):
        original = _plan(plan_id="ORIGINAL", enacted_date="2022-01-01", events=[
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
            _event(PlanLifecycleStatus.CHALLENGED, "2022-06-01"),
        ])
        successor = _plan(
            plan_id="SUCCESSOR", enacted_date="2023-01-01",
            supersedes_id=original.plan_id, enacted_by=EnactedBy.COURT,
            events=[
                _event(PlanLifecycleStatus.ENACTED, "2023-01-01"),
                _event(PlanLifecycleStatus.STAYED, "2023-03-01"),
            ],
        )
        prov = DictPlanLifecycleProvider()
        prov.add(successor)
        prov.add(original)
        lineage = build_lineage([successor, original])
        when = date(2023, 3, 1)

        assert original.status_at(when) == PlanLifecycleStatus.CHALLENGED
        assert original.was_active_at(when)
        assert original.is_active
        assert lineage.plan_at(date(2023, 2, 1)) is successor
        assert lineage.plan_at(when) is original
        assert lineage.current_plan is original
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, when) is original

    @pytest.mark.parametrize("when", [date(2022, 1, 1), date(2023, 1, 1)])
    def test_same_day_adoption_and_enactment_are_in_effect(self, when):
        p = _plan(enacted_date="2022-01-01", events=[
            _event(PlanLifecycleStatus.ADOPTED, "2022-01-01"),
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
        ])
        prov = DictPlanLifecycleProvider()
        prov.add(p)
        lineage = build_lineage([p])

        assert p.status_at(when) == PlanLifecycleStatus.ENACTED
        assert p.was_active_at(when)
        assert p.is_active
        assert lineage.current_plan is p
        assert lineage.plan_at(when) is p
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, when) is p

    @pytest.mark.parametrize("earlier,later", [
        ("proposed", "adopted"),
        ("adopted", "enacted"),
        ("enacted", "challenged"),
        ("challenged", "stayed"),
        ("stayed", "struck"),
        ("struck", "superseded"),
        ("superseded", "expired"),
    ])
    @pytest.mark.parametrize("reverse_events", [False, True])
    @pytest.mark.parametrize("query", ["latest_event", "status_at"])
    def test_same_day_stage_order(self, earlier, later, reverse_events, query):
        when = date(2022, 1, 1)
        advanced = _event(PlanLifecycleStatus(later), when)
        events = [_event(PlanLifecycleStatus(earlier), when), advanced]
        p = _plan(events=events[::-1] if reverse_events else events)

        if query == "latest_event":
            assert p.latest_event is advanced
        else:
            assert p.status_at(when) == advanced.status

    def test_later_date_takes_priority_over_stage(self):
        reinstated = _event(PlanLifecycleStatus.ENACTED, "2023-01-01")
        p = _plan(events=[
            reinstated,
            _event(PlanLifecycleStatus.STAYED, "2022-06-01"),
            _event(PlanLifecycleStatus.ENACTED, "2022-01-01"),
        ])
        prov = DictPlanLifecycleProvider()
        prov.add(p)
        when = date(2023, 1, 1)

        assert p.status_at(date(2022, 3, 1)) == PlanLifecycleStatus.ENACTED
        assert p.status_at(date(2022, 6, 1)) == PlanLifecycleStatus.STAYED
        assert p.status_at(when) == PlanLifecycleStatus.ENACTED
        assert p.latest_event is reinstated
        assert p.was_active_at(when)
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, when) is p

    def test_single_event_timeline_is_unchanged(self):
        enacted = _event(PlanLifecycleStatus.ENACTED, "2022-01-01")
        p = _plan(events=[enacted])
        prov = DictPlanLifecycleProvider()
        prov.add(p)

        assert p.latest_event is enacted
        assert p.status_at(date(2021, 12, 31)) is None
        assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2021, 12, 31)) is None
        for when in (date(2022, 1, 1), date(2023, 1, 1)):
            assert p.status_at(when) == PlanLifecycleStatus.ENACTED
            assert p.was_active_at(when)
            assert build_lineage([p]).plan_at(when) is p
            assert resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, when) is p


# ── Error-path tests ──────────────────────────────────────────────────


class TestBuildLineageEmpty:
    """build_lineage() with empty plans list returns an empty lineage."""

    def test_empty_plans_returns_empty_lineage(self):
        lin = build_lineage([])
        assert lin.plans == []
        assert lin.state == ""
        assert lin.plan_type == PlanType.CONGRESSIONAL
        assert lin.current_plan is None


class TestBuildLineageMissingEnactedDate:
    """build_lineage() with plans that have no enacted_date."""

    def test_no_enacted_date_sorts_to_beginning(self):
        # Plans without enacted_date get date.min as sort key
        p1 = _plan(plan_id="P1", enacted_date=None)
        p2 = _plan(plan_id="P2", enacted_date="2022-01-01")
        lin = build_lineage([p2, p1])
        # None enacted_date maps to date.min, so P1 sorts first
        assert lin.plans[0].plan_id == "P1"
        assert lin.plans[1].plan_id == "P2"

    def test_all_none_enacted_dates(self):
        p1 = _plan(plan_id="A", enacted_date=None)
        p2 = _plan(plan_id="B", enacted_date=None)
        lin = build_lineage([p1, p2])
        assert len(lin.plans) == 2
        # Both have date.min as key, so order is stable
        assert lin.state == "TX"


class TestResolvePlanAtBeforeAnyPlan:
    """resolve_plan_at() with a date before any plan existed returns None."""

    def test_date_before_all_plans_returns_none(self):
        prov = DictPlanLifecycleProvider()
        p = _plan(
            plan_id="P1",
            state="TX",
            enacted_date="2022-01-01",
            events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")],
        )
        prov.add(p)
        result = resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2000, 1, 1))
        assert result is None


class TestResolvePlanAtAfterAllExpired:
    """resolve_plan_at() with a date after all plans expired returns None."""

    def test_date_after_all_expired_returns_none(self):
        prov = DictPlanLifecycleProvider()
        p = _plan(
            plan_id="P1",
            state="TX",
            enacted_date="2012-01-01",
            events=[
                _event(PlanLifecycleStatus.ENACTED, "2012-01-01"),
                _event(PlanLifecycleStatus.EXPIRED, "2022-01-01"),
            ],
        )
        prov.add(p)
        result = resolve_plan_at(prov, "TX", PlanType.CONGRESSIONAL, date(2025, 1, 1))
        assert result is None


class TestPlanLineageDuplicateIds:
    """PlanLineage with duplicate plan IDs in the list."""

    def test_duplicate_plan_ids_in_lineage(self):
        # build_lineage uses a dict keyed by plan_id, so duplicates
        # overwrite earlier entries in by_id (though sorted_plans keeps all)
        p1 = _plan(
            plan_id="DUP",
            state="TX",
            enacted_date="2012-01-01",
            events=[_event(PlanLifecycleStatus.ENACTED, "2012-01-01")],
        )
        p2 = _plan(
            plan_id="DUP",
            state="TX",
            enacted_date="2022-01-01",
            events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")],
        )
        lin = build_lineage([p1, p2])
        # Both plans appear in the lineage (sorted by enacted_date)
        assert len(lin.plans) == 2
        assert lin.plans[0].enacted_date == date(2012, 1, 1)
        assert lin.plans[1].enacted_date == date(2022, 1, 1)

    def test_duplicate_ids_current_plan_is_latest_active(self):
        p1 = _plan(
            plan_id="DUP",
            state="TX",
            enacted_date="2012-01-01",
            events=[
                _event(PlanLifecycleStatus.ENACTED, "2012-01-01"),
                _event(PlanLifecycleStatus.SUPERSEDED, "2022-01-01"),
            ],
        )
        p2 = _plan(
            plan_id="DUP",
            state="TX",
            enacted_date="2022-01-01",
            events=[_event(PlanLifecycleStatus.ENACTED, "2022-01-01")],
        )
        lin = build_lineage([p1, p2])
        assert lin.current_plan is not None
        assert lin.current_plan.enacted_date == date(2022, 1, 1)
