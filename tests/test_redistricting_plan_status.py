"""Tests for RedistrictingPlan.plan_status lifecycle field (SU#552).

Pure-Python tests validate the choices definition and the Alabama 2023
redistricting scenario. Django-dependent tests (field introspection,
manager queryset filtering) are skipped when Django is not installed.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

try:
    import django  # noqa: F401
    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False


PLAN_STATUS_CHOICES = [
    ("proposed", "Proposed"),
    ("enacted", "Enacted / In Effect"),
    ("challenged", "Challenged (under litigation)"),
    ("invalidated", "Invalidated by Court"),
    ("superseded", "Superseded by New Plan"),
    ("rejected", "Rejected"),
]

ACTIVE_STATUSES = ("enacted", "challenged")


# ---------------------------------------------------------------------------
# Choice definition tests (pure Python)
# ---------------------------------------------------------------------------

class TestPlanStatusChoices:
    def test_all_expected_statuses_present(self):
        keys = [k for k, _ in PLAN_STATUS_CHOICES]
        assert keys == ["proposed", "enacted", "challenged", "invalidated", "superseded", "rejected"]

    def test_max_length_sufficient(self):
        max_key_len = max(len(k) for k, _ in PLAN_STATUS_CHOICES)
        assert max_key_len <= 20

    def test_no_duplicate_keys(self):
        keys = [k for k, _ in PLAN_STATUS_CHOICES]
        assert len(keys) == len(set(keys))

    def test_active_statuses_are_valid_choices(self):
        valid = {k for k, _ in PLAN_STATUS_CHOICES}
        for s in ACTIVE_STATUSES:
            assert s in valid


# ---------------------------------------------------------------------------
# Django model field tests (requires Django)
# ---------------------------------------------------------------------------

@pytest.fixture
def _bootstrap_django():
    """Minimal Django bootstrap for model introspection."""
    import django.conf
    if not django.conf.settings.configured:
        django.conf.settings.configure(
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        )
        django.setup()


@pytest.mark.skipif(not HAS_DJANGO, reason="Django not installed")
class TestPlanStatusField:
    @pytest.fixture(autouse=True)
    def _setup_django(self, _bootstrap_django):
        pass

    def _get_field(self):
        from siege_utilities.geo.django.models.redistricting import RedistrictingPlan
        return RedistrictingPlan._meta.get_field("plan_status")

    def test_field_exists(self):
        assert self._get_field() is not None

    def test_field_default_is_enacted(self):
        assert self._get_field().default == "enacted"

    def test_field_has_db_index(self):
        assert self._get_field().db_index is True

    def test_field_max_length(self):
        assert self._get_field().max_length == 20

    def test_field_choices_match(self):
        assert list(self._get_field().choices) == PLAN_STATUS_CHOICES


@pytest.mark.skipif(not HAS_DJANGO, reason="Django not installed")
class TestManagerFiltering:
    @pytest.fixture(autouse=True)
    def _setup_django(self, _bootstrap_django):
        pass

    def test_active_statuses_constant(self):
        from siege_utilities.geo.django.models.redistricting import RedistrictingPlanManager
        assert RedistrictingPlanManager.ACTIVE_STATUSES == ("enacted", "challenged")


# ---------------------------------------------------------------------------
# Alabama 2023 scenario — end-to-end lifecycle test (pure Python)
# ---------------------------------------------------------------------------

class TestAlabamaScenario:
    """Allen v. Milligan redistricting scenario as described in SU#552.

    Uses SimpleNamespace objects to simulate plan records without a DB.
    Validates that plan_status correctly represents all four stages of
    the Alabama congressional redistricting dispute.
    """

    @pytest.fixture
    def alabama_plans(self):
        return [
            SimpleNamespace(
                plan_name="AL-Congress-2020-enacted",
                state_fips="01",
                chamber="congress",
                cycle_year=2020,
                plan_type="enacted",
                plan_status="superseded",
                effective_from=datetime.date(2022, 1, 1),
                effective_to=datetime.date(2023, 10, 5),
                court_case="",
            ),
            SimpleNamespace(
                plan_name="AL-Congress-2020-enacted-challenged",
                state_fips="01",
                chamber="congress",
                cycle_year=2020,
                plan_type="enacted",
                plan_status="invalidated",
                effective_from=datetime.date(2022, 1, 1),
                effective_to=datetime.date(2023, 10, 5),
                court_case="Allen v. Milligan",
            ),
            SimpleNamespace(
                plan_name="AL-Congress-2023-legislature-remedy",
                state_fips="01",
                chamber="congress",
                cycle_year=2020,
                plan_type="proposed",
                plan_status="rejected",
                effective_from=None,
                effective_to=None,
                court_case="Allen v. Milligan",
            ),
            SimpleNamespace(
                plan_name="AL-Congress-2023-court-VRA",
                state_fips="01",
                chamber="congress",
                cycle_year=2020,
                plan_type="court_ordered",
                plan_status="enacted",
                effective_from=datetime.date(2023, 10, 5),
                effective_to=None,
                court_case="Allen v. Milligan",
            ),
        ]

    def _simulate_for_date(self, plans, state_fips, chamber, query_date):
        """Replicate for_date() logic in pure Python."""
        candidates = [
            p for p in plans
            if p.state_fips == state_fips
            and p.chamber == chamber
            and p.plan_status in ACTIVE_STATUSES
            and p.effective_from is not None
            and p.effective_from <= query_date
            and (p.effective_to is None or p.effective_to >= query_date)
        ]
        candidates.sort(key=lambda p: p.effective_from, reverse=True)
        return candidates[0] if candidates else None

    def test_all_four_plans_have_valid_statuses(self, alabama_plans):
        valid = {k for k, _ in PLAN_STATUS_CHOICES}
        for p in alabama_plans:
            assert p.plan_status in valid, f"{p.plan_name} has invalid status {p.plan_status}"

    def test_only_court_plan_is_currently_active(self, alabama_plans):
        active = [
            p for p in alabama_plans
            if p.plan_status in ACTIVE_STATUSES and p.effective_to is None
        ]
        assert len(active) == 1
        assert active[0].plan_name == "AL-Congress-2023-court-VRA"

    def test_proposed_rejected_excluded_from_active(self, alabama_plans):
        excluded = [p for p in alabama_plans if p.plan_status not in ACTIVE_STATUSES]
        excluded_names = {p.plan_name for p in excluded}
        assert "AL-Congress-2023-legislature-remedy" in excluded_names
        assert "AL-Congress-2020-enacted" in excluded_names
        assert "AL-Congress-2020-enacted-challenged" in excluded_names

    def test_for_date_2024_returns_court_plan(self, alabama_plans):
        result = self._simulate_for_date(alabama_plans, "01", "congress", datetime.date(2024, 6, 1))
        assert result is not None
        assert result.plan_name == "AL-Congress-2023-court-VRA"

    def test_for_date_pre_redistricting_returns_none(self, alabama_plans):
        result = self._simulate_for_date(alabama_plans, "01", "congress", datetime.date(2021, 1, 1))
        assert result is None

    def test_rejected_plan_never_has_effective_dates(self, alabama_plans):
        rejected = [p for p in alabama_plans if p.plan_status == "rejected"]
        assert len(rejected) == 1
        assert rejected[0].effective_from is None
        assert rejected[0].effective_to is None

    def test_invalidated_plan_has_effective_to(self, alabama_plans):
        invalidated = [p for p in alabama_plans if p.plan_status == "invalidated"]
        assert len(invalidated) == 1
        assert invalidated[0].effective_to is not None

    def test_superseded_plan_has_effective_to(self, alabama_plans):
        superseded = [p for p in alabama_plans if p.plan_status == "superseded"]
        assert len(superseded) == 1
        assert superseded[0].effective_to is not None
