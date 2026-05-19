"""Tests for siege_utilities.geo.plans (issue #361)."""

from __future__ import annotations

import datetime as _dt

import pytest

from siege_utilities.geo.plans import (
    PlanAuthority,
    PlanDistrict,
    PlanOverlapError,
    PlanRegistry,
    PlanResolutionError,
    RedistrictingPlan,
    get_default_plan_registry,
)


# ---------------------------------------------------------------------------
# Real-world fixture: Alabama 2022/2023 congressional plans
# (legislative enacted → court interim → court final/Allen v. Milligan)
# ---------------------------------------------------------------------------

AL = "01"

AL_DISTRICTS = ("1", "2", "3", "4", "5", "6", "7")


def _make_districts(plan_name: str, authority: PlanAuthority,
                    start: _dt.date, end: _dt.date | None) -> tuple[PlanDistrict, ...]:
    return tuple(
        PlanDistrict(
            state_fips=AL,
            district_type="cd",
            district_id=did,
            plan_name=plan_name,
            authority=authority,
            effective_from=start,
            effective_to=end,
        )
        for did in AL_DISTRICTS
    )


def _enacted_plan() -> RedistrictingPlan:
    start = _dt.date(2022, 1, 28)
    end = _dt.date(2023, 6, 7)  # day before court order
    return RedistrictingPlan(
        plan_name="AL_2022_CD_ENACTED",
        state_fips=AL,
        district_type="cd",
        authority=PlanAuthority.LEGISLATURE,
        effective_from=start,
        effective_to=end,
        districts=_make_districts("AL_2022_CD_ENACTED", PlanAuthority.LEGISLATURE, start, end),
    )


def _interim_plan() -> RedistrictingPlan:
    start = _dt.date(2023, 6, 8)
    end = _dt.date(2023, 10, 4)
    return RedistrictingPlan(
        plan_name="AL_2023_CD_INTERIM",
        state_fips=AL,
        district_type="cd",
        authority=PlanAuthority.COURT,
        effective_from=start,
        effective_to=end,
        districts=_make_districts("AL_2023_CD_INTERIM", PlanAuthority.COURT, start, end),
        metadata={"docket": "Allen v. Milligan", "court": "S.D. Ala."},
    )


def _final_plan() -> RedistrictingPlan:
    start = _dt.date(2023, 10, 5)
    return RedistrictingPlan(
        plan_name="AL_2023_CD_FINAL",
        state_fips=AL,
        district_type="cd",
        authority=PlanAuthority.COURT,
        effective_from=start,
        effective_to=None,  # currently active
        districts=_make_districts("AL_2023_CD_FINAL", PlanAuthority.COURT, start, None),
        metadata={"docket": "Allen v. Milligan"},
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestPlanDistrict:
    def test_covers_date_within_span(self):
        d = PlanDistrict(
            state_fips=AL, district_type="cd", district_id="7",
            plan_name="P", authority=PlanAuthority.LEGISLATURE,
            effective_from=_dt.date(2022, 1, 28),
            effective_to=_dt.date(2023, 6, 7),
        )
        assert d.covers_date(_dt.date(2022, 5, 1))
        assert d.covers_date(_dt.date(2022, 1, 28))   # inclusive lower
        assert d.covers_date(_dt.date(2023, 6, 7))    # inclusive upper

    def test_covers_date_excludes_before_and_after(self):
        d = PlanDistrict(
            state_fips=AL, district_type="cd", district_id="7",
            plan_name="P", authority=PlanAuthority.LEGISLATURE,
            effective_from=_dt.date(2022, 1, 28),
            effective_to=_dt.date(2023, 6, 7),
        )
        assert not d.covers_date(_dt.date(2022, 1, 27))
        assert not d.covers_date(_dt.date(2023, 6, 8))

    def test_open_ended_district_covers_far_future(self):
        d = PlanDistrict(
            state_fips=AL, district_type="cd", district_id="7",
            plan_name="P", authority=PlanAuthority.COURT,
            effective_from=_dt.date(2023, 10, 5),
            effective_to=None,
        )
        assert d.covers_date(_dt.date(2030, 1, 1))

    def test_inverted_dates_rejected(self):
        with pytest.raises(ValueError, match="effective_to"):
            PlanDistrict(
                state_fips=AL, district_type="cd", district_id="7",
                plan_name="P", authority=PlanAuthority.LEGISLATURE,
                effective_from=_dt.date(2023, 1, 1),
                effective_to=_dt.date(2022, 1, 1),
            )

    def test_frozen(self):
        d = PlanDistrict(
            state_fips=AL, district_type="cd", district_id="7",
            plan_name="P", authority=PlanAuthority.LEGISLATURE,
            effective_from=_dt.date(2022, 1, 28),
        )
        with pytest.raises(Exception):
            d.district_id = "8"  # frozen=True


class TestRedistrictingPlan:
    def test_district_lookup_by_id(self):
        p = _enacted_plan()
        assert p.district("7").district_id == "7"
        assert p.district("nonexistent") is None

    def test_district_metadata_consistency(self):
        with pytest.raises(ValueError, match="state_fips"):
            RedistrictingPlan(
                plan_name="P", state_fips=AL, district_type="cd",
                authority=PlanAuthority.LEGISLATURE,
                effective_from=_dt.date(2022, 1, 28),
                districts=(PlanDistrict(
                    state_fips="48",  # mismatch
                    district_type="cd", district_id="7",
                    plan_name="P", authority=PlanAuthority.LEGISLATURE,
                    effective_from=_dt.date(2022, 1, 28),
                ),),
            )

    def test_district_plan_name_consistency(self):
        with pytest.raises(ValueError, match="plan_name"):
            RedistrictingPlan(
                plan_name="P_OUTER", state_fips=AL, district_type="cd",
                authority=PlanAuthority.LEGISLATURE,
                effective_from=_dt.date(2022, 1, 28),
                districts=(PlanDistrict(
                    state_fips=AL, district_type="cd", district_id="7",
                    plan_name="P_INNER",  # mismatch
                    authority=PlanAuthority.LEGISLATURE,
                    effective_from=_dt.date(2022, 1, 28),
                ),),
            )

    def test_metadata_passes_through(self):
        p = _interim_plan()
        assert p.metadata["docket"] == "Allen v. Milligan"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestPlanRegistry:
    def _registered(self) -> PlanRegistry:
        r = PlanRegistry()
        r.register_plans([_enacted_plan(), _interim_plan(), _final_plan()])
        return r

    def test_resolves_enacted_plan(self):
        r = self._registered()
        plan = r.resolve_plan_at_date(AL, "cd", _dt.date(2022, 5, 1))
        assert plan.plan_name == "AL_2022_CD_ENACTED"
        assert plan.authority == PlanAuthority.LEGISLATURE

    def test_resolves_interim_plan(self):
        r = self._registered()
        plan = r.resolve_plan_at_date(AL, "cd", _dt.date(2023, 8, 15))
        assert plan.plan_name == "AL_2023_CD_INTERIM"
        assert plan.authority == PlanAuthority.COURT

    def test_resolves_final_plan_open_ended(self):
        r = self._registered()
        plan = r.resolve_plan_at_date(AL, "cd", _dt.date(2026, 5, 6))
        assert plan.plan_name == "AL_2023_CD_FINAL"
        assert plan.effective_to is None

    def test_resolution_at_boundary_dates(self):
        """The day a new plan takes effect resolves to the new plan."""
        r = self._registered()
        # June 7, 2023 — last day of enacted
        assert r.resolve_plan_at_date(AL, "cd", _dt.date(2023, 6, 7)).plan_name \
            == "AL_2022_CD_ENACTED"
        # June 8, 2023 — first day of interim
        assert r.resolve_plan_at_date(AL, "cd", _dt.date(2023, 6, 8)).plan_name \
            == "AL_2023_CD_INTERIM"

    def test_resolution_before_any_plan_raises(self):
        r = self._registered()
        with pytest.raises(PlanResolutionError, match="No registered plan"):
            r.resolve_plan_at_date(AL, "cd", _dt.date(2020, 1, 1))

    def test_unknown_state_raises(self):
        r = self._registered()
        with pytest.raises(PlanResolutionError):
            r.resolve_plan_at_date("99", "cd", _dt.date(2022, 5, 1))

    def test_resolve_district_at_date(self):
        r = self._registered()
        d = r.resolve_district_at_date(AL, "cd", "7", _dt.date(2023, 8, 15))
        assert d.plan_name == "AL_2023_CD_INTERIM"
        assert d.district_id == "7"

    def test_resolve_district_unknown_id_raises(self):
        r = self._registered()
        with pytest.raises(PlanResolutionError, match="contains no district"):
            r.resolve_district_at_date(AL, "cd", "99", _dt.date(2023, 8, 15))

    def test_overlap_detected_in_strict_mode(self):
        r = PlanRegistry()
        # Two court orders that technically overlap by one day (typical of
        # interim/final pair where the order isn't a clean cutover).
        a = _interim_plan()
        b = RedistrictingPlan(
            plan_name="AL_2023_CD_FINAL_OVERLAP",
            state_fips=AL, district_type="cd",
            authority=PlanAuthority.COURT,
            effective_from=_dt.date(2023, 10, 4),  # overlaps with interim's last day
            effective_to=None,
            districts=_make_districts(
                "AL_2023_CD_FINAL_OVERLAP", PlanAuthority.COURT,
                _dt.date(2023, 10, 4), None,
            ),
        )
        r.register_plans([a, b])
        with pytest.raises(PlanOverlapError, match="2 plans cover"):
            r.resolve_plan_at_date(AL, "cd", _dt.date(2023, 10, 4))

    def test_overlap_non_strict_returns_most_recent(self):
        r = PlanRegistry()
        a = _interim_plan()
        b = RedistrictingPlan(
            plan_name="AL_2023_CD_FINAL_OVERLAP",
            state_fips=AL, district_type="cd",
            authority=PlanAuthority.COURT,
            effective_from=_dt.date(2023, 10, 4),
            effective_to=None,
            districts=_make_districts(
                "AL_2023_CD_FINAL_OVERLAP", PlanAuthority.COURT,
                _dt.date(2023, 10, 4), None,
            ),
        )
        r.register_plans([a, b])
        plan = r.resolve_plan_at_date(
            AL, "cd", _dt.date(2023, 10, 4), strict=False,
        )
        assert plan.plan_name == "AL_2023_CD_FINAL_OVERLAP"

    def test_plans_for_state_returns_sorted(self):
        r = self._registered()
        plans = r.plans_for_state(AL, "cd")
        assert [p.plan_name for p in plans] == [
            "AL_2022_CD_ENACTED",
            "AL_2023_CD_INTERIM",
            "AL_2023_CD_FINAL",
        ]

    def test_plans_for_state_empty_returns_empty_list(self):
        r = PlanRegistry()
        assert r.plans_for_state(AL, "cd") == []

    def test_clear(self):
        r = self._registered()
        r.clear()
        assert r.plans_for_state(AL, "cd") == []


class TestDefaultRegistry:
    def test_default_is_singleton(self):
        a = get_default_plan_registry()
        b = get_default_plan_registry()
        assert a is b

    def test_default_is_isolated_per_test(self):
        # Each test should NOT see leftover state from other tests.
        # We clear at the start to make this explicit; the singleton is
        # process-global so production callers carry their state.
        r = get_default_plan_registry()
        r.clear()
        assert r.plans_for_state(AL, "cd") == []
